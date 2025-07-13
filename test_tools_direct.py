#!/usr/bin/env python
"""Test the actual tool functions directly (not the CrewAI @tool wrappers)"""

import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

# Simple logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

def test_research_direct():
    """Test research functionality directly"""
    print("=== TESTING RESEARCH FUNCTIONALITY ===")
    
    # Import the class and functions directly
    try:
        from src.agents.research_agent import PerplexityResearcher
        
        # Test the researcher class directly
        researcher = PerplexityResearcher()
        
        query = """
        For small to medium Professional Services businesses in US (revenue $1M-$5M):
        1. Current EBITDA multiples
        2. Revenue multiples  
        3. Key success factors
        """
        
        print(f"Testing Perplexity search...")
        result = researcher.search(query)
        
        if "error" in result:
            print(f"⚠ Perplexity API error: {result['error']}")
            print("This is expected if API key is invalid or API is down")
        else:
            print(f"✓ Perplexity API working - got response")
            
        return result
        
    except Exception as e:
        print(f"✗ Research import/setup failed: {str(e)}")
        import traceback
        traceback.print_exc()

def test_intake_direct():
    """Test intake functionality by calling the actual function logic"""
    print("\n=== TESTING INTAKE FUNCTIONALITY ===")
    
    try:
        # Import the PII detector directly
        from src.tools.pii_detector import PIIDetector
        from src.tools.google_sheets import GoogleSheetsLogger
        
        # Test PII detection
        pii_detector = PIIDetector()
        test_text = "My email is john@example.com and my company is Acme Corp"
        
        result = pii_detector.detect_and_redact(test_text)
        print(f"✓ PII Detection working: found {len(result.get('mapping', {}))} PII items")
        print(f"   Redacted text: {result.get('redacted_text', '')}")
        
        # Test Google Sheets (will be in mock mode)
        sheets = GoogleSheetsLogger()
        test_data = {"uuid": "test", "name": "Test", "email": "test@test.com"}
        
        crm_result = sheets.log_to_crm(test_data)
        print(f"✓ Google Sheets logging: {crm_result.get('mode', 'unknown')} mode")
        
    except Exception as e:
        print(f"✗ Intake functionality failed: {str(e)}")
        import traceback
        traceback.print_exc()

def test_crew_import():
    """Test if we can import and create the crew"""
    print("\n=== TESTING CREW IMPORT ===")
    
    try:
        from src.crew import ExitReadySnapshotCrew
        
        print("✓ Crew class imported successfully")
        
        # Try to initialize
        crew = ExitReadySnapshotCrew(locale='us')
        print("✓ Crew initialized successfully")
        print(f"✓ Crew has {len(crew.agents)} agents")
        
        return crew
        
    except Exception as e:
        print(f"✗ Crew import/init failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_environment():
    """Quick environment check"""
    print("=== ENVIRONMENT CHECK ===")
    
    required_keys = ['OPENAI_API_KEY', 'PERPLEXITY_API_KEY']
    for key in required_keys:
        value = os.getenv(key)
        if value:
            print(f"✓ {key}: Set ({len(value)} chars)")
        else:
            print(f"✗ {key}: Missing")

def main():
    print("DIRECT TOOL TESTING - BYPASSING CREWAI @tool WRAPPERS")
    print("=" * 60)
    
    test_environment()
    test_intake_direct()
    test_research_direct()
    
    crew = test_crew_import()
    
    if crew:
        print("\n=== TESTING CREW AGENTS ===")
        for name, agent in crew.agents.items():
            print(f"✓ Agent '{name}': {type(agent).__name__}")
            print(f"   Tools: {len(agent.tools) if hasattr(agent, 'tools') else 0}")
    
    print("\n" + "=" * 60)
    print("DIRECT TOOL TEST COMPLETE")

if __name__ == "__main__":
    main()