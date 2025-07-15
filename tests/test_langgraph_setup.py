#!/usr/bin/env python
"""
Test script to verify LangGraph setup and imports
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔍 Testing LangGraph Setup")
print("=" * 50)

# Test 1: Import checks
print("\n1. Testing imports...")
try:
    from langgraph.graph import StateGraph, END
    print("✅ LangGraph core imports successful")
except ImportError as e:
    print(f"❌ LangGraph import failed: {e}")
    print("   Run: pip install langgraph")

try:
    from langchain_openai import ChatOpenAI
    print("✅ LangChain OpenAI imports successful")
except ImportError as e:
    print(f"❌ LangChain OpenAI import failed: {e}")
    print("   Run: pip install langchain-openai")

# Test 2: Load environment
print("\n2. Testing environment...")
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    print(f"✅ OpenAI API key found (length: {len(api_key)})")
else:
    print("❌ OpenAI API key not found")

# Test 3: Import our workflow
print("\n3. Testing workflow import...")
try:
    from src.workflow import AssessmentState, create_assessment_workflow, determine_locale
    print("✅ Workflow module imported successfully")
    print(f"   - AssessmentState fields: {list(AssessmentState.__annotations__.keys())[:5]}...")
    print(f"   - Locale test: 'Pacific/Western US' → '{determine_locale('Pacific/Western US')}'")
except ImportError as e:
    print(f"❌ Workflow import failed: {e}")
    print("   Make sure src/workflow.py exists")

# Test 4: Check existing tools
print("\n4. Checking existing tools availability...")
tools_to_check = [
    ("Intake tools", "src.agents.intake_agent", ["process_complete_form", "validate_form_data"]),
    ("Research tools", "src.agents.research_agent", ["research_industry_trends"]),
    ("Scoring tools", "src.agents.scoring_agent", ["calculate_category_score"]),
    ("Summary tools", "src.agents.summary_agent", ["create_executive_summary"]),
    ("QA tools", "src.agents.qa_agent", ["check_scoring_consistency"]),
    ("PII tools", "src.agents.pii_reinsertion_agent", ["process_complete_reinsertion"])
]

for name, module, tools in tools_to_check:
    try:
        imported_module = __import__(module, fromlist=tools)
        available = [t for t in tools if hasattr(imported_module, t)]
        print(f"✅ {name}: {len(available)}/{len(tools)} tools available")
    except ImportError as e:
        print(f"❌ {name}: Import failed - {e}")

print("\n" + "=" * 50)
print("Setup test complete!")
print("\nNext steps:")
print("1. Create src/nodes/ directory if it doesn't exist")
print("2. Start implementing intake_node.py")
print("3. Test each node as you build it")