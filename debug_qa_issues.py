#!/usr/bin/env python
"""
Debug why QA is finding PII and why it's so fast
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("🔍 DEBUGGING QA ISSUES")
print("=" * 60)

# Run a minimal test to see what PII is being detected
from src.agents.qa_agent import scan_for_pii

# Test with sample content that should NOT have PII
test_content = {
    "executive_summary": "Thank you [OWNER_NAME] for completing the assessment. Your business in [LOCATION] shows strong potential.",
    "recommendations": "As [OWNER_NAME], you should focus on improving documentation.",
    "test_email": "Contact us at success@onpulsesolutions.com"  # This should be OK
}

print("\n1️⃣ Testing PII Scanner with anonymized content...")
result = scan_for_pii._run(full_content=json.dumps(test_content))
print(f"Result preview: {result[:500]}...")

# Check if it's detecting our placeholders as PII
if "Failed" in result:
    print("\n❌ PII Scanner is incorrectly failing on anonymized content!")
    
    # Test what it considers PII
    test_cases = [
        ("[OWNER_NAME]", "placeholder"),
        ("John Smith", "real name"),
        ("test@example.com", "email"),
        ("success@onpulsesolutions.com", "company email"),
        ("Pacific/Western US", "location")
    ]
    
    print("\n2️⃣ Testing individual patterns...")
    for test_text, desc in test_cases:
        result = scan_for_pii._run(full_content=test_text)
        status = "FAIL" if "Failed" in result else "PASS"
        print(f"   {test_text:<30} ({desc:<15}): {status}")

# Now let's check why QA is so fast
print("\n3️⃣ Checking QA timing...")

# Run QA node with minimal state
from src.nodes.qa_node import qa_node

minimal_state = {
    "uuid": "debug-qa",
    "scoring_result": {
        "category_scores": {
            "financial_performance": {"score": 7.0},
            "revenue_stability": {"score": 8.0}
        },
        "overall_score": 7.5,
        "readiness_level": "Market Ready"
    },
    "summary_result": {
        "executive_summary": "Test summary with [OWNER_NAME]",
        "recommendations": "Test recommendations",
        "category_summaries": {
            "financial_performance": "Test category summary"
        },
        "final_report": "Complete report text"
    },
    "anonymized_data": {
        "responses": {"q1": "test", "q2": "test"}
    },
    "processing_time": {},
    "messages": []
}

import time
start = time.time()
result_state = qa_node(minimal_state)
end = time.time()

print(f"\nQA execution time: {end - start:.4f}s")
qa_result = result_state.get("qa_result", {})
print(f"QA approved: {qa_result.get('approved')}")
print(f"Issues found: {qa_result.get('issues_found', [])}")

# Check if tools are being called
print("\n4️⃣ Checking tool execution...")

# Monkey patch to trace tool calls
tool_calls = []
original_run_methods = {}

for tool_name in ['check_scoring_consistency', 'verify_content_quality', 'scan_for_pii', 'validate_report_structure']:
    module = __import__('src.agents.qa_agent', fromlist=[tool_name])
    tool = getattr(module, tool_name)
    original_run_methods[tool_name] = tool._run
    
    def make_wrapper(name):
        def wrapper(*args, **kwargs):
            tool_calls.append(name)
            print(f"   ✓ {name} called")
            return original_run_methods[name](*args, **kwargs)
        return wrapper
    
    tool._run = make_wrapper(tool_name)

# Run QA again with tracing
print("\nRunning QA with tool tracing...")
qa_node(minimal_state)

print(f"\nTools called: {len(tool_calls)}")
for tool in tool_calls:
    print(f"   - {tool}")

# Save debug output
output = {
    "pii_test_failed": "Failed" in result,
    "qa_execution_time": end - start,
    "tool_calls": tool_calls,
    "issues": qa_result.get('issues_found', [])
}

# Check report structure validation
print("\n5️⃣ Testing Report Structure Validation...")
from src.agents.qa_agent import validate_report_structure

test_report = {
    "executive_summary": "Test executive summary",
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
    "next_steps": "Test next steps"
}

structure_result = validate_report_structure._run(report_data=json.dumps(test_report))
print(f"Structure validation result: {'PASS' if 'Passed' in structure_result else 'FAIL'}")
print(f"Result preview: {structure_result[:300]}...")

# Test with missing sections
print("\nTesting with missing 'next_steps'...")
incomplete_report = test_report.copy()
del incomplete_report["next_steps"]
structure_result2 = validate_report_structure._run(report_data=json.dumps(incomplete_report))
print(f"Result: {'PASS' if 'Passed' in structure_result2 else 'FAIL'}")

output["structure_validation_test"] = {
    "complete_report": "Passed" in structure_result,
    "incomplete_report": "Passed" in structure_result2
}

filename = f"output_qa_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Debug output saved to: {filename}")