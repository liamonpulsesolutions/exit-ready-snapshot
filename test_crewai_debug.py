#!/usr/bin/env python
"""Clean debug test script with proper syntax"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment first
load_dotenv()

# Enhanced logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"debug_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_environment():
    """Test environment setup"""
    logger.info("=== Environment Check ===")
    
    required_vars = ['OPENAI_API_KEY', 'PERPLEXITY_API_KEY', 'CREWAI_API_KEY']
    for var in required_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✓ {var}: Set (length: {len(value)})")
        else:
            logger.warning(f"✗ {var}: Not set")
    
    # Test imports
    logger.info("Testing imports...")
    try:
        import crewai
        logger.info(f"✓ CrewAI version: {crewai.__version__}")
    except Exception as e:
        logger.error(f"✗ CrewAI import error: {e}")
    
    try:
        from langchain_openai import ChatOpenAI
        logger.info("✓ LangChain OpenAI imported")
    except Exception as e:
        logger.error(f"✗ LangChain import error: {e}")

def test_json_parsing():
    """Test the JSON helper utility"""
    try:
        from src.utils.json_helper import safe_parse_json
        
        logger.info("=== Testing JSON Helper ===")
        
        # Test valid JSON
        valid_json = '{"test": "value"}'
        result = safe_parse_json(valid_json, {}, "test")
        logger.info(f"Valid JSON result: {result}")
        
        # Test empty string
        result = safe_parse_json("", {}, "test")
        logger.info(f"Empty string result: {result}")
        
        # Test invalid JSON
        result = safe_parse_json("invalid json", {}, "test")
        logger.info(f"Invalid JSON result: {result}")
        
    except Exception as e:
        logger.error(f"JSON helper test failed: {e}")

def test_individual_tools():
    """Test individual agent tools"""
    logger.info("=== Testing Individual Tools ===")
    
    # Test data
    test_form_data = {
        "uuid": "tool-test-123",
        "name": "Test User",
        "email": "test@example.com",
        "industry": "Professional Services",
        "years_in_business": "10-20 years",
        "age_range": "55-64",
        "exit_timeline": "1-2 years",
        "location": "Pacific/Western US",
        "revenue_range": "$1M-$5M",
        "responses": {
            "q1": "I handle all client meetings",
            "q2": "Less than 3 days",
            "q3": "Consulting 80%, Training 20%",
            "q4": "40-60%",
            "q5": "6",
            "q6": "Stayed flat",
            "q7": "Senior consultant with client relationships",
            "q8": "4",
            "q9": "Specialized industry knowledge",
            "q10": "7"
        }
    }
    
    # Test intake agent tool
    logger.info("Testing intake agent tool...")
    try:
        from src.agents.intake_agent import process_complete_form
        result = process_complete_form(json.dumps(test_form_data))
        logger.info(f"Intake tool result length: {len(result)} chars")
        
        # Try to parse result
        from src.utils.json_helper import safe_parse_json
        result_data = safe_parse_json(result, {}, "test_intake")
        if result_data.get('pii_mapping'):
            logger.info(f"PII mapping created: {list(result_data['pii_mapping'].keys())}")
        
    except Exception as e:
        logger.error(f"Intake tool error: {str(e)}", exc_info=True)
    
    # Test research agent tool
    logger.info("Testing research agent tool...")
    try:
        from src.agents.research_agent import research_industry_trends
        research_query = {
            "industry": "Professional Services",
            "location": "US",
            "revenue_range": "$1M-$5M"
        }
        result = research_industry_trends(json.dumps(research_query))
        logger.info(f"Research tool result length: {len(result)} chars")
        
    except Exception as e:
        logger.error(f"Research tool error: {str(e)}", exc_info=True)

def test_crew_execution():
    """Test full crew execution"""
    logger.info("=== Testing Full Crew ===")
    
    test_data = {
        "uuid": "crew-test-123",
        "timestamp": datetime.now().isoformat(),
        "name": "Test User",
        "email": "test@example.com",
        "industry": "Professional Services",
        "years_in_business": "10-20 years",
        "age_range": "55-64",
        "exit_timeline": "1-2 years",
        "location": "Pacific/Western US",
        "revenue_range": "$1M-$5M",
        "responses": {
            "q1": "I handle all final client presentations personally",
            "q2": "Less than 3 days",
            "q3": "Monthly retainer clients 70%, project work 30%",
            "q4": "60-80%",
            "q5": "7",
            "q6": "Improved slightly",
            "q7": "Senior consultant with technical knowledge",
            "q8": "5",
            "q9": "Exclusive partnerships with software vendors",
            "q10": "8"
        }
    }
    
    try:
        # Initialize crew
        logger.info("Initializing crew...")
        from src.crew import ExitReadySnapshotCrew
        crew = ExitReadySnapshotCrew(locale='us')
        logger.info("Crew initialized successfully")
        
        # Execute
        logger.info("Starting crew execution...")
        result = crew.kickoff(inputs=test_data)
        logger.info("Crew execution completed")
        
        logger.info(f"Result type: {type(result)}")
        if isinstance(result, dict):
            logger.info(f"Result keys: {list(result.keys())}")
            logger.info(f"Status: {result.get('status', 'unknown')}")
            if 'error' in result:
                logger.error(f"Crew returned error: {result['error']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Crew execution failed: {str(e)}", exc_info=True)
        return {"error": str(e)}

def main():
    """Main test function"""
    logger.info("=== DEBUG TEST SESSION STARTED ===")
    
    try:
        # Test environment
        test_environment()
        
        # Test JSON parsing
        test_json_parsing()
        
        # Test individual tools
        test_individual_tools()
        
        # Test full crew
        print("\n" + "="*50)
        print("STARTING FULL CREW TEST")
        print("="*50)
        
        result = test_crew_execution()
        
        print("\n" + "="*50)
        print("FINAL RESULT:")
        print("="*50)
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(str(result))
        
    except Exception as e:
        logger.error(f"Test session failed: {str(e)}", exc_info=True)
        print(f"ERROR: {str(e)}")
    finally:
        logger.info("=== DEBUG TEST SESSION ENDED ===")

if __name__ == "__main__":
    main()