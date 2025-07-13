#!/usr/bin/env python
"""
Validate environment setup for CrewAI 0.141.0 compatibility
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def validate_environment():
    """Comprehensive environment validation"""
    issues = []
    warnings = []
    
    # Required environment variables
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API access',
        'PERPLEXITY_API_KEY': 'Industry research functionality',
        'CREWAI_API_KEY': 'API authentication'
    }
    
    # Optional but recommended
    optional_vars = {
        'GOOGLE_SHEETS_CREDENTIALS_PATH': 'CRM logging functionality',
        'CRM_SPREADSHEET_ID': 'Lead tracking',
        'RESPONSES_SPREADSHEET_ID': 'Response analytics'
    }
    
    print("🔍 ENVIRONMENT VALIDATION")
    print("=" * 50)
    
    # Check required variables
    for var, purpose in required_vars.items():
        value = os.getenv(var)
        if not value:
            issues.append(f"❌ {var}: Missing - needed for {purpose}")
        elif len(value) < 10:
            issues.append(f"⚠️ {var}: Too short - check if valid")
        else:
            print(f"✅ {var}: Set ({len(value)} chars)")
    
    # Check optional variables
    for var, purpose in optional_vars.items():
        value = os.getenv(var)
        if not value:
            warnings.append(f"⚠️ {var}: Not set - {purpose} will be in mock mode")
        else:
            print(f"✅ {var}: Set")
    
    # Check configuration files
    config_files = [
        'config/prompts.yaml',
        'config/scoring_rubric.yaml', 
        'config/industry_prompts.yaml',
        'config/locale_terms.yaml'
    ]
    
    print("\n📁 CONFIGURATION FILES")
    print("-" * 30)
    
    for file in config_files:
        if os.path.exists(file):
            print(f"✅ {file}: Found")
        else:
            issues.append(f"❌ {file}: Missing")
    
    # Test imports
    print("\n📦 DEPENDENCIES")
    print("-" * 20)
    
    try:
        import crewai
        print(f"✅ CrewAI: {crewai.__version__}")
        
        # Check if it's the right version
        version = crewai.__version__
        if version.startswith("0.141") or version.startswith("0.142"):
            print("✅ CrewAI version compatible with BaseTool updates")
        else:
            warnings.append(f"⚠️ CrewAI version {version} may not be compatible with BaseTool format")
            
    except ImportError as e:
        issues.append(f"❌ CrewAI import failed: {e}")
    
    try:
        from langchain_openai import ChatOpenAI
        print("✅ LangChain OpenAI: Available")
    except ImportError as e:
        issues.append(f"❌ LangChain OpenAI import failed: {e}")
    
    try:
        import requests
        print("✅ Requests: Available")
    except ImportError as e:
        issues.append(f"❌ Requests import failed: {e}")
    
    # Test project structure
    print("\n🏗️ PROJECT STRUCTURE")
    print("-" * 25)
    
    project_files = [
        'src/crew.py',
        'src/agents/intake_agent.py',
        'src/agents/research_agent.py', 
        'src/agents/scoring_agent.py',
        'src/agents/summary_agent.py',
        'src/agents/qa_agent.py',
        'src/agents/pii_reinsertion_agent.py',
        'src/utils/json_helper.py',
        'src/tools/google_sheets.py',
        'src/tools/pii_detector.py'
    ]
    
    for file in project_files:
        if os.path.exists(file):
            print(f"✅ {file}: Found")
        else:
            issues.append(f"❌ {file}: Missing")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    if not issues and not warnings:
        print("🎉 Perfect! Environment is fully configured.")
        return True
    
    if warnings:
        print("⚠️ WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
    
    if issues:
        print("❌ CRITICAL ISSUES:")
        for issue in issues:
            print(f"   {issue}")
        print("\n🚨 Fix these issues before running the system!")
        return False
    
    print("\n✅ Core functionality should work, but consider addressing warnings.")
    return True

if __name__ == "__main__":
    success = validate_environment()
    sys.exit(0 if success else 1)