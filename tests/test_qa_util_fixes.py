#!/usr/bin/env python3
"""
Test script to verify LLM utils and QA node fixes.
Tests percentage parsing, model name extraction, and JSON response handling.
"""

import os
import sys
import json
import logging
import time
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

# Capture output using TeeOutput pattern
_original_stdout = sys.stdout
_original_stderr = sys.stderr
_stdout_capture = StringIO()
_stderr_capture = StringIO()

class TeeOutput:
    """Write to both capture and original output"""
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

# Start capturing
sys.stdout = TeeOutput(_stdout_capture, _original_stdout)
sys.stderr = TeeOutput(_stderr_capture, _original_stderr)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG to see model name extraction
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Store all test data
_test_data = {
    "test_name": "test_llm_fixes.py",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": [],
    "tests": []
}

def log_test(name, passed, details=None):
    """Log a test result"""
    test_result = {
        "name": name,
        "passed": passed,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        test_result["details"] = details
    _test_data["tests"].append(test_result)
    
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details and not passed:
        print(f"   Details: {details}")


print("\n" + "="*80)
print("🧪 TESTING LLM UTILS AND QA NODE FIXES")
print("="*80 + "\n")


# Test 1: Percentage Parsing
print("📊 Test 1: Percentage Parsing")
print("-" * 50)

try:
    from workflow.nodes.summary import parse_percentage_range
    
    test_cases = [
        ("15%", "10-20%"),
        ("10-20%", "10-20%"),
        ("Up to 15% increase", "10-15%"),
        ("15-25% improvement", "15-25%"),
        ("Up to 15 increase in valuations", "10-15%"),
        ("", "10-20%"),
        (None, "10-20%"),
        ("no numbers here", "10-20%"),
        ("25", "20-30%"),
        ("up to 40%", "26-40%"),
    ]
    
    all_passed = True
    for input_val, expected in test_cases:
        result = parse_percentage_range(input_val)
        passed = result == expected
        all_passed &= passed
        
        status = "✓" if passed else "✗"
        print(f"   {status} parse_percentage_range({repr(input_val)}) = {repr(result)} (expected {repr(expected)})")
        
        if not passed:
            log_test(f"parse_percentage_range({repr(input_val)})", False, 
                    {"result": result, "expected": expected})
    
    log_test("Percentage parsing", all_passed)
    _test_data["results"]["percentage_parsing"] = all_passed
    
except Exception as e:
    print(f"   ❌ Error testing percentage parsing: {e}")
    log_test("Percentage parsing", False, {"error": str(e)})
    _test_data["errors"].append({"test": "percentage_parsing", "error": str(e)})


# Test 2: LLM Model Name Extraction
print(f"\n📊 Test 2: LLM Model Name Extraction")
print("-" * 50)

try:
    from workflow.core.llm_utils import get_llm_with_fallback, ensure_json_response
    from langchain.schema import SystemMessage, HumanMessage
    
    # Create an LLM instance
    print("   Creating LLM instance...")
    llm = get_llm_with_fallback("gpt-4.1-mini", temperature=0.1)
    
    # Check if custom attribute was set
    has_custom_attr = hasattr(llm, '_custom_model_name')
    print(f"   Has _custom_model_name attribute: {has_custom_attr}")
    
    if has_custom_attr:
        print(f"   Model name: {llm._custom_model_name}")
        log_test("LLM custom attribute", True, {"model_name": llm._custom_model_name})
    else:
        log_test("LLM custom attribute", False, {"error": "Missing _custom_model_name"})
    
    # Test ensure_json_response
    print("\n   Testing ensure_json_response...")
    messages = [
        SystemMessage(content="You are a test assistant."),
        HumanMessage(content='Respond with JSON: {"test": "success", "number": 42}')
    ]
    
    start_time = time.time()
    result = ensure_json_response(llm, messages, "test_ensure_json")
    elapsed = time.time() - start_time
    
    print(f"   Response time: {elapsed:.2f}s")
    print(f"   Response type: {type(result)}")
    print(f"   Response: {result}")
    
    # Check if it's a valid response
    is_valid = isinstance(result, dict) and elapsed > 0.5  # Should take >0.5s for real API call
    log_test("ensure_json_response", is_valid, {
        "elapsed": elapsed,
        "response": result,
        "is_dict": isinstance(result, dict)
    })
    
    _test_data["results"]["llm_model_extraction"] = has_custom_attr and is_valid
    
except Exception as e:
    print(f"   ❌ Error testing LLM utils: {e}")
    log_test("LLM model extraction", False, {"error": str(e)})
    _test_data["errors"].append({"test": "llm_model_extraction", "error": str(e)})


# Test 3: QA Node LLM Calls
print(f"\n📊 Test 3: QA Node LLM Functions")
print("-" * 50)

try:
    from workflow.nodes.qa import (
        check_redundancy_llm,
        check_tone_consistency_llm,
        verify_citations_llm,
        verify_outcome_framing_llm
    )
    
    # Create test LLM
    qa_llm = get_llm_with_fallback("gpt-4.1-nano", temperature=0)
    
    # Test report content
    test_report = """EXECUTIVE SUMMARY
    
    Your business scored 6.5/10 indicating solid readiness with room for improvement.
    
    RECOMMENDATIONS
    
    This will increase your value by 30% in 6 months.
    You will achieve premium multiples.
    Document processes - businesses typically see 20-30% faster sales (IBBA 2023).
    """
    
    # Test redundancy check
    print("\n   Testing redundancy check...")
    start_time = time.time()
    redundancy_result = check_redundancy_llm(test_report, qa_llm)
    elapsed = time.time() - start_time
    
    print(f"   Redundancy check time: {elapsed:.2f}s")
    print(f"   Redundancy score: {redundancy_result.get('redundancy_score', 'N/A')}/10")
    
    redundancy_passed = (
        elapsed > 0.5 and 
        isinstance(redundancy_result, dict) and 
        'redundancy_score' in redundancy_result
    )
    log_test("check_redundancy_llm", redundancy_passed, {
        "elapsed": elapsed,
        "score": redundancy_result.get('redundancy_score')
    })
    
    # Test tone consistency
    print("\n   Testing tone consistency...")
    start_time = time.time()
    tone_result = check_tone_consistency_llm(test_report, qa_llm)
    elapsed = time.time() - start_time
    
    print(f"   Tone check time: {elapsed:.2f}s")
    print(f"   Tone score: {tone_result.get('tone_score', 'N/A')}/10")
    
    tone_passed = (
        elapsed > 0.5 and 
        isinstance(tone_result, dict) and 
        'tone_score' in tone_result
    )
    log_test("check_tone_consistency_llm", tone_passed, {
        "elapsed": elapsed,
        "score": tone_result.get('tone_score')
    })
    
    # Test outcome framing
    print("\n   Testing outcome framing...")
    start_time = time.time()
    framing_result = verify_outcome_framing_llm(
        test_report,
        "This will increase value by 30%",
        "You will achieve results",
        qa_llm
    )
    elapsed = time.time() - start_time
    
    print(f"   Outcome framing time: {elapsed:.2f}s")
    print(f"   Framing score: {framing_result.get('framing_score', 'N/A')}/10")
    print(f"   Violations found: {framing_result.get('violations_found', 'N/A')}")
    
    # Should find violations in test content
    framing_passed = (
        elapsed > 0.5 and 
        isinstance(framing_result, dict) and 
        'framing_score' in framing_result and
        framing_result.get('violations_found', 0) > 0  # Should find "will" violations
    )
    log_test("verify_outcome_framing_llm", framing_passed, {
        "elapsed": elapsed,
        "score": framing_result.get('framing_score'),
        "violations": framing_result.get('violations_found')
    })
    
    _test_data["results"]["qa_llm_calls"] = all([redundancy_passed, tone_passed, framing_passed])
    
except Exception as e:
    print(f"   ❌ Error testing QA functions: {e}")
    log_test("QA LLM functions", False, {"error": str(e)})
    _test_data["errors"].append({"test": "qa_llm_functions", "error": str(e)})


# Test 4: Error Handling and Fallbacks
print(f"\n📊 Test 4: Error Handling and Fallbacks")
print("-" * 50)

try:
    # Test with invalid messages to trigger fallbacks
    print("   Testing fallback on invalid JSON response...")
    
    # Create messages that might not return JSON
    bad_messages = [
        SystemMessage(content="You are a test assistant."),
        HumanMessage(content="Just say hello, don't use JSON")
    ]
    
    start_time = time.time()
    result = ensure_json_response(qa_llm, bad_messages, "test_fallback", retry_count=2)
    elapsed = time.time() - start_time
    
    print(f"   Fallback test time: {elapsed:.2f}s")
    print(f"   Got result: {result}")
    print(f"   Is dict: {isinstance(result, dict)}")
    
    fallback_passed = isinstance(result, dict)  # Should always return dict even on failure
    log_test("ensure_json_response fallback", fallback_passed, {
        "elapsed": elapsed,
        "result": result
    })
    
    _test_data["results"]["error_handling"] = fallback_passed
    
except Exception as e:
    print(f"   ❌ Error testing fallbacks: {e}")
    log_test("Error handling", False, {"error": str(e)})
    _test_data["errors"].append({"test": "error_handling", "error": str(e)})


# Summary
print("\n" + "="*80)
print("📈 TEST SUMMARY")
print("="*80)

total_tests = len(_test_data["tests"])
passed_tests = sum(1 for t in _test_data["tests"] if t["passed"])
failed_tests = total_tests - passed_tests

print(f"\nTotal Tests: {total_tests}")
print(f"Passed: {passed_tests} ✅")
print(f"Failed: {failed_tests} ❌")

if failed_tests > 0:
    print("\nFailed Tests:")
    for test in _test_data["tests"]:
        if not test["passed"]:
            print(f"  - {test['name']}")
            if test.get("details"):
                print(f"    Details: {test['details']}")

print("\nKey Results:")
for key, value in _test_data["results"].items():
    status = "✅" if value else "❌"
    print(f"  {status} {key}: {value}")

if _test_data["errors"]:
    print("\nErrors Encountered:")
    for error in _test_data["errors"]:
        print(f"  - {error['test']}: {error['error']}")

# Save output
def save_test_output():
    """Save all captured output to JSON"""
    # Restore original stdout/stderr
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    
    # Add captured output
    _test_data["terminal_output"] = _stdout_capture.getvalue().split('\n')
    if _stderr_capture.getvalue():
        _test_data["stderr_output"] = _stderr_capture.getvalue().split('\n')
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output_test_llm_fixes_{timestamp}.json"
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete test output saved to: {filename}")

save_test_output()

# Final verdict
if failed_tests == 0 and not _test_data["errors"]:
    print("\n✨ All fixes verified successfully! Ready to run E2E test.")
else:
    print("\n⚠️  Some issues remain. Review the failed tests above.")