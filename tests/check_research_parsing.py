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

# Test the research tool output format - using ACTUAL functions that exist
from src.agents.research_agent import research_industry_trends, find_exit_benchmarks, format_research_output

test_data = {
    "industry": "Technology/Software",
    "location": "Pacific/Western US",
    "revenue_range": "$5M-$10M"
}

print("\n1. Testing research_industry_trends output:")
print("-" * 40)
result1 = research_industry_trends._run(query=json.dumps(test_data))
print(f"Output type: {type(result1)}")
print(f"Output length: {len(result1)}")
print(f"First 500 chars:\n{result1[:500]}")
print(f"\nContains 'Research Status:'? {('Research Status:' in result1)}")
print(f"Contains 'INDUSTRY RESEARCH RESULTS'? {('INDUSTRY RESEARCH RESULTS' in result1)}")

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

print("\n3. Testing find_exit_benchmarks:")
print("-" * 40)
# This tool expects just an industry string or dict with industry
result2 = find_exit_benchmarks._run(industry="Technology/Software")
print(f"Output type: {type(result2)}")
print(f"First 300 chars:\n{result2[:300]}")

print("\n4. Testing format_research_output:")
print("-" * 40)
# This tool expects raw research to format
raw_research = {
    "raw_content": result1  # Use output from first tool
}
result3 = format_research_output._run(raw_research=json.dumps(raw_research))
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
elif "parse" in source and "text" in source:
    print("✓ Node appears to parse text output")
else:
    print("❓ Not clear how node parses tool output")

# Find how it extracts data
print("\nChecking data extraction patterns:")
if "EBITDA multiples:" in source:
    print("✓ Node looks for 'EBITDA multiples:' pattern")
if "Revenue multiples:" in source:
    print("✓ Node looks for 'Revenue multiples:' pattern")
if "IMPROVEMENT STRATEGIES:" in source:
    print("✓ Node looks for 'IMPROVEMENT STRATEGIES:' pattern")

# Check how results are stored
print("\nChecking result storage:")
if '"structured_findings"' in source:
    print("✓ Node stores structured_findings")
if '"trends_analysis"' in source:
    print("✓ Node stores trends_analysis")
if '"benchmarks_analysis"' in source:
    print("✓ Node stores benchmarks_analysis")