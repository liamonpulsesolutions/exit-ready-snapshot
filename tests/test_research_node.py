#!/usr/bin/env python3
"""
Test script for the research node in LangGraph workflow.
Validates all research functionality including:
- Perplexity API integration
- Fallback data handling
- Industry-specific research
- Benchmark gathering
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

# Capture all output using TeeOutput pattern
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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Store all test data
_test_data = {
    "test_name": "test_research_node.py",
    "timestamp": datetime.now().isoformat(),
    "results": {},
    "errors": [],
    "assertions": []
}

def log_result(key, value):
    """Log a result to be saved"""
    _test_data["results"][key] = value

def log_assertion(description, passed, details=None):
    """Log an assertion result"""
    assertion = {
        "description": description,
        "passed": passed,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        assertion["details"] = details
    _test_data["assertions"].append(assertion)
    
    # Print result
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {description}")
    if details and not passed:
        print(f"   Details: {details}")

# Sample state from successful intake node
SAMPLE_STATE_AFTER_INTAKE = {
    "uuid": "test-research-001",
    "form_data": {
        "uuid": "test-research-001",
        "name": "John Smith",
        "email": "john@techcorp.com",
        "industry": "Professional Services",
        "revenue_range": "$1M-$5M",
        "years_in_business": "10-20 years",
        "age_range": "55-64",
        "exit_timeline": "1-2 years",
        "location": "Pacific/Western US",
        "responses": {
            "q1": "I am the CEO and founder",
            "q2": "Less than 3 days",
            "q3": "Consulting 60%, Training 40%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Improved slightly",
            "q7": "Client relationships and expertise",
            "q8": "4",
            "q9": "Long-term clients and reputation",
            "q10": "8"
        }
    },
    "locale": "us",
    "current_stage": "intake",
    "processing_time": {"intake": 0.005},
    "messages": ["Intake completed"],
    "error": None,
    # From intake node
    "intake_result": {
        "validation_status": "success",
        "pii_entries": 4,
        "crm_logged": True,
        "responses_logged": True
    },
    "anonymized_data": {
        "name": "[OWNER_NAME]",
        "email": "[EMAIL]",
        "industry": "Professional Services",
        "revenue_range": "$1M-$5M",
        "years_in_business": "10-20 years",
        "age_range": "55-64",
        "exit_timeline": "1-2 years",
        "location": "Pacific/Western US",
        "responses": {
            "q1": "I am the CEO and founder",
            "q2": "Less than 3 days",
            "q3": "Consulting 60%, Training 40%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Improved slightly",
            "q7": "Client relationships and expertise",
            "q8": "4",
            "q9": "Long-term clients and reputation",
            "q10": "8"
        }
    },
    "pii_mapping": {
        "[OWNER_NAME]": "John Smith",
        "[EMAIL]": "john@techcorp.com",
        "[UUID]": "test-research-001",
        "[LOCATION]": "Pacific/Western US"
    },
    # Initialize empty for future nodes
    "research_result": None,
    "scoring_result": None,
    "summary_result": None,
    "qa_result": None,
    "final_output": None,
    # Business context
    "industry": "Professional Services",
    "location": "Pacific/Western US",
    "revenue_range": "$1M-$5M",
    "exit_timeline": "1-2 years",
    "years_in_business": "10-20 years"
}

def test_research_node():
    """Test the research node functionality"""
    print("\n" + "="*80)
    print("🧪 TESTING RESEARCH NODE")
    print("="*80 + "\n")
    
    try:
        # Import after environment setup
        from workflow.nodes.research import research_node
        from workflow.state import WorkflowState
        
        log_result("imports_successful", True)
        print("✅ Successfully imported research_node and WorkflowState")
        
        # Check if Perplexity API key is available
        has_perplexity_key = bool(os.getenv("PERPLEXITY_API_KEY"))
        print(f"\n📡 Perplexity API Key: {'✅ Found' if has_perplexity_key else '⚠️  Not found (will use fallback data)'}")
        log_result("has_perplexity_key", has_perplexity_key)
        
        # Use the state from intake
        state = SAMPLE_STATE_AFTER_INTAKE.copy()
        
        log_result("initial_state", state)
        print(f"\n📋 Using state from intake node - UUID: {state['uuid']}")
        print(f"   Industry: {state['industry']}")
        print(f"   Location: {state['location']}")
        print(f"   Revenue: {state['revenue_range']}")
        
        # Execute research node
        print("\n🚀 Executing research_node...")
        start_time = datetime.now()
        
        result_state = research_node(state)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_result("execution_time", execution_time)
        log_result("result_state", result_state)
        
        print(f"\n⏱️  Execution completed in {execution_time:.2f} seconds")
        
        # Validate results
        print("\n🔍 Validating results...")
        
        # 1. Check stage updated
        log_assertion(
            "Stage updated to 'research'",
            result_state.get("current_stage") == "research",
            {"actual": result_state.get("current_stage"), "expected": "research"}
        )
        
        # 2. Check research_result exists
        research_result = result_state.get("research_result")
        log_assertion(
            "research_result populated",
            research_result is not None,
            {"has_result": research_result is not None}
        )
        
        if research_result:
            # 3. Check data source
            data_source = research_result.get("data_source")
            log_assertion(
                "Data source identified",
                data_source in ["live", "fallback"],
                {"data_source": data_source}
            )
            
            # 4. Check industry context
            log_assertion(
                "Industry context included",
                "industry_context" in research_result,
                {"has_context": "industry_context" in research_result}
            )
            
            # 5. Check valuation benchmarks
            log_assertion(
                "Valuation benchmarks present",
                "valuation_benchmarks" in research_result,
                {"has_benchmarks": "valuation_benchmarks" in research_result}
            )
            
            # 6. Check improvement strategies
            log_assertion(
                "Improvement strategies present",
                "improvement_strategies" in research_result,
                {"has_strategies": "improvement_strategies" in research_result}
            )
            
            # 7. Check market conditions
            log_assertion(
                "Market conditions present",
                "market_conditions" in research_result,
                {"has_conditions": "market_conditions" in research_result}
            )
            
            # 8. If using live data, check for raw content
            if data_source == "live":
                log_assertion(
                    "Raw trends data captured",
                    "raw_trends" in research_result and len(research_result.get("raw_trends", "")) > 0,
                    {"has_raw_data": "raw_trends" in research_result}
                )
            
            # 9. Check timestamp
            log_assertion(
                "Research timestamp recorded",
                "timestamp" in research_result,
                {"timestamp": research_result.get("timestamp")}
            )
            
            # 10. Display research summary
            print(f"\n📊 Research Summary:")
            print(f"   Data Source: {data_source}")
            print(f"   Industry: {research_result.get('industry')}")
            print(f"   Location: {research_result.get('location')}")
            
            if "valuation_benchmarks" in research_result:
                benchmarks = research_result["valuation_benchmarks"]
                print(f"\n   Valuation Benchmarks:")
                for key, value in benchmarks.items():
                    print(f"     - {key}: {str(value)[:60]}...")
            
            if "improvement_strategies" in research_result:
                strategies = research_result["improvement_strategies"]
                print(f"\n   Improvement Areas: {len(strategies)} found")
                
            if "market_conditions" in research_result:
                conditions = research_result["market_conditions"]
                print(f"   Market Conditions: {len(conditions)} factors")
        
        # 11. Check processing time recorded
        log_assertion(
            "Processing time recorded",
            "research" in result_state.get("processing_time", {}),
            {"time": result_state.get("processing_time", {}).get("research")}
        )
        
        # 12. Check no errors
        log_assertion(
            "No errors occurred",
            result_state.get("error") is None,
            {"error": result_state.get("error")}
        )
        
        # 13. Check messages updated
        log_assertion(
            "Messages updated with research status",
            len(result_state.get("messages", [])) > len(state.get("messages", [])),
            {"message_count": len(result_state.get("messages", []))}
        )
        
        # Summary
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        total_assertions = len(_test_data["assertions"])
        passed_assertions = sum(1 for a in _test_data["assertions"] if a["passed"])
        
        print(f"\nTotal assertions: {total_assertions}")
        print(f"Passed: {passed_assertions}")
        print(f"Failed: {total_assertions - passed_assertions}")
        print(f"Success rate: {(passed_assertions/total_assertions)*100:.1f}%")
        
        if passed_assertions == total_assertions:
            print("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
        
        # Log final summary
        log_result("test_summary", {
            "total_assertions": total_assertions,
            "passed": passed_assertions,
            "failed": total_assertions - passed_assertions,
            "success_rate": (passed_assertions/total_assertions)*100,
            "data_source": research_result.get("data_source") if research_result else None
        })
        
    except Exception as e:
        print(f"\n❌ ERROR during test execution: {str(e)}")
        import traceback
        error_details = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        _test_data["errors"].append(error_details)
        print(traceback.format_exc())


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
    filename = f"output_test_research_node_{timestamp}.json"
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete test output saved to: {filename}")
    
    # Also create a summary file
    summary = {
        "test": "research_node",
        "timestamp": _test_data["timestamp"],
        "execution_time": _test_data["results"].get("execution_time"),
        "assertions": {
            "total": len(_test_data["assertions"]),
            "passed": sum(1 for a in _test_data["assertions"] if a["passed"]),
            "failed": sum(1 for a in _test_data["assertions"] if not a["passed"])
        },
        "errors": len(_test_data["errors"]),
        "has_perplexity_key": _test_data["results"].get("has_perplexity_key"),
        "data_source": _test_data["results"].get("test_summary", {}).get("data_source"),
        "key_results": {
            "stage": _test_data["results"].get("result_state", {}).get("current_stage"),
            "has_benchmarks": "valuation_benchmarks" in _test_data["results"].get("result_state", {}).get("research_result", {}),
            "has_strategies": "improvement_strategies" in _test_data["results"].get("result_state", {}).get("research_result", {})
        }
    }
    
    summary_filename = f"summary_test_research_node_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Test summary saved to: {summary_filename}")


if __name__ == "__main__":
    try:
        test_research_node()
    finally:
        save_test_output()