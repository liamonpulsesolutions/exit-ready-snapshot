#!/usr/bin/env python
"""
Test the summary node with full 4-agent pipeline
(Intake → Research → Scoring → Summary)
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("🧪 Testing Summary Node (4-agent pipeline)")
print("=" * 60)

# Import all nodes
from src.nodes.intake_node import intake_node
from src.nodes.research_node import research_node
from src.nodes.scoring_node import scoring_node
from src.nodes.summary_node import summary_node
from src.workflow import AssessmentState

print("✅ All nodes imported successfully")

# Test data - manufacturing company preparing for exit
test_form_data = {
    "uuid": "test-summary-456",
    "timestamp": datetime.now().isoformat(),
    "name": "Robert Chen",
    "email": "robert@techmanufacturing.com",
    "industry": "Technology/Software",
    "years_in_business": "10-20 years",
    "age_range": "45-54",
    "exit_timeline": "1-2 years",
    "location": "Pacific/Western US",
    "revenue_range": "$10M-$25M",
    "responses": {
        "q1": "I handle strategic decisions and key client relationships. My COO manages daily operations.",
        "q2": "Up to 1 week with some disruption",
        "q3": "SaaS subscriptions 60%, Professional services 30%, One-time licenses 10%",
        "q4": "60%+",  # High recurring revenue
        "q5": "8",  # Strong financial confidence
        "q6": "Grew 10-25%",
        "q7": "COO and department heads can handle most things, but major contracts need my approval",
        "q8": "7",  # Good documentation
        "q9": "Our AI-powered automation saves clients 40% on operational costs",
        "q10": "9"  # High growth potential
    }
}

# Create initial state
initial_state = {
    "uuid": test_form_data["uuid"],
    "form_data": test_form_data,
    "locale": "us",
    "current_stage": "starting",
    "processing_time": {},
    "messages": ["4-agent pipeline test started"],
    # Business context
    "industry": test_form_data.get("industry"),
    "location": test_form_data.get("location"),
    "revenue_range": test_form_data.get("revenue_range"),
    "exit_timeline": test_form_data.get("exit_timeline"),
    "years_in_business": test_form_data.get("years_in_business")
}

# Run through pipeline
print("\n1️⃣  Running Intake Node...")
state = intake_node(initial_state)
if state.get("error"):
    print(f"❌ Intake failed: {state['error']}")
    sys.exit(1)
print(f"✅ Intake complete - PII mapping created: {len(state.get('pii_mapping', {}))} items")

print("\n2️⃣  Running Research Node...")
state = research_node(state)
if state.get("error"):
    print(f"❌ Research failed: {state['error']}")
    sys.exit(1)
print(f"✅ Research complete - Found {len(state['research_result'].get('industry_trends', {}))} trends")

print("\n3️⃣  Running Scoring Node...")
state = scoring_node(state)
if state.get("error"):
    print(f"❌ Scoring failed: {state['error']}")
    sys.exit(1)

scoring_result = state.get("scoring_result", {})
overall_results = scoring_result.get("overall_results", {})
print(f"✅ Scoring complete:")
print(f"   - Overall Score: {overall_results.get('overall_score', 'N/A')}/10")
print(f"   - Readiness Level: {overall_results.get('readiness_level', 'N/A')}")

print("\n4️⃣  Running Summary Node...")
state = summary_node(state)
if state.get("error"):
    print(f"❌ Summary failed: {state['error']}")
    sys.exit(1)

# Display results
summary_result = state.get("summary_result", {})
print(f"\n✅ Summary complete in {summary_result.get('processing_time', 0):.2f}s")

print("\n📊 SUMMARY RESULTS:")
print("=" * 60)

# Executive Summary (first 500 chars)
exec_summary = summary_result.get("executive_summary", "")
print("\n📋 Executive Summary Preview:")
print("-" * 40)
if exec_summary:
    print(exec_summary[:500] + "..." if len(exec_summary) > 500 else exec_summary)
else:
    print("No executive summary generated")

# Category Summaries
category_summaries = summary_result.get("category_summaries", {})
print(f"\n📊 Category Summaries Generated: {len(category_summaries)}")
for category in category_summaries:
    print(f"   - {category}")

# Recommendations
recommendations = summary_result.get("recommendations", "")
print("\n💡 Recommendations Preview:")
print("-" * 40)
if recommendations:
    print(recommendations[:400] + "..." if len(recommendations) > 400 else recommendations)
else:
    print("No recommendations generated")

# Industry Context
industry_context = summary_result.get("industry_context", "")
print("\n🏭 Industry Context Preview:")
print("-" * 40)
if industry_context:
    print(industry_context[:300] + "..." if len(industry_context) > 300 else industry_context)
else:
    print("No industry context generated")

# Final Report Structure
final_report = summary_result.get("final_report", "")
print(f"\n📄 Final Report Length: {len(final_report)} characters")

# Processing times
print("\n⏱️  Processing Times:")
for stage, time in state.get("processing_time", {}).items():
    print(f"   - {stage}: {time:.2f}s")

total_time = sum(state.get("processing_time", {}).values())
print(f"   - TOTAL: {total_time:.2f}s")

# Show last few debug messages
print("\n🔍 Debug Messages (last 5):")
for msg in state.get("messages", [])[-5:]:
    print(f"   - {msg}")

print("\n✅ 4-AGENT PIPELINE TEST SUCCESSFUL!")

# Save output for inspection
output_file = "test_output_4agent_summary.json"
with open(output_file, 'w') as f:
    json.dump({
        "summary_result": summary_result,
        "overall_results": overall_results,
        "processing_times": state.get("processing_time", {}),
        "messages": state.get("messages", [])
    }, f, indent=2)
print(f"\n💾 Full output saved to: {output_file}")