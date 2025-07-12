from crewai import Crew, Agent, Task
from langchain_openai import ChatOpenAI
import yaml
import os
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ExitReadySnapshotCrew:
    def __init__(self, locale: str = 'us'):
        """Initialize the Exit Ready Snapshot Crew"""
        self.locale = locale
        self.load_configurations()
        self.setup_llms()
        self.setup_agents()
        self.setup_tasks()
        
    def load_configurations(self):
        """Load all configuration files"""
        # Load main prompts (with locale fallback)
        prompt_file = f'config/prompts_{self.locale}.yaml'
        if not os.path.exists(prompt_file):
            prompt_file = 'config/prompts.yaml'  # Default to US
            
        with open(prompt_file, 'r') as f:
            self.prompts = yaml.safe_load(f)
            
        # Load scoring rubric
        with open('config/scoring_rubric.yaml', 'r') as f:
            self.scoring_rubric = yaml.safe_load(f)
            
        # Load industry-specific prompts
        with open('config/industry_prompts.yaml', 'r') as f:
            self.industry_prompts = yaml.safe_load(f)
            
        # Load locale terms
        with open('config/locale_terms.yaml', 'r') as f:
            self.locale_terms = yaml.safe_load(f).get(self.locale, {})
    
    def setup_llms(self):
        """Configure LLMs for different agent types"""
        # Use GPT-4.1 for main analysis agents
        self.analysis_llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0.7,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Use GPT-4.1 mini for PII-handling agents (will swap to Ollama later)
        self.pii_llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.3,  # Lower temperature for more consistent PII handling
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
    
    def setup_agents(self):
        """Initialize all agents with appropriate LLMs"""
        # Import agent creation functions
        from .agents.intake_agent import create_intake_agent
        from .agents.research_agent import create_research_agent
        from .agents.scoring_agent import create_scoring_agent
        from .agents.summary_agent import create_summary_agent
        from .agents.qa_agent import create_qa_agent
        from .agents.pii_reinsertion_agent import create_pii_reinsertion_agent
        # All agents imported
        
        self.agents = {
            'intake': create_intake_agent(self.pii_llm, self.prompts),
            'research': create_research_agent(self.analysis_llm, self.prompts),  # Uses GPT-4.1
            'scoring': create_scoring_agent(self.analysis_llm, self.prompts, self.scoring_rubric),
            'summary': create_summary_agent(self.analysis_llm, self.prompts),
            'qa': create_qa_agent(self.pii_llm, self.prompts),  # Uses mini for efficiency
            'pii_reinsertion': create_pii_reinsertion_agent(self.pii_llm, self.prompts)
        }
        
        logger.info(f"Initialized {len(self.agents)} agents for locale: {self.locale}")
    
    def get_industry_context(self, industry: str) -> str:
        """Get industry-specific context if available"""
        industry_key = industry.lower().replace(' ', '_')
        industry_data = self.industry_prompts.get(industry_key, {})
        return industry_data.get('research_context', '')
    
    def setup_tasks(self):
        """Define the task pipeline using modular templates"""
        self.tasks = []
        
        # Task 1: Intake and PII Processing
        intake_task = Task(
            description=self.prompts['intake_agent']['task_template'],
            agent=self.agents['intake'],
            expected_output="Structured JSON with anonymized data and PII mapping"
        )
        self.tasks.append(intake_task)
        
        # Task 2: Industry Research
        research_task = Task(
            description=self.prompts['research_agent']['task_template'],
            agent=self.agents['research'],
            expected_output="Industry analysis with trends and benchmarks",
            context=[intake_task]  # Uses output from intake task
        )
        self.tasks.append(research_task)

        # Task 3: Scoring and Evaluation
        scoring_task = Task(
            description=self.prompts['scoring_agent']['task_template'],
            agent=self.agents['scoring'],
            expected_output="Structured scoring with category scores and justifications",
            context=[intake_task, research_task]  # Uses outputs from both previous tasks
        )
        self.tasks.append(scoring_task)

        # Task 4: Summary and Recommendations
        summary_task = Task(
            description=self.prompts['summary_agent']['task_template'],
            agent=self.agents['summary'],
            expected_output="Complete assessment summary with recommendations",
            context=[scoring_task, research_task]  # Uses scoring and research outputs
        )
        self.tasks.append(summary_task)

        # Task 5: Quality Assurance
        qa_task = Task(
            description=self.prompts['qa_agent']['task_template'],
            agent=self.agents['qa'],
            expected_output="Quality assessment with approval status",
            context=[scoring_task, summary_task]  # Reviews scoring and summary outputs
        )
        self.tasks.append(qa_task)
        
        # Task 6: PII Reinsertion and Final Personalization
        pii_reinsertion_task = Task(
            description=self.prompts['pii_reinsertion_agent']['task_template'],
            agent=self.agents['pii_reinsertion'],
            expected_output="Complete personalized report ready for PDF generation",
            context=[qa_task, intake_task]  # Needs QA approval and original PII mapping
        )
        self.tasks.append(pii_reinsertion_task)
    
    def kickoff(self, inputs: dict) -> dict:
        """Execute the crew pipeline"""
        crew = Crew(
            agents=list(self.agents.values()),
            tasks=self.tasks,
            verbose=True,
            process="sequential"  # Tasks run in order
        )
        
        # Get industry-specific context
        industry_context = self.get_industry_context(inputs.get('industry', ''))
        
        # Format inputs for the task templates
        formatted_inputs = {
            "form_data": json.dumps(inputs),  # Convert to JSON string for tools
            "industry": inputs.get("industry"),
            "location": inputs.get("location"),
            "years_in_business": inputs.get("years_in_business"),
            "industry_specific_context": industry_context,
            "locale": self.locale,
            "locale_specific_terminology": self.locale_terms,
            "scoring_rubric": json.dumps(self.scoring_rubric),
            "anonymized_responses": json.dumps(inputs.get("responses", {})),
            "industry_research": "",  # Will be filled by research agent output
            "category_scores": "",  # Will be filled by scoring agent output
            "scoring_results": "",  # Will be filled by scoring agent output
            "summary_content": "",  # Will be filled by summary agent output
            "pii_mapping": json.dumps({"[OWNER_NAME]": inputs.get("name", ""), "[EMAIL]": inputs.get("email", "")}),
            "approved_report": "",  # Will be filled by QA agent output
            "original_data": json.dumps(inputs)
        }
        
        result = crew.kickoff(inputs=formatted_inputs)
        
        # For now, return a structured result
        # This will be replaced with actual crew output
        return {
            "uuid": inputs.get("uuid"),
            "status": "completed",
            "locale": self.locale,
            "scores": {
                "overall": 6.5,
                "owner_dependence": 5.0,
                "revenue_quality": 7.0,
                "financial_readiness": 7.5,
                "operational_resilience": 6.0,
                "growth_value": 7.0
            },
            "summary": "Assessment completed successfully",
            "recommendations": ["Focus on reducing owner dependence", "Document core processes"]
        }