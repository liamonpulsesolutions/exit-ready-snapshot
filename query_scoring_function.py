#!/usr/bin/env python
"""
Debug why scoring functions aren't being called in scoring_node
"""

import sys
import os
import json
from datetime import datetime
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Capture output
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

from dotenv import load_dotenv
load_dotenv()

print("🔍 DEBUGGING SCORING NODE EXECUTION PATH")
print("=" * 60)

# First, let's add extensive tracing to see where execution stops
execution_trace = []

def trace(msg):
    """Add to execution trace"""
    execution_trace.append(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} - {msg}")
    print(f"   TRACE: {msg}")

# Monkey-patch the scoring_node to add trace points
print("\n1️⃣ Patching scoring_node with trace points...")

# Import the module
import src.nodes.scoring_node as scoring_module

# Save original
original_scoring_node = scoring_module.scoring_node

def traced_scoring_node(state):
    """Heavily traced version of scoring_node"""
    trace("Entered traced_scoring_node")
    trace(f"State has keys: {list(state.keys())}")
    
    # Check state contents
    if "anonymized_data" in state:
        trace("Found anonymized_data in state")
        anon_data = state.get("anonymized_data", {})
        trace(f"anonymized_data has keys: {list(anon_data.keys())}")
    else:
        trace("WARNING: No anonymized_data in state")
    
    # Try to call the original
    trace("About to call original scoring_node...")
    
    try:
        result = original_scoring_node(state)
        trace("Original scoring_node returned successfully")
        
        # Check what was returned
        if "scoring_result" in result:
            trace("Found scoring_result in return value")
            scoring_result = result["scoring_result"]
            trace(f"Scoring status: {scoring_result.get('status', 'unknown')}")
            trace(f"Overall score: {scoring_result.get('overall_score', 'N/A')}")
        else:
            trace("WARNING: No scoring_result in return value")
        
        return result
        
    except Exception as e:
        trace(f"EXCEPTION in scoring_node: {type(e).__name__}: {str(e)}")
        import traceback
        trace("Full traceback:")
        for line in traceback.format_exc().split('\n'):
            trace(line)
        raise

# Replace with traced version
scoring_module.scoring_node = traced_scoring_node

print("✅ Patching complete")

# Now let's also check if the scoring functions exist and are callable
print("\n2️⃣ Checking if scoring functions are importable...")

try:
    from src.agents.scoring_agent import (
        score_financial_performance,
        score_revenue_stability,
        score_operations_efficiency,
        score_growth_value,
        score_exit_readiness
    )
    print("   ✅ All scoring functions imported successfully")
    
    # Check if they're callable
    for name, func in [
        ("score_financial_performance", score_financial_performance),
        ("score_revenue_stability", score_revenue_stability),
        ("score_operations_efficiency", score_operations_efficiency),
        ("score_growth_value", score_growth_value),
        ("score_exit_readiness", score_exit_readiness)
    ]:
        if callable(func):
            print(f"   ✅ {name} is callable")
        else:
            print(f"   ❌ {name} is NOT callable - type: {type(func)}")
            
except Exception as e:
    print(f"   ❌ Failed to import scoring functions: {e}")
    import traceback
    traceback.print_exc()

# Create test state
print("\n3️⃣ Creating test state...")

test_state = {
    "uuid": "debug-test",
    "anonymized_data": {
        "responses": {
            "q1": "Test response",
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

print("   ✅ Test state created")

# Run the traced node
print("\n4️⃣ Running traced scoring node...")
print("-" * 60)

from src.nodes.scoring_node import scoring_node

try:
    result = scoring_node(test_state)
    print("-" * 60)
    print("✅ Execution completed")
    
except Exception as e:
    print("-" * 60)
    print(f"❌ Execution failed: {e}")

# Show execution trace
print("\n5️⃣ EXECUTION TRACE:")
print("-" * 60)
for trace_line in execution_trace:
    print(trace_line)

# Check the scoring_node source to see if there's an early return
print("\n6️⃣ Checking for early returns in scoring_node...")
import inspect

try:
    source = inspect.getsource(original_scoring_node)
    lines = source.split('\n')
    
    # Look for early returns
    for i, line in enumerate(lines):
        if 'return state' in line and i < 50:  # Early return in first 50 lines
            print(f"   ⚠️  Found early return at line {i}: {line.strip()}")
            # Show context
            start = max(0, i-3)
            end = min(len(lines), i+3)
            print("   Context:")
            for j in range(start, end):
                marker = ">>>" if j == i else "   "
                print(f"   {marker} {lines[j]}")
                
except Exception as e:
    print(f"   Could not inspect source: {e}")

# Save complete debug output
output = {
    "timestamp": datetime.now().isoformat(),
    "execution_trace": execution_trace,
    "trace_count": len(execution_trace),
    "completed": 'result' in locals(),
    "terminal_output": _stdout_capture.getvalue().split('\n')
}

filename = f"output_debug_scoring_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Debug output saved to: {filename}")
print("\n" + "=" * 60)
print("DEBUG COMPLETE")