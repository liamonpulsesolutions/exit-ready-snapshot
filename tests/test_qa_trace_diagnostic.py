#!/usr/bin/env python3
"""
Diagnostic test to trace the exact failure point in QA node.
Intercepts and logs every step to identify where the issue occurs.
"""

import os
import sys
import json
import time
import logging
import traceback
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, Any

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

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Store all test data
_test_data = {
    "test_name": "test_qa_trace_diagnostic.py",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": [],
    "traces": []
}

def trace_step(step_name: str, data: Any = None) -> None:
    """Log a trace step with timing"""
    trace = {
        "step": step_name,
        "timestamp": datetime.now().isoformat(),
        "data": str(data)[:200] if data else None
    }
    _test_data["traces"].append(trace)
    print(f"   TRACE: {step_name}")
    if data:
        print(f"         Data: {str(data)[:100]}...")

print("\n" + "="*80)
print("🔍 QA NODE TRACE DIAGNOSTIC")
print("="*80 + "\n")

# Test 1: Replicate Exact QA Function Logic
print("📊 Test 1: Trace QA Function Execution")
print("-" * 50)

try:
    # Import exactly what QA node imports
    trace_step("import_start")
    from workflow.core.llm_utils import get_llm_with_fallback
    from langchain.schema import SystemMessage, HumanMessage
    trace_step("imports_complete")
    
    # Create test data matching what QA node receives
    test_report = """EXIT READY SNAPSHOT ASSESSMENT REPORT

============================================================

EXECUTIVE SUMMARY

Your business scored 7.5/10 showing strong readiness with focused improvements needed.

============================================================"""
    
    trace_step("test_data_created", {"report_length": len(test_report)})
    
    # Initialize LLM exactly as QA node does
    trace_step("llm_init_start")
    try:
        qa_llm = get_llm_with_fallback(
            model="gpt-4.1-nano",
            temperature=0,
            max_tokens=8000
        )
        trace_step("llm_init_success", {"llm_type": type(qa_llm).__name__})
    except Exception as e:
        trace_step("llm_init_failed", {"error": str(e), "traceback": traceback.format_exc()})
        raise
    
    # Create the exact prompt
    trace_step("prompt_creation_start")
    prompt = """Analyze this business assessment report for redundancy and repetitive content.

Report:
{report}

Evaluate:
1. Are key points repeated unnecessarily across sections?
2. Is the same information presented multiple times without adding value?
3. Are there verbose explanations that could be more concise?
4. Do multiple sections say essentially the same thing?

Important: Strategic repetition is ESSENTIAL in business reports:
- Key metrics appearing in summary and detailed sections is GOOD
- Important recommendations emphasized 2-3 times is EFFECTIVE
- Scores and critical findings in multiple contexts is NECESSARY

Only flag TRUE redundancy where:
- The exact same sentence appears 3+ times
- A concept is explained identically 4+ times with no new context
- Filler content repeats without purpose

Provide your analysis in this exact JSON format:
{{
    "redundancy_score": 8,
    "redundant_sections": ["list", "of", "truly", "redundant", "sections"],
    "specific_examples": ["exact duplicate content only"],
    "suggested_consolidations": ["only if truly excessive"]
}}S"""
    
    formatted_prompt = prompt.format(report=test_report[:10000])
    trace_step("prompt_created", {"prompt_length": len(formatted_prompt)})
    
    # Create messages
    trace_step("messages_creation_start")
    messages = [
        SystemMessage(content="You are an expert business communication analyst using GPT-4.1's superior comprehension. You understand the difference between strategic emphasis and true redundancy. Always respond with valid JSON."),
        HumanMessage(content=formatted_prompt)
    ]
    trace_step("messages_created", {"num_messages": len(messages)})
    
    # Try bind() method
    trace_step("bind_start")
    try:
        llm_with_json = qa_llm.bind(response_format={"type": "json_object"})
        trace_step("bind_success", {"bound_llm_type": type(llm_with_json).__name__})
    except Exception as e:
        trace_step("bind_failed", {"error": str(e), "traceback": traceback.format_exc()})
        _test_data["errors"].append({
            "step": "bind",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    
    # Try invoke
    trace_step("invoke_start")
    start_time = time.time()
    try:
        response = llm_with_json.invoke(messages)
        elapsed = time.time() - start_time
        trace_step("invoke_success", {
            "elapsed": elapsed,
            "response_type": type(response).__name__,
            "has_content": hasattr(response, 'content')
        })
        
        # Check response content
        if hasattr(response, 'content'):
            content = response.content
            trace_step("response_content", {
                "content_type": type(content).__name__,
                "content_length": len(content) if content else 0,
                "content_preview": str(content)[:100] if content else None
            })
        else:
            trace_step("response_no_content", {"response": str(response)[:100]})
            
    except Exception as e:
        elapsed = time.time() - start_time
        trace_step("invoke_failed", {
            "elapsed": elapsed,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        })
        _test_data["errors"].append({
            "step": "invoke",
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        })
        
        # This is likely where the QA node fails
        print(f"\n   ❌ CRITICAL FAILURE POINT: {type(e).__name__}: {str(e)}")
        
except Exception as e:
    trace_step("test1_failed", {"error": str(e), "traceback": traceback.format_exc()})
    _test_data["errors"].append({
        "test": "trace_qa_execution",
        "error": str(e),
        "traceback": traceback.format_exc()
    })

# Test 2: Compare with Working Node Pattern
print("\n📊 Test 2: Compare with Working Node Pattern")
print("-" * 50)

try:
    # Test how scoring node does it (which works)
    trace_step("scoring_pattern_start")
    
    # Scoring node pattern - simple invoke without bind
    scoring_llm = get_llm_with_fallback("gpt-4.1-mini", temperature=0.3)
    trace_step("scoring_llm_created")
    
    messages = [
        SystemMessage(content="You are an M&A advisor. Be concise."),
        HumanMessage(content="Provide 2-3 sentences about business readiness.")
    ]
    
    start_time = time.time()
    response = scoring_llm.invoke(messages)
    elapsed = time.time() - start_time
    
    trace_step("scoring_pattern_success", {
        "elapsed": elapsed,
        "response_type": type(response).__name__,
        "has_content": hasattr(response, 'content')
    })
    
    print(f"   ✅ Scoring pattern works: {elapsed:.2f}s")
    
except Exception as e:
    trace_step("scoring_pattern_failed", {"error": str(e)})
    print(f"   ❌ Scoring pattern failed: {e}")

# Test 3: Test bind() in isolation
print("\n📊 Test 3: Test bind() Method in Isolation")
print("-" * 50)

try:
    # Test if bind() works at all
    trace_step("isolated_bind_test_start")
    
    test_llm = get_llm_with_fallback("gpt-4.1-nano", temperature=0)
    trace_step("test_llm_created", {"has_bind": hasattr(test_llm, 'bind')})
    
    # Check LLM attributes
    llm_attrs = dir(test_llm)
    relevant_attrs = [attr for attr in llm_attrs if 'bind' in attr or 'format' in attr]
    trace_step("llm_attributes", {"relevant_attrs": relevant_attrs})
    
    # Try different bind approaches
    approaches = [
        ("standard_bind", lambda: test_llm.bind(response_format={"type": "json_object"})),
        ("minimal_bind", lambda: test_llm.bind()),
        ("direct_invoke", lambda: test_llm)
    ]
    
    for approach_name, approach_func in approaches:
        try:
            trace_step(f"{approach_name}_start")
            bound_llm = approach_func()
            
            # Try a minimal invoke
            start = time.time()
            response = bound_llm.invoke("Return JSON: {\"test\": true}")
            elapsed = time.time() - start
            
            trace_step(f"{approach_name}_success", {
                "elapsed": elapsed,
                "response_preview": str(response)[:50]
            })
            print(f"   ✅ {approach_name} works: {elapsed:.2f}s")
            
        except Exception as e:
            trace_step(f"{approach_name}_failed", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            print(f"   ❌ {approach_name} failed: {type(e).__name__}: {str(e)}")
            
except Exception as e:
    trace_step("isolated_bind_test_failed", {"error": str(e)})
    _test_data["errors"].append({
        "test": "isolated_bind_test",
        "error": str(e),
        "traceback": traceback.format_exc()
    })

# Test 4: Test parse_json_with_fixes
print("\n📊 Test 4: Test parse_json_with_fixes Function")
print("-" * 50)

try:
    from workflow.nodes.qa import parse_json_with_fixes
    
    # Test with the exact error message we see
    error_fragment = '\n    "redundancy_score"'
    
    trace_step("parse_error_fragment", {"fragment": repr(error_fragment)})
    
    try:
        result = parse_json_with_fixes(error_fragment, "test_error_fragment")
        trace_step("parse_error_success", {"result": result})
        print(f"   ✅ Parsed error fragment: {result}")
    except Exception as e:
        trace_step("parse_error_failed", {"error": str(e)})
        print(f"   ❌ Failed to parse error fragment: {e}")
        
except Exception as e:
    trace_step("parse_test_failed", {"error": str(e)})

# Summary and Analysis
print("\n" + "="*80)
print("📈 TRACE ANALYSIS")
print("="*80)

# Analyze traces to find failure point
invoke_traces = [t for t in _test_data["traces"] if "invoke" in t["step"]]
failed_steps = [t for t in _test_data["traces"] if "failed" in t["step"]]

print(f"\nTotal trace steps: {len(_test_data['traces'])}")
print(f"Failed steps: {len(failed_steps)}")
print(f"Errors captured: {len(_test_data['errors'])}")

if _test_data["errors"]:
    print("\n🔍 CRITICAL ERRORS FOUND:")
    for i, error in enumerate(_test_data["errors"], 1):
        print(f"\n{i}. Step: {error.get('step', 'unknown')}")
        print(f"   Error Type: {error.get('error_type', 'unknown')}")
        print(f"   Error: {error.get('error', 'unknown')}")
        if error.get('traceback'):
            print(f"   Traceback:\n{error['traceback']}")

# Find the exact failure point
failure_point = None
for i, trace in enumerate(_test_data["traces"]):
    if "failed" in trace["step"] and i > 0:
        failure_point = _test_data["traces"][i-1]["step"]
        break

if failure_point:
    print(f"\n❌ FAILURE OCCURRED AFTER: {failure_point}")

# Key findings
print("\n💡 KEY FINDINGS:")
if any("bind_failed" in t["step"] for t in _test_data["traces"]):
    print("  ❌ bind() method is failing")
elif any("invoke_failed" in t["step"] for t in _test_data["traces"]):
    print("  ❌ invoke() method is failing after bind()")
elif any("parse_error" in t["step"] for t in _test_data["traces"]):
    print("  ❌ JSON parsing is receiving error messages instead of responses")

# Save complete output
def save_test_output():
    """Save all captured output to JSON"""
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    
    _test_data["terminal_output"] = _stdout_capture.getvalue().split('\n')
    if _stderr_capture.getvalue():
        _test_data["stderr_output"] = _stderr_capture.getvalue().split('\n')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"output_qa_trace_diagnostic_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete trace output saved to: {filename}")

save_test_output()

print("\n✅ Trace diagnostic complete - check output file for full details")