#!/usr/bin/env python
"""Test script to verify setup is working"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🚀 Exit Ready Snapshot - Setup Test")
print("=" * 50)

# Check Python version
import sys
print(f"✓ Python version: {sys.version}")

# Check environment variables
env_vars = ['OPENAI_API_KEY']
for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"✓ {var}: Set (hidden)")
    else:
        print(f"✗ {var}: Not set - please add to .env file")

# Check configuration files
config_files = [
    'config/prompts.yaml',
    'config/scoring_rubric.yaml',
    'config/industry_prompts.yaml',
    'config/locale_terms.yaml'
]

print("\nChecking configuration files...")
for file in config_files:
    if os.path.exists(file):
        print(f"✓ {file}: Found")
    else:
        print(f"✗ {file}: Missing - please create this file")

# Check imports
print("\nChecking imports...")
try:
    import crewai
    print("✓ CrewAI imported successfully")
except ImportError as e:
    print(f"✗ CrewAI import failed: {e}")

try:
    import langchain
    print("✓ LangChain imported successfully")
except ImportError as e:
    print(f"✗ LangChain import failed: {e}")

try:
    from src.crew import ExitReadySnapshotCrew
    print("✓ Project imports working")
except ImportError as e:
    print(f"✗ Project import failed: {e}")

print("\n✅ Setup test complete!")