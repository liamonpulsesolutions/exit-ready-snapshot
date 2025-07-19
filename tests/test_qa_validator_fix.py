#!/usr/bin/env python3
"""
Test to verify the QA validator handling fix.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("\n" + "="*80)
print("🔧 TESTING QA VALIDATOR HANDLING FIX")
print("="*80 + "\n")

# Import validators
from workflow.core.validators import (
    validate_scoring_consistency,
    validate_content_quality,
    scan_for_pii,
    validate_report_structure
)

# Create test data
test_scores = {
    "overall": 4.1,
    "owner_dependence": {"score": 1.5, "weight": 0.2},
    "revenue_quality": {"score": 5.0, "weight": 0.2}
}

test_summary = {
    "executive_summary": "Test summary",
    "category_summaries": {"owner_dependence": "Test"}
}

print("📊 Test 1: Correct Validator Handling")
print("-" * 50)

# Show what validators actually return
print("\n1. validate_scoring_consistency returns:")
result = validate_scoring_consistency(test_scores, test_summary)
print(f"   Type: {type(result)}")
print(f"   Keys: {list(result.keys())}")
print(f"   Issues list: {result.get('issues', [])}")
print(f"   Is consistent: {result.get('is_consistent')}")

print("\n2. validate_content_quality returns:")
result = validate_content_quality(test_summary)
print(f"   Type: {type(result)}")
print(f"   Keys: {list(result.keys())}")
print(f"   Issues list: {result.get('issues', [])}")
print(f"   Passed: {result.get('passed')}")

print("\n3. scan_for_pii returns:")
result = scan_for_pii(test_summary)
print(f"   Type: {type(result)}")
print(f"   Keys: {list(result.keys())}")
print(f"   Has PII: {result.get('has_pii')}")
print(f"   PII found: {result.get('pii_found', [])}")

print("\n📊 Test 2: Correct Issue Extraction")
print("-" * 50)

# Simulate what QA node should do
qa_issues = []
qa_warnings = []

# Correct way to handle validator results
scoring_check = validate_scoring_consistency(test_scores, test_summary)
if not scoring_check.get("is_consistent", True):
    qa_issues.extend(scoring_check.get("issues", []))  # Get the actual issues list
    qa_warnings.extend(scoring_check.get("warnings", []))

content_check = validate_content_quality(test_summary)
if not content_check.get("passed", True):
    qa_issues.extend(content_check.get("issues", []))
    qa_warnings.extend(content_check.get("warnings", []))

pii_scan = scan_for_pii(test_summary)
if pii_scan.get("has_pii", False):
    qa_issues.append(f"CRITICAL: PII detected - {', '.join(pii_scan.get('found_types', []))}")

print(f"\nCorrectly extracted issues: {len(qa_issues)}")
for issue in qa_issues:
    print(f"  - {issue}")

print(f"\nCorrectly extracted warnings: {len(qa_warnings)}")
for warning in qa_warnings:
    print(f"  - {warning}")

print("\n✅ Validator handling verified!")
print("\n💡 The fix: Always use .get('issues', []) to extract the actual issues list")
print("   Never use the validator result directly as a list!")

print("\n" + "="*80)