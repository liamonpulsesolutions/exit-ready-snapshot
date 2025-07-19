#!/usr/bin/env python3
"""
Diagnostic test to identify state management issues in QA node.
Tests state passing between nodes and the bind() compatibility issue.
"""

import os
import sys
import json
import time
import logging
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
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Store all test data
_test_data = {
    "test_name": "test_qa_state_diagnostic.py",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": [],
    "diagnostics": []
}

print("\n" + "="*80)
print("🔍 QA STATE MANAGEMENT DIAGNOSTIC")
print("="*80 + "\n")

# Test 1: Simulate State Passing
print("📊 Test 1: State Passing Simulation")
print("-" * 50)

try:
    # Create a mock state like what summary node produces
    mock_state = {
        "uuid": "test-uuid-123",
        "current_stage": "summary",
        "summary_result": {
            "status": "success",
            "executive_summary": "Your business scored 7.5/10 showing strong readiness.",
            "category_summaries": {
                "financial_readiness": {
                    "summary": "Strong financial performance with consistent growth.",
                    "score": 7.5
                },
                "revenue_quality": {
                    "summary": "Recurring revenue provides stability.",
                    "score": 8.0
                },
                "operational_resilience": {
                    "summary": "Well-documented processes ensure continuity.",
                    "score": 7.0
                }
            },
            "recommendations": "Focus on improving documentation. Companies typically see 20-30% value increase.",
            "final_report": "EXIT READY SNAPSHOT\n\nOverall Score: 7.5/10\n\nYour business shows strong readiness.",
            "report_metadata": {
                "overall_score": 7.5,
                "word_count": 1500
            }
        },
        "scoring_result": {
            "overall_score": 7.5,
            "category_scores": {
                "financial_performance": 7.5,
                "revenue_stability": 8.0,
                "operations_efficiency": 7.0
            }
        },
        "research_result": {
            "citations": [
                {"source": "IBBA Market Report", "year": "2023"}
            ]
        },
        "messages": [],
        "processing_time": {}
    }
    
    print("✅ Created mock state with summary_result")
    print(f"   Keys in state: {list(mock_state.keys())}")
    print(f"   Keys in summary_result: {list(mock_state['summary_result'].keys())}")
    
    _test_data["diagnostics"].append({
        "test": "mock_state_creation",
        "success": True,
        "state_keys": list(mock_state.keys()),
        "summary_keys": list(mock_state['summary_result'].keys())
    })
    
except Exception as e:
    print(f"❌ Failed to create mock state: {e}")
    _test_data["errors"].append({
        "test": "mock_state_creation",
        "error": str(e)
    })

# Test 2: Test ensure_json_response vs bind()
print("\n📊 Test 2: ensure_json_response vs bind() Compatibility")
print("-" * 50)

try:
    from workflow.core.llm_utils import get_llm_with_fallback, ensure_json_response
    from langchain.schema import SystemMessage, HumanMessage
    
    # Create base LLM
    base_llm = get_llm_with_fallback("gpt-4.1-nano", temperature=0)
    
    # Test 1: Using ensure_json_response (old method)
    print("\n   Testing ensure_json_response method:")
    messages = [
        SystemMessage(content="You are a helpful assistant. Always respond with JSON."),
        HumanMessage(content='Return JSON: {"test": "old_method", "value": 123}')
    ]
    
    start = time.time()
    try:
        result1 = ensure_json_response(base_llm, messages, "test_old_method")
        elapsed1 = time.time() - start
        print(f"   ✅ Old method succeeded in {elapsed1:.2f}s")
        print(f"   Result: {result1}")
        
        _test_data["diagnostics"].append({
            "test": "ensure_json_response",
            "success": True,
            "elapsed": elapsed1,
            "result": result1
        })
    except Exception as e:
        print(f"   ❌ Old method failed: {e}")
        _test_data["errors"].append({
            "test": "ensure_json_response",
            "error": str(e)
        })
    
    # Test 2: Using bind() directly
    print("\n   Testing bind() method:")
    bound_llm = base_llm.bind(response_format={"type": "json_object"})
    
    start = time.time()
    try:
        response = bound_llm.invoke(messages)
        elapsed2 = time.time() - start
        
        # Extract content
        content = response.content if hasattr(response, 'content') else str(response)
        result2 = json.loads(content)
        
        print(f"   ✅ Bind method succeeded in {elapsed2:.2f}s")
        print(f"   Result: {result2}")
        
        _test_data["diagnostics"].append({
            "test": "bind_method",
            "success": True,
            "elapsed": elapsed2,
            "result": result2
        })
    except Exception as e:
        print(f"   ❌ Bind method failed: {e}")
        _test_data["errors"].append({
            "test": "bind_method",
            "error": str(e)
        })
    
    # Test 3: Using bind() with ensure_json_response wrapper
    print("\n   Testing bind() + ensure_json_response (current QA implementation):")
    bound_llm2 = base_llm.bind(response_format={"type": "json_object"})
    
    start = time.time()
    try:
        # This is what QA node does - it's redundant and causes issues
        result3 = ensure_json_response(bound_llm2, messages, "test_combined")
        elapsed3 = time.time() - start
        
        print(f"   ✅ Combined method succeeded in {elapsed3:.2f}s")
        print(f"   Result: {result3}")
        
        _test_data["diagnostics"].append({
            "test": "bind_plus_ensure",
            "success": True,
            "elapsed": elapsed3,
            "result": result3
        })
    except Exception as e:
        print(f"   ❌ Combined method failed: {e}")
        print(f"   This is likely the QA node issue!")
        _test_data["errors"].append({
            "test": "bind_plus_ensure",
            "error": str(e),
            "note": "This is the QA node pattern that fails"
        })

except Exception as e:
    print(f"❌ Failed to test LLM methods: {e}")
    _test_data["errors"].append({
        "test": "llm_method_comparison",
        "error": str(e)
    })

# Test 3: Test QA Function with Different Approaches
print("\n📊 Test 3: QA Function with Different LLM Approaches")
print("-" * 50)

try:
    from workflow.nodes.qa import parse_json_with_fixes
    
    # Create test report
    test_report = mock_state["summary_result"]["final_report"]
    
    # Approach 1: Direct LLM call with manual JSON parsing
    print("\n   Approach 1: Direct LLM call:")
    direct_llm = get_llm_with_fallback("gpt-4.1-nano", temperature=0)
    
    messages = [
        SystemMessage(content="Analyze for redundancy. Respond with JSON containing redundancy_score (1-10)."),
        HumanMessage(content=f"Analyze this report:\n\n{test_report}")
    ]
    
    start = time.time()
    try:
        response = direct_llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Try to parse JSON
        try:
            result = json.loads(content)
        except:
            # Use the QA node's JSON fixer
            result = parse_json_with_fixes(content, "direct_llm_test")
        
        elapsed = time.time() - start
        print(f"   ✅ Direct call succeeded in {elapsed:.2f}s")
        print(f"   Score: {result.get('redundancy_score', 'N/A')}")
        
        _test_data["diagnostics"].append({
            "test": "direct_llm_approach",
            "success": True,
            "elapsed": elapsed,
            "score": result.get('redundancy_score')
        })
    except Exception as e:
        print(f"   ❌ Direct call failed: {e}")
        _test_data["errors"].append({
            "test": "direct_llm_approach",
            "error": str(e)
        })
    
    # Approach 2: Using bind() without ensure_json_response
    print("\n   Approach 2: Bind only (no ensure wrapper):")
    bound_only_llm = direct_llm.bind(response_format={"type": "json_object"})
    
    start = time.time()
    try:
        response = bound_only_llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        result = json.loads(content)
        
        elapsed = time.time() - start
        print(f"   ✅ Bind-only succeeded in {elapsed:.2f}s")
        print(f"   Score: {result.get('redundancy_score', 'N/A')}")
        
        _test_data["diagnostics"].append({
            "test": "bind_only_approach",
            "success": True,
            "elapsed": elapsed,
            "score": result.get('redundancy_score')
        })
    except Exception as e:
        print(f"   ❌ Bind-only failed: {e}")
        _test_data["errors"].append({
            "test": "bind_only_approach",
            "error": str(e)
        })

except Exception as e:
    print(f"❌ Failed to test QA approaches: {e}")
    _test_data["errors"].append({
        "test": "qa_approaches",
        "error": str(e)
    })

# Test 4: Actual QA Function Call
print("\n📊 Test 4: Actual QA Function Execution")
print("-" * 50)

try:
    from workflow.nodes.qa import check_redundancy_llm
    
    # Create LLM as QA node does
    qa_llm = get_llm_with_fallback("gpt-4.1-nano", temperature=0, max_tokens=8000)
    
    print("   Testing check_redundancy_llm function...")
    start = time.time()
    
    try:
        result = check_redundancy_llm(test_report, qa_llm)
        elapsed = time.time() - start
        
        print(f"   Function execution time: {elapsed:.2f}s")
        print(f"   Result: {result}")
        
        if elapsed < 0.1:
            print(f"   ⚠️  WARNING: Execution too fast ({elapsed:.3f}s) - likely not calling LLM")
        
        _test_data["diagnostics"].append({
            "test": "check_redundancy_llm",
            "success": elapsed > 0.5,
            "elapsed": elapsed,
            "result": result,
            "warning": "Execution too fast - no LLM call" if elapsed < 0.1 else None
        })
        
    except Exception as e:
        print(f"   ❌ Function failed: {e}")
        _test_data["errors"].append({
            "test": "check_redundancy_llm",
            "error": str(e)
        })
        
except Exception as e:
    print(f"❌ Failed to test QA function: {e}")
    _test_data["errors"].append({
        "test": "qa_function_test",
        "error": str(e)
    })

# Summary and Analysis
print("\n" + "="*80)
print("📈 DIAGNOSTIC SUMMARY")
print("="*80)

# Analyze results
successful_tests = sum(1 for d in _test_data["diagnostics"] if d.get("success", False))
total_tests = len(_test_data["diagnostics"])
errors = len(_test_data["errors"])

print(f"\nTests run: {total_tests}")
print(f"Successful: {successful_tests}")
print(f"Failed: {total_tests - successful_tests}")
print(f"Errors: {errors}")

# Key findings
print("\n🔍 ROOT CAUSE ANALYSIS:")

# Check for bind + ensure issue
bind_ensure_error = next((e for e in _test_data["errors"] if e.get("test") == "bind_plus_ensure"), None)
if bind_ensure_error:
    print("\n❌ CRITICAL ISSUE FOUND:")
    print("   The combination of bind() + ensure_json_response is incompatible!")
    print("   This is why QA node LLM calls fail immediately.")
    print(f"   Error: {bind_ensure_error['error']}")
    print("\n   SOLUTION: Remove ensure_json_response wrapper when using bind()")

# Check execution speed
fast_executions = [d for d in _test_data["diagnostics"] if d.get("elapsed", 1) < 0.1]
if fast_executions:
    print("\n⚠️  PERFORMANCE ISSUE:")
    print(f"   {len(fast_executions)} tests executed too fast (<0.1s)")
    print("   This indicates LLM calls are not being made")

# Recommendations
print("\n💡 RECOMMENDATIONS:")
print("1. Remove ensure_json_response when using bind() - they're incompatible")
print("2. Use bind() directly for JSON responses, not through wrappers")
print("3. Add proper error handling for malformed JSON responses")
print("4. Ensure state is properly passed between nodes")

# Save complete output
def save_test_output():
    """Save all captured output to JSON"""
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    
    _test_data["terminal_output"] = _stdout_capture.getvalue().split('\n')
    if _stderr_capture.getvalue():
        _test_data["stderr_output"] = _stderr_capture.getvalue().split('\n')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output_qa_state_diagnostic_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete diagnostic output saved to: {filename}")

save_test_output()

print("\n✅ Diagnostic complete - check output file for full details")