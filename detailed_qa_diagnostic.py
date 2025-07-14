#!/usr/bin/env python
"""
Detailed diagnostic to find exact QA validation issues
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("🔍 DETAILED QA DIAGNOSTIC")
print("=" * 60)

# Test each QA tool individually with real pipeline data
from src.agents.qa_agent import (
    check_scoring_consistency,
    verify_content_quality,
    scan_for_pii,
    validate_report_structure
)

# 1. Test structure validation to find what's missing
print("\n1️⃣ TESTING STRUCTURE VALIDATION")
print("-" * 40)

# This is what the QA node sends
qa_node_structure = {
    "executive_summary": "Test summary",
    "category_scores": {
        "financial_performance": {"score": 7.0},
        "revenue_stability": {"score": 8.0},
        "operations_efficiency": {"score": 6.0},
        "growth_value": {"score": 7.5},
        "exit_readiness": {"score": 7.0}
    },
    "category_summaries": {
        "financial_performance": "Summary 1",
        "revenue_stability": "Summary 2", 
        "operations_efficiency": "Summary 3",
        "growth_value": "Summary 4",
        "exit_readiness": "Summary 5"
    },
    "recommendations": "Test recommendations",
    "next_steps": "Schedule a consultation"
}

result = validate_report_structure._run(report_data=json.dumps(qa_node_structure))
print(f"Result: {'PASS' if 'Passed' in result else 'FAIL'}")
print(f"Full result:\n{result}")

# 2. Test content quality to see what's failing
print("\n\n2️⃣ TESTING CONTENT QUALITY")
print("-" * 40)

content_data = {
    "summary": "Thank you for completing the Exit Ready Snapshot assessment. Your business shows strong potential.",
    "recommendations": "Focus on improving documentation and reducing owner dependence.",
    "category_summaries": {
        "financial_performance": "Your financial performance is strong with good margins."
    }
}

result = verify_content_quality._run(content_data=json.dumps(content_data))
print(f"Result: {'PASS' if 'Acceptable' in result or 'Excellent' in result else 'FAIL'}")
print(f"Full result:\n{result}")

# 3. Test PII scanner with real report content
print("\n\n3️⃣ TESTING PII SCANNER")
print("-" * 40)

# Test with content that has actual names (not placeholders)
real_content = {
    "summary": "Thank you Jennifer Martinez for completing the assessment.",
    "email_mention": "Contact jennifer@saascompany.com for more info",
    "safe_email": "Reach out to success@onpulsesolutions.com"
}

result = scan_for_pii._run(full_content=json.dumps(real_content))
print(f"Result: {'PASS' if 'Passed' in result else 'FAIL'}")
if "Failed" in result:
    print("PII FOUND - this explains the issue!")
print(f"Full result:\n{result}")

# Test with placeholders only
placeholder_content = {
    "summary": "Thank you [OWNER_NAME] for completing the assessment.",
    "location": "Your business in [LOCATION] shows potential.",
    "email": "Your email [EMAIL] has been recorded."
}

result2 = scan_for_pii._run(full_content=json.dumps(placeholder_content))
print(f"\nPlaceholder test: {'PASS' if 'Passed' in result2 else 'FAIL'}")

# 4. Find out why QA is so fast
print("\n\n4️⃣ TIMING ANALYSIS")
print("-" * 40)

import time

# Time each tool
tools_timing = {}

# Scoring consistency
start = time.time()
check_scoring_consistency._run(scoring_data=json.dumps({"scores": {}, "responses": {}}))
tools_timing["scoring_consistency"] = time.time() - start

# Content quality
start = time.time()
verify_content_quality._run(content_data=json.dumps(content_data))
tools_timing["content_quality"] = time.time() - start

# PII scan
start = time.time()
scan_for_pii._run(full_content=json.dumps(placeholder_content))
tools_timing["pii_scan"] = time.time() - start

# Structure validation
start = time.time()
validate_report_structure._run(report_data=json.dumps(qa_node_structure))
tools_timing["structure_validation"] = time.time() - start

print("Tool execution times:")
for tool, timing in tools_timing.items():
    print(f"  {tool}: {timing:.6f}s")

print(f"\nTotal tools time: {sum(tools_timing.values()):.6f}s")

# Save results
output = {
    "structure_validation": {
        "passed": "Passed" in validate_report_structure._run(report_data=json.dumps(qa_node_structure)),
        "missing_fields": []  # Will be populated based on error messages
    },
    "content_quality": {
        "passed": "Acceptable" in verify_content_quality._run(content_data=json.dumps(content_data))
    },
    "pii_detection": {
        "real_names_detected": "Failed" in scan_for_pii._run(full_content=json.dumps(real_content)),
        "placeholders_detected": "Failed" in scan_for_pii._run(full_content=json.dumps(placeholder_content))
    },
    "timing": tools_timing
}

filename = f"output_detailed_qa_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Diagnostic saved to: {filename}")