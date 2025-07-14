#!/usr/bin/env python
"""
Debug why scoring node completes in 0.00s
"""

import sys
import os
import json
from datetime import datetime
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Output capture setup
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
        # Delegate any other attributes to the original
        return getattr(self.original, name)

sys.stdout = TeeOutput(_stdout_capture, _original_stdout)
sys.stderr = TeeOutput(_stderr_capture, _original_stderr)

_test_data = {
    "test_name": "debug_scoring_node",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": []
}

from dotenv import load_dotenv
load_dotenv()

print("🔍 DEBUGGING SCORING NODE")
print("=" * 60)

# First, let's check if the issue is in the node itself
print("\n1️⃣ Checking scoring_node source for timing issues...")

import inspect
from src.nodes.scoring_node import scoring_node

# Get the source code
source = inspect.getsource(scoring_node)

# Check for timing code
print("Looking for timing code...")
if "start_time = datetime.now()" in source:
    print("✅ Found start_time assignment")
else:
    print("❌ Missing start_time assignment")

if "end_time = datetime.now()" in source:
    print("✅ Found end_time assignment")
else:
    print("❌ Missing end_time assignment")

# Check if there's an early return
lines = source.split('\n')
for i, line in enumerate(lines):
    if 'return state' in line and i < 50:  # Early return
        print(f"⚠️  Found early return at line {i}: {line.strip()}")

# Now let's trace execution
print("\n2️⃣ Running scoring node with detailed logging...")

# Monkey-patch the datetime to see what's happening
original_datetime = datetime
call_count = 0

class DebugDateTime:
    @staticmethod
    def now():
        global call_count
        call_count += 1
        result = original_datetime.now()
        print(f"  datetime.now() called #{call_count}: {result}")
        return result

# Temporarily replace datetime
import src.nodes.scoring_node
src.nodes.scoring_node.datetime = DebugDateTime

# Create test state
test_state = {
    "uuid": "debug-test",
    "anonymized_data": {
        "responses": {
            "q1": "I handle everything",
            "q2": "Less than 3 days",
            "q3": "Services 100%",
            "q4": "20-40%",
            "q5": "6",
            "q6": "Stayed flat",
            "q7": "Major disruption",
            "q8": "3",
            "q9": "Good customer service",
            "q10": "5"
        },
        "industry": "Technology",
        "revenue_range": "$5M-$10M",
        "years_in_business": "5-10 years",
        "exit_timeline": "1-2 years"
    },
    "research_result": {"structured_findings": {}},
    "processing_time": {},
    "messages": [],
    "current_stage": "scoring"
}

print("\nExecuting scoring node...")
try:
    result_state = scoring_node(test_state)
    print("✅ Scoring node completed")
    
    # Check the timing
    actual_time = result_state['processing_time'].get('scoring', -1)
    print(f"\nRecorded processing time: {actual_time}s")
    
    if actual_time == 0 or actual_time < 0.001:
        print("❌ Processing time is essentially 0")
        
        # Check if datetime was called correctly
        print(f"datetime.now() was called {call_count} times")
        
except Exception as e:
    print(f"❌ Error in scoring node: {e}")
    import traceback
    traceback.print_exc()

# Restore original datetime
src.nodes.scoring_node.datetime = original_datetime

# Check the actual calculation
print("\n3️⃣ Checking if calculations are happening...")

# Import scoring functions
from src.agents.scoring_agent import (
    score_financial_performance,
    score_revenue_stability,
    score_operations_efficiency,
    score_growth_value,
    score_exit_readiness
)

# Time a single scoring function
import time
start = time.time()
test_responses = {
    "q5": "6",
    "q6": "Stayed flat",
    "revenue_range": "$5M-$10M",
    "years_in_business": "5"
}
result = score_financial_performance(test_responses, {})
end = time.time()

print(f"\nSingle scoring function time: {end - start:.4f}s")
print(f"Result: {result.get('score')}/10")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")

# Summary
print("\nLikely issues:")
if call_count < 2:
    print("- datetime.now() not called twice (start/end)")
if actual_time == 0:
    print("- Time calculation is wrong (same start/end time)")
print("- Check if scoring functions are actually being called")

# Save all results to test data
_test_data["results"]["datetime_call_count"] = call_count if 'call_count' in locals() else 0
_test_data["results"]["actual_processing_time"] = actual_time if 'actual_time' in locals() else -1
_test_data["results"]["single_function_time"] = (end - start) if 'end' in locals() and 'start' in locals() else -1
_test_data["results"]["test_score"] = result.get('score') if 'result' in locals() and isinstance(result, dict) else None

# Save output
def save_test_output():
    try:
        sys.stdout = _original_stdout
        sys.stderr = _original_stderr
        
        _test_data["terminal_output"] = _stdout_capture.getvalue().split('\n')
        if _stderr_capture.getvalue():
            _test_data["stderr_output"] = _stderr_capture.getvalue().split('\n')
        
        filename = f"output_debug_scoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(_test_data, f, indent=2)
        
        print(f"\n💾 Complete test output saved to: {filename}")
    except Exception as e:
        print(f"\n❌ Error saving output: {e}")

save_test_output()