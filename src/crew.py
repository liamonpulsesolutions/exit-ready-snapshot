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
            expected_output="""Structured research data including:
            - Valuation benchmarks with specific multiples and thresholds
            - Improvement examples with timelines and impacts
            - Market conditions and buyer priorities
            - All data properly formatted for scoring and summary agents""",
            context=[intake_task]
        )
        self.tasks.append(research_task)

        # Task 3: Scoring and Evaluation
        scoring_task = Task(
            description=self.prompts['scoring_agent']['task_template'],
            agent=self.agents['scoring'],
            expected_output="""Comprehensive scoring output including:
            - Detailed category scores with breakdowns
            - Specific strengths and gaps for each category
            - Industry context and benchmarks
            - Overall readiness assessment
            - Priority focus areas with ROI calculations""",
            context=[intake_task, research_task]
        )
        self.tasks.append(scoring_task)

        # Task 4: Summary and Recommendations
        summary_task = Task(
            description=self.prompts['summary_agent']['task_template'],
            agent=self.agents['summary'],
            expected_output="""Complete personalized report including:
            - 200-250 word executive summary
            - 150-200 word analysis for each category
            - Quick wins and strategic priorities
            - Industry context and market positioning
            - All content ready for client delivery""",
            context=[scoring_task, research_task, intake_task]  # Access to all previous outputs
        )
        self.tasks.append(summary_task)

        # Task 5: Quality Assurance
        qa_task = Task(
            description=self.prompts['qa_agent']['task_template'],
            agent=self.agents['qa'],
            expected_output="Quality assessment with approval status",
            context=[scoring_task, summary_task]
        )
        self.tasks.append(qa_task)
        
        # Task 6: PII Reinsertion and Final Personalization
        pii_reinsertion_task = Task(
            description=self.prompts['pii_reinsertion_agent']['task_template'],
            agent=self.agents['pii_reinsertion'],
            expected_output="Complete personalized report ready for PDF generation",
            context=[qa_task, intake_task]
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
        
        # Create business info package for summary agent
        business_info = {
            "industry": inputs.get("industry"),
            "location": inputs.get("location"),
            "years_in_business": inputs.get("years_in_business"),
            "revenue_range": inputs.get("revenue_range"),
            "exit_timeline": inputs.get("exit_timeline"),
            "age_range": inputs.get("age_range")
        }
        
        # Format inputs for the task templates
        # Format inputs for the task templates
        formatted_inputs = {
            "uuid": inputs.get("uuid"),  # Add this
            "form_data": json.dumps(inputs),
            "industry": inputs.get("industry"),
            "location": inputs.get("location"),
            "years_in_business": inputs.get("years_in_business"),
            "revenue_range": inputs.get("revenue_range"),
            "exit_timeline": inputs.get("exit_timeline"),
            "age_range": inputs.get("age_range"),  # Add this if used in prompts
            "industry_specific_context": industry_context,
            "locale": self.locale,
            "locale_specific_terminology": json.dumps(self.locale_terms),
            "scoring_rubric": json.dumps(self.scoring_rubric),
            "anonymized_responses": json.dumps(inputs.get("responses", {})),
            "business_info": json.dumps(business_info),
            "industry_research": "",
            "research_data": "",
            "category_scores": "",
            "scoring_results": "",
            "focus_areas": "",
            "summary_content": "",
            "pii_mapping": json.dumps({"[OWNER_NAME]": inputs.get("name", ""), "[EMAIL]": inputs.get("email", "")}),
            "approved_report": "",
            "original_data": json.dumps(inputs)
        }
        
        result = crew.kickoff(inputs=formatted_inputs)
        
        # Parse the final output from the PII reinsertion agent
        try:
            # The last task (PII reinsertion) should return the complete personalized report
            final_output = result.raw if hasattr(result, 'raw') else str(result)
            
            # Parse the output - it should be JSON from the PII reinsertion agent
            if isinstance(final_output, str):
                try:
                    parsed_output = json.loads(final_output)
                except:
                    # If not JSON, use the raw output
                    parsed_output = {"content": final_output}
            else:
                parsed_output = final_output
            
            # Extract structured data from the crew output
            # This assumes the crew agents properly structure their outputs
            return {
                "uuid": inputs.get("uuid"),
                "status": "completed",
                "locale": self.locale,
                "owner_name": inputs.get("name"),
                "email": inputs.get("email"),
                "company_name": parsed_output.get("company_name"),
                "industry": inputs.get("industry"),
                "location": inputs.get("location"),
                "scores": self._extract_scores(parsed_output),
                "executive_summary": self._extract_executive_summary(parsed_output),
                "category_summaries": self._extract_category_summaries(parsed_output),
                "recommendations": self._extract_recommendations(parsed_output),
                "next_steps": self._extract_next_steps(parsed_output),
                "raw_output": parsed_output  # Keep raw output for debugging
            }
        except Exception as e:
            logger.error(f"Error parsing crew output: {str(e)}")
            # Return a basic structure on error
            return {
                "uuid": inputs.get("uuid"),
                "status": "error",
                "error": str(e),
                "locale": self.locale
            }
    
    def _extract_scores(self, output: dict) -> dict:
        """Extract scores from crew output"""
        # Look for scores in various possible locations
        if "scores" in output:
            return output["scores"]
        elif "category_scores" in output:
            scores = output["category_scores"]
            # Calculate overall if not present
            if "overall" not in scores and len(scores) > 0:
                scores["overall"] = sum(scores.values()) / len(scores)
            return scores
        else:
            # Default scores if extraction fails
            return {
                "overall": 5.0,
                "owner_dependence": 5.0,
                "revenue_quality": 5.0,
                "financial_readiness": 5.0,
                "operational_resilience": 5.0,
                "growth_value": 5.0
            }
    
    def _extract_executive_summary(self, output: dict) -> str:
        """Extract executive summary from crew output"""
        return output.get("executive_summary", 
                         output.get("summary", 
                         output.get("content", "").split("Executive Summary")[-1].split("\n\n")[0] 
                         if "Executive Summary" in output.get("content", "") else ""))
    
    def _extract_category_summaries(self, output: dict) -> dict:
        """Extract category summaries from crew output"""
        if "category_summaries" in output:
            return output["category_summaries"]
        
        # Try to parse from content if structured data not available
        summaries = {}
        categories = ["owner_dependence", "revenue_quality", "financial_readiness", 
                     "operational_resilience", "growth_value"]
        
        content = output.get("content", "")
        for category in categories:
            # Simple extraction - you may need to enhance this
            summaries[category] = f"Assessment of {category.replace('_', ' ').title()}"
        
        return summaries
    
    def _extract_recommendations(self, output: dict) -> dict:
        """Extract recommendations from crew output"""
        if "recommendations" in output:
            return output["recommendations"]
        
        return {
            "quick_wins": output.get("quick_wins", []),
            "strategic_priorities": output.get("strategic_priorities", []),
            "critical_focus": output.get("critical_focus", "")
        }
    
    def _extract_next_steps(self, output: dict) -> str:
        """Extract next steps from crew output"""
        return output.get("next_steps", 
                         "Schedule a consultation to discuss your personalized Exit Value Growth Plan.")