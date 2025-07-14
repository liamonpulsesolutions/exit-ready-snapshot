#!/usr/bin/env python
"""
Check how research data is being parsed
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("Checking research data parsing...")

# Test the research tool output format
from src.agents.research_agent import research_industry_trends, analyze_market_position, find_improvement_strategies

test_data = {
    "industry": "Technology/Software",
    "location": "Pacific/Western US",
    "revenue_range": "$5M-$10M"
}

print("\n1. Testing research_industry_trends output:")
print("-" * 40)
result1 = research_industry_trends._run(industry_data=json.dumps(test_data))
print(f"Output type: {type(result1)}")
print(f"Output length: {len(result1)}")
print(f"First 500 chars:\n{result1[:500]}")
print(f"\nContains 'Status:'? {('Status:' in result1)}")
print(f"Contains 'RESEARCH COMPLETE'? {('RESEARCH COMPLETE' in result1)}")

# Check if it's trying to parse as JSON
print("\n2. Checking if output is JSON:")
print("-" * 40)
try:
    parsed = json.loads(result1)
    print("✓ Output IS valid JSON")
    print(f"Keys: {list(parsed.keys())}")
except:
    print("✗ Output is NOT JSON (it's plain text)")
    # Check structure
    lines = result1.split('\n')
    print(f"Number of lines: {len(lines)}")
    print("First 5 lines:")
    for i, line in enumerate(lines[:5]):
        print(f"  {i}: {line[:80]}")

print("\n3. Testing analyze_market_position:")
print("-" * 40)
market_data = {
    "industry": "Technology/Software",
    "revenue_range": "$5M-$10M",
    "location": "Pacific/Western US",
    "responses": {}
}
result2 = analyze_market_position._run(market_data=json.dumps(market_data))
print(f"Output type: {type(result2)}")
print(f"First 300 chars:\n{result2[:300]}")

print("\n4. Testing find_improvement_strategies:")
print("-" * 40)
assessment_data = {
    "scores": {"financial_performance": 5.0, "revenue_stability": 5.5},
    "gaps": ["owner dependence", "low documentation"],
    "industry": "Technology/Software",
    "research_insights": {}
}
result3 = find_improvement_strategies._run(assessment_data=json.dumps(assessment_data))
print(f"Output type: {type(result3)}")
print(f"First 300 chars:\n{result3[:300]}")

print("\n✓ Analysis complete!")

# Now let's see how the node processes this
print("\n5. Checking node processing:")
print("-" * 40)
from src.nodes.research_node import research_node

# Look at the node code to see how it processes tool outputs
import inspect
source = inspect.getsource(research_node)
print("Looking for tool result processing in research_node...")

# Check if it's expecting JSON
if "json.loads" in source:
    print("⚠️  Node is trying to parse JSON from tools")
elif "parse_research_output" in source:
    print("⚠️  Node uses custom parser")
else:
    print("❓ Not clear how node parses tool output")

# Find how it stores results
if "industry_trends" in source:
    lines = source.split('\n')
    for i, line in enumerate(lines):
        if "industry_trends" in line and "=" in line:
            print(f"Found assignment: {line.strip()}")
            # Check surrounding lines
            if i > 0:
                print(f"  Previous: {lines[i-1].strip()}")
            if i < len(lines)-1:
                print(f"  Next: {lines[i+1].strip()}")