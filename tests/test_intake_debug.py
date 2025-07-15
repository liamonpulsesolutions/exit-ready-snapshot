#!/usr/bin/env python3
"""
Debug test for intake node with detailed logging.
Shows exactly what's happening at each step.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from io import StringIO

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Capture output
_original_stdout = sys.stdout
_stdout_capture = StringIO()

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
        return False

sys.stdout = TeeOutput(_stdout_capture, _original_stdout)

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Test data with PII to detect
TEST_DATA = {
    "uuid": "debug-test-001",
    "timestamp": datetime.now().isoformat(),
    "name": "John Smith",
    "email": "john@techcorp.com",
    "industry": "Technology",
    "revenue_range": "$1M-$5M",
    "years_in_business": "5-10 years",
    "age_range": "45-54",
    "exit_timeline": "1-2 years",
    "location": "Pacific/Western US",
    "responses": {
        "q1": "I'm the CEO of TechCorp (phone: 555-1234). We're based in San Francisco.",
        "q2": "Less than 3 days",
        "q3": "Software 80%, Services 20%",
        "q4": "60-80%",
        "q5": "8",
        "q6": "Improved significantly", 
        "q7": "My knowledge and our IP",
        "q8": "6",
        "q9": "Strong product",
        "q10": "9"
    }
}

def test_with_debug():
    """Run intake node with debug output"""
    print("\n🔍 INTAKE NODE DEBUG TEST")
    print("="*60 + "\n")
    
    results = {
        "test": "intake_debug",
        "timestamp": datetime.now().isoformat(),
        "steps": []
    }
    
    try:
        # Step 1: Import modules
        print("STEP 1: Importing modules...")
        step_result = {"step": "imports", "status": "starting"}
        
        try:
            from workflow.nodes.intake import intake_node
            from workflow.state import WorkflowState
            from workflow.core.validators import validate_form_data
            from workflow.core.pii_handler import anonymize_form_data
            
            step_result["status"] = "success"
            step_result["modules"] = [
                "workflow.nodes.intake",
                "workflow.state", 
                "workflow.core.validators",
                "workflow.core.pii_handler"
            ]
            print("✅ All modules imported successfully\n")
        except Exception as e:
            step_result["status"] = "failed"
            step_result["error"] = str(e)
            print(f"❌ Import failed: {e}\n")
            
        results["steps"].append(step_result)
        
        # Step 2: Validate form data directly
        print("STEP 2: Testing form validation...")
        step_result = {"step": "validation", "status": "starting"}
        
        try:
            is_valid, missing, details = validate_form_data(TEST_DATA)
            step_result["status"] = "success"
            step_result["valid"] = is_valid
            step_result["missing_fields"] = missing
            step_result["details"] = details
            
            print(f"   Valid: {is_valid}")
            print(f"   Missing fields: {missing}")
            print(f"   Response count: {details.get('response_count', 0)}")
            print("✅ Validation function works\n")
        except Exception as e:
            step_result["status"] = "failed"
            step_result["error"] = str(e)
            print(f"❌ Validation failed: {e}\n")
            
        results["steps"].append(step_result)
        
        # Step 3: Test PII anonymization directly
        print("STEP 3: Testing PII anonymization...")
        step_result = {"step": "pii_anonymization", "status": "starting"}
        
        try:
            anon_data, pii_map = anonymize_form_data(TEST_DATA)
            step_result["status"] = "success"
            step_result["pii_entries"] = len(pii_map)
            step_result["pii_keys"] = list(pii_map.keys())
            
            print(f"   PII entries found: {len(pii_map)}")
            print(f"   PII keys: {list(pii_map.keys())}")
            print("✅ PII anonymization works\n")
        except Exception as e:
            step_result["status"] = "failed"
            step_result["error"] = str(e)
            print(f"❌ PII anonymization failed: {e}\n")
            
        results["steps"].append(step_result)
        
        # Step 4: Create state
        print("STEP 4: Creating workflow state...")
        step_result = {"step": "create_state", "status": "starting"}
        
        try:
            state = {
                "uuid": TEST_DATA["uuid"],
                "form_data": TEST_DATA,
                "locale": "us",
                "current_stage": "starting",
                "processing_time": {},
                "messages": [],
                "error": None,
                # Add all required fields
                "intake_result": None,
                "research_result": None,
                "scoring_result": None,
                "summary_result": None,
                "qa_result": None,
                "final_output": None,
                "pii_mapping": None,
                "anonymized_data": None,
                "industry": TEST_DATA.get("industry"),
                "location": TEST_DATA.get("location"),
                "revenue_range": TEST_DATA.get("revenue_range"),
                "exit_timeline": TEST_DATA.get("exit_timeline"),
                "years_in_business": TEST_DATA.get("years_in_business")
            }
            
            step_result["status"] = "success"
            step_result["state_keys"] = list(state.keys())
            print(f"✅ State created with {len(state)} fields\n")
        except Exception as e:
            step_result["status"] = "failed"
            step_result["error"] = str(e)
            print(f"❌ State creation failed: {e}\n")
            
        results["steps"].append(step_result)
        
        # Step 5: Run intake node
        print("STEP 5: Running intake node...")
        step_result = {"step": "intake_node", "status": "starting"}
        
        try:
            start_time = datetime.now()
            result_state = intake_node(state)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            step_result["status"] = "success"
            step_result["execution_time"] = elapsed
            step_result["current_stage"] = result_state.get("current_stage")
            step_result["has_error"] = result_state.get("error") is not None
            
            intake_result = result_state.get("intake_result", {})
            step_result["intake_result"] = {
                "validation_status": intake_result.get("validation_status"),
                "pii_entries": intake_result.get("pii_entries"),
                "crm_logged": intake_result.get("crm_logged"),
                "responses_logged": intake_result.get("responses_logged")
            }
            
            print(f"✅ Intake node completed in {elapsed:.2f}s")
            print(f"   Stage: {result_state.get('current_stage')}")
            print(f"   Validation: {intake_result.get('validation_status')}")
            print(f"   PII entries: {intake_result.get('pii_entries')}")
            
        except Exception as e:
            step_result["status"] = "failed"
            step_result["error"] = str(e)
            print(f"❌ Intake node failed: {e}")
            import traceback
            traceback.print_exc()
            
        results["steps"].append(step_result)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        results["error"] = str(e)
    
    # Save results
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for step in results["steps"]:
        status_icon = "✅" if step["status"] == "success" else "❌"
        print(f"{status_icon} {step['step']}: {step['status']}")
    
    # Save output
    results["terminal_output"] = _stdout_capture.getvalue().split('\n')
    
    filename = f"debug_intake_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Debug results saved to: {filename}")
    
    # Restore stdout
    sys.stdout = _original_stdout

if __name__ == "__main__":
    test_with_debug()