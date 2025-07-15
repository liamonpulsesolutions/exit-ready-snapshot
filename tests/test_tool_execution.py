#!/usr/bin/env python
"""
Test to verify tools are actually executing
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("🔧 Tool Execution Test")
print("=" * 60)

# Test Research Tools Directly
print("\n1️⃣  TESTING RESEARCH TOOLS DIRECTLY")
print("-" * 40)

from src.agents.research_agent import research_industry_trends

# Check if we have the API key
api_key = os.getenv('PERPLEXITY_API_KEY')
print(f"Perplexity API Key: {'FOUND' if api_key else 'NOT FOUND'}")

# Test the research tool directly
test_input = {
    "industry": "Technology/Software",
    "location": "Pacific/Western US",
    "revenue_range": "$5M-$10M"
}

print("\nCalling research_industry_trends directly...")
try:
    result = research_industry_trends._run(
        industry_data=json.dumps(test_input)
    )
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result) if isinstance(result, str) else 'N/A'}")
    print(f"First 200 chars: {result[:200]}...")
    
    # Check if it's a fallback
    if "Failed to fetch" in result or "Error" in result:
        print("\n⚠️  FALLBACK DETECTED - Tool returned error message")
    elif "Technology/Software" in result and len(result) > 100:
        print("\n✅ Tool appears to be working")
    else:
        print("\n❓ Unclear if tool is working properly")
        
except Exception as e:
    print(f"❌ Tool execution failed: {e}")

# Test Scoring Tools Directly
print("\n\n2️⃣  TESTING SCORING TOOLS DIRECTLY")
print("-" * 40)

from src.agents.scoring_agent import calculate_category_score

test_scoring_input = {
    "category": "financial_performance",
    "responses": {
        "q5": "8",  # Financial confidence
        "q6": "Grew 10-25%",  # Revenue trend
        "years_in_business": "5-10 years",
        "revenue_range": "$5M-$10M"
    },
    "research_data": {}
}

print("\nCalling calculate_category_score directly...")
try:
    result = calculate_category_score._run(
        score_data=json.dumps(test_scoring_input)
    )
    print(f"Result type: {type(result)}")
    print(f"Result preview: {result[:300]}...")
    
    # Check if it contains expected elements
    if "SCORE:" in result and "/10" in result:
        print("\n✅ Scoring tool is working")
    else:
        print("\n⚠️  Unexpected scoring output format")
        
except Exception as e:
    print(f"❌ Tool execution failed: {e}")

# Test with missing data
print("\n\n3️⃣  TESTING FALLBACK BEHAVIOR")
print("-" * 40)

print("\nTesting scoring with empty input...")
try:
    result = calculate_category_score._run(score_data="{}")
    print(f"Empty input result: {result[:200]}...")
    if "No scoring data provided" in result or "Error" in result:
        print("✅ Proper error handling for empty input")
except Exception as e:
    print(f"Exception on empty input: {e}")

print("\nTesting scoring with invalid category...")
try:
    invalid_input = {"category": "invalid_category", "responses": {}}
    result = calculate_category_score._run(
        score_data=json.dumps(invalid_input)
    )
    print(f"Invalid category result: {result[:200]}...")
    if "not recognized" in result or "Invalid" in result:
        print("✅ Proper error handling for invalid category")
except Exception as e:
    print(f"Exception on invalid category: {e}")

print("\n✅ Tool execution test complete!")