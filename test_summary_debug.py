#!/usr/bin/env python
"""
Debug version of summary test to identify import issues
"""

import sys
import os

print("🔍 Starting debug test...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
print(f"Python path: {sys.path[0]}")

# Test environment
print("\n1. Testing environment variables...")
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
print(f"   OpenAI API key: {'Found' if api_key else 'NOT FOUND'}")

# Test imports one by one
print("\n2. Testing imports...")

try:
    from datetime import datetime
    print("   ✓ datetime imported")
except Exception as e:
    print(f"   ✗ datetime import failed: {e}")

try:
    import json
    print("   ✓ json imported")
except Exception as e:
    print(f"   ✗ json import failed: {e}")

try:
    from src.workflow import AssessmentState
    print("   ✓ AssessmentState imported")
except Exception as e:
    print(f"   ✗ AssessmentState import failed: {e}")

try:
    from src.nodes.intake_node import intake_node
    print("   ✓ intake_node imported")
except Exception as e:
    print(f"   ✗ intake_node import failed: {e}")

try:
    from src.nodes.research_node import research_node
    print("   ✓ research_node imported")
except Exception as e:
    print(f"   ✗ research_node import failed: {e}")

try:
    from src.nodes.scoring_node import scoring_node
    print("   ✓ scoring_node imported")
except Exception as e:
    print(f"   ✗ scoring_node import failed: {e}")

try:
    from src.nodes.summary_node import summary_node
    print("   ✓ summary_node imported")
except Exception as e:
    print(f"   ✗ summary_node import failed: {e}")
    
    # Try to import the summary agent directly
    print("\n   Debugging summary_node import...")
    try:
        from src.agents.summary_agent import generate_category_summary
        print("   ✓ summary agent tools imported")
    except Exception as e2:
        print(f"   ✗ summary agent import failed: {e2}")

print("\n3. Checking file existence...")
files_to_check = [
    "src/nodes/intake_node.py",
    "src/nodes/research_node.py", 
    "src/nodes/scoring_node.py",
    "src/nodes/summary_node.py",
    "src/agents/summary_agent.py",
    "src/workflow.py"
]

for file in files_to_check:
    exists = os.path.exists(file)
    print(f"   {file}: {'EXISTS' if exists else 'NOT FOUND'}")

print("\n✅ Debug test complete!")
print("\nIf all imports succeeded, run: python test_summary_node.py")
print("If imports failed, check the error messages above.")