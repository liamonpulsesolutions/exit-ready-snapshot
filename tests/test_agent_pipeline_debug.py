#!/usr/bin/env python
"""
Test script for debugging inter-agent data transfer
Tests: Intake → Research → Scoring pipeline
This will reveal if agents can pass data correctly with text-based tools
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable debug mode
os.environ['CREWAI_DEBUG'] = 'true'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 80)
print("INTER-AGENT DATA TRANSFER TEST")
print("Testing: Intake → Research → Scoring Pipeline")
print("=" * 80)
print(f"Debug logs will be saved to: debug_logs/")
print(f"Test started at: {datetime.now().isoformat()}")
print("=" * 80)

# Original form data
test_form_data = {
    "uuid": "pipeline-test-001",
    "timestamp": datetime.now().isoformat(),
    "name": "Test User",
    "email": "test@example.com",
    "industry": "Technology",
    "years_in_business": "5-10 years",
    "age_range": "45-54",
    "exit_timeline": "1-2 years",
    "location": "California",
    "revenue_range": "$1M-$5M",
    "responses": {
        "q1": "I personally handle all client relationships and sales closing",
        "q2": "Less than 3 days",
        "q3": "Software development services for healthcare companies",
        "q4": "70-80% recurring",
        "q5": "8",
        "q6": "Improved slightly",
        "q7": "My lead developer Sarah knows most systems but not client relationships",
        "q8": "6",
        "q9": "Our proprietary healthcare data integration platform that took 3 years to develop",
        "q10": "7"
    }
}

def test_full_pipeline():
    """Test the full 3-agent pipeline"""
    print("\n" + "=" * 80)
    print("TESTING 3-AGENT PIPELINE")
    print("=" * 80)
    
    try:
        from crewai import Task, Crew
        from langchain_openai import ChatOpenAI
        
        # Import debug versions of agents
        from src.agents.intake_agent import create_intake_agent
        from src.agents.research_agent import create_research_agent
        from src.agents.scoring_agent import create_scoring_agent
        
        # Load configurations
        import yaml
        with open('config/prompts.yaml', 'r') as f:
            prompts = yaml.safe_load(f)
        
        with open('config/scoring_rubric.yaml', 'r') as f:
            scoring_rubric = yaml.safe_load(f)
        
        # Create LLMs
        print("\nCreating LLMs...")
        intake_llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=0.1,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        research_llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.1,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        scoring_llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.1,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Create agents
        print("Creating agents...")
        intake_agent = create_intake_agent(intake_llm, prompts)
        research_agent = create_research_agent(research_llm, prompts)
        scoring_agent = create_scoring_agent(scoring_llm, prompts, scoring_rubric)
        
        print(f"✓ Intake agent created with {len(intake_agent.tools)} tools")
        print(f"✓ Research agent created with {len(research_agent.tools)} tools")
        print(f"✓ Scoring agent created with {len(scoring_agent.tools)} tools")
        
        # Create tasks with explicit context passing
        print("\nCreating tasks...")
        
        # Task 1: Intake
        intake_task = Task(
            description=f"""
Process the form data provided below.

Form data: {json.dumps(test_form_data)}

Use the process_complete_form tool to handle the complete intake workflow.

Return a JSON object with these keys:
- uuid
- anonymized_data
- pii_mapping_stored
- validation_status
            """,
            agent=intake_agent,
            expected_output="A valid JSON object with uuid, anonymized_data, pii_mapping_stored, and validation_status."
        )
        
        # Task 2: Research (depends on intake)
        research_task = Task(
            description="""
Research industry context using the anonymized data from the intake task.

Extract the industry, location, and revenue range from the context.
Use research_industry_trends tool to gather market data.

Structure your findings into:
- VALUATION BENCHMARKS
- IMPROVEMENT STRATEGIES
- MARKET CONDITIONS
            """,
            agent=research_agent,
            expected_output="Structured research findings with benchmarks, strategies, and conditions.",
            context=[intake_task]  # This creates the dependency
        )
        
        # Task 3: Scoring (depends on both intake and research)
        scoring_task = Task(
            description="""
Score the assessment using:
1. Anonymized responses from the intake task
2. Industry research from the research task

For each category, use calculate_category_score tool.
Then use aggregate_final_scores tool.
Finally, use calculate_focus_areas tool.

Return structured scoring results.
            """,
            agent=scoring_agent,
            expected_output="Complete scoring results with category scores, overall score, and focus areas.",
            context=[intake_task, research_task]  # Depends on both
        )
        
        # Create crew
        print("\nCreating crew with 3 agents...")
        crew = Crew(
            agents=[intake_agent, research_agent, scoring_agent],
            tasks=[intake_task, research_task, scoring_task],
            verbose=True,
            process="sequential"  # Ensure sequential execution
        )
        
        # Execute
        print("\n" + "=" * 80)
        print("EXECUTING PIPELINE - WATCH FOR DATA TRANSFER")
        print("=" * 80)
        
        start_time = datetime.now()
        result = crew.kickoff()
        end_time = datetime.now()
        
        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION COMPLETE")
        print("=" * 80)
        print(f"Total duration: {(end_time - start_time).total_seconds():.2f} seconds")
        print(f"Result type: {type(result)}")
        
        # Analyze the result
        if hasattr(result, 'raw'):
            print(f"\nFinal output preview: {str(result.raw)[:500]}...")
        else:
            print(f"\nFinal output preview: {str(result)[:500]}...")
        
        return result
        
    except Exception as e:
        print(f"\nERROR in pipeline testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_individual_agent_outputs():
    """Test what each agent outputs individually"""
    print("\n" + "=" * 80)
    print("TESTING INDIVIDUAL AGENT OUTPUTS")
    print("=" * 80)
    
    # This helps us understand what format each agent returns
    # You can add individual agent tests here if needed
    
    print("See main pipeline test above for inter-agent behavior")

def analyze_debug_logs():
    """Analyze debug logs for data transfer patterns"""
    print("\n" + "=" * 80)
    print("ANALYZING DEBUG LOGS")
    print("=" * 80)
    
    debug_dir = 'debug_logs'
    if os.path.exists(debug_dir):
        files = os.listdir(debug_dir)
        
        # Group files by agent
        intake_files = [f for f in files if 'intake_agent' in f and f.endswith('.json')]
        research_files = [f for f in files if 'research_agent' in f and f.endswith('.json')]
        scoring_files = [f for f in files if 'scoring_agent' in f and f.endswith('.json')]
        
        print(f"\nDebug files found:")
        print(f"- Intake agent: {len(intake_files)} files")
        print(f"- Research agent: {len(research_files)} files")
        print(f"- Scoring agent: {len(scoring_files)} files")
        
        # Show latest file from each agent
        for agent_files, agent_name in [(intake_files, 'Intake'), 
                                       (research_files, 'Research'), 
                                       (scoring_files, 'Scoring')]:
            if agent_files:
                latest = sorted(agent_files)[-1]
                print(f"\nLatest {agent_name} output: {latest}")
                
                # Read and show tool call count
                try:
                    with open(os.path.join(debug_dir, latest), 'r') as f:
                        data = json.load(f)
                        outputs = data.get('outputs', [])
                        print(f"  - Tool calls: {len(outputs)}")
                        
                        # Show tool names
                        tools_used = [o['tool'] for o in outputs]
                        for tool in set(tools_used):
                            count = tools_used.count(tool)
                            print(f"    • {tool}: {count} call(s)")
                except:
                    pass

def main():
    """Main test execution"""
    
    # Create debug directory
    os.makedirs('debug_logs', exist_ok=True)
    
    # Run the pipeline test
    print("\nRunning 3-agent pipeline test...")
    result = test_full_pipeline()
    
    # Analyze logs
    analyze_debug_logs()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print("\n🔍 Key things to check:")
    print("1. Did each agent successfully receive data from the previous agent?")
    print("2. Did the research agent get the anonymized data from intake?")
    print("3. Did the scoring agent get both intake data AND research findings?")
    print("4. Were there any retry loops at any stage?")
    print("5. Check the debug logs for actual data passed between agents")
    
    print("\n📁 Check these debug files for details:")
    print("- intake_agent_*_output.json - What intake produced")
    print("- research_agent_*_output.json - What research received and produced")
    print("- scoring_agent_*_output.json - What scoring received from both agents")
    
    print("\n💡 The console output above shows the real-time agent interactions")
    print("   Look for the 'context' being passed between tasks")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()