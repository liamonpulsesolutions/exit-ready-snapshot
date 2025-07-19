#!/usr/bin/env python3
"""
Diagnostic test to understand why QA is failing
Extracts and displays the specific QA issues from the workflow state
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from io import StringIO

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Capture output
_original_stdout = sys.stdout
_original_stderr = sys.stderr
_stdout_capture = StringIO()
_stderr_capture = StringIO()

class TeeOutput:
    def __init__(self, capture, original):
        self.capture = capture
        self.original = original
        
    def write(self, data):
        self.capture.write(data)
        self.original.write(data)
        
    def flush(self):
        self.capture.flush()
        self.original.flush()
    
    def isatty(self):
        return self.original.isatty() if hasattr(self.original, 'isatty') else False
    
    def __getattr__(self, name):
        return getattr(self.original, name)

sys.stdout = TeeOutput(_stdout_capture, _original_stdout)
sys.stderr = TeeOutput(_stderr_capture, _original_stderr)

# Test data
_test_data = {
    "test_name": "diagnose_qa_issues.py",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": []
}

# Sample form data
SAMPLE_FORM_DATA = {
    "uuid": "test-qa-diagnosis-001",
    "timestamp": "2025-07-20T00:00:00.000Z",
    "name": "Test User",
    "email": "test@example.com",
    "industry": "Manufacturing & Production",
    "years_in_business": "5-10 years",
    "revenue_range": "$10M-$25M",
    "location": "Northeast US",
    "exit_timeline": "1-2 years",
    "age_range": "55-64",
    "responses": {
        "q1": "I handle all quality control and client meetings personally",
        "q2": "3-7 days",
        "q3": "Manufacturing (60%), Services (30%), Maintenance (10%)",
        "q4": "40-60%",
        "q5": "6",
        "q6": "Stayed flat",
        "q7": "Only Tom knows our CNC systems",
        "q8": "6",
        "q9": "30-year reputation with automotive OEMs",
        "q10": "7"
    }
}

async def diagnose_qa_issues():
    """Run workflow and extract detailed QA diagnostics"""
    print("\n" + "="*80)
    print("🔍 DIAGNOSING QA ISSUES IN LANGGRAPH WORKFLOW")
    print("="*80 + "\n")
    
    try:
        # Import workflow components
        from workflow.graph import create_workflow
        from workflow.core.pii_handler import retrieve_pii_mapping
        
        print("📊 Creating workflow...")
        app = create_workflow()
        
        # Prepare initial state
        from workflow.graph import determine_locale
        initial_state = {
            "uuid": SAMPLE_FORM_DATA["uuid"],
            "form_data": SAMPLE_FORM_DATA,
            "locale": determine_locale(SAMPLE_FORM_DATA.get("location", "Other")),
            "current_stage": "intake",
            "error": None,
            "processing_time": {},
            "messages": []
        }
        
        print("🚀 Executing workflow...")
        start_time = datetime.now()
        
        # Execute workflow
        result_state = await app.ainvoke(initial_state)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ Workflow completed in {elapsed:.1f}s")
        
        # Extract QA result
        qa_result = result_state.get("qa_result", {})
        
        print("\n" + "="*60)
        print("📋 QA VALIDATION RESULTS")
        print("="*60)
        
        # Overall status
        print(f"\n🎯 Overall Status:")
        print(f"   Approved: {qa_result.get('approved', False)}")
        print(f"   Quality Score: {qa_result.get('quality_score', 0)}/10")
        print(f"   Fix Attempts: {qa_result.get('fix_attempts', 0)}")
        
        # Issues found
        issues = qa_result.get('issues', [])
        print(f"\n❌ Issues Found ({len(issues)}):")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
            
        # Warnings
        warnings = qa_result.get('warnings', [])
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for i, warning in enumerate(warnings[:10], 1):  # First 10
            print(f"   {i}. {warning}")
        
        # Quality check details
        quality_checks = qa_result.get('quality_checks', {})
        print(f"\n📊 Quality Check Scores:")
        for check_name, check_data in quality_checks.items():
            if isinstance(check_data, dict):
                score = check_data.get('quality_score', 
                        check_data.get('redundancy_score',
                        check_data.get('tone_score',
                        check_data.get('citation_score',
                        check_data.get('framing_score', 
                        check_data.get('completeness_score', 0))))))
                
                print(f"\n   {check_name}:")
                print(f"      Score: {score}/10")
                
                # Special handling for different checks
                if check_name == "scoring_consistency":
                    print(f"      Consistent: {check_data.get('is_consistent', False)}")
                    if not check_data.get('is_consistent'):
                        for issue in check_data.get('issues', []):
                            print(f"      - {issue}")
                            
                elif check_name == "content_quality":
                    print(f"      Passed: {check_data.get('passed', False)}")
                    for issue in check_data.get('issues', [])[:3]:
                        print(f"      - Issue: {issue}")
                    for warning in check_data.get('warnings', [])[:3]:
                        print(f"      - Warning: {warning}")
                        
                elif check_name == "pii_compliance":
                    print(f"      Has PII: {check_data.get('has_pii', False)}")
                    if check_data.get('has_pii'):
                        for pii in check_data.get('pii_found', []):
                            print(f"      - {pii['type']}: {pii['count']} instances")
                            
                elif check_name == "structure_validation":
                    print(f"      Passed: {check_data.get('passed', False)}")
                    for issue in check_data.get('issues', []):
                        print(f"      - {issue}")
                        
                elif check_name == "redundancy_check":
                    if check_data.get('redundant_sections'):
                        print(f"      Redundant sections: {len(check_data.get('redundant_sections', []))}")
                        
                elif check_name == "citation_verification":
                    print(f"      Issues found: {check_data.get('issues_found', 0)}")
                    if check_data.get('uncited_claims'):
                        print(f"      Uncited claims: {len(check_data.get('uncited_claims', []))}")
                        
                elif check_name == "outcome_framing":
                    print(f"      Promises found: {check_data.get('promises_found', 0)}")
                    if check_data.get('promise_phrases'):
                        for phrase in check_data.get('promise_phrases', [])[:3]:
                            print(f"      - '{phrase}'")
        
        # Calculate why not approved
        print(f"\n🔍 Approval Analysis:")
        critical_issues = [i for i in issues if "CRITICAL" in i]
        print(f"   Critical Issues: {len(critical_issues)}")
        for ci in critical_issues:
            print(f"      - {ci}")
            
        overall_score = qa_result.get('quality_score', 0)
        print(f"   Overall QA Score: {overall_score}/10 (need >= 6.0)")
        print(f"   Approval Formula: No critical issues AND score >= 6.0")
        print(f"   Result: {'APPROVED' if len(critical_issues) == 0 and overall_score >= 6.0 else 'NOT APPROVED'}")
        
        # Save results
        _test_data["results"]["qa_result"] = qa_result
        _test_data["results"]["workflow_completed"] = result_state.get("current_stage") == "completed"
        _test_data["results"]["total_time"] = elapsed
        
        # Check if we have PII mapping for debugging
        pii_mapping = retrieve_pii_mapping(SAMPLE_FORM_DATA["uuid"])
        print(f"\n🔐 PII Mapping Status: {'Found' if pii_mapping else 'Not found'}")
        if pii_mapping:
            print(f"   Entries: {len(pii_mapping)}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        _test_data["errors"].append({
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        })

def save_test_output():
    """Save test output"""
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    
    _test_data["terminal_output"] = _stdout_capture.getvalue().split('\n')
    if _stderr_capture.getvalue():
        _test_data["stderr_output"] = _stderr_capture.getvalue().split('\n')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output_diagnose_qa_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Test output saved to: {filename}")

if __name__ == "__main__":
    try:
        asyncio.run(diagnose_qa_issues())
    finally:
        save_test_output()