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
        # Don't setup tasks until kickoff - we need the actual inputs
        
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
    
    def get_industry_context(self, industry: str) -> str:
        """Get industry-specific context if available"""
        industry_key = industry.lower().replace(' ', '_').replace('&', 'and')
        industry_data = self.industry_prompts.get(industry_key, {})
        return industry_data.get('research_context', '')
    
    def setup_tasks(self, formatted_inputs: dict):
        """Define the task pipeline using the actual input data - called during kickoff"""
        self.tasks = []
        
        # Task 1: Intake and PII Processing (GPT-4.1 nano)
        # CRITICAL FIX: Make expected_output very specific and structured
        intake_task = Task(
            description=f"""
{self.prompts['intake_agent']['task_template']}

Process the form data provided in the inputs.

Use the process_complete_form tool to handle the complete intake workflow.

CRITICAL: You must return your output as a valid JSON object with these exact keys:
{{
  "uuid": "assessment-uuid",
  "anonymized_data": {{...}},
  "pii_mapping_stored": true,
  "validation_status": "success"
}}

Do not add any explanation text before or after the JSON.
            """,
            agent=self.agents['intake'],
            expected_output="""A valid JSON object with keys: uuid, anonymized_data, pii_mapping_stored, validation_status. No additional text or explanation."""
        )
        self.tasks.append(intake_task)
        
        # Task 2: Industry Research (GPT-4.1 mini)
        # CRITICAL FIX: Specify exact output format to prevent retries
        research_task = Task(
            description=f"""
{self.prompts['research_agent']['task_template']}

Research data for:
- Industry: {formatted_inputs.get('industry', 'Professional Services')}
- Location: {formatted_inputs.get('location', 'US')}
- Revenue Range: {formatted_inputs.get('revenue_range', '$1M-$5M')}

PROCESS:
1. Use research_industry_trends tool with the industry information provided
2. Use format_research_output to structure the findings into the required format

CRITICAL: Return only a valid JSON object with this structure:
{{
  "valuation_benchmarks": {{...}},
  "improvements": {{...}},
  "market_conditions": {{...}},
  "sources": [...]
}}

Do not add explanatory text. Return only the JSON.
            """,
            agent=self.agents['research'],
            expected_output="""A valid JSON object containing valuation_benchmarks, improvements, market_conditions, and sources. No explanatory text.""",
            context=[intake_task]
        )
        self.tasks.append(research_task)

        # Task 3: Scoring and Evaluation (GPT-4.1 mini)
        # CRITICAL FIX: Structured output expectation
        scoring_task = Task(
            description=f"""
{self.prompts['scoring_agent']['task_template']}

Score the assessment using the anonymized responses from the intake task and industry research from the research task.

For each category (owner_dependence, revenue_quality, financial_readiness, operational_resilience, growth_value):
1. Use calculate_category_score tool with the category data
2. Use aggregate_final_scores tool to combine all scores
3. Use calculate_focus_areas tool to determine priorities

Exit timeline: {formatted_inputs.get('exit_timeline', 'Unknown')}

CRITICAL: Return a valid JSON object with this exact structure:
{{
  "category_scores": {{
    "owner_dependence": {{"score": 6.5, "strengths": [...], "gaps": [...]}},
    "revenue_quality": {{"score": 7.0, "strengths": [...], "gaps": [...]}},
    ...
  }},
  "overall_score": 6.8,
  "readiness_level": "Approaching Ready",
  "focus_areas": {{...}}
}}

Return only the JSON object, no additional text.
            """,
            agent=self.agents['scoring'],
            expected_output="""A valid JSON object with category_scores, overall_score, readiness_level, and focus_areas. No explanatory text.""",
            context=[intake_task, research_task]
        )
        self.tasks.append(scoring_task)

        # Task 4: Summary and Recommendations (GPT-4.1 mini)
        # CRITICAL FIX: Detailed output structure specification
        summary_task = Task(
            description=f"""
{self.prompts['summary_agent']['task_template']}

Create comprehensive report sections using the results from previous tasks.

Business info: Industry: {formatted_inputs.get('industry', '')}, Location: {formatted_inputs.get('location', '')}, Exit Timeline: {formatted_inputs.get('exit_timeline', '')}

Use these tools in sequence:
1. create_executive_summary - for the main summary
2. generate_category_summary - for each scoring category
3. generate_recommendations - for actionable advice
4. create_industry_context - for market positioning
5. structure_final_report - to organize everything

CRITICAL: Return a valid JSON object with this structure:
{{
  "executive_summary": "Your 200-word summary here...",
  "category_summaries": {{
    "owner_dependence": "Category analysis...",
    "revenue_quality": "Category analysis...",
    ...
  }},
  "recommendations": {{
    "quick_wins": [...],
    "strategic_priorities": [...],
    "critical_focus": "..."
  }},
  "industry_context": "Market analysis...",
  "next_steps": "Clear next steps..."
}}

Return only this JSON structure, no other text.

Locale: {formatted_inputs.get('locale', 'us')}
            """,
            agent=self.agents['summary'],
            expected_output="""A valid JSON object with executive_summary, category_summaries, recommendations, industry_context, and next_steps. All text must be complete and professional. No additional formatting or explanatory text.""",
            context=[scoring_task, research_task, intake_task]
        )
        self.tasks.append(summary_task)

        # Task 5: Quality Assurance (GPT-4.1 nano)
        # CRITICAL FIX: Simple boolean output
        qa_task = Task(
            description=f"""
{self.prompts['qa_agent']['task_template']}

Validate the complete report from the summary task using your QA tools:
1. check_scoring_consistency
2. verify_content_quality  
3. scan_for_pii
4. validate_report_structure

CRITICAL: Return only a JSON object with this structure:
{{
  "approved": true,
  "quality_score": 8.5,
  "issues": [],
  "ready_for_delivery": true
}}

Return only this JSON, no explanation.
            """,
            agent=self.agents['qa'],
            expected_output="""A valid JSON object with approved (boolean), quality_score (number), issues (array), and ready_for_delivery (boolean). No explanatory text.""",
            context=[scoring_task, summary_task]
        )
        self.tasks.append(qa_task)
        
        # Task 6: PII Reinsertion and Final Personalization (GPT-4.1 nano)
        # CRITICAL FIX: Clear final output specification
        pii_reinsertion_task = Task(
            description=f"""
{self.prompts['pii_reinsertion_agent']['task_template']}

Personalize the final report using the UUID and approved content.

UUID: {formatted_inputs.get('uuid', 'unknown')}

Use process_complete_reinsertion tool with the UUID and report content from previous tasks.

CRITICAL: Return a valid JSON object with this structure:
{{
  "success": true,
  "content": "Complete personalized report with actual names...",
  "metadata": {{
    "owner_name": "Actual Name",
    "email": "actual@email.com",
    "validation": {{...}}
  }}
}}

The content field must contain the complete, personalized report text.
Return only this JSON structure.
            """,
            agent=self.agents['pii_reinsertion'],
            expected_output="""A valid JSON object with success (boolean), content (complete report text), and metadata (owner details and validation). No additional formatting.""",
            context=[qa_task, summary_task, intake_task]
        )
        self.tasks.append(pii_reinsertion_task)
    
    def kickoff(self, inputs: dict) -> dict:
        """Execute the crew pipeline"""
        print("="*60)
        print(f"CREW KICKOFF STARTED - UUID: {inputs.get('uuid')}")
        print("="*60)
        logger.info(f"Starting crew execution for UUID: {inputs.get('uuid')}")
        
        # Get industry-specific context
        print(f"Getting industry context for: {inputs.get('industry', 'Unknown')}")
        industry_context = self.get_industry_context(inputs.get('industry', ''))
        logger.info(f"Industry context loaded: {len(industry_context)} chars")
        
        # Create business info package for summary agent
        business_info = {
            "industry": inputs.get("industry"),
            "location": inputs.get("location"),
            "years_in_business": inputs.get("years_in_business"),
            "revenue_range": inputs.get("revenue_range"),
            "exit_timeline": inputs.get("exit_timeline"),
            "age_range": inputs.get("age_range")
        }
        print(f"Business info created: {business_info}")
        
        # Format inputs for the task templates with safe JSON serialization
        try:
            print("Formatting inputs...")
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
                "original_data": json.dumps(inputs)
            }
            
            print("Inputs formatted successfully")
            logger.info("Formatted inputs successfully")
            
        except Exception as e:
            print(f"Error formatting inputs: {str(e)}")
            logger.error(f"Error formatting inputs: {str(e)}")
            # Fallback to basic inputs
            formatted_inputs = {
                "uuid": inputs.get("uuid", "error"),
                "form_data": str(inputs),
                "industry": inputs.get("industry", ""),
                "location": inputs.get("location", ""),
                "locale": self.locale
            }
        
        # Setup tasks with the actual input data
        print("Setting up tasks with real data...")
        try:
            self.setup_tasks(formatted_inputs)
            print(f"{len(self.tasks)} tasks created successfully")
            logger.info(f"Created {len(self.tasks)} tasks")
        except Exception as e:
            print(f"Error setting up tasks: {str(e)}")
            logger.error(f"Error setting up tasks: {str(e)}", exc_info=True)
            return {
                "uuid": inputs.get("uuid"),
                "status": "error",
                "error": f"Task setup failed: {str(e)}",
                "locale": self.locale
            }
        
        # Create crew with tasks that have real data
        print("Creating CrewAI crew...")
        try:
            crew = Crew(
                agents=list(self.agents.values()),
                tasks=self.tasks,
                verbose=True,
                process="sequential"  # Tasks run in order
            )
            print(f"Crew created with {len(self.agents)} agents and {len(self.tasks)} tasks")
            logger.info(f"Crew created successfully")
        except Exception as e:
            print(f"Error creating crew: {str(e)}")
            logger.error(f"Error creating crew: {str(e)}", exc_info=True)
            return {
                "uuid": inputs.get("uuid"),
                "status": "error",
                "error": f"Crew creation failed: {str(e)}",
                "locale": self.locale
            }
        
        try:
            print("\n" + "="*60)
            print("STARTING CREW EXECUTION")
            print("="*60)
            logger.info("Starting crew execution...")
            
            # Cross-platform timeout handling
            import time
            import threading
            
            start_time = time.time()
            print(f"Execution started at: {time.strftime('%H:%M:%S')}")
            
            # Create a timeout mechanism using threading (Windows compatible)
            result = None
            exception = None
            
            def run_crew():
                nonlocal result, exception
                try:
                    result = crew.kickoff(inputs=formatted_inputs)
                except Exception as e:
                    exception = e
            
            # Start crew execution in a separate thread
            crew_thread = threading.Thread(target=run_crew)
            crew_thread.daemon = True
            crew_thread.start()
            
            # Wait for completion with timeout (10 minutes)
            crew_thread.join(timeout=600)  # 10 minutes
            
            if crew_thread.is_alive():
                # Timeout occurred
                print(f"\nCREW EXECUTION TIMED OUT after 10 minutes")
                logger.error("Crew execution timed out")
                return {
                    "uuid": inputs.get("uuid"),
                    "status": "error",
                    "error": "Execution timed out after 10 minutes",
                    "locale": self.locale
                }
            
            if exception:
                # Exception occurred during execution
                raise exception
            
            elapsed_time = time.time() - start_time
            print(f"\n" + "="*60)
            print(f"CREW EXECUTION COMPLETED in {elapsed_time:.1f} seconds")
            print("="*60)
            logger.info(f"Crew execution completed successfully in {elapsed_time:.1f}s")
            
        except Exception as e:
            print(f"\nCREW EXECUTION FAILED: {str(e)}")
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