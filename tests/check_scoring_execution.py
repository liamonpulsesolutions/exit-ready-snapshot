#!/usr/bin/env python
"""
Check if scoring functions are actually being called in scoring_node
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Checking scoring node execution...")

# Let's trace what's happening
import src.nodes.scoring_node as scoring_module

# Monkey-patch the scoring functions to see if they're called
original_functions = {}
call_counts = {}

def make_wrapper(func_name):
    def wrapper(*args, **kwargs):
        call_counts[func_name] = call_counts.get(func_name, 0) + 1
        print(f"  ✓ {func_name} called (#{call_counts[func_name]})")
        return original_functions[func_name](*args, **kwargs)
    return wrapper

# Patch all scoring functions
scoring_functions = [
    'score_financial_performance',
    'score_revenue_stability', 
    'score_operations_efficiency',
    'score_growth_value',
    'score_exit_readiness'
]

for func_name in scoring_functions:
    if hasattr(scoring_module, func_name):
        original_functions[func_name] = getattr(scoring_module, func_name)
        setattr(scoring_module, func_name, make_wrapper(func_name))

# Also check tool calls
tool_calls = []
original_aggregate = None
original_calculate_focus = None

if hasattr(scoring_module, 'aggregate_final_scores'):
    original_aggregate = scoring_module.aggregate_final_scores._run
    def aggregate_wrapper(*args, **kwargs):
        tool_calls.append('aggregate_final_scores')
        print("  ✓ aggregate_final_scores tool called")
        return original_aggregate(*args, **kwargs)
    scoring_module.aggregate_final_scores._run = aggregate_wrapper

if hasattr(scoring_module, 'calculate_focus_areas'):
    original_calculate_focus = scoring_module.calculate_focus_areas._run
    def focus_wrapper(*args, **kwargs):
        tool_calls.append('calculate_focus_areas')
        print("  ✓ calculate_focus_areas tool called")
        return original_calculate_focus(*args, **kwargs)
    scoring_module.calculate_focus_areas._run = focus_wrapper

# Now run the scoring node
from src.nodes.scoring_node import scoring_node

test_state = {
    "uuid": "trace-test",
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

print("\nExecuting scoring node with function tracing...")
try:
    result = scoring_node(test_state)
    print("\n✅ Scoring node completed")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print(f"\nFunction call summary:")
print(f"  Scoring functions called: {sum(call_counts.values())} times")
for func, count in call_counts.items():
    print(f"    - {func}: {count} times")
print(f"  Tool functions called: {len(tool_calls)} times")
for tool in tool_calls:
    print(f"    - {tool}")

if sum(call_counts.values()) == 0:
    print("\n❌ NO SCORING FUNCTIONS WERE CALLED!")
    print("   The scoring node is not executing the scoring logic.")
    
    # Let's check the source
    import inspect
    source = inspect.getsource(scoring_node)
    
    # Look for early returns
    lines = source.split('\n')
    for i, line in enumerate(lines):
        if 'return state' in line and i < 100:  # Early return in first 100 lines
            print(f"\n   Found early return at line {i}: {line.strip()}")
            # Show context
            start = max(0, i-3)
            end = min(len(lines), i+2)
            print("   Context:")
            for j in range(start, end):
                marker = ">>>" if j == i else "   "
                print(f"   {marker} {lines[j]}")

# Save output
import json
from datetime import datetime

output = {
    "function_calls": call_counts,
    "tool_calls": tool_calls,
    "test_passed": sum(call_counts.values()) > 0
}

filename = f"output_scoring_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Trace saved to: {filename}")