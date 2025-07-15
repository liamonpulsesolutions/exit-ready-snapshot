#!/usr/bin/env python3
"""
Test script for the enhanced QA node with LLM intelligence.
Validates redundancy detection, tone consistency, and final polish.
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
    "test_name": "test_enhanced_qa_node.py",
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

# Sample state after summary with intentional issues for QA to catch
SAMPLE_STATE_AFTER_SUMMARY = {
    "uuid": "test-enhanced-qa-001",
    "form_data": {},
    "locale": "us",
    "current_stage": "summary",
    "error": None,
    "processing_time": {"intake": 0.5, "research": 26.5, "scoring": 47.3, "summary": 81.0},
    "messages": ["Previous stages completed"],
    "industry": "Professional Services",
    "location": "Pacific/Western US",
    "revenue_range": "$1M-$5M",
    "exit_timeline": "1-2 years",
    "anonymized_data": {
        "responses": {
            "q1": "I handle everything",
            "q2": "Less than 3 days",
            "q3": "Consulting 60%, Training 40%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Improved slightly",
            "q7": "Critical knowledge only I have",
            "q8": "4",
            "q9": "Long-term relationships",
            "q10": "8"
        }
    },
    "research_result": {
        "citations": ["BizBuySell 2025", "IBBA Market Pulse 2025", "M&A Source 2025"],
        "valuation_benchmarks": {
            "base_EBITDA": "4-6x for well-run businesses (per BizBuySell 2025)",
            "base_revenue": "1.2-2.0x depending on recurring revenue (per IBBA Market Pulse 2025)",
            "owner_dependence_impact": "20-30% discount if owner critical (per M&A Source 2025)"
        },
        "market_conditions": {
            "average_sale_time": "9-12 months for prepared businesses (per BizBuySell 2025)"
        }
    },
    "scoring_result": {
        "overall_score": 4.3,
        "readiness_level": "Needs Work",
        "category_scores": {
            "owner_dependence": {
                "score": 2.5, 
                "weight": 0.25,
                "gaps": ["Business cannot operate without owner"],
                "strengths": ["Some delegation evident"],
                "insight": "Heavy owner involvement limits value"
            },
            "revenue_quality": {"score": 5.5, "weight": 0.20},
            "financial_readiness": {"score": 6.0, "weight": 0.20},
            "operational_resilience": {
                "score": 3.0, 
                "weight": 0.20,
                "gaps": ["Critical knowledge concentrated in owner"]
            },
            "growth_value": {"score": 5.0, "weight": 0.15}
        }
    },
    "summary_result": {
        "executive_summary": """Thank you for completing the Exit Ready Snapshot. Your overall score of 4.3/10 indicates your business Needs Work.

Your strongest area is financial readiness (6.0/10), while your biggest opportunity for improvement is owner dependence (2.5/10).

Based on your assessment, focused improvements could increase your business value by 35-45%. Given your 1-2 years timeline, we recommend prioritizing owner dependence.

Your overall score of 4.3/10 shows significant room for improvement. The score of 4.3 reflects challenges across multiple areas.""",  # Intentional redundancy + UNCITED claim (35-45%)
        
        "category_summaries": {
            "owner_dependence": "Your score of 2.5/10 indicates critical issues...",  # Too brief
            "revenue_quality": "Your score of 5.5/10 shows moderate revenue quality...",
            "financial_readiness": "Your score of 6.0/10 demonstrates decent financial readiness...",
            "operational_resilience": "Your score of 3.0/10 reveals operational weaknesses...",  # Missing gaps
            "growth_value": "Your score of 5.0/10 suggests average growth potential..."
        },
        
        "recommendations": """Based on your assessment, here are your recommendations:

QUICK WINS (30 Days):
- Start documenting your daily activities
- Begin training a key employee
- Review your client concentration

Industry data shows that businesses with low owner dependence sell for 40% more. Given your 1-2 years timeline, you need to act quickly. Your 1-2 years timeline requires urgent action.""",  # UNCITED statistic + redundancy
        
        "industry_context": """Professional Services businesses in your revenue range typically trade at 4-6x EBITDA (per BizBuySell 2025). 
        
        However, businesses like yours with high owner dependence often see discounts of 20-30% (per M&A Source 2025).
        
        The average business takes 18 months to sell in current market conditions.""",  # Last claim is UNCITED and WRONG
        
        "next_steps": "Your immediate priority should be reducing owner dependence...",
        
        "final_report": "[Full report with all the above content]",
        
        "report_metadata": {
            "overall_score": 4.3,
            "readiness_level": "Needs Work",
            "word_count": 3000
        }
    }
}

def test_enhanced_qa_node():
    """Test the enhanced QA node functionality"""
    print("\n" + "="*80)
    print("🧪 TESTING ENHANCED QA NODE WITH LLM INTELLIGENCE")
    print("="*80 + "\n")
    
    try:
        # Import after environment setup
        from workflow.nodes.qa import qa_node
        from workflow.state import WorkflowState
        
        log_result("imports_successful", True)
        print("✅ Successfully imported enhanced qa_node")
        
        # Check OpenAI API key
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        print(f"\n📡 OpenAI API Key: {'✅ Found' if has_openai else '❌ REQUIRED'}")
        log_result("has_openai_key", has_openai)
        
        if not has_openai:
            print("\n❌ ERROR: OpenAI API key is required for LLM QA checks")
            return
        
        # Use the state from summary
        state = SAMPLE_STATE_AFTER_SUMMARY.copy()
        
        log_result("initial_state", state)
        print(f"\n📋 Testing with state - UUID: {state['uuid']}")
        print(f"   Overall Score: {state['scoring_result']['overall_score']}/10")
        print(f"   Report Word Count: {state['summary_result']['report_metadata']['word_count']}")
        print("\n   Note: Test data includes intentional redundancies for QA to detect")
        
        # Execute enhanced QA node
        print("\n🚀 Executing enhanced qa_node...")
        start_time = datetime.now()
        
        result_state = qa_node(state)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_result("execution_time", execution_time)
        log_result("result_state", result_state)
        
        print(f"\n⏱️  Execution completed in {execution_time:.2f} seconds")
        
        # Validate results
        print("\n🔍 Validating enhanced QA results...")
        
        qa_result = result_state.get("qa_result")
        
        # 1. Check QA result exists
        log_assertion(
            "QA result populated",
            qa_result is not None,
            {"has_result": qa_result is not None}
        )
        
        if qa_result:
            # 2. Check overall quality score
            quality_score = qa_result.get("overall_quality_score")
            log_assertion(
                "Overall quality score calculated",
                quality_score is not None and 0 <= quality_score <= 10,
                {"score": quality_score}
            )
            
            # 3. Check all quality checks performed
            quality_scores = qa_result.get("quality_scores", {})
            expected_checks = ["scoring_consistency", "content_quality", "pii_compliance", 
                             "structure_validation", "redundancy_check", "tone_consistency",
                             "citation_verification"]
            
            for check in expected_checks:
                log_assertion(
                    f"{check} performed",
                    check in quality_scores,
                    {"has_check": check in quality_scores}
                )
            
            # 4. Check redundancy detection worked
            redundancy_check = quality_scores.get("redundancy_check", {})
            log_assertion(
                "Redundancy detection completed",
                "redundancy_score" in redundancy_check,
                {
                    "score": redundancy_check.get("redundancy_score"),
                    "redundancies_found": len(redundancy_check.get("redundancies_found", []))
                }
            )
            
            # 5. Check tone consistency analysis
            tone_check = quality_scores.get("tone_consistency", {})
            log_assertion(
                "Tone consistency checked",
                "tone_score" in tone_check,
                {
                    "score": tone_check.get("tone_score"),
                    "consistent": tone_check.get("consistent")
                }
            )
            
            # 7. Check citation verification worked
            citation_check = quality_scores.get("citation_verification", {})
            log_assertion(
                "Citation verification completed",
                "citation_score" in citation_check,
                {
                    "score": citation_check.get("citation_score"),
                    "uncited_claims": citation_check.get("issues_found", 0),
                    "total_claims": citation_check.get("total_claims_found", 0)
                }
            )
            
            # 8. Check if sections were polished or fixed
            polished_sections = qa_result.get("polished_sections", {})
            fixed_sections = qa_result.get("fixed_sections", {})
            fix_attempts = qa_result.get("fix_attempts", 0)
            
            log_assertion(
                "Fix attempts made when issues found",
                fix_attempts > 0 or len(qa_result.get("issues", [])) == 0,
                {
                    "fix_attempts": fix_attempts,
                    "sections_fixed": len(fixed_sections),
                    "sections_polished": len(polished_sections),
                    "issues_before_fix": len(qa_result.get("issues", []))
                }
            )
            
            # 7. Check approval status
            log_assertion(
                "Approval status determined",
                "approved" in qa_result and "ready_for_delivery" in qa_result,
                {
                    "approved": qa_result.get("approved"),
                    "ready_for_delivery": qa_result.get("ready_for_delivery")
                }
            )
            
            # 8. Check execution time (should be under 15s with nano model)
            log_assertion(
                "Execution time reasonable for LLM QA",
                execution_time < 15,
                {"execution_time": execution_time}
            )
            
            # Display results
            print(f"\n📊 QA Results Summary:")
            print(f"   Overall Quality Score: {quality_score}/10")
            print(f"   Approved: {'✅ Yes' if qa_result.get('approved') else '❌ No'}")
            print(f"   Ready for Delivery: {'✅ Yes' if qa_result.get('ready_for_delivery') else '❌ No'}")
            
            print(f"\n   Quality Checks:")
            for check, result in quality_scores.items():
                if isinstance(result, dict):
                    if "score" in result:
                        print(f"   - {check}: {result.get('score')}/10")
                    elif "redundancy_score" in result:
                        print(f"   - {check}: {result.get('redundancy_score')}/10")
                    elif "tone_score" in result:
                        print(f"   - {check}: {result.get('tone_score')}/10")
                    elif "citation_score" in result:
                        print(f"   - {check}: {result.get('citation_score')}/10 ({result.get('issues_found', 0)} issues)")
                    else:
                        print(f"   - {check}: ✓")
            
            if qa_result.get("issues"):
                print(f"\n   Issues Found: {len(qa_result['issues'])}")
                for issue in qa_result['issues'][:3]:
                    print(f"   - {issue}")
            
            if qa_result.get("warnings"):
                print(f"\n   Warnings: {len(qa_result['warnings'])}")
                for warning in qa_result['warnings'][:3]:
                    print(f"   - {warning}")
        
        # Summary
        print("\n📈 Test Summary:")
        total_assertions = len(_test_data["assertions"])
        passed_assertions = sum(1 for a in _test_data["assertions"] if a["passed"])
        
        print(f"   Total Assertions: {total_assertions}")
        print(f"   Passed: {passed_assertions}")
        print(f"   Failed: {total_assertions - passed_assertions}")
        
        if passed_assertions == total_assertions:
            print("\n✨ All enhanced QA tests passed! 🎉")
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
        
        # Log final summary
        log_result("test_summary", {
            "total_assertions": total_assertions,
            "passed": passed_assertions,
            "failed": total_assertions - passed_assertions,
            "success_rate": (passed_assertions/total_assertions)*100 if total_assertions > 0 else 0,
            "quality_score": quality_score if qa_result else None,
            "approved": qa_result.get("approved") if qa_result else None
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
    filename = f"output_test_enhanced_qa_{timestamp}.json"
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete test output saved to: {filename}")
    
    # Also create a summary file
    summary = {
        "test": "enhanced_qa_node",
        "timestamp": _test_data["timestamp"],
        "execution_time": _test_data["results"].get("execution_time"),
        "assertions": {
            "total": len(_test_data["assertions"]),
            "passed": sum(1 for a in _test_data["assertions"] if a["passed"]),
            "failed": sum(1 for a in _test_data["assertions"] if not a["passed"])
        },
        "errors": len(_test_data["errors"]),
        "has_openai_key": _test_data["results"].get("has_openai_key"),
        "quality_score": _test_data["results"].get("test_summary", {}).get("quality_score"),
        "approved": _test_data["results"].get("test_summary", {}).get("approved")
    }
    
    summary_filename = f"summary_test_enhanced_qa_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Test summary saved to: {summary_filename}")


if __name__ == "__main__":
    try:
        test_enhanced_qa_node()
    finally:
        save_test_output()