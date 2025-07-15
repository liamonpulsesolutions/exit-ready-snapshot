#!/usr/bin/env python
"""
Test the fixed scoring node directly with timing
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

print("🧪 TESTING FIXED SCORING NODE")
print("=" * 60)

# Force module reload to get latest version
print("\n1️⃣ Force reloading modules...")
modules_to_reload = [
    'src.nodes.scoring_node',
    'src.agents.scoring_agent',
    'src.utils.json_helper'
]

for module in modules_to_reload:
    if module in sys.modules:
        del sys.modules[module]
        print(f"   Cleared {module}")

# Import fresh
from src.nodes.scoring_node import scoring_node

print("\n2️⃣ Creating comprehensive test state...")

test_state = {
    "uuid": "fixed-scoring-test",
    "form_data": {
        "industry": "Technology/Software",
        "revenue_range": "$10M-$25M",
        "years_in_business": "5-10 years",
        "exit_timeline": "1-2 years",
        "responses": {
            "q1": "I handle all strategic decisions but have a COO for operations",
            "q2": "Up to 1 week",
            "q3": "SaaS subscriptions 70%, Services 30%",
            "q4": "60%+",
            "q5": "8",
            "q6": "Grew 10-25%",
            "q7": "COO handles operations, but technical knowledge is with me",
            "q8": "7",
            "q9": "Proprietary AI technology that saves customers 40% time",
            "q10": "8"
        }
    },
    "anonymized_data": {
        "responses": {
            "q1": "I handle all strategic decisions but have a COO for operations",
            "q2": "Up to 1 week",
            "q3": "SaaS subscriptions 70%, Services 30%",
            "q4": "60%+",
            "q5": "8",
            "q6": "Grew 10-25%",
            "q7": "COO handles operations, but technical knowledge is with me",
            "q8": "7",
            "q9": "Proprietary AI technology that saves customers 40% time",
            "q10": "8"
        },
        "industry": "Technology/Software",
        "revenue_range": "$10M-$25M",
        "years_in_business": "5-10 years",
        "exit_timeline": "1-2 years"
    },
    "research_result": {
        "structured_findings": {
            "valuation_benchmarks": {
                "ebitda_multiples": {"low": 5, "high": 8},
                "revenue_multiples": {"low": 2, "high": 3.5}
            },
            "improvement_strategies": {
                "reduce_owner_dependence": "Document technical knowledge",
                "increase_recurring": "Focus on SaaS growth"
            },
            "market_conditions": {
                "buyer_priorities": ["Recurring revenue", "Technical moat"],
                "favorable": True
            }
        }
    },
    "industry": "Technology/Software",
    "revenue_range": "$10M-$25M",
    "years_in_business": "5-10 years",
    "exit_timeline": "1-2 years",
    "processing_time": {},
    "messages": [],
    "current_stage": "scoring"
}

print("   ✅ Rich test data created")

print("\n3️⃣ Monitoring scoring execution...")

# Track actual wall clock time
wall_start = time.time()

try:
    # Run the scoring node
    print("\n   🚀 Executing scoring node...\n")
    result_state = scoring_node(test_state)
    
    wall_end = time.time()
    wall_time = wall_end - wall_start
    
    print(f"\n   ✅ Scoring completed!")
    print(f"   ⏱️  Wall clock time: {wall_time:.4f}s")
    
    # Check reported processing time
    reported_time = result_state.get("processing_time", {}).get("scoring", 0)
    print(f"   ⏱️  Reported time: {reported_time:.4f}s")
    
    # Analyze execution speed
    if wall_time < 0.01:
        print("\n   ⚠️  WARNING: Still executing too fast!")
        print("   The scoring functions are likely NOT being called")
    elif wall_time < 0.1:
        print("\n   ⚠️  Moderately fast - might be using cached/default values")
    else:
        print("\n   ✅ Execution time looks reasonable for actual scoring")
    
    # Check results
    scoring_result = result_state.get("scoring_result", {})
    
    print("\n4️⃣ Analyzing results...")
    print(f"\n   Overall Score: {scoring_result.get('overall_score')}/10")
    print(f"   Readiness: {scoring_result.get('readiness_level')}")
    print(f"   Status: {scoring_result.get('status')}")
    
    # Check category scores
    category_scores = scoring_result.get("category_scores", {})
    if category_scores:
        print("\n   Category Scores:")
        for cat, data in category_scores.items():
            score = data.get("score", "N/A")
            print(f"   - {cat}: {score}/10")
    
    # Check if scores are varied (not all defaults)
    scores = [v.get("score", 0) for v in category_scores.values() if isinstance(v, dict)]
    unique_scores = len(set(scores))
    
    if unique_scores == 1:
        print("\n   ⚠️  WARNING: All categories have the same score!")
        print("   This suggests default values rather than actual calculations")
    else:
        print(f"\n   ✅ Found {unique_scores} different scores - looks like real calculations")
    
except Exception as e:
    print(f"\n   ❌ Error during execution: {str(e)}")
    import traceback
    traceback.print_exc()
    wall_time = -1

# Save results
output = {
    "test_name": "fixed_scoring_direct_test",
    "timestamp": datetime.now().isoformat(),
    "wall_clock_time": wall_time,
    "reported_processing_time": reported_time if 'reported_time' in locals() else None,
    "execution_fast": wall_time < 0.01 if wall_time > 0 else None,
    "scoring_result": scoring_result if 'scoring_result' in locals() else None,
    "unique_scores": unique_scores if 'unique_scores' in locals() else 0,
    "error": str(e) if 'e' in locals() else None
}

# Save with terminal output
sys.stdout = _original_stdout
output["terminal_output"] = _stdout_capture.getvalue().split('\n')

filename = f"output_fixed_scoring_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Complete results saved to: {filename}")

# Final verdict
print("\n" + "=" * 60)
print("FINAL VERDICT:")
if wall_time > 0.1 and unique_scores > 3:
    print("✅ The fixed scoring node appears to be working correctly!")
else:
    print("❌ The scoring node is still not executing properly")
    print("   Please ensure the fixed version is saved and modules are reloaded")
print("=" * 60)