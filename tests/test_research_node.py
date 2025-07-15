#!/usr/bin/env python
"""
Test the research node with data from intake
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("🧪 Testing Research Node (with Intake → Research pipeline)")
print("=" * 60)

try:
    # Import both nodes
    from src.nodes.intake_node import intake_node
    from src.nodes.research_node import research_node
    from src.workflow import AssessmentState
    
    print("✅ Nodes imported successfully")
    
    # Test data
    test_form_data = {
        "uuid": "test-research-123",
        "timestamp": datetime.now().isoformat(),
        "name": "Jane Doe",
        "email": "jane@techcompany.com",
        "industry": "Technology",
        "years_in_business": "5-10 years",
        "age_range": "45-54",
        "exit_timeline": "1-2 years",
        "location": "Pacific/Western US",
        "revenue_range": "$1M-$5M",
        "responses": {
            "q1": "I personally handle all sales and client relationships",
            "q2": "Less than 3 days",
            "q3": "Software development services for healthcare",
            "q4": "70-80%",
            "q5": "8",
            "q6": "Improved slightly",
            "q7": "Lead developer knows systems but not clients",
            "q8": "6",
            "q9": "Proprietary healthcare data platform",
            "q10": "7"
        }
    }
    
    # Create initial state
    initial_state = {
        "uuid": test_form_data["uuid"],
        "form_data": test_form_data,
        "locale": "us",
        "current_stage": "starting",
        "processing_time": {},
        "messages": ["Pipeline test started"],
        # Business context
        "industry": test_form_data.get("industry"),
        "location": test_form_data.get("location"),
        "revenue_range": test_form_data.get("revenue_range"),
        "exit_timeline": test_form_data.get("exit_timeline"),
        "years_in_business": test_form_data.get("years_in_business")
    }
    
    print(f"\n📋 Test Data:")
    print(f"   UUID: {test_form_data['uuid']}")
    print(f"   Industry: {test_form_data['industry']}")
    print(f"   Location: {test_form_data['location']}")
    print(f"   Revenue: {test_form_data['revenue_range']}")
    
    # Step 1: Run intake node
    print("\n🚀 Step 1: Running intake node...")
    state_after_intake = intake_node(initial_state)
    
    intake_result = state_after_intake.get("intake_result", {})
    print(f"   ✅ Intake completed - PII entries: {intake_result.get('pii_entries')}")
    
    # Step 2: Run research node
    print("\n🚀 Step 2: Running research node...")
    state_after_research = research_node(state_after_intake)
    
    print("\n✅ Research node completed successfully!")
    
    # Check research results
    research_result = state_after_research.get("research_result", {})
    
    print(f"\n📊 Research Results:")
    print(f"   Status: {research_result.get('status')}")
    print(f"   Industry: {research_result.get('industry')}")
    print(f"   Location: {research_result.get('location')}")
    print(f"   Data source: {research_result.get('data_source')}")
    print(f"   Research quality: {research_result.get('research_quality')}")
    
    # Check structured findings
    structured = research_result.get("structured_findings", {})
    print(f"\n📈 Structured Findings:")
    
    benchmarks = structured.get("valuation_benchmarks", {})
    if benchmarks:
        print("   Valuation Benchmarks:")
        for key, value in benchmarks.items():
            print(f"      - {key}: {value}")
    
    strategies = structured.get("improvement_strategies", {})
    if strategies:
        print("   Improvement Strategies:")
        for category, details in list(strategies.items())[:2]:  # First 2
            print(f"      - {category}: {details.get('timeline', 'N/A')}")
    
    conditions = structured.get("market_conditions", {})
    if conditions:
        print("   Market Conditions:")
        for key, value in conditions.items():
            print(f"      - {key}: {value}")
    
    # Check processing times
    print(f"\n⏱️ Processing times:")
    for stage, time in state_after_research['processing_time'].items():
        print(f"   {stage}: {time:.2f}s")
    
    # Show pipeline messages
    print(f"\n📝 Pipeline Messages:")
    for msg in state_after_research.get("messages", [])[-5:]:  # Last 5
        print(f"   - {msg}")
    
    # Verify data flow
    print(f"\n✅ Data Flow Verification:")
    print(f"   Intake provided anonymized data: {'anonymized_data' in state_after_intake}")
    print(f"   Research accessed anonymized data: {research_result.get('industry') == test_form_data['industry']}")
    print(f"   Research completed analysis: {'trends_analysis' in research_result}")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Pipeline test complete!")