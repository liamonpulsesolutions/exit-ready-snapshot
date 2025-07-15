#!/usr/bin/env python
"""
Test the 5-agent pipeline with the QA category mapping fix
Run this after applying the QA node fix to verify it works
"""

import sys
import os
import json
from datetime import datetime
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Capture all terminal output
_original_stdout = sys.stdout
_original_stderr = sys.stderr
_stdout_capture = StringIO()
_stderr_capture = StringIO()

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
sys.stderr = TeeOutput(_stderr_capture, _original_stderr)

from dotenv import load_dotenv
load_dotenv()

print("🧪 Testing 5-Agent Pipeline with QA Category Fix")
print("=" * 60)

# Import all nodes (make sure QA node has the fix applied)
from src.nodes.intake_node import intake_node
from src.nodes.research_node import research_node
from src.nodes.scoring_node import scoring_node
from src.nodes.summary_node import summary_node
from src.nodes.qa_node import qa_node

print("✅ All nodes imported successfully")

# Test data - high-performing SaaS company
test_form_data = {
    "uuid": "test-qa-fix",
    "timestamp": datetime.now().isoformat(),
    "name": "Sarah Johnson",
    "email": "sarah@highgrowthsaas.com",
    "industry": "Software/SaaS",
    "years_in_business": "5-10 years",
    "age_range": "35-44",
    "exit_timeline": "6-12 months",
    "location": "Pacific/Western US",
    "revenue_range": "$25M-$50M",
    "responses": {
        "q1": "CEO focuses on vision and strategy. COO runs daily operations independently.",
        "q2": "More than 2 weeks",
        "q3": "SaaS subscriptions 95%, Professional services 5%",
        "q4": "80%+",
        "q5": "9",
        "q6": "Grew 25-50%",
        "q7": "Strong leadership team handles everything. Board-level decisions only.",
        "q8": "9",
        "q9": "Market-leading AI features with 3 patents pending. 50% cost savings for enterprise.",
        "q10": "10"
    }
}

# Create initial state
initial_state = {
    "uuid": test_form_data["uuid"],
    "form_data": test_form_data,
    "locale": "us",
    "current_stage": "starting",
    "processing_time": {},
    "messages": ["5-agent QA fix test started"],
    # Business context
    "industry": test_form_data.get("industry"),
    "location": test_form_data.get("location"),
    "revenue_range": test_form_data.get("revenue_range"),
    "exit_timeline": test_form_data.get("exit_timeline"),
    "years_in_business": test_form_data.get("years_in_business")
}

# Track timing for each stage
stage_times = {}

# Run through pipeline
state = initial_state

try:
    # 1. Intake
    print("\n1️⃣ Running Intake Node...")
    start = datetime.now()
    state = intake_node(state)
    stage_times['intake'] = (datetime.now() - start).total_seconds()
    if state.get("error"):
        raise Exception(f"Intake failed: {state['error']}")
    print(f"✅ Intake complete in {stage_times['intake']:.2f}s")

    # 2. Research
    print("\n2️⃣ Running Research Node...")
    start = datetime.now()
    state = research_node(state)
    stage_times['research'] = (datetime.now() - start).total_seconds()
    if state.get("error"):
        raise Exception(f"Research failed: {state['error']}")
    print(f"✅ Research complete in {stage_times['research']:.2f}s")

    # 3. Scoring
    print("\n3️⃣ Running Scoring Node...")
    start = datetime.now()
    state = scoring_node(state)
    stage_times['scoring'] = (datetime.now() - start).total_seconds()
    if state.get("error"):
        raise Exception(f"Scoring failed: {state['error']}")
    
    scoring_result = state.get("scoring_result", {})
    print(f"✅ Scoring complete in {stage_times['scoring']:.2f}s")
    print(f"   Overall Score: {scoring_result.get('overall_score')}/10")
    
    # Show category names to verify they need mapping
    if 'category_scores' in scoring_result:
        print(f"   Categories from scoring: {list(scoring_result['category_scores'].keys())}")

    # 4. Summary
    print("\n4️⃣ Running Summary Node...")
    start = datetime.now()
    state = summary_node(state)
    stage_times['summary'] = (datetime.now() - start).total_seconds()
    if state.get("error"):
        raise Exception(f"Summary failed: {state['error']}")
    print(f"✅ Summary complete in {stage_times['summary']:.2f}s")

    # 5. QA (with fix)
    print("\n5️⃣ Running QA Node (with category mapping fix)...")
    start = datetime.now()
    state = qa_node(state)
    stage_times['qa'] = (datetime.now() - start).total_seconds()
    if state.get("error"):
        raise Exception(f"QA failed: {state['error']}")
    
    qa_result = state.get("qa_result", {})
    print(f"✅ QA complete in {stage_times['qa']:.2f}s")
    
    # Detailed QA results
    print(f"\n📊 QA RESULTS:")
    print(f"   Approved: {qa_result.get('approved')}")
    print(f"   Quality Score: {qa_result.get('quality_score')}/10")
    print(f"   Ready for Delivery: {qa_result.get('ready_for_delivery')}")
    print(f"   Issues Found: {len(qa_result.get('issues_found', []))}")
    
    if qa_result.get('issues_found'):
        print("\n   Issues:")
        for issue in qa_result['issues_found']:
            print(f"   - {issue}")
    
    # Check validation details
    validation_details = qa_result.get('validation_details', {})
    if validation_details:
        print("\n   Validation Results:")
        for check, result in validation_details.items():
            passed = "Passed" in str(result)
            print(f"   - {check}: {'✅ PASS' if passed else '❌ FAIL'}")

    # Total time
    total_time = sum(stage_times.values())
    print(f"\n⏱️ Total Pipeline Time: {total_time:.2f}s")
    
    # Success message
    print("\n✅ 5-AGENT PIPELINE WITH QA FIX COMPLETED SUCCESSFULLY!")
    
    # Save results
    output = {
        "test_name": "5agent_qa_fix_test",
        "timestamp": datetime.now().isoformat(),
        "success": True,
        "stage_times": stage_times,
        "total_time": total_time,
        "overall_score": scoring_result.get('overall_score'),
        "qa_approved": qa_result.get('approved'),
        "qa_score": qa_result.get('quality_score'),
        "qa_issues": qa_result.get('issues_found', []),
        "category_mapping_worked": "Report structure incomplete" not in qa_result.get('issues_found', [])
    }
    
    filename = f"output_5agent_qa_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")

except Exception as e:
    print(f"\n❌ Pipeline failed: {str(e)}")
    import traceback
    traceback.print_exc()
    
    # Save error output
    error_output = {
        "test_name": "5agent_qa_fix_test",
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "error": str(e),
        "stage_times": stage_times,
        "last_stage": state.get("current_stage", "unknown") if 'state' in locals() else "unknown"
    }
    
    filename = f"output_5agent_qa_fix_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(error_output, f, indent=2)
    
    print(f"\n💾 Error details saved to: {filename}")

# Save complete output including terminal
def save_complete_output():
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    
    # Get the output dict (either success or error)
    final_output = output if 'output' in locals() else error_output if 'error_output' in locals() else {}
    
    # Add terminal output
    final_output["terminal_output"] = _stdout_capture.getvalue().split('\n')
    if _stderr_capture.getvalue():
        final_output["stderr_output"] = _stderr_capture.getvalue().split('\n')
    
    # Determine filename
    if 'filename' in locals():
        complete_filename = filename.replace('.json', '_complete.json')
    else:
        complete_filename = f"output_5agent_qa_fix_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Save complete output
    with open(complete_filename, 'w') as f:
        json.dump(final_output, f, indent=2)
    
    print(f"\n💾 Complete output (including terminal) saved to: {complete_filename}")

save_complete_output()