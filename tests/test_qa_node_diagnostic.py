#!/usr/bin/env python3
"""
Diagnostic test to identify why QA node LLM functions are failing.
Tests each QA function individually with proper inputs.
"""

import os
import sys
import json
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
    "test_name": "test_qa_node_diagnostic.py",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": [],
    "diagnostics": []
}

print("\n" + "="*80)
print("🔍 QA NODE DIAGNOSTIC TEST")
print("="*80 + "\n")

try:
    # Import QA functions
    from workflow.nodes.qa import (
        check_redundancy_llm,
        check_tone_consistency_llm,
        verify_outcome_framing_llm,
        verify_citations_llm
    )
    
    # Also test direct LLM invocation
    from workflow.core.llm_utils import get_llm_with_fallback, ensure_json_response
    from langchain.schema import SystemMessage, HumanMessage
    
    # Create test data that mimics real summary data
    test_summary = {
        "executive_summary": "Based on our analysis, your business shows strong potential. Revenue typically increases 15-25% when implementing these strategies. Market conditions favor sellers.",
        "category_analyses": {
            "financial_readiness": {
                "summary": "Strong financial performance positions you well. Businesses often see 10-20% value increases.",
                "score": 7.5
            },
            "revenue_quality": {
                "summary": "Recurring revenue provides stability. Companies typically achieve higher multiples.",
                "score": 8.0
            }
        },
        "recommendations": [
            {
                "category": "financial_readiness",
                "priority": "High",
                "timeline": "3 months",
                "action": "Implement automated reporting",
                "impact": "Could increase efficiency by 15-25%"
            }
        ],
        "citations": {
            "total_citations": 5,
            "sources": ["Industry Report 2024", "Market Analysis"]
        }
    }
    
    print("📊 Test 1: Direct LLM Invocation")
    print("-" * 50)
    
    # Test basic LLM call
    try:
        llm = get_llm_with_fallback("gpt-4.1-nano", temperature=0)
        print(f"   LLM created: {type(llm)}")
        print(f"   Has _custom_model_name: {hasattr(llm, '_custom_model_name')}")
        
        # Test simple invoke
        start = datetime.now()
        response = llm.invoke("Say 'test successful'")
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"   Direct invoke time: {elapsed:.2f}s")
        print(f"   Response type: {type(response)}")
        print(f"   Response content: {response.content if hasattr(response, 'content') else str(response)[:50]}")
        
        _test_data["diagnostics"].append({
            "test": "direct_llm_invoke",
            "elapsed": elapsed,
            "success": elapsed > 0.1,
            "response_type": str(type(response))
        })
        
    except Exception as e:
        print(f"   ❌ Direct LLM test failed: {e}")
        import traceback
        _test_data["errors"].append({
            "test": "direct_llm_invoke",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    
    print("\n📊 Test 2: JSON Response Wrapper")
    print("-" * 50)
    
    # Test ensure_json_response
    try:
        json_llm = ensure_json_response(llm)
        print(f"   JSON LLM created: {type(json_llm)}")
        
        start = datetime.now()
        messages = [
            SystemMessage(content="Return JSON only."),
            HumanMessage(content='Return: {"status": "ok", "value": 42}')
        ]
        response = json_llm.invoke(messages)
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"   JSON invoke time: {elapsed:.2f}s")
        print(f"   Response type: {type(response)}")
        print(f"   Is dict: {isinstance(response, dict)}")
        if isinstance(response, dict):
            print(f"   Response: {response}")
        
        _test_data["diagnostics"].append({
            "test": "json_wrapper",
            "elapsed": elapsed,
            "success": elapsed > 0.1 and isinstance(response, dict),
            "is_dict": isinstance(response, dict)
        })
        
    except Exception as e:
        print(f"   ❌ JSON wrapper test failed: {e}")
        _test_data["errors"].append({
            "test": "json_wrapper",
            "error": str(e)
        })
    
    print("\n📊 Test 3: QA Function Internals")
    print("-" * 50)
    
    # Test check_redundancy_llm with debugging
    try:
        print("   Testing redundancy check...")
        
        # Manually construct what the function does
        json_llm = ensure_json_response(get_llm_with_fallback("gpt-4.1-nano", temperature=0))
        
        # Create the exact prompt the function uses
        prompt = f"""Analyze this executive summary for redundancy and clarity.

Executive Summary:
{test_summary['executive_summary']}

Category Analyses:
{json.dumps(test_summary['category_analyses'], indent=2)}

Provide your assessment as JSON:
{{
    "redundancy_score": <1-10, where 10 is excellent conciseness>,
    "repetitive_phrases": ["phrase1", "phrase2"],
    "improvement_suggestions": ["suggestion1", "suggestion2"]
}}"""
        
        print(f"   Prompt length: {len(prompt)} chars")
        print(f"   Prompt preview: {prompt[:200]}...")
        
        # Try to invoke
        start = datetime.now()
        try:
            messages = [
                SystemMessage(content="You are a business writing expert. Analyze text for redundancy."),
                HumanMessage(content=prompt)
            ]
            response = json_llm.invoke(messages)
            elapsed = (datetime.now() - start).total_seconds()
            
            print(f"   Manual redundancy check time: {elapsed:.2f}s")
            print(f"   Response type: {type(response)}")
            print(f"   Response: {response}")
            
            _test_data["diagnostics"].append({
                "test": "manual_redundancy",
                "elapsed": elapsed,
                "success": elapsed > 0.1,
                "response": response if isinstance(response, dict) else str(response)[:100]
            })
            
        except Exception as e:
            print(f"   ❌ Manual redundancy check failed: {e}")
            _test_data["errors"].append({
                "test": "manual_redundancy",
                "error": str(e)
            })
        
        # Now test the actual function
        print("\n   Testing actual redundancy function...")
        start = datetime.now()
        score = check_redundancy_llm(test_summary, json_llm)
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"   Function call time: {elapsed:.2f}s")
        print(f"   Score returned: {score}")
        
        _test_data["diagnostics"].append({
            "test": "check_redundancy_llm",
            "elapsed": elapsed,
            "success": elapsed > 0.1,
            "score": score
        })
        
    except Exception as e:
        print(f"   ❌ Redundancy function test failed: {e}")
        import traceback
        _test_data["errors"].append({
            "test": "check_redundancy_llm",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    
    print("\n📊 Test 4: Raw Model Configuration Test")
    print("-" * 50)
    
    # Test using bind for JSON response format
    try:
        from langchain_openai import ChatOpenAI
        
        # Create LLM with JSON response format using bind
        base_llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0)
        json_bound_llm = base_llm.bind(response_format={"type": "json_object"})
        
        print(f"   Created bound LLM: {type(json_bound_llm)}")
        
        messages = [
            SystemMessage(content="You must respond with valid JSON only."),
            HumanMessage(content='Return: {"test": "success", "number": 123}')
        ]
        
        start = datetime.now()
        response = json_bound_llm.invoke(messages)
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"   Bound LLM invoke time: {elapsed:.2f}s")
        print(f"   Response: {response.content if hasattr(response, 'content') else str(response)}")
        
        # Try to parse as JSON
        if hasattr(response, 'content'):
            try:
                parsed = json.loads(response.content)
                print(f"   Parsed JSON: {parsed}")
                _test_data["diagnostics"].append({
                    "test": "bound_json_llm",
                    "elapsed": elapsed,
                    "success": True,
                    "parsed": parsed
                })
            except:
                print(f"   Failed to parse as JSON")
                _test_data["diagnostics"].append({
                    "test": "bound_json_llm",
                    "elapsed": elapsed,
                    "success": False,
                    "error": "JSON parse failed"
                })
                
    except Exception as e:
        print(f"   ❌ Bound LLM test failed: {e}")
        _test_data["errors"].append({
            "test": "bound_json_llm",
            "error": str(e)
        })
    
    print("\n" + "="*80)
    print("📈 DIAGNOSTIC SUMMARY")
    print("="*80)
    
    # Analyze results
    successful_tests = sum(1 for d in _test_data["diagnostics"] if d.get("success", False))
    total_tests = len(_test_data["diagnostics"])
    
    print(f"\nTests run: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Errors: {len(_test_data['errors'])}")
    
    # Key findings
    print("\n🔍 Key Findings:")
    
    # Check if any LLM calls succeeded
    any_llm_success = any(d.get("elapsed", 0) > 0.5 for d in _test_data["diagnostics"])
    if any_llm_success:
        print("  ✅ LLM calls ARE working (>0.5s execution time)")
    else:
        print("  ❌ LLM calls are NOT working (all <0.5s)")
    
    # Check JSON parsing
    json_tests = [d for d in _test_data["diagnostics"] if "json" in d.get("test", "").lower()]
    if any(d.get("success", False) for d in json_tests):
        print("  ✅ JSON response parsing is working")
    else:
        print("  ❌ JSON response parsing is failing")
    
    # Specific QA function status
    qa_test = next((d for d in _test_data["diagnostics"] if d.get("test") == "check_redundancy_llm"), None)
    if qa_test and qa_test.get("success"):
        print("  ✅ QA functions can work with proper setup")
    else:
        print("  ❌ QA functions are failing")
        
    # Recommendations
    print("\n💡 Recommendations:")
    if not any_llm_success:
        print("  - Check OpenAI API key and network connectivity")
        print("  - Verify model names (gpt-4.1-mini, gpt-4.1-nano)")
    
    if _test_data["errors"]:
        print(f"  - Review {len(_test_data['errors'])} errors in output file")
        
    _test_data["results"]["summary"] = {
        "total_tests": total_tests,
        "successful": successful_tests,
        "any_llm_working": any_llm_success,
        "json_parsing_working": any(d.get("success", False) for d in json_tests)
    }
    
except Exception as e:
    print(f"\n❌ CRITICAL ERROR: {e}")
    import traceback
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
    filename = f"output_qa_diagnostic_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Diagnostic output saved to: {filename}")