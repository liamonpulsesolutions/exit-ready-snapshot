#!/usr/bin/env python
"""
Comprehensive diagnostic to check if real data is being used vs fallbacks
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("🔍 COMPREHENSIVE PIPELINE DIAGNOSTIC")
print("=" * 60)

# Check API Keys
print("\n1️⃣ API KEY CHECK:")
print("-" * 40)
openai_key = os.getenv('OPENAI_API_KEY')
perplexity_key = os.getenv('PERPLEXITY_API_KEY')
print(f"OpenAI API Key: {'✅ Found' if openai_key else '❌ MISSING'}")
print(f"Perplexity API Key: {'✅ Found' if perplexity_key else '❌ MISSING'}")

if not perplexity_key:
    print("⚠️  WARNING: Without Perplexity key, research will use fallback data!")

# Test Research Tool Directly
print("\n2️⃣ RESEARCH TOOL TEST:")
print("-" * 40)
from src.agents.research_agent import research_industry_trends

test_input = {"industry": "Technology", "location": "US", "revenue_range": "$5M-$10M"}
result = research_industry_trends._run(query=json.dumps(test_input))

if "Fallback" in result or "fallback" in result:
    print("❌ Research is using FALLBACK data")
elif "Success" in result and len(result) > 1000:
    print("✅ Research appears to be using LIVE Perplexity data")
else:
    print("❓ Unclear if research is real or fallback")

print(f"Research output length: {len(result)} chars")
print(f"Contains 'Success': {'Yes' if 'Success' in result else 'No'}")

# Test Scoring Function Directly
print("\n3️⃣ SCORING FUNCTION TEST:")
print("-" * 40)
from src.agents.scoring_agent import score_financial_performance

test_responses = {
    "q5": "8",  # High confidence
    "q6": "Grew 10-25%",  # Good growth
    "revenue_range": "$5M-$10M",
    "years_in_business": "10"
}

score_result = score_financial_performance(test_responses, {})
print(f"Financial score: {score_result.get('score')}/10")
print(f"Scoring includes adjustments: {len(score_result.get('scoring_breakdown', {}).get('adjustments', [])) > 0}")
print(f"Strengths found: {len(score_result.get('strengths', []))}")
print(f"Gaps found: {len(score_result.get('gaps', []))}")

# Run Mini Pipeline Test
print("\n4️⃣ MINI PIPELINE TEST:")
print("-" * 40)

from src.nodes.intake_node import intake_node
from src.nodes.research_node import research_node
from src.nodes.scoring_node import scoring_node

test_form = {
    "uuid": "diagnostic-test",
    "name": "Test User",
    "email": "test@test.com",
    "industry": "Technology",
    "location": "Pacific/Western US",
    "revenue_range": "$5M-$10M",
    "years_in_business": "10-20 years",
    "exit_timeline": "1-2 years",
    "responses": {
        "q1": "I handle strategic decisions",
        "q2": "Up to 1 week",
        "q3": "SaaS 60%, Services 40%",
        "q4": "60%+",
        "q5": "8",
        "q6": "Grew 10-25%",
        "q7": "COO handles operations",
        "q8": "7",
        "q9": "Our AI technology saves 40% costs",
        "q10": "9"
    }
}

initial_state = {
    "uuid": test_form["uuid"],
    "form_data": test_form,
    "locale": "us",
    "current_stage": "starting",
    "processing_time": {},
    "messages": [],
    "industry": test_form["industry"],
    "location": test_form["location"],
    "revenue_range": test_form["revenue_range"],
    "exit_timeline": test_form["exit_timeline"],
    "years_in_business": test_form["years_in_business"]
}

# Run intake
print("\nRunning intake...")
state = intake_node(initial_state)
print(f"✅ Intake time: {state['processing_time'].get('intake', 0):.2f}s")

# Run research
print("\nRunning research...")
state = research_node(state)
research_time = state['processing_time'].get('research', 0)
print(f"✅ Research time: {research_time:.2f}s")

if research_time < 1.0:
    print("⚠️  Research was too fast - likely using cached/fallback data")

# Run scoring
print("\nRunning scoring...")
state = scoring_node(state)
scoring_time = state['processing_time'].get('scoring', 0)
print(f"✅ Scoring time: {scoring_time:.2f}s")

if scoring_time < 0.1:
    print("⚠️  Scoring was too fast - likely using defaults")

# Check scoring results
scoring_result = state.get('scoring_result', {})
print(f"\nScoring Results:")
print(f"Overall Score: {scoring_result.get('overall_score', 'MISSING')}")
print(f"Readiness Level: {scoring_result.get('readiness_level', 'MISSING')}")

# Check category scores
categories = scoring_result.get('category_scores', {})
print(f"\nCategory Scores:")
for cat, data in categories.items():
    score = data.get('score', 'N/A') if isinstance(data, dict) else data
    print(f"  {cat}: {score}")

# Analyze quality
print("\n5️⃣ QUALITY ANALYSIS:")
print("-" * 40)

# Check for default scores
scores = [data.get('score', 0) for data in categories.values() if isinstance(data, dict)]
if scores:
    avg_score = sum(scores) / len(scores)
    if all(abs(s - 5.0) < 0.5 for s in scores):
        print("❌ All scores are near 5.0 - likely using DEFAULTS")
    else:
        print(f"✅ Scores vary appropriately (avg: {avg_score:.1f})")

# Check research data usage
research_result = state.get('research_result', {})
if research_result.get('research_quality') == 'fallback':
    print("❌ Research is confirmed FALLBACK data")
elif research_result.get('research_quality') == 'live':
    print("✅ Research is confirmed LIVE data")

# Check for specific patterns in scoring
if scoring_result.get('strengths'):
    print(f"✅ Found {len(scoring_result['strengths'])} specific strengths")
if scoring_result.get('critical_gaps'):
    print(f"✅ Found {len(scoring_result['critical_gaps'])} critical gaps")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)

# Summary
issues = []
if not perplexity_key:
    issues.append("No Perplexity API key - using fallback research")
if scoring_time < 0.1:
    issues.append("Scoring too fast - may be using defaults")
if research_time < 1.0:
    issues.append("Research too fast - may be cached/fallback")

if issues:
    print("\n⚠️  ISSUES FOUND:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("\n✅ All systems appear to be working correctly!")

print("\nRecommendation: Check the detailed output above to verify data quality.")