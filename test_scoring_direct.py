#!/usr/bin/env python
"""
Direct test of scoring functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("Testing scoring functionality directly...")

# Test 1: Import and call scoring function
print("\n1. Testing scoring function import...")
try:
    from src.agents.scoring_agent import score_financial_performance
    print("✓ score_financial_performance imported")
    
    # Test with sample data
    test_responses = {
        "q5": "8",  # High confidence
        "q6": "Grew 10-25%",
        "years_in_business": "5-10 years",
        "revenue_range": "$5M-$10M"
    }
    
    result = score_financial_performance(test_responses, {})
    print(f"✓ Function executed, score: {result.get('score', 'N/A')}/10")
    
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Check research functionality
print("\n2. Testing research (checking for API key)...")
api_key = os.getenv('PERPLEXITY_API_KEY')
print(f"Perplexity API key: {'Found' if api_key else 'NOT FOUND'}")

if not api_key:
    print("⚠️  Research will use fallback data without API key")

# Test 3: Run a minimal scoring flow
print("\n3. Testing minimal scoring flow...")
try:
    from src.nodes.scoring_node import scoring_node
    
    minimal_state = {
        "uuid": "test",
        "anonymized_data": {
            "responses": {
                "q1": "I handle everything",
                "q2": "Less than 3 days",
                "q3": "Services 100%",
                "q4": "20-40%",
                "q5": "6",
                "q6": "Stayed flat",
                "q7": "Major disruption",
                "q8": "3",
                "q9": "Good customer service",
                "q10": "5"
            },
            "years_in_business": "5-10 years",
            "revenue_range": "$1M-$5M"
        },
        "research_result": {
            "industry_trends": {},
            "benchmarks": {},
            "strategies": {}
        },
        "processing_time": {},
        "messages": [],
        "current_stage": "scoring"
    }
    
    result = scoring_node(minimal_state)
    
    scoring_result = result.get("scoring_result", {})
    overall = scoring_result.get("overall_results", {})
    
    print(f"✓ Scoring complete")
    print(f"  Overall score: {overall.get('overall_score', 'N/A')}")
    print(f"  Readiness: {overall.get('readiness_level', 'N/A')}")
    
    # Check if we got real scores or defaults
    if overall.get('overall_score') == 5.0:
        print("  ⚠️  Score is exactly 5.0 (possible default)")
    
    # Show category scores
    categories = scoring_result.get("category_scores", {})
    if categories:
        print("  Category scores:")
        for cat, data in categories.items():
            score = data.get('score', 'N/A') if isinstance(data, dict) else data
            print(f"    - {cat}: {score}")
    
except Exception as e:
    print(f"✗ Error in scoring flow: {e}")
    import traceback
    traceback.print_exc()

print("\n✓ Test complete!")