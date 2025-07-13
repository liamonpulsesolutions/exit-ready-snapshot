from crewai import Crew, Agent, Task
from langchain_openai import ChatOpenAI
import yaml
import os
import json
from typing import Dict, List, Optional
import logging
from .utils.json_helper import safe_parse_json

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
        # Use GPT-4.1 mini for main analysis agents (scoring and summary)
        self.analysis_llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.1,  # Very low for consistent business analysis
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Use GPT-4.1 nano for PII-handling agents (much cheaper for simple tasks)
        self.pii_llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=0.1,  # Minimal temperature for maximum consistency
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Research agent uses GPT-4.1 mini (data formatting, not complex research)
        self.research_llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.1,  # Consistent data parsing and formatting
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
            'intake': create_intake_agent(self.pii_llm, self.prompts),              # GPT-4.1 nano
            'research': create_research_agent(self.research_llm, self.prompts),     # GPT-4.1 mini
            'scoring': create_scoring_agent(self.analysis_llm, self.prompts, self.scoring_rubric),  # GPT-4.1 mini
            'summary': create_summary_agent(self.analysis_llm, self.prompts),      # GPT-4.1 mini
            'qa': create_qa_agent(self.pii_llm, self.prompts),                     # GPT-4.1 nano
            'pii_reinsertion': create_pii_reinsertion_agent(self.pii_llm, self.prompts)  # GPT-4.1 nano
        }
        
        logger.info(f"Initialized {len(self.agents)} agents for locale: {self.locale}")
        logger.info("LLM Configuration:")
        logger.info("  - Research Agent: GPT-4.1 mini (data formatting)")
        logger.info("  - Scoring Agent: GPT-4.1 mini (analysis)")
        logger.info("  - Summary Agent: GPT-4.1 mini (content generation)")
        logger.info("  - Intake Agent: GPT-4.1 nano (PII handling)")
        logger.info("  - QA Agent: GPT-4.1 nano (validation)")
        logger.info("  - PII Reinsertion Agent: GPT-4.1 nano (text replacement)")
    
    def get_industry_context(self, industry: str) -> str:
        """Get industry-specific context if available"""
        industry_key = industry.lower().replace(' ', '_').replace('&', 'and')
        industry_data = self.industry_prompts.get(industry_key, {})
        return industry_data.get('research_context', '')
    
    def setup_tasks(self):
        """Define the task pipeline using modular templates"""
        self.tasks = []
        
        # Task 1: Intake and PII Processing (GPT-4.1 nano)
        intake_task = Task(
            description=self.prompts['intake_agent']['task_template'],
            agent=self.agents['intake'],
            expected_output="Structured JSON with anonymized data and PII mapping stored"
        )
        self.tasks.append(intake_task)
        
        # Task 2: Industry Research (GPT-4.1 mini)
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

        # Task 3: Scoring and Evaluation (GPT-4.1 mini)
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

        # Task 4: Summary and Recommendations (GPT-4.1 mini)
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

        # Task 5: Quality Assurance (GPT-4.1 nano)
        qa_task = Task(
            description=self.prompts['qa_agent']['task_template'],
            agent=self.agents['qa'],
            expected_output="Quality assessment with approval status and any issues identified",
            context=[scoring_task, summary_task]
        )
        self.tasks.append(qa_task)
        
        # Task 6: PII Reinsertion and Final Personalization (GPT-4.1 nano)
        pii_reinsertion_task = Task(
            description=self.prompts['pii_reinsertion_agent']['task_template'],
            agent=self.agents['pii_reinsertion'],
            expected_output="Complete personalized report ready for PDF generation with all PII properly reinserted",
            context=[qa_task, summary_task, intake_task]  # Needs QA approval, summary content, and PII mapping
        )
        self.tasks.append(pii_reinsertion_task)
    
    def kickoff(self, inputs: dict) -> dict:
        """Execute the crew pipeline"""
        logger.info(f"Starting crew execution for UUID: {inputs.get('uuid')}")
        
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
        
        # Format inputs for the task templates with safe JSON serialization
        try:
            formatted_inputs = {
                "uuid": inputs.get("uuid", "unknown"),
                "form_data": json.dumps(inputs),
                "industry": inputs.get("industry", ""),
                "location": inputs.get("location", ""),
                "years_in_business": inputs.get("years_in_business", ""),
                "revenue_range": inputs.get("revenue_range", ""),
                "exit_timeline": inputs.get("exit_timeline", ""),
                "age_range": inputs.get("age_range", ""),
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
            
            logger.info("Formatted inputs successfully")
            
        except Exception as e:
            logger.error(f"Error formatting inputs: {str(e)}")
            # Fallback to basic inputs
            formatted_inputs = {
                "uuid": inputs.get("uuid", "error"),
                "form_data": str(inputs),
                "industry": inputs.get("industry", ""),
                "location": inputs.get("location", ""),
                "locale": self.locale
            }
        
        try:
            logger.info("Starting crew execution...")
            result = crew.kickoff(inputs=formatted_inputs)
            logger.info("Crew execution completed successfully")
            
        except Exception as e:
            logger.error(f"Crew execution failed: {str(e)}", exc_info=True)
            return {
                "uuid": inputs.get("uuid"),
                "status": "error",
                "error": str(e),
                "locale": self.locale
            }
        
        # Parse the final output from the crew
        try:
            # The result should be the output from the final PII reinsertion task
            if hasattr(result, 'raw'):
                final_output = result.raw
            elif hasattr(result, 'result'):
                final_output = result.result
            else:
                final_output = str(result)
            
            logger.info(f"Raw result type: {type(final_output)}")
            logger.info(f"Raw result preview: {str(final_output)[:200]}...")
            
            # Try to parse as JSON first
            if isinstance(final_output, str):
                try:
                    parsed_output = safe_parse_json(final_output, {}, "crew_kickoff")
                except:
                    # If not JSON, treat as plain text content
                    parsed_output = {"content": final_output}
            else:
                parsed_output = final_output
            
            # Extract structured data from the crew output
            return {
                "uuid": inputs.get("uuid"),
                "status": "completed" if parsed_output.get("success", True) else "partial",
                "locale": self.locale,
                "owner_name": inputs.get("name"),
                "email": inputs.get("email"),
                "company_name": parsed_output.get("metadata", {}).get("company_name"),
                "industry": inputs.get("industry"),
                "location": inputs.get("location"),
                "scores": self._extract_scores(parsed_output),
                "executive_summary": self._extract_executive_summary(parsed_output),
                "category_summaries": self._extract_category_summaries(parsed_output),
                "recommendations": self._extract_recommendations(parsed_output),
                "next_steps": self._extract_next_steps(parsed_output),
                "content": parsed_output.get("content", ""),
                "metadata": parsed_output.get("metadata", {}),
                "raw_output": parsed_output  # Keep raw output for debugging
            }
            
        except Exception as e:
            logger.error(f"Error parsing crew output: {str(e)}", exc_info=True)
            # Return a basic structure on error
            return {
                "uuid": inputs.get("uuid"),
                "status": "error",
                "error": f"Output parsing failed: {str(e)}",
                "locale": self.locale,
                "raw_result": str(result) if 'result' in locals() else "No result"
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
        elif "metadata" in output and "scores" in output["metadata"]:
            return output["metadata"]["scores"]
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
        # Try multiple extraction strategies
        if "executive_summary" in output:
            return output["executive_summary"]
        elif "summary" in output:
            return output["summary"]
        elif "content" in output:
            content = output["content"]
            # Try to extract from content
            if "Executive Summary" in content:
                lines = content.split("Executive Summary")
                if len(lines) > 1:
                    summary_section = lines[1].split("\n\n")[0].strip()
                    return summary_section
        
        return "Assessment completed successfully. Detailed analysis available in full report."
    
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
            category_title = category.replace('_', ' ').title()
            if category_title in content:
                # Try to extract section
                lines = content.split(category_title)
                if len(lines) > 1:
                    section = lines[1].split("\n\n")[0].strip()
                    summaries[category] = section[:300]  # Limit length
                else:
                    summaries[category] = f"Assessment of {category_title} completed"
            else:
                summaries[category] = f"Analysis of {category_title}"
        
        return summaries
    
    def _extract_recommendations(self, output: dict) -> dict:
        """Extract recommendations from crew output"""
        if "recommendations" in output:
            return output["recommendations"]
        
        return {
            "quick_wins": output.get("quick_wins", ["Schedule process documentation", "Identify delegation opportunities", "Review client contracts"]),
            "strategic_priorities": output.get("strategic_priorities", ["Reduce owner dependence", "Improve financial documentation", "Systematize operations"]),
            "critical_focus": output.get("critical_focus", "Focus on the highest-impact improvements identified in your assessment")
        }
    
    def _extract_next_steps(self, output: dict) -> str:
        """Extract next steps from crew output"""
        if "next_steps" in output:
            return output["next_steps"]
        elif "content" in output and "Next Steps" in output["content"]:
            content = output["content"]
            lines = content.split("Next Steps")
            if len(lines) > 1:
                return lines[1].split("\n\n")[0].strip()
        
        return "Schedule a consultation to discuss your personalized Exit Value Growth Plan and begin implementing the recommended improvements."