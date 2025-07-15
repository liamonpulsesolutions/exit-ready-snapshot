#!/usr/bin/env python
"""
Direct test of research functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("Testing research functionality...")

# Check API key
api_key = os.getenv('PERPLEXITY_API_KEY')
print(f"\nPerplexity API key: {'FOUND' if api_key else 'NOT FOUND'}")
if api_key:
    print(f"  Key length: {len(api_key)} characters")
    print(f"  First 4 chars: {api_key[:4]}...")

# Test research tool
print("\n1. Testing research tool directly...")
try:
    from src.agents.research_agent import research_industry_trends
    import json
    
    test_data = {
        "industry": "Technology/Software",
        "location": "Pacific/Western US",
        "revenue_range": "$5M-$10M"
    }
    
    result = research_industry_trends._run(industry_data=json.dumps(test_data))
    
    print(f"✓ Tool executed")
    print(f"  Result type: {type(result)}")
    print(f"  Result length: {len(result)}")
    
    # Check if it's an error/fallback
    if "Failed to fetch" in result or "Error" in result:
        print("  ⚠️  Got fallback/error response")
        print(f"  Message: {result[:200]}")
    elif "live" in result.lower() or "market" in result.lower():
        print("  ✓ Appears to be real research data")
    else:
        print("  ❓ Unclear if real data or fallback")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test research node
print("\n2. Testing research node...")
try:
    from src.nodes.research_node import research_node
    
    test_state = {
        "uuid": "test-research",
        "anonymized_data": {
            "industry": "Technology/Software",
            "location": "Pacific/Western US", 
            "revenue_range": "$5M-$10M",
            "years_in_business": "5-10 years"
        },
        "intake_result": {
            "validation_status": "valid"
        },
        "processing_time": {},
        "messages": [],
        "current_stage": "research"
    }
    
    result = research_node(test_state)
    
    research_result = result.get("research_result", {})
    print(f"✓ Research node executed")
    print(f"  Keys in result: {list(research_result.keys())}")
    
    # Check each component
    trends = research_result.get("industry_trends", {})
    print(f"  Industry trends: {type(trends).__name__}, {'empty' if not trends else f'{len(str(trends))} chars'}")
    
    benchmarks = research_result.get("benchmarks", {})
    print(f"  Benchmarks: {type(benchmarks).__name__}, {'empty' if not benchmarks else 'has data'}")
    
    strategies = research_result.get("strategies", {})
    print(f"  Strategies: {type(strategies).__name__}, {'empty' if not strategies else 'has data'}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n✓ Test complete!")