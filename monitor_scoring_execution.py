#!/usr/bin/env python
"""
Monitor actual execution of scoring functions
"""

import sys
import os
import json
import time
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

print("🔍 MONITORING SCORING FUNCTION EXECUTION")
print("=" * 60)

# Force reload of modules
print("\n1️⃣ Force reloading modules...")
modules_to_reload = [
    'src.nodes.scoring_node',
    'src.agents.scoring_agent',
]

for module_name in modules_to_reload:
    if module_name in sys.modules:
        del sys.modules[module_name]
        print(f"   Cleared {module_name}")

# Now import fresh
import src.nodes.scoring_node as scoring_node_module
import src.agents.scoring_agent as scoring_agent_module

# Track actual function calls with detailed info
function_calls = []

def create_monitor(func_name, original_func):
    """Create a monitoring wrapper for a function"""
    def monitor_wrapper(*args, **kwargs):
        call_info = {
            "function": func_name,
            "timestamp": datetime.now().isoformat(),
            "start_time": time.time()
        }
        
        print(f"\n   📊 {func_name} CALLED")
        print(f"      Args: {len(args)}")
        print(f"      Kwargs: {list(kwargs.keys())}")
        
        # Check first arg (responses)
        if args:
            responses = args[0]
            if isinstance(responses, dict):
                print(f"      Response keys: {list(responses.keys())[:5]}...")
                call_info["response_count"] = len(responses)
        
        try:
            # Call original function
            result = original_func(*args, **kwargs)
            
            call_info["end_time"] = time.time()
            call_info["duration"] = call_info["end_time"] - call_info["start_time"]
            call_info["success"] = True
            
            # Check result
            if isinstance(result, dict):
                call_info["score"] = result.get("score", "N/A")
                print(f"      Returned score: {call_info['score']}")
                print(f"      Duration: {call_info['duration']:.4f}s")
            
            function_calls.append(call_info)
            return result
            
        except Exception as e:
            call_info["error"] = str(e)
            call_info["success"] = False
            function_calls.append(call_info)
            print(f"      ❌ ERROR: {e}")
            raise
    
    return monitor_wrapper

# Monitor all scoring functions
print("\n2️⃣ Installing monitors on scoring functions...")

scoring_functions = [
    'score_financial_performance',
    'score_revenue_stability',
    'score_operations_efficiency',
    'score_growth_value',
    'score_exit_readiness'
]

for func_name in scoring_functions:
    if hasattr(scoring_agent_module, func_name):
        original = getattr(scoring_agent_module, func_name)
        monitored = create_monitor(func_name, original)
        setattr(scoring_agent_module, func_name, monitored)
        # Also update in scoring_node if it imported them
        if hasattr(scoring_node_module, func_name):
            setattr(scoring_node_module, func_name, monitored)
        print(f"   ✅ Monitoring {func_name}")

# Create test state
print("\n3️⃣ Creating rich test state...")

test_state = {
    "uuid": "monitor-test",
    "anonymized_data": {
        "responses": {
            "q1": "I handle all strategic decisions",
            "q2": "Less than 3 days",
            "q3": "Services 60%, Products 40%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Grew 10-25%",
            "q7": "Critical knowledge with me",
            "q8": "5",
            "q9": "Strong customer relationships",
            "q10": "7"
        },
        "industry": "Professional Services",
        "revenue_range": "$5M-$10M",
        "years_in_business": "10-20 years",
        "exit_timeline": "1-2 years"
    },
    "research_result": {
        "structured_findings": {
            "valuation_benchmarks": {
                "ebitda_multiples": {"low": 4, "high": 6}
            }
        }
    },
    "processing_time": {},
    "messages": [],
    "current_stage": "scoring",
    # Add these at state level too
    "industry": "Professional Services",
    "revenue_range": "$5M-$10M",
    "years_in_business": "10-20 years",
    "exit_timeline": "1-2 years"
}

# Run the scoring node
print("\n4️⃣ Executing scoring node with monitors...")
print("-" * 60)

wall_start = time.time()

try:
    # Import the scoring_node function
    from src.nodes.scoring_node import scoring_node
    
    result = scoring_node(test_state)
    
    wall_end = time.time()
    wall_duration = wall_end - wall_start
    
    print("-" * 60)
    print(f"\n✅ Scoring completed in {wall_duration:.4f}s")
    
    # Analyze results
    scoring_result = result.get("scoring_result", {})
    print(f"\nOverall score: {scoring_result.get('overall_score')}")
    print(f"Status: {scoring_result.get('status')}")
    
    # Check function calls
    print(f"\n📊 FUNCTION CALL SUMMARY:")
    print(f"Total functions called: {len(function_calls)}")
    
    if function_calls:
        total_function_time = sum(call.get("duration", 0) for call in function_calls)
        print(f"Total time in functions: {total_function_time:.4f}s")
        print(f"Overhead time: {wall_duration - total_function_time:.4f}s")
        
        print("\nIndividual calls:")
        for call in function_calls:
            print(f"   - {call['function']}: {call.get('score', 'N/A')} in {call.get('duration', 0):.4f}s")
    else:
        print("   ❌ NO SCORING FUNCTIONS WERE CALLED!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    wall_duration = -1

# Save detailed results
output = {
    "timestamp": datetime.now().isoformat(),
    "wall_duration": wall_duration,
    "function_calls": function_calls,
    "function_count": len(function_calls),
    "total_function_time": sum(call.get("duration", 0) for call in function_calls),
    "scoring_result": scoring_result if 'scoring_result' in locals() else None,
    "terminal_output": _stdout_capture.getvalue().split('\n')
}

# Restore stdout
sys.stdout = _original_stdout

filename = f"output_monitor_scoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Detailed monitoring saved to: {filename}")
print("\n" + "=" * 60)
print("MONITORING COMPLETE")