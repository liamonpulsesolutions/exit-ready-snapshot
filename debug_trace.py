#!/usr/bin/env python
"""
Trace execution to find where silent error occurs
"""

print("Starting debug trace...")

try:
    import sys
    print("✓ sys imported")
    
    import os
    print("✓ os imported")
    
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("✓ path configured")
    
    from dotenv import load_dotenv
    print("✓ dotenv imported")
    
    load_dotenv()
    print("✓ env loaded")
    
    import json
    print("✓ json imported")
    
    from datetime import datetime
    print("✓ datetime imported")
    
    import pprint
    print("✓ pprint imported")
    
    print("\nTrying node imports...")
    
    from src.nodes.intake_node import intake_node
    print("✓ intake_node imported")
    
    from src.nodes.research_node import research_node
    print("✓ research_node imported")
    
    from src.nodes.scoring_node import scoring_node
    print("✓ scoring_node imported")
    
    print("\nAll imports successful!")
    
    print("\nCreating test data...")
    test_form_data = {
        "uuid": "test-trace",
        "name": "Test",
        "email": "test@test.com",
        "industry": "Technology",
        "responses": {"q1": "test"}
    }
    print("✓ test data created")
    
    print("\nCreating initial state...")
    state = {
        "uuid": "test-trace",
        "form_data": test_form_data,
        "locale": "us",
        "current_stage": "starting",
        "processing_time": {},
        "messages": ["trace started"]
    }
    print("✓ state created")
    
    print("\nTrying intake node...")
    result = intake_node(state)
    print("✓ intake node executed")
    print(f"  Current stage: {result.get('current_stage')}")
    print(f"  Has error: {bool(result.get('error'))}")
    
    if result.get('error'):
        print(f"  Error: {result['error']}")
    
    print("\n✅ Trace completed successfully!")
    
except Exception as e:
    print(f"\n❌ Exception at line {sys.exc_info()[2].tb_lineno}: {e}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()

print("\nScript finished.")