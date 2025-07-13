#!/usr/bin/env python
"""
Test script for debugging the Research Agent in isolation
This will help us understand if the text return format works for the research agent
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
    level=logging.INFO,  # Less verbose than DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 80)
print("RESEARCH AGENT DEBUG TEST")
print("=" * 80)
print(f"Debug logs will be saved to: debug_logs/")
print(f"Test started at: {datetime.now().isoformat()}")
print("=" * 80)

# Test data - using intake agent output format
test_data = {
    "uuid": "debug-test-002",
    "anonymized_data": {
        "uuid": "debug-test-002",
        "timestamp": datetime.now().isoformat(),
        "name": "[OWNER_NAME]",
        "email": "[EMAIL]",
        "industry": "Technology",
        "years_in_business": "5-10 years",
        "age_range": "45-54",
        "exit_timeline": "1-2 years",
        "location": "[LOCATION]",
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
    },
    "pii_mapping_stored": True,
    "validation_status": "success"
}

def test_individual_tools():
    """Test each tool individually first"""
    print("\n" + "=" * 80)
    print("TESTING INDIVIDUAL TOOLS")
    print("=" * 80)
    
    try:
        # Import the debug version
        from src.agents.research_agent import (
            research_industry_trends,
            find_exit_benchmarks,
            format_research_output
        )
        
        # Test 1: Research Industry Trends
        print("\n1. Testing research_industry_trends tool...")
        research_input = {
            "industry": "Technology",
            "location": "US",
            "revenue_range": "$1M-$5M"
        }
        trends_result = research_industry_trends._run(json.dumps(research_input))
        print(f"Result preview: {trends_result[:300]}...")
        print(f"Result length: {len(trends_result)} chars")
        
        # Test 2: Find Exit Benchmarks
        print("\n2. Testing find_exit_benchmarks tool...")
        benchmarks_result = find_exit_benchmarks._run("Technology")
        print(f"Result preview: {benchmarks_result[:300]}...")
        print(f"Result length: {len(benchmarks_result)} chars")
        
        # Test 3: Format Research Output
        print("\n3. Testing format_research_output tool...")
        # Use the output from the first tool
        format_result = format_research_output._run(trends_result)
        print(f"Result preview: {format_result[:300]}...")
        print(f"Result length: {len(format_result)} chars")
        
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
        from src.agents.research_agent import create_research_agent
        
        # Load prompts
        import yaml
        with open('config/prompts.yaml', 'r') as f:
            prompts = yaml.safe_load(f)
        
        # Create LLM (using GPT-4.1 mini for research)
        print("\nCreating LLM...")
        llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.1,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Create agent
        print("Creating research agent...")
        research_agent = create_research_agent(llm, prompts)
        print(f"Agent created with {len(research_agent.tools)} tools")
        
        # Create task - mimicking what the real crew would pass
        print("\nCreating task...")
        research_task = Task(
            description=f"""
Research industry context for the business and format the findings into structured data.

Business Information:
- Industry: {test_data['anonymized_data']['industry']}
- Location: US (from {test_data['anonymized_data']['location']})
- Revenue Range: {test_data['anonymized_data']['revenue_range']}

Your research should focus on:

SECTION 1 - VALUATION BENCHMARKS (150 words max):
1. Current revenue and EBITDA multiples for businesses this size
2. Multiple variations for recurring revenue, owner dependence, and client concentration
3. Top 2 factors causing valuation discounts

SECTION 2 - IMPROVEMENT STRATEGIES (200 words max):
Provide 3 proven improvement examples with timelines and impact

SECTION 3 - MARKET CONDITIONS (100 words max):
Current buyer priorities, average time to sell, and key trends

Process:
1. Use research_industry_trends tool with the industry information
2. Parse the response to extract key data points
3. Structure the findings into clear categories

Expected Output: Structured research data that other agents can use for scoring and recommendations.
            """,
            agent=research_agent,
            expected_output="""Structured research findings with:
- Valuation benchmarks (multiples, premiums, discounts)
- Improvement strategies (with timelines and impacts)
- Market conditions (buyer priorities, sale timelines, trends)
All data should be specific, quantified, and ready for analysis."""
        )
        
        # Create minimal crew
        print("\nCreating crew...")
        crew = Crew(
            agents=[research_agent],
            tasks=[research_task],
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
        print(f"Result preview: {str(result)[:500]}...")
        
        return result
        
    except Exception as e:
        print(f"\nERROR in agent testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def check_perplexity_api():
    """Quick check of Perplexity API availability"""
    print("\n" + "=" * 80)
    print("CHECKING PERPLEXITY API")
    print("=" * 80)
    
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if api_key:
        print(f"✓ Perplexity API Key found (starts with: {api_key[:10]}...)")
    else:
        print("✗ No Perplexity API Key found - will use fallback data")
    
    # You could add a test API call here if needed

def main():
    """Main test execution"""
    
    # Create debug directory
    os.makedirs('debug_logs', exist_ok=True)
    
    # Check API availability
    check_perplexity_api()
    
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
        recent_files = [f for f in files if 'research_agent' in f]
        
        if recent_files:
            print(f"\n📁 Debug files created:")
            for f in sorted(recent_files)[-2:]:  # Show last 2 files
                print(f"   - {f}")
            print(f"\n💡 Review these files for detailed execution logs")
    
    print("\n🔍 Key things to check:")
    print("1. Did the agent retry any tool calls?")
    print("2. What format did the agent return?")
    print("3. Did the agent successfully extract structured data from text?")
    print("4. Check debug_logs/*.log for tool input/output flow")
    print("5. Check if Perplexity API calls succeeded or used fallback")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()