#!/usr/bin/env python
"""
Test the intake node in isolation
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Test data
test_form_data = {
    "uuid": "test-intake-123",
    "timestamp": datetime.now().isoformat(),
    "name": "John Smith",
    "email": "john@example.com",
    "industry": "Technology",
    "years_in_business": "10-20 years",
    "age_range": "55-64",
    "exit_timeline": "1-2 years",
    "location": "Pacific/Western US",
    "revenue_range": "$1M-$5M",
    "responses": {
        "q1": "I handle all client meetings and final approvals on projects",
        "q2": "Less than 3 days",
        "q3": "Consulting services 60%, Training workshops 40%",
        "q4": "20-40%",
        "q5": "7",
        "q6": "Improved slightly",
        "q7": "Client relationships and technical knowledge of our main service",
        "q8": "4",
        "q9": "Long-term client relationships and specialized expertise in our niche",
        "q10": "8"
    }
}

print("🧪 Testing Intake Node")
print("=" * 60)

try:
    # Import the intake node
    from src.nodes.intake_node import intake_node
    from src.workflow import AssessmentState
    
    print("✅ Intake node imported successfully")
    
    # Create initial state
    initial_state = {
        "uuid": test_form_data["uuid"],
        "form_data": test_form_data,
        "locale": "us",
        "current_stage": "starting",
        "processing_time": {},
        "messages": ["Test started"],
        # Business context
        "industry": test_form_data.get("industry"),
        "location": test_form_data.get("location"),
        "revenue_range": test_form_data.get("revenue_range"),
        "exit_timeline": test_form_data.get("exit_timeline"),
        "years_in_business": test_form_data.get("years_in_business")
    }
    
    print(f"\n📋 Test Data:")
    print(f"   UUID: {test_form_data['uuid']}")
    print(f"   Name: {test_form_data['name']}")
    print(f"   Industry: {test_form_data['industry']}")
    print(f"   Responses: {len(test_form_data['responses'])} questions")
    
    print("\n🚀 Running intake node...")
    
    # Run the node
    result_state = intake_node(initial_state)
    
    print("\n✅ Intake node completed successfully!")
    
    # Check results
    intake_result = result_state.get("intake_result", {})
    
    print(f"\n📊 Results:")
    print(f"   Validation: {intake_result.get('validation_status')}")
    print(f"   PII entries: {intake_result.get('pii_entries')}")
    print(f"   PII stored: {intake_result.get('pii_mapping_stored')}")
    print(f"   CRM logged: {intake_result.get('crm_logged')}")
    print(f"   Responses logged: {intake_result.get('responses_logged')}")
    print(f"   Company detected: {intake_result.get('company_detected')}")
    
    # Check anonymized data
    anonymized = result_state.get("anonymized_data", {})
    print(f"\n🔒 Anonymization Check:")
    print(f"   Name: {anonymized.get('name')} (was: {test_form_data['name']})")
    print(f"   Email: {anonymized.get('email')} (was: {test_form_data['email']})")
    
    # Check PII mapping
    pii_mapping = result_state.get("pii_mapping", {})
    print(f"\n🗺️ PII Mapping ({len(pii_mapping)} entries):")
    for key, value in list(pii_mapping.items())[:5]:  # Show first 5
        print(f"   {key}: {value}")
    
    # Check processing time
    print(f"\n⏱️ Processing time: {result_state['processing_time'].get('intake', 0):.2f}s")
    
    # Show messages
    print(f"\n📝 Messages:")
    for msg in result_state.get("messages", [])[-3:]:  # Last 3 messages
        print(f"   - {msg}")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")