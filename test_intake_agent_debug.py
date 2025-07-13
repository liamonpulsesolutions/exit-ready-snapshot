#!/usr/bin/env python
"""
Test script for debugging the Intake Agent in isolation
This will help us understand if the text return format solves the retry issue
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
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 80)
print("INTAKE AGENT DEBUG TEST")
print("=" * 80)
print(f"Debug logs will be saved to: debug_logs/")
print(f"Test started at: {datetime.now().isoformat()}")
print("=" * 80)

# Test data
test_data = {
    "uuid": "debug-test-001",
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

def test_individual_tools():
    """Test each tool individually first"""
    print("\n" + "=" * 80)
    print("TESTING INDIVIDUAL TOOLS")
    print("=" * 80)
    
    try:
        from src.agents.intake_agent import (
            validate_form_data,
            detect_and_redact_pii_tool,
            process_complete_form
        )
        
        # Test 1: Validation
        print("\n1. Testing validate_form_data tool...")
        validation_result = validate_form_data._run(json.dumps(test_data))
        print(f"Result: {validation_result[:200]}...")
        
        # Test 2: PII Detection
        print("\n2. Testing detect_and_redact_pii tool...")
        sample_text = "My name is John Doe and my email is john@example.com"
        pii_result = detect_and_redact_pii_tool._run(sample_text)
        print(f"Result: {pii_result[:200]}...")
        
        # Test 3: Complete form processing
        print("\n3. Testing process_complete_form tool...")
        complete_result = process_complete_form._run(json.dumps(test_data))
        print(f"Result: {complete_result[:500]}...")
        
        return True
        
    except Exception as e:
        print(f"ERROR in tool testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_with_crewai():
    """Test the agent within CrewAI context"""
    print("\n" + "=" * 80)
    print("TESTING AGENT WITH CREWAI")
    print("=" * 80)
    
    try:
        from crewai import Task, Crew
        from langchain_openai import ChatOpenAI
        from src.agents.intake_agent import create_intake_agent
        
        # Load prompts
        import yaml
        with open('config/prompts.yaml', 'r') as f:
            prompts = yaml.safe_load(f)
        
        # Create LLM
        print("\nCreating LLM...")
        llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=0.1,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Create agent
        print("Creating intake agent...")
        intake_agent = create_intake_agent(llm, prompts)
        print(f"Agent created with {len(intake_agent.tools)} tools")
        
        # Create task
        print("\nCreating task...")
        intake_task = Task(
            description=f"""
Process the form data provided below.

Form data: {json.dumps(test_data)}

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
            agent=intake_agent,
            expected_output="""A valid JSON object with keys: uuid, anonymized_data, pii_mapping_stored, validation_status. No additional text or explanation."""
        )
        
        # Create minimal crew
        print("\nCreating crew...")
        crew = Crew(
            agents=[intake_agent],
            tasks=[intake_task],
            verbose=True
        )
        
        # Execute
        print("\n" + "=" * 80)
        print("EXECUTING CREW - WATCH FOR RETRIES")
        print("=" * 80)
        
        start_time = datetime.now()
        result = crew.kickoff()
        end_time = datetime.now()
        
        print("\n" + "=" * 80)
        print("EXECUTION COMPLETE")
        print("=" * 80)
        print(f"Duration: {(end_time - start_time).total_seconds():.2f} seconds")
        print(f"Result type: {type(result)}")
        print(f"Result: {str(result)[:500]}...")
        
        # Check if result is JSON
        try:
            if hasattr(result, 'raw'):
                json_result = json.loads(result.raw)
                print("\n✅ Agent returned valid JSON")
                print(f"Keys: {list(json_result.keys())}")
            else:
                print("\n❌ Agent did not return expected format")
        except:
            print("\n❌ Agent output is not valid JSON")
        
        return result
        
    except Exception as e:
        print(f"\nERROR in agent testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test execution"""
    
    # Create debug directory
    os.makedirs('debug_logs', exist_ok=True)
    
    print("\nPhase 1: Testing individual tools...")
    tools_ok = test_individual_tools()
    
    if not tools_ok:
        print("\n❌ Tool tests failed. Check the errors above.")
        return
    
    print("\n✅ Individual tools working correctly")
    
    print("\nPhase 2: Testing agent with CrewAI...")
    result = test_agent_with_crewai()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    # Find debug files
    debug_dir = 'debug_logs'
    if os.path.exists(debug_dir):
        files = os.listdir(debug_dir)
        recent_files = [f for f in files if 'intake_agent' in f]
        
        if recent_files:
            print(f"\n📁 Debug files created:")
            for f in sorted(recent_files)[-2:]:  # Show last 2 files
                print(f"   - {f}")
            print(f"\n💡 Review these files for detailed execution logs")
    
    print("\n🔍 Key things to check:")
    print("1. Did the agent retry any tool calls?")
    print("2. What format did the agent return?")
    print("3. Check debug_logs/*.log for detailed execution flow")
    print("4. Check debug_logs/*_output.json for tool input/output pairs")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()