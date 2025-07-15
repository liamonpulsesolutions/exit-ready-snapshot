#!/usr/bin/env python
"""
Simple test to identify the issue with summary node
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Starting test...")

# First, let's just try to import everything
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Environment loaded")
    
    from src.nodes.intake_node import intake_node
    print("✓ Intake node imported")
    
    from src.nodes.research_node import research_node
    print("✓ Research node imported")
    
    from src.nodes.scoring_node import scoring_node
    print("✓ Scoring node imported")
    
    from src.nodes.summary_node import summary_node
    print("✓ Summary node imported")
    
    from src.workflow import AssessmentState
    print("✓ AssessmentState imported")
    
    print("\nAll imports successful! The issue might be in the main test logic.")
    
except Exception as e:
    print(f"\n❌ Import failed: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Now let's try a minimal test
print("\nTrying minimal node execution...")

try:
    from datetime import datetime
    
    # Minimal test data
    test_state = {
        "uuid": "test-123",
        "form_data": {
            "uuid": "test-123",
            "name": "Test User",
            "email": "test@test.com",
            "industry": "Technology",
            "location": "Pacific/Western US",
            "revenue_range": "$5M-$10M",
            "exit_timeline": "1-2 years",
            "years_in_business": "5-10 years",
            "responses": {
                "q1": "I handle everything",
                "q2": "Less than 3 days",
                "q3": "Software subscriptions",
                "q4": "40-60%",
                "q5": "7",
                "q6": "Grew 10-25%",
                "q7": "Some disruption",
                "q8": "6",
                "q9": "Our AI technology",
                "q10": "8"
            }
        },
        "locale": "us",
        "current_stage": "starting",
        "processing_time": {},
        "messages": ["Test started"],
        "industry": "Technology",
        "location": "Pacific/Western US",
        "revenue_range": "$5M-$10M",
        "exit_timeline": "1-2 years",
        "years_in_business": "5-10 years"
    }
    
    print("\n1. Running intake node...")
    result = intake_node(test_state)
    print(f"   Intake complete: {result.get('current_stage')}")
    
    if result.get("error"):
        print(f"   Error: {result['error']}")
    else:
        print("   ✓ Success")
    
except Exception as e:
    print(f"\n❌ Execution failed: {str(e)}")
    import traceback
    traceback.print_exc()

print("\nTest complete!")