#!/usr/bin/env python3
"""
Diagnostic to understand what QA validation is actually checking and why it fails.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

print("\n" + "="*80)
print("🔍 QA VALIDATION LOGIC DIAGNOSTIC")
print("="*80 + "\n")

# Create a mock state that mimics what QA receives
mock_state = {
    "uuid": "test-qa-validation",
    "scoring_result": {
        "scores": {
            "overall": 4.1,
            "owner_dependence": 1.5,
            "revenue_quality": 5.0,
            "financial_readiness": 5.0,
            "operational_resilience": 4.5,
            "growth_value": 5.1
        },
        "readiness_level": "Needs Work",
        "focus_areas": {
            "primary": {"category": "owner_dependence", "score": 1.5}
        }
    },
    "summary_result": {
        "executive_summary": "With your planned exit timeline of 1-2 years, your current readiness score of 4.1/10 places your business at a 'Needs Work' level. You will see significant improvements by focusing on operational independence.",
        "category_summaries": {
            "owner_dependence": "A 1.5/10 score indicates heavy reliance on you. Businesses typically see 15-25% value increase when implementing delegation strategies.",
            "revenue_quality": "A 5.0/10 score signals moderate quality. Companies often achieve higher multiples with improved contracts.",
            "financial_readiness": "Your 5.0/10 score indicates moderate preparedness. You will benefit from systematic improvements.",
            "operational_resilience": "Your 4.5/10 score shows foundational capabilities. Businesses typically see 10-20% value increase with improvements.",
            "growth_value": "Your 5.1/10 score signals moderate potential. Focus on strengthening your value proposition."
        },
        "recommendations": "QUICK WINS (Next 30 Days)\n• Map owner-dependent functions - you will reduce transition risks\n• Delegate one key relationship - this will improve buyer confidence\n\nSTRATEGIC PRIORITIES (3-6 Months)\n• Develop management depth chart - businesses typically see 15-25% value improvement\n• Document all processes - companies often achieve 10-20% efficiency gains",
        "next_steps": "IMMEDIATE ACTIONS (This Week)\n□ Map all daily tasks to identify dependencies\n□ List top 3 tasks that can be delegated\n□ Schedule team meeting to communicate changes"
    }
}

try:
    # Import QA validation functions
    from workflow.core.validators import (
        validate_scoring_consistency,
        validate_content_quality,
        scan_for_pii,
        validate_report_structure
    )
    
    print("📊 Test 1: Scoring Consistency Check")
    print("-" * 50)
    
    consistency_issues = validate_scoring_consistency(
        mock_state["scoring_result"], 
        mock_state["summary_result"]
    )
    print(f"Issues found: {len(consistency_issues)}")
    for issue in consistency_issues:
        print(f"  - {issue}")
    
    print("\n📊 Test 2: Content Quality Check")
    print("-" * 50)
    
    quality_issues = validate_content_quality(mock_state["summary_result"])
    print(f"Issues found: {len(quality_issues)}")
    for issue in quality_issues:
        print(f"  - {issue}")
    
    print("\n📊 Test 3: PII Scan")
    print("-" * 50)
    
    pii_found = scan_for_pii(mock_state["summary_result"])
    print(f"PII items found: {len(pii_found)}")
    for item in pii_found:
        print(f"  - {item}")
    
    print("\n📊 Test 4: Report Structure")
    print("-" * 50)
    
    structure_issues = validate_report_structure(mock_state["summary_result"])
    print(f"Issues found: {len(structure_issues)}")
    for issue in structure_issues:
        print(f"  - {issue}")
    
    # Test promise language detection
    print("\n📊 Test 5: Promise Language Detection")
    print("-" * 50)
    
    import re
    promise_patterns = [
        r'\bwill\s+increase\b',
        r'\bwill\s+improve\b', 
        r'\bwill\s+see\b',
        r'\bwill\s+benefit\b',
        r'\bwill\s+reduce\b',
        r'\byou\s+will\b'
    ]
    
    full_text = json.dumps(mock_state["summary_result"])
    promises_found = []
    
    for pattern in promise_patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            promises_found.extend(matches)
    
    print(f"Promise phrases found: {len(promises_found)}")
    for promise in set(promises_found):
        print(f"  - '{promise}'")
    
    # Test outcome framing
    print("\n📊 Test 6: Outcome Framing Check")
    print("-" * 50)
    
    outcome_patterns = [
        r'typically\s+see',
        r'often\s+achieve',
        r'companies\s+typically',
        r'businesses\s+typically',
        r'could\s+increase',
        r'may\s+improve'
    ]
    
    outcome_found = []
    for pattern in outcome_patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            outcome_found.extend(matches)
    
    print(f"Outcome phrases found: {len(outcome_found)}")
    for outcome in set(outcome_found):
        print(f"  - '{outcome}'")
    
    print("\n💡 ANALYSIS:")
    print("-" * 50)
    
    total_issues = (len(consistency_issues) + len(quality_issues) + 
                   len(pii_found) + len(structure_issues))
    
    print(f"Total validation issues: {total_issues}")
    print(f"Promise language violations: {len(promises_found)}")
    print(f"Outcome framing compliance: {len(outcome_found)} phrases")
    
    if promises_found:
        print("\n⚠️  CRITICAL: Promise language detected!")
        print("This is likely why QA keeps failing - it can't remove all 'will' statements")
    
except Exception as e:
    print(f"\n❌ Error during diagnostic: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)