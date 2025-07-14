#!/usr/bin/env python
"""Minimal debug test - only shows errors and key info"""

import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

# Simple logging - only errors and warnings
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

def test_research_only():
    """Test only the research agent that's failing"""
    print("=== TESTING RESEARCH AGENT ONLY ===")
    
    # Check API key
    api_key = os.getenv('PERPLEXITY_API_KEY')
    print(f"Perplexity API Key: {'✓ Set' if api_key else '✗ Missing'}")
    if api_key:
        print(f"Key starts with: {api_key[:10]}...")
    
    try:
        from src.agents.research_agent import research_industry_trends
        
        test_query = {
            "industry": "Professional Services",
            "location": "US",
            "revenue_range": "$1M-$5M"
        }
        
        print(f"Calling research with: {test_query}")
        result = research_industry_trends(json.dumps(test_query))
        
        print(f"✓ Research succeeded - result length: {len(result)} chars")
        
        # Try to parse the result
        try:
            parsed = json.loads(result)
            print(f"✓ Result is valid JSON with keys: {list(parsed.keys())}")
            if 'error' in parsed:
                print(f"⚠ Research returned error: {parsed['error']}")
        except:
            print("⚠ Result is not valid JSON")
            print(f"First 200 chars: {result[:200]}")
            
    except Exception as e:
        print(f"✗ Research failed: {str(e)}")
        import traceback
        print("Full error:")
        traceback.print_exc()

def test_json_helper():
    """Test JSON helper briefly"""
    print("\n=== TESTING JSON HELPER ===")
    try:
        from src.utils.json_helper import safe_parse_json
        
        # Test with empty string (common issue)
        result = safe_parse_json("", {}, "test")
        print(f"✓ Empty string handling: {result}")
        
        # Test with invalid JSON
        result = safe_parse_json("invalid", {}, "test")
        print(f"✓ Invalid JSON handling: {result}")
        
    except Exception as e:
        print(f"✗ JSON helper failed: {str(e)}")

def test_intake_only():
    """Test only the intake agent"""
    print("\n=== TESTING INTAKE AGENT ONLY ===")
    
    test_data = {
        "uuid": "test-123",
        "name": "John Doe",
        "email": "john@test.com",
        "industry": "Professional Services",
        "responses": {"q1": "Test response", "q2": "Another response"}
    }
    
    try:
        from src.agents.intake_agent import process_complete_form
        result = process_complete_form(json.dumps(test_data))
        
        print(f"✓ Intake succeeded - result length: {len(result)} chars")
        
        # Check if result is valid JSON
        try:
            parsed = json.loads(result)
            print(f"✓ Intake result is valid JSON")
            if parsed.get('pii_mapping'):
                print(f"✓ PII mapping created with {len(parsed['pii_mapping'])} entries")
        except:
            print("⚠ Intake result is not valid JSON")
            
    except Exception as e:
        print(f"✗ Intake failed: {str(e)}")

def main():
    print("MINIMAL DEBUG TEST - ONLY SHOWING ERRORS")
    print("=" * 50)
    
    # Test each component separately
    test_json_helper()
    test_intake_only() 
    test_research_only()
    
    print("\n" + "=" * 50)
    print("MINIMAL TEST COMPLETE")

if __name__ == "__main__":
    main()