#!/usr/bin/env python3
"""
Quick test to verify research node fix.
Tests data structure output without running full workflow.
"""

import os
import sys
import json
from datetime import datetime
from io import StringIO
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Capture output
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

print("\n" + "="*80)
print("🔬 TESTING RESEARCH NODE FIX")
print("="*80 + "\n")

# Test data
_test_data = {
    "test_name": "research_fix_test.py",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": []
}

try:
    # Import research node
    from workflow.nodes.research import research_node
    
    # Create minimal state
    test_state = {
        "uuid": "test-research-001",
        "messages": [],
        "processing_time": {},
        "anonymized_data": {
            "industry": "Manufacturing & Production",
            "location": "Northeast US",
            "revenue_range": "$10M-$25M",
            "responses": {
                "q1": "Test response",
                "q2": "3-7 days"
            }
        }
    }
    
    print("📊 Running research node...")
    
    # Execute research node
    result_state = research_node(test_state)
    
    # Check results
    research_result = result_state.get("research_result", {})
    
    print("\n✅ Research node completed")
    print(f"   Data source: {research_result.get('data_source', 'unknown')}")
    print(f"   Type of research_result: {type(research_result)}")
    print(f"   Keys in research_result: {list(research_result.keys())}")
    
    # Check critical structures
    print("\n🔍 Checking critical structures:")
    
    # 1. Check valuation_benchmarks
    val_benchmarks = research_result.get("valuation_benchmarks", {})
    print(f"   valuation_benchmarks type: {type(val_benchmarks)}")
    print(f"   valuation_benchmarks keys: {list(val_benchmarks.keys()) if isinstance(val_benchmarks, dict) else 'NOT A DICT'}")
    
    # 2. Check market_conditions
    market_conditions = research_result.get("market_conditions", {})
    print(f"   market_conditions type: {type(market_conditions)}")
    print(f"   market_conditions keys: {list(market_conditions.keys()) if isinstance(market_conditions, dict) else 'NOT A DICT'}")
    
    # 3. Check if it would work in scoring
    print("\n🧪 Testing scoring compatibility:")
    
    # Simulate what scoring node does
    industry = "Manufacturing & Production"
    
    # This is the line that was failing
    try:
        valuation_data = research_result.get('valuation_benchmarks', {})
        ebitda_data = valuation_data.get('base_EBITDA', {})
        
        if isinstance(ebitda_data, dict):
            ebitda_range = ebitda_data.get('range', '4-6x')
            print(f"   ✅ Can extract EBITDA range: {ebitda_range}")
        else:
            print(f"   ❌ ebitda_data is not a dict: {type(ebitda_data)}")
            
        # Test owner_dependence extraction
        owner_data = valuation_data.get('owner_dependence', {})
        if isinstance(owner_data, dict):
            days_threshold = owner_data.get('days_threshold', '14 days')
            print(f"   ✅ Can extract owner days threshold: {days_threshold}")
        else:
            print(f"   ❌ owner_data is not a dict: {type(owner_data)}")
            
    except Exception as e:
        print(f"   ❌ ERROR in data extraction: {e}")
        _test_data["errors"].append(str(e))
    
    # Log results
    _test_data["results"]["research_result_type"] = str(type(research_result))
    _test_data["results"]["research_result_keys"] = list(research_result.keys()) if isinstance(research_result, dict) else []
    _test_data["results"]["valuation_benchmarks_valid"] = isinstance(val_benchmarks, dict)
    _test_data["results"]["market_conditions_valid"] = isinstance(market_conditions, dict)
    
    print("\n📈 Summary:")
    if isinstance(research_result, dict) and isinstance(val_benchmarks, dict):
        print("   ✅ Research node fix appears to be working!")
        print("   Research data is properly structured for scoring node.")
    else:
        print("   ❌ Research node still has issues")
        print("   Research data structure is incorrect")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    _test_data["errors"].append({
        "error": str(e),
        "traceback": traceback.format_exc()
    })

finally:
    # Restore stdout/stderr
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    
    # Save output
    _test_data["terminal_output"] = _stdout_capture.getvalue().split('\n')
    if _stderr_capture.getvalue():
        _test_data["stderr_output"] = _stderr_capture.getvalue().split('\n')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output_research_fix_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Test output saved to: {filename}")