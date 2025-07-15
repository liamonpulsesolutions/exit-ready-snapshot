#!/usr/bin/env python
"""
Diagnostic test for scoring node to identify why it's completing too fast
"""

import sys
import os
import json
import time
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

print("🔍 SCORING NODE DIAGNOSTIC TEST")
print("=" * 60)

# Test 1: Check if scoring functions are being called
print("\n1️⃣ Testing if scoring functions are actually called...")

# Import the scoring node
from src.nodes.scoring_node import scoring_node

# Monkey-patch to trace function calls
import src.agents.scoring_agent as scoring_agent_module

original_functions = {}
function_calls = []

def make_tracer(func_name):
    def tracer(*args, **kwargs):
        function_calls.append({
            "function": func_name,
            "timestamp": datetime.now().isoformat(),
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys())
        })
        print(f"   ✓ {func_name} called")
        return original_functions[func_name](*args, **kwargs)
    return tracer

# Patch the scoring functions
scoring_functions = [
    'score_financial_performance',
    'score_revenue_stability',
    'score_operations_efficiency',
    'score_growth_value',
    'score_exit_readiness'
]

for func_name in scoring_functions:
    if hasattr(scoring_agent_module, func_name):
        original_functions[func_name] = getattr(scoring_agent_module, func_name)
        setattr(scoring_agent_module, func_name, make_tracer(func_name))

# Test 2: Create test state with complete data
print("\n2️⃣ Creating test state with all required data...")

test_state = {
    "uuid": "diagnostic-test",
    "anonymized_data": {
        "responses": {
            "q1": "I handle all strategic decisions and client relationships",
            "q2": "Less than 3 days",
            "q3": "Services 60%, Products 40%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Stayed flat",
            "q7": "Critical knowledge mostly with me",
            "q8": "5",
            "q9": "Strong customer service and niche expertise",
            "q10": "7"
        }
    },
    "research_result": {
        "structured_findings": {
            "valuation_benchmarks": {
                "ebitda_multiples": {"low": 4, "high": 6},
                "revenue_multiples": {"low": 1.2, "high": 2.0}
            },
            "improvement_strategies": {
                "reduce_owner_dependence": "Implement leadership team",
                "systematize_operations": "Document all processes"
            },
            "market_conditions": {
                "buyer_priorities": ["Strong management", "Recurring revenue"],
                "average_time_to_sell": "6-12 months"
            }
        }
    },
    "form_data": {
        "industry": "Professional Services",
        "revenue_range": "$5M-$10M",
        "years_in_business": "10-20 years",
        "exit_timeline": "1-2 years"
    },
    "industry": "Professional Services",
    "revenue_range": "$5M-$10M",
    "years_in_business": "10-20 years",
    "exit_timeline": "1-2 years",
    "processing_time": {},
    "messages": [],
    "current_stage": "scoring"
}

print("   ✓ Test state created with all required fields")

# Test 3: Run scoring node and measure time
print("\n3️⃣ Running scoring node...")

start_time = time.time()
try:
    result_state = scoring_node(test_state)
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"   ✓ Scoring completed in {execution_time:.4f}s")
    
    if execution_time < 0.1:
        print("   ⚠️  WARNING: Execution too fast! Likely not calling scoring functions")
    
except Exception as e:
    print(f"   ❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

# Test 4: Analyze results
print("\n4️⃣ Analyzing results...")

if 'result_state' in locals():
    scoring_result = result_state.get("scoring_result", {})
    
    print(f"\n   Function calls made: {len(function_calls)}")
    if function_calls:
        for call in function_calls:
            print(f"      - {call['function']}")
    else:
        print("      ❌ NO SCORING FUNCTIONS WERE CALLED!")
    
    print(f"\n   Scoring result structure:")
    print(f"      - Has category_scores: {'category_scores' in scoring_result}")
    print(f"      - Has overall_score: {'overall_score' in scoring_result}")
    print(f"      - Has focus_areas: {'focus_areas' in scoring_result}")
    
    if 'category_scores' in scoring_result:
        print(f"\n   Categories scored: {list(scoring_result['category_scores'].keys())}")
        
        # Check if scores are default values
        scores = [v.get('score', 0) for v in scoring_result['category_scores'].values() if isinstance(v, dict)]
        if all(score == 5.0 for score in scores):
            print("      ⚠️  WARNING: All scores are 5.0 - likely using defaults!")

# Test 5: Check if tools are being called
print("\n5️⃣ Checking tool usage...")

# Import tools
from src.agents.scoring_agent import aggregate_final_scores, calculate_focus_areas

# Check tool structure
print(f"   aggregate_final_scores is a: {type(aggregate_final_scores)}")
print(f"   calculate_focus_areas is a: {type(calculate_focus_areas)}")

# Save diagnostic results
output = {
    "test_timestamp": datetime.now().isoformat(),
    "execution_time": execution_time if 'execution_time' in locals() else None,
    "function_calls": function_calls,
    "scoring_result": scoring_result if 'scoring_result' in locals() else None,
    "warnings": []
}

if 'execution_time' in locals() and execution_time < 0.1:
    output["warnings"].append("Execution too fast")
if not function_calls:
    output["warnings"].append("No scoring functions called")

filename = f"output_scoring_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Diagnostic results saved to: {filename}")

# Final diagnosis
print("\n" + "=" * 60)
print("DIAGNOSIS:")
if not function_calls:
    print("❌ The scoring node is NOT calling the individual scoring functions")
    print("   This explains why it completes in nanoseconds")
    print("   The node may be using the CrewAI tools incorrectly or bypassing them")
else:
    print("✅ Scoring functions are being called")
    print(f"   Total functions called: {len(function_calls)}")

print("=" * 60)

# Save complete output including terminal
def save_complete_output():
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    
    # Add terminal output to the existing output dict
    output["terminal_output"] = _stdout_capture.getvalue().split('\n')
    if _stderr_capture.getvalue():
        output["stderr_output"] = _stderr_capture.getvalue().split('\n')
    
    # Save again with terminal output included
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Complete output (including terminal) saved to: {filename}")

save_complete_output()