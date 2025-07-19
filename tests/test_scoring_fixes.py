#!/usr/bin/env python3
"""
Test the scoring node fixes before running full E2E.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from io import StringIO

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

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

_test_data = {
    "test_name": "test_scoring_fixes.py",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": []
}

print("\n" + "="*80)
print("🧪 TESTING SCORING NODE FIXES")
print("="*80 + "\n")

try:
    # Test 1: Check the safe_get function
    print("📝 Test 1: Testing safe_get function")
    print("-" * 50)
    
    from workflow.nodes.scoring import safe_get
    
    test_data = {
        "level1": {
            "level2": {
                "level3": "value"
            }
        }
    }
    
    # Test valid path
    result1 = safe_get(test_data, "level1.level2.level3", "default")
    print(f"Valid path: {result1} (expected: 'value')")
    _test_data["results"]["safe_get_valid"] = result1 == "value"
    
    # Test invalid path
    result2 = safe_get(test_data, "level1.missing.level3", "default")
    print(f"Invalid path: {result2} (expected: 'default')")
    _test_data["results"]["safe_get_invalid"] = result2 == "default"
    
    # Test with string instead of dict
    result3 = safe_get("not a dict", "some.path", "fallback")
    print(f"Non-dict input: {result3} (expected: 'fallback')")
    _test_data["results"]["safe_get_string"] = result3 == "fallback"
    
    # Test 2: Check generate_category_insights with mock data
    print("\n📝 Test 2: Testing generate_category_insights")
    print("-" * 50)
    
    from workflow.nodes.scoring import generate_category_insights
    from workflow.core.llm_utils import get_llm_with_fallback
    
    # Create mock data that mimics the real structure
    mock_score_data = {
        "score": 6.5,
        "strengths": ["Good documentation", "Regular time away"],
        "gaps": ["Key person dependencies", "No succession plan"],
        "industry_context": {"benchmark": "Industry leaders delegate 80% of operations"}
    }
    
    mock_responses = {
        "q1": "I handle all quality control final sign-offs",
        "q2": "3-7 days",
        "industry": "Manufacturing & Production"
    }
    
    # This is the structure that was causing issues
    mock_research_data = {
        "market_conditions": {
            "key_trend": {
                "trend": "Automation and tech integration valued"
            }
        },
        "valuation_benchmarks": {
            "recurring_revenue": {
                "premium": "1.5-2x multiple for 60%+ recurring"
            }
        }
    }
    
    # Create LLM
    test_llm = get_llm_with_fallback("gpt-4.1-nano", temperature=0)
    
    print("Testing with properly structured data...")
    try:
        # This should work without errors
        insight = generate_category_insights(
            "owner_dependence",
            mock_score_data,
            mock_responses,
            mock_research_data,
            test_llm
        )
        
        print(f"✅ Generated insight: {insight[:100]}...")
        _test_data["results"]["generate_insights_success"] = True
        _test_data["results"]["insight_sample"] = insight[:200]
        
    except Exception as e:
        print(f"❌ Error: {e}")
        _test_data["errors"].append(str(e))
        _test_data["results"]["generate_insights_success"] = False
    
    # Test 3: Check with malformed research_data
    print("\n📝 Test 3: Testing with malformed research_data")
    print("-" * 50)
    
    # This simulates what might have been happening
    bad_research_data = "not a dictionary"
    
    print("Testing with string instead of dict...")
    try:
        insight = generate_category_insights(
            "owner_dependence",
            mock_score_data,
            mock_responses,
            bad_research_data,  # This would have caused the original error
            test_llm
        )
        
        # With safe_get, this should still work
        print(f"✅ Handled gracefully: {insight[:100]}...")
        _test_data["results"]["handle_bad_data"] = True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        _test_data["errors"].append(str(e))
        _test_data["results"]["handle_bad_data"] = False
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    all_passed = all([
        _test_data["results"].get("safe_get_valid", False),
        _test_data["results"].get("safe_get_invalid", False),
        _test_data["results"].get("safe_get_string", False),
        _test_data["results"].get("generate_insights_success", False),
        _test_data["results"].get("handle_bad_data", False)
    ])
    
    if all_passed:
        print("\n✅ All tests passed! The scoring node fixes are working.")
        print("\n🚀 Ready to run the full E2E test again.")
    else:
        print("\n❌ Some tests failed. Review the output above.")
        for key, value in _test_data["results"].items():
            print(f"  {key}: {'✅' if value else '❌'}")
    
except Exception as e:
    print(f"\n❌ Critical error: {e}")
    import traceback
    traceback.print_exc()
    _test_data["errors"].append({
        "error": str(e),
        "traceback": traceback.format_exc()
    })

finally:
    sys.stdout = _original_stdout
    _test_data["terminal_output"] = _stdout_capture.getvalue().split('\n')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output_scoring_fixes_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Test output saved to: {filename}")