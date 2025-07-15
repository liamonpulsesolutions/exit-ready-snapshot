#!/usr/bin/env python3
"""
Simple diagnostic test for intake node.
Minimal dependencies, maximum visibility.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"Python path: {sys.path[0]}")
print(f"Current directory: {os.getcwd()}")

# Minimal test data
TEST_FORM = {
    "uuid": "simple-test-001",
    "name": "Test User",
    "email": "test@example.com",
    "industry": "Technology",
    "revenue_range": "$1M-$5M",
    "years_in_business": "5-10 years",
    "age_range": "45-54",
    "exit_timeline": "1-2 years",
    "location": "Pacific/Western US",
    "responses": {
        "q1": "I am the CEO and handle everything",
        "q2": "Less than 3 days",
        "q3": "Software 80%, Services 20%",
        "q4": "60-80%",
        "q5": "8",
        "q6": "Improved significantly",
        "q7": "My technical knowledge",
        "q8": "6",
        "q9": "Strong product and customer base",
        "q10": "9"
    }
}

def main():
    print("\n🧪 SIMPLE INTAKE NODE TEST\n")
    
    try:
        # Test imports
        print("1️⃣ Testing imports...")
        from workflow.nodes.intake import intake_node
        from workflow.state import WorkflowState
        print("✅ Imports successful\n")
        
        # Create minimal state
        print("2️⃣ Creating state...")
        state = {
            "uuid": TEST_FORM["uuid"],
            "form_data": TEST_FORM,
            "locale": "us",
            "current_stage": "starting",
            "processing_time": {},
            "messages": [],
            "error": None
        }
        print(f"✅ State created for UUID: {state['uuid']}\n")
        
        # Run intake node
        print("3️⃣ Running intake_node...")
        start = datetime.now()
        
        result = intake_node(state)
        
        elapsed = (datetime.now() - start).total_seconds()
        print(f"✅ Completed in {elapsed:.2f} seconds\n")
        
        # Check results
        print("4️⃣ Checking results...")
        
        print(f"   Stage: {result.get('current_stage')}")
        print(f"   Error: {result.get('error', 'None')}")
        
        intake_result = result.get('intake_result', {})
        if intake_result:
            print(f"   Validation: {intake_result.get('validation_status')}")
            print(f"   PII entries: {intake_result.get('pii_entries', 0)}")
            print(f"   CRM logged: {intake_result.get('crm_logged')}")
            print(f"   Responses logged: {intake_result.get('responses_logged')}")
        
        pii_mapping = result.get('pii_mapping', {})
        if pii_mapping:
            print(f"\n   PII Mapping ({len(pii_mapping)} entries):")
            for key, value in pii_mapping.items():
                print(f"     {key}: {value[:30]}...")
        
        # Save output
        output = {
            "test": "simple_intake",
            "timestamp": datetime.now().isoformat(),
            "execution_time": elapsed,
            "success": result.get('error') is None,
            "stage": result.get('current_stage'),
            "pii_entries": len(pii_mapping),
            "intake_result": intake_result
        }
        
        filename = f"simple_intake_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")
        
        if result.get('error'):
            print(f"\n❌ TEST FAILED: {result['error']}")
            return False
        else:
            print("\n✅ TEST PASSED!")
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)