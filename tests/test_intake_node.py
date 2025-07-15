#!/usr/bin/env python3
"""
Test script for the intake node in LangGraph workflow.
Validates all intake functionality including:
- Form validation
- PII detection and redaction
- PII mapping storage
- CRM logging
- Response logging
"""

import os
import sys
import json
import logging
from datetime import datetime
from io import StringIO
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Capture all output using TeeOutput pattern
_original_stdout = sys.stdout
_original_stderr = sys.stderr
_stdout_capture = StringIO()
_stderr_capture = StringIO()

class TeeOutput:
    """Write to both capture and original output"""
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

# Start capturing
sys.stdout = TeeOutput(_stdout_capture, _original_stdout)
sys.stderr = TeeOutput(_stderr_capture, _original_stderr)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Store all test data
_test_data = {
    "test_name": "test_intake_node.py",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": [],
    "assertions": []
}

def log_result(key, value):
    """Log a result to be saved"""
    _test_data["results"][key] = value

def log_assertion(description, passed, details=None):
    """Log an assertion result"""
    assertion = {
        "description": description,
        "passed": passed,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        assertion["details"] = details
    _test_data["assertions"].append(assertion)
    
    # Print result
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {description}")
    if details and not passed:
        print(f"   Details: {details}")

# Sample form data - comprehensive test case
SAMPLE_FORM_DATA = {
    "uuid": "test-intake-node-001",
    "timestamp": datetime.now().isoformat(),
    "name": "John Smith",
    "email": "john.smith@techcorp.com",
    "industry": "Professional Services",
    "revenue_range": "$1M-$5M",
    "years_in_business": "10-20 years",
    "age_range": "55-64",
    "exit_timeline": "1-2 years",
    "location": "Pacific/Western US",
    "responses": {
        "q1": "I am the CEO and founder of TechCorp Solutions. I handle all client meetings, oversee product development, and make final decisions on all major contracts. My phone number is 555-123-4567.",
        "q2": "Less than 3 days - I can only be away for short periods",
        "q3": "Consulting services generate 60% of revenue, our SaaS platform brings in 30%, and training workshops account for 10%",
        "q4": "20-40% - We have some recurring revenue from our SaaS subscriptions",
        "q5": "7 - Most clients stay with us for several years",
        "q6": "Improved slightly - We've added two new major clients this year",
        "q7": "My personal relationships with key clients and deep technical knowledge of our proprietary platform",
        "q8": "4 - We have basic procedures but they're mostly in my head",
        "q9": "Long-term client relationships, specialized expertise in fintech integration, and our location in San Francisco gives us access to talent",
        "q10": "8 - I'm very satisfied with the business but ready to retire"
    }
}

def test_intake_node():
    """Test the intake node functionality"""
    print("\n" + "="*80)
    print("🧪 TESTING INTAKE NODE")
    print("="*80 + "\n")
    
    try:
        # Import after environment setup
        from workflow.nodes.intake import intake_node
        from workflow.state import WorkflowState
        
        log_result("imports_successful", True)
        print("✅ Successfully imported intake_node and WorkflowState")
        
        # Create initial state
        initial_state = {
            "uuid": SAMPLE_FORM_DATA["uuid"],
            "form_data": SAMPLE_FORM_DATA,
            "locale": "us",
            "current_stage": "starting",
            "processing_time": {},
            "messages": ["Test started"],
            "industry": SAMPLE_FORM_DATA.get("industry"),
            "location": SAMPLE_FORM_DATA.get("location"),
            "revenue_range": SAMPLE_FORM_DATA.get("revenue_range"),
            "exit_timeline": SAMPLE_FORM_DATA.get("exit_timeline"),
            "years_in_business": SAMPLE_FORM_DATA.get("years_in_business"),
            # Initialize empty results
            "intake_result": None,
            "research_result": None,
            "scoring_result": None,
            "summary_result": None,
            "qa_result": None,
            "final_output": None,
            "pii_mapping": None,
            "anonymized_data": None,
            "error": None
        }
        
        log_result("initial_state", initial_state)
        print(f"\n📋 Created initial state for UUID: {initial_state['uuid']}")
        
        # Execute intake node
        print("\n🚀 Executing intake_node...")
        start_time = datetime.now()
        
        result_state = intake_node(initial_state)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_result("execution_time", execution_time)
        log_result("result_state", result_state)
        
        print(f"\n⏱️  Execution completed in {execution_time:.2f} seconds")
        
        # Validate results
        print("\n🔍 Validating results...")
        
        # 1. Check stage updated
        log_assertion(
            "Stage updated to 'intake'",
            result_state.get("current_stage") == "intake",
            {"actual": result_state.get("current_stage"), "expected": "intake"}
        )
        
        # 2. Check intake_result exists
        intake_result = result_state.get("intake_result")
        log_assertion(
            "intake_result populated",
            intake_result is not None,
            {"has_result": intake_result is not None}
        )
        
        # 3. Check validation passed
        if intake_result:
            log_assertion(
                "Validation status is success",
                intake_result.get("validation_status") == "success",
                {"status": intake_result.get("validation_status")}
            )
            
            # 4. Check PII mapping created
            pii_mapping = result_state.get("pii_mapping")
            log_assertion(
                "PII mapping created",
                pii_mapping is not None and len(pii_mapping) > 0,
                {"pii_entries": len(pii_mapping) if pii_mapping else 0}
            )
            
            # 5. Check expected PII entries
            if pii_mapping:
                expected_pii_keys = ["[OWNER_NAME]", "[EMAIL]", "[UUID]"]
                for key in expected_pii_keys:
                    log_assertion(
                        f"PII mapping contains {key}",
                        key in pii_mapping,
                        {"found": key in pii_mapping, "value": pii_mapping.get(key, "NOT FOUND")}
                    )
                
                # Check for phone number detection
                phone_detected = any("PHONE" in k for k in pii_mapping.keys())
                log_assertion(
                    "Phone number detected in responses",
                    phone_detected,
                    {"pii_keys": list(pii_mapping.keys())}
                )
            
            # 6. Check anonymized data
            anonymized_data = result_state.get("anonymized_data")
            log_assertion(
                "Anonymized data created",
                anonymized_data is not None,
                {"has_data": anonymized_data is not None}
            )
            
            if anonymized_data:
                # Check PII is redacted
                log_assertion(
                    "Name is anonymized",
                    anonymized_data.get("name") == "[OWNER_NAME]",
                    {"actual": anonymized_data.get("name")}
                )
                
                log_assertion(
                    "Email is anonymized",
                    anonymized_data.get("email") == "[EMAIL]",
                    {"actual": anonymized_data.get("email")}
                )
                
                # Check responses are anonymized
                anon_responses = anonymized_data.get("responses", {})
                q1_response = anon_responses.get("q1", "")
                log_assertion(
                    "Phone number redacted from Q1",
                    "555-123-4567" not in q1_response and "[PHONE" in q1_response,
                    {"contains_original": "555-123-4567" in q1_response}
                )
            
            # 7. Check logging flags
            log_assertion(
                "CRM logged successfully",
                intake_result.get("crm_logged") == True,
                {"logged": intake_result.get("crm_logged")}
            )
            
            log_assertion(
                "Responses logged successfully",
                intake_result.get("responses_logged") == True,
                {"logged": intake_result.get("responses_logged")}
            )
            
            # 8. Check processing time recorded
            log_assertion(
                "Processing time recorded",
                "intake" in result_state.get("processing_time", {}),
                {"time": result_state.get("processing_time", {}).get("intake")}
            )
        
        # 9. Check no errors
        log_assertion(
            "No errors occurred",
            result_state.get("error") is None,
            {"error": result_state.get("error")}
        )
        
        # Summary
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        total_assertions = len(_test_data["assertions"])
        passed_assertions = sum(1 for a in _test_data["assertions"] if a["passed"])
        
        print(f"\nTotal assertions: {total_assertions}")
        print(f"Passed: {passed_assertions}")
        print(f"Failed: {total_assertions - passed_assertions}")
        print(f"Success rate: {(passed_assertions/total_assertions)*100:.1f}%")
        
        if passed_assertions == total_assertions:
            print("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
        
        # Log final summary
        log_result("test_summary", {
            "total_assertions": total_assertions,
            "passed": passed_assertions,
            "failed": total_assertions - passed_assertions,
            "success_rate": (passed_assertions/total_assertions)*100
        })
        
    except Exception as e:
        print(f"\n❌ ERROR during test execution: {str(e)}")
        import traceback
        error_details = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        _test_data["errors"].append(error_details)
        print(traceback.format_exc())


def save_test_output():
    """Save all captured output to JSON"""
    # Restore original stdout/stderr
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    
    # Add captured output
    _test_data["terminal_output"] = _stdout_capture.getvalue().split('\n')
    if _stderr_capture.getvalue():
        _test_data["stderr_output"] = _stderr_capture.getvalue().split('\n')
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output_test_intake_node_{timestamp}.json"
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete test output saved to: {filename}")
    
    # Also create a summary file
    summary = {
        "test": "intake_node",
        "timestamp": _test_data["timestamp"],
        "execution_time": _test_data["results"].get("execution_time"),
        "assertions": {
            "total": len(_test_data["assertions"]),
            "passed": sum(1 for a in _test_data["assertions"] if a["passed"]),
            "failed": sum(1 for a in _test_data["assertions"] if not a["passed"])
        },
        "errors": len(_test_data["errors"]),
        "key_results": {
            "pii_entries": len(_test_data["results"].get("result_state", {}).get("pii_mapping", {})),
            "stage": _test_data["results"].get("result_state", {}).get("current_stage"),
            "validation_status": _test_data["results"].get("result_state", {}).get("intake_result", {}).get("validation_status")
        }
    }
    
    summary_filename = f"summary_test_intake_node_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Test summary saved to: {summary_filename}")


if __name__ == "__main__":
    try:
        test_intake_node()
    finally:
        save_test_output()