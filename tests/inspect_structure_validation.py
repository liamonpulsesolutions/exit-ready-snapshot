#!/usr/bin/env python
"""
Inspect why structure validation is failing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔍 Inspecting Structure Validation Tool")
print("=" * 60)

# Look at the tool source to understand what it expects
import inspect
from src.agents.qa_agent import ValidateReportStructureTool

# Get the source code
source = inspect.getsource(ValidateReportStructureTool._run)

# Find what fields it's checking for
print("\n1️⃣ Looking for required fields in tool...")
lines = source.split('\n')
for i, line in enumerate(lines):
    if 'required_sections' in line:
        # Print context around this line
        start = max(0, i-2)
        end = min(len(lines), i+10)
        print(f"\nFound required_sections definition:")
        for j in range(start, end):
            print(f"  {lines[j]}")
        break

# Now let's test with different inputs to see what makes it pass
from src.agents.qa_agent import validate_report_structure
import json

print("\n\n2️⃣ Testing different input formats...")

# Test 1: Empty dict
test1 = {}
result1 = validate_report_structure._run(report_data=json.dumps(test1))
print(f"\nEmpty dict: {'PASS' if 'Passed' in result1 else 'FAIL'}")

# Test 2: With all expected fields (based on source inspection)
test2 = {
    'executive_summary': 'Summary text',
    'category_scores': {'test': 1},
    'category_summaries': {'test': 'summary'},
    'recommendations': 'Recommendations text',
    'next_steps': 'Next steps text'
}
result2 = validate_report_structure._run(report_data=json.dumps(test2))
print(f"With all fields: {'PASS' if 'Passed' in result2 else 'FAIL'}")

# Check what the error message says
if 'Failed' in result2:
    print(f"\nError details: {result2}")
    # Look for what's missing
    if 'Missing' in result2:
        missing_start = result2.find('Missing')
        missing_end = result2.find('\n', missing_start)
        print(f"Missing sections: {result2[missing_start:missing_end]}")

# Test 3: Try passing the string "{}" which might be happening
print("\n\n3️⃣ Testing edge cases...")
result3 = validate_report_structure._run(report_data="{}")
print(f'Empty JSON string "{{}}": {"PASS" if "Passed" in result3 else "FAIL"}')
if "No report data provided" in result3:
    print("  → This is the issue! Empty data is being passed.")

# Test what QA node is actually passing
print("\n\n4️⃣ Simulating QA node data preparation...")

# This mimics what qa_node.py does
scoring_result = {
    "category_scores": {
        "financial_performance": {"score": 7.0},
        "revenue_stability": {"score": 8.0}
    }
}
summary_result = {
    "executive_summary": "Test summary",
    "category_summaries": {"financial": "test"},
    "recommendations": "Test rec"
}

# This is what QA node creates
report_data = {
    "executive_summary": summary_result.get("executive_summary", ""),
    "category_scores": scoring_result.get("category_scores", {}),
    "category_summaries": summary_result.get("category_summaries", {}),
    "recommendations": summary_result.get("recommendations", ""),
    "next_steps": "Schedule a consultation to discuss your Exit Value Growth Plan"  # Default
}

print(f"\nQA node would send: {json.dumps(report_data, indent=2)}")
result4 = validate_report_structure._run(report_data=json.dumps(report_data))
print(f"Result: {'PASS' if 'Passed' in result4 else 'FAIL'}")

if "Failed" in result4:
    print(f"\nFull error:\n{result4}")

# Save findings
import json
from datetime import datetime

findings = {
    "empty_dict_passes": "Passed" in result1,
    "all_fields_passes": "Passed" in result2,
    "empty_json_passes": "Passed" in result3,
    "qa_format_passes": "Passed" in result4,
    "error_details": result4 if "Failed" in result4 else None
}

filename = f"output_structure_inspection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(findings, f, indent=2)

print(f"\n💾 Findings saved to: {filename}")