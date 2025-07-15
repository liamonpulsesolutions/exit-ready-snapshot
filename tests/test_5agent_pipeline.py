#!/usr/bin/env python
"""
Test the 5-agent pipeline (Intake → Research → Scoring → Summary → QA)
"""

import sys
import os
import json
from datetime import datetime

# Add logging capture
from io import StringIO
_original_stdout = sys.stdout
_stdout_capture = StringIO()

class TeeOutput:
    def __init__(self, capture, original):
        self.capture = capture
        self.original = original
    def write(self, data):
        self.capture.write(data)
        self.original.write(data)
    def flush(self):
        self.capture.flush()
        self.original.flush()
    def isatty(self):
        return self.original.isatty() if hasattr(self.original, 'isatty') else False
    def __getattr__(self, name):
        return getattr(self.original, name)

sys.stdout = TeeOutput(_stdout_capture, _original_stdout)
_test_data = {"test_name": "5agent_pipeline", "timestamp": datetime.now().isoformat(), "results": {}}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("🧪 Testing 5-Agent Pipeline (with QA)")
print("=" * 60)

# Import all nodes
from src.nodes.intake_node import intake_node
from src.nodes.research_node import research_node
from src.nodes.scoring_node import scoring_node
from src.nodes.summary_node import summary_node
from src.nodes.qa_node import qa_node

print("✅ All nodes imported successfully")

# Test data - high quality business ready for exit
test_form_data = {
    "uuid": "test-5agent-qa",
    "timestamp": datetime.now().isoformat(),
    "name": "Jennifer Martinez",
    "email": "jennifer@saascompany.com",
    "industry": "Software/SaaS",
    "years_in_business": "10-20 years",
    "age_range": "45-54",
    "exit_timeline": "6-12 months",
    "location": "Northeast US",
    "revenue_range": "$10M-$25M",
    "responses": {
        "q1": "COO manages daily operations. I focus on strategy and major partnerships.",
        "q2": "Up to 2 weeks without disruption",
        "q3": "SaaS subscriptions 85%, Professional services 15%",
        "q4": "80%+",  # High recurring revenue
        "q5": "9",  # Very strong financial confidence
        "q6": "Grew 25-50%",
        "q7": "Minimal disruption - strong leadership team in place",
        "q8": "8",  # Excellent documentation
        "q9": "Patented AI optimization reduces customer churn by 60%",
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
    "messages": ["5-agent pipeline test started"],
    # Business context
    "industry": test_form_data.get("industry"),
    "location": test_form_data.get("location"),
    "revenue_range": test_form_data.get("revenue_range"),
    "exit_timeline": test_form_data.get("exit_timeline"),
    "years_in_business": test_form_data.get("years_in_business")
}

# Run through pipeline
state = initial_state

print("\n1️⃣  Running Intake Node...")
state = intake_node(state)
if state.get("error"):
    print(f"❌ Intake failed: {state['error']}")
    sys.exit(1)
print(f"✅ Intake complete - PII: {state['intake_result'].get('pii_entries', 0)} items")

print("\n2️⃣  Running Research Node...")
state = research_node(state)
if state.get("error"):
    print(f"❌ Research failed: {state['error']}")
    sys.exit(1)
print(f"✅ Research complete - Quality: {state['research_result'].get('research_quality', 'unknown')}")

print("\n3️⃣  Running Scoring Node...")
state = scoring_node(state)
if state.get("error"):
    print(f"❌ Scoring failed: {state['error']}")
    sys.exit(1)
scoring_result = state.get("scoring_result", {})
print(f"✅ Scoring complete - Overall: {scoring_result.get('overall_score')}/10")

print("\n4️⃣  Running Summary Node...")
state = summary_node(state)
if state.get("error"):
    print(f"❌ Summary failed: {state['error']}")
    sys.exit(1)
print(f"✅ Summary complete - Report length: {len(state['summary_result'].get('final_report', ''))} chars")

print("\n5️⃣  Running QA Node...")
state = qa_node(state)
if state.get("error"):
    print(f"❌ QA failed: {state['error']}")
    sys.exit(1)

# Display QA results
qa_result = state.get("qa_result", {})
print(f"\n✅ QA complete:")
print(f"   - Quality Score: {qa_result.get('overall_quality_score')}/10")
print(f"   - Approved: {qa_result.get('approved')}")
print(f"   - Ready for Delivery: {qa_result.get('ready_for_delivery')}")
print(f"   - Issues Found: {len(qa_result.get('issues_found', []))}")

if qa_result.get('issues_found'):
    print("\n   Issues:")
    for issue in qa_result['issues_found']:
        print(f"   - {issue}")

# Processing times
print("\n⏱️  Processing Times:")
total_time = 0
for stage, time in state.get("processing_time", {}).items():
    print(f"   - {stage}: {time:.2f}s")
    total_time += time
print(f"   - TOTAL: {total_time:.2f}s")

# Save results
_test_data["results"] = {
    "overall_score": scoring_result.get("overall_score"),
    "readiness_level": scoring_result.get("readiness_level"),
    "qa_approved": qa_result.get("approved"),
    "qa_score": qa_result.get("overall_quality_score"),
    "processing_times": state.get("processing_time", {}),
    "total_time": total_time
}

# Show last messages
print("\n🔍 Last Pipeline Messages:")
for msg in state.get("messages", [])[-5:]:
    print(f"   - {msg}")

print("\n✅ 5-AGENT PIPELINE TEST COMPLETE!")

# Save output
def save_test_output():
    sys.stdout = _original_stdout
    _test_data["terminal_output"] = _stdout_capture.getvalue().split('\n')
    filename = f"output_5agent_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2)
    print(f"\n💾 Full output saved to: {filename}")

save_test_output()