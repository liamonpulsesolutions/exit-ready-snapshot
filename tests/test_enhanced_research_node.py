#!/usr/bin/env python3
"""
Test script for the enhanced research node with LLM intelligence.
Validates structured prompts, citation extraction, and quality checks.
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

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env from: {env_path}")
else:
    print(f"Warning: No .env file found at {env_path}")

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
    "test_name": "test_enhanced_research_node.py",
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

# Sample state from intake node
SAMPLE_STATE_AFTER_INTAKE = {
    "uuid": "test-enhanced-research-001",
    "form_data": {},
    "locale": "us",
    "current_stage": "intake",
    "error": None,
    "processing_time": {"intake": 0.5},
    "messages": ["Intake completed"],
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
    "research_result": None,
    "scoring_result": None,
    "summary_result": None,
    "qa_result": None,
    "final_output": None,
    "industry": "Professional Services",
    "location": "Pacific/Western US",
    "revenue_range": "$1M-$5M",
    "exit_timeline": "1-2 years",
    "years_in_business": "10-20 years"
}

def test_enhanced_research_node():
    """Test the enhanced research node functionality"""
    print("\n" + "="*80)
    print("🧪 TESTING ENHANCED RESEARCH NODE WITH LLM INTELLIGENCE")
    print("="*80 + "\n")
    
    try:
        # Import after environment setup
        from workflow.nodes.research import research_node
        from workflow.state import WorkflowState
        
        log_result("imports_successful", True)
        print("✅ Successfully imported enhanced research_node")
        
        # Check API keys
        has_perplexity = bool(os.getenv("PERPLEXITY_API_KEY"))
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        
        print(f"\n📡 API Keys:")
        print(f"   Perplexity: {'✅ Found' if has_perplexity else '⚠️  Not found (will use fallback)'}")
        print(f"   OpenAI: {'✅ Found' if has_openai else '❌ REQUIRED - Set OPENAI_API_KEY'}")
        
        log_result("has_perplexity_key", has_perplexity)
        log_result("has_openai_key", has_openai)
        
        if not has_openai:
            print("\n❌ ERROR: OpenAI API key is required for LLM extraction/validation")
            print("   Set your key: export OPENAI_API_KEY='your-key-here'")
            return
        
        # Use the state from intake
        state = SAMPLE_STATE_AFTER_INTAKE.copy()
        
        log_result("initial_state", state)
        print(f"\n📋 Testing with state - UUID: {state['uuid']}")
        print(f"   Industry: {state['industry']}")
        print(f"   Location: {state['location']}")
        print(f"   Revenue: {state['revenue_range']}")
        
        # Execute enhanced research node
        print("\n🚀 Executing enhanced research_node...")
        start_time = datetime.now()
        
        result_state = research_node(state)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_result("execution_time", execution_time)
        log_result("result_state", result_state)
        
        print(f"\n⏱️  Execution completed in {execution_time:.2f} seconds")
        
        # Validate results
        print("\n🔍 Validating enhanced results...")
        
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
            
            # 4. Check for citations list
            citations = research_result.get("citations", [])
            log_assertion(
                "Citations list present",
                isinstance(citations, list) and len(citations) > 0,
                {"citation_count": len(citations), "sample": citations[:3] if citations else []}
            )
            
            # 5. Check valuation benchmarks have citations
            benchmarks = research_result.get("valuation_benchmarks", {})
            has_citations_in_benchmarks = any(
                "(" in str(v) and ")" in str(v) 
                for v in benchmarks.values()
            )
            log_assertion(
                "Valuation benchmarks include citations",
                has_citations_in_benchmarks,
                {"sample": list(benchmarks.values())[:2] if benchmarks else []}
            )
            
            # 6. Check improvement strategies structure
            strategies = research_result.get("improvement_strategies", {})
            valid_strategies = all(
                isinstance(s, dict) and "strategy" in s and "timeline" in s and "value_impact" in s
                for s in strategies.values()
            )
            log_assertion(
                "Improvement strategies properly structured",
                valid_strategies,
                {"strategy_count": len(strategies)}
            )
            
            # 7. Check market conditions
            conditions = research_result.get("market_conditions", {})
            has_buyer_priorities = isinstance(conditions.get("buyer_priorities"), list)
            has_sale_time = "average_sale_time" in conditions
            has_trend = "key_trend" in conditions
            
            log_assertion(
                "Market conditions complete",
                has_buyer_priorities and has_sale_time and has_trend,
                {
                    "has_priorities": has_buyer_priorities,
                    "has_sale_time": has_sale_time,
                    "has_trend": has_trend
                }
            )
            
            # 8. If live data, check raw content
            if data_source == "live":
                log_assertion(
                    "Raw content captured from Perplexity",
                    "raw_content" in research_result,
                    {"content_length": len(research_result.get("raw_content", ""))}
                )
            
            # 9. Check execution time is reasonable (should be 10-20s with LLM calls)
            log_assertion(
                "Execution time reasonable for LLM processing",
                5 < execution_time < 30,
                {"execution_time": execution_time}
            )
            
            # 10. Display sample results
            print("\n📊 Sample Enhanced Results:")
            print(f"   Data Source: {data_source}")
            print(f"   Citations Found: {len(citations)}")
            if benchmarks:
                print(f"   Sample Benchmark: {list(benchmarks.items())[0]}")
            if strategies:
                first_strategy = list(strategies.items())[0]
                print(f"   Sample Strategy: {first_strategy[0]} - {first_strategy[1].get('timeline')}")
            
        # Summary
        print("\n📈 Test Summary:")
        total_assertions = len(_test_data["assertions"])
        passed_assertions = sum(1 for a in _test_data["assertions"] if a["passed"])
        
        print(f"   Total Assertions: {total_assertions}")
        print(f"   Passed: {passed_assertions}")
        print(f"   Failed: {total_assertions - passed_assertions}")
        
        if passed_assertions == total_assertions:
            print("\n✨ All enhanced research tests passed! 🎉")
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
        
        # Log final summary
        log_result("test_summary", {
            "total_assertions": total_assertions,
            "passed": passed_assertions,
            "failed": total_assertions - passed_assertions,
            "success_rate": (passed_assertions/total_assertions)*100,
            "data_source": research_result.get("data_source") if research_result else None,
            "citation_count": len(research_result.get("citations", [])) if research_result else 0
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
    filename = f"output_test_enhanced_research_{timestamp}.json"
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete test output saved to: {filename}")
    
    # Also create a summary file
    summary = {
        "test": "enhanced_research_node",
        "timestamp": _test_data["timestamp"],
        "execution_time": _test_data["results"].get("execution_time"),
        "assertions": {
            "total": len(_test_data["assertions"]),
            "passed": sum(1 for a in _test_data["assertions"] if a["passed"]),
            "failed": sum(1 for a in _test_data["assertions"] if not a["passed"])
        },
        "errors": len(_test_data["errors"]),
        "has_perplexity_key": _test_data["results"].get("has_perplexity_key"),
        "has_openai_key": _test_data["results"].get("has_openai_key"),
        "data_source": _test_data["results"].get("test_summary", {}).get("data_source"),
        "citation_count": _test_data["results"].get("test_summary", {}).get("citation_count"),
        "key_results": {
            "stage": _test_data["results"].get("result_state", {}).get("current_stage"),
            "has_citations": "citations" in _test_data["results"].get("result_state", {}).get("research_result", {}),
            "has_llm_extraction": _test_data["results"].get("execution_time", 0) > 5
        }
    }
    
    summary_filename = f"summary_test_enhanced_research_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Test summary saved to: {summary_filename}")


if __name__ == "__main__":
    try:
        test_enhanced_research_node()
    finally:
        save_test_output()