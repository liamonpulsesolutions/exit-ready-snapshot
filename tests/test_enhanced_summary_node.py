#!/usr/bin/env python3
"""
Test script for the enhanced summary node with LLM generation.
Validates intelligent report generation replacing templates.
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
    "test_name": "test_enhanced_summary_node.py",
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

# Sample state after scoring with insights
SAMPLE_STATE_AFTER_SCORING = {
    "uuid": "test-enhanced-summary-001",
    "form_data": {},
    "locale": "us",
    "current_stage": "scoring",
    "error": None,
    "processing_time": {"intake": 0.5, "research": 26.5, "scoring": 47.3},
    "messages": ["Intake completed", "Enhanced research completed", "Enhanced scoring completed"],
    "intake_result": {"validation_status": "success"},
    "anonymized_data": {
        "industry": "Professional Services",
        "revenue_range": "$1M-$5M",
        "years_in_business": "10-20 years",
        "exit_timeline": "1-2 years",
        "location": "Pacific/Western US",
        "responses": {
            "q1": "I am the CEO and founder. I handle all major client relationships.",
            "q2": "Less than 3 days",
            "q3": "Consulting 60%, Training 40%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Improved slightly",
            "q7": "Client relationships and my industry expertise.",
            "q8": "4",
            "q9": "Long-term clients, specialized expertise",
            "q10": "8"
        }
    },
    "research_result": {
        "industry": "Professional Services",
        "data_source": "live",
        "valuation_benchmarks": {
            "base_EBITDA": "4-6x for well-run businesses (per BizBuySell 2025)",
            "base_revenue": "1.2-2.0x depending on recurring revenue (per IBBA 2025)",
            "recurring_premium": "1-2x additional EBITDA multiple (per Axial 2025)"
        },
        "improvement_strategies": {
            "owner_dependence": {
                "strategy": "Delegate key decisions and client relationships",
                "timeline": "6 months",
                "value_impact": "15-20% increase (per Exit Planning Institute 2025)"
            }
        },
        "market_conditions": {
            "buyer_priorities": ["Recurring revenue", "Systematic operations"],
            "average_sale_time": "9-12 months for prepared businesses (per BizBuySell 2025)",
            "key_trend": "Technology integration increasingly valued (per GF Data 2025)"
        },
        "citations": ["BizBuySell 2025", "IBBA 2025", "Axial 2025"],
        "industry_context": {
            "key_factors": "Client relationships, recurring contracts",
            "typical_multiples": "4-6x EBITDA for established firms"
        }
    },
    "scoring_result": {
        "status": "success",
        "overall_score": 4.3,
        "readiness_level": "Needs Work",
        "category_scores": {
            "owner_dependence": {
                "score": 2.5,
                "strengths": ["Some delegation evident"],
                "gaps": ["Business cannot operate without owner", "Owner handles all key relationships"],
                "insight": "Your heavy involvement in daily operations significantly limits business value. Buyers need to see the business can run without you for at least 2 weeks."
            },
            "revenue_quality": {
                "score": 5.5,
                "strengths": ["Mix of revenue streams"],
                "gaps": ["High customer concentration risk"],
                "insight": "Your 60/40 revenue split shows some diversification, but the 20-40% concentration risk could reduce valuations by up to 30%."
            },
            "financial_readiness": {
                "score": 6.0,
                "strengths": ["Improving profit margins"],
                "gaps": ["Documentation confidence only moderate"],
                "insight": "Your confidence level of 7/10 and improving margins are positive, but buyers expect bulletproof financials for smooth due diligence."
            },
            "operational_resilience": {
                "score": 3.0,
                "strengths": ["Some processes documented"],
                "gaps": ["Critical knowledge concentrated in owner"],
                "insight": "With only you holding key expertise and limited documentation (4/10), operational transfer risk is high."
            },
            "growth_value": {
                "score": 5.0,
                "strengths": ["Long-term client relationships"],
                "gaps": ["Limited scalability without owner"],
                "insight": "Your specialized expertise and loyal clients are valuable, but growth potential is capped by owner dependence."
            }
        },
        "focus_areas": {
            "primary": {
                "category": "owner_dependence",
                "urgency": "CRITICAL",
                "roi": 8.5
            }
        },
        "key_insights": [
            {"category": "owner_dependence", "score": 2.5, "insight": "Your heavy involvement..."},
            {"category": "revenue_quality", "score": 5.5, "insight": "Your 60/40 revenue split..."},
            {"category": "financial_readiness", "score": 6.0, "insight": "Your confidence level..."},
            {"category": "operational_resilience", "score": 3.0, "insight": "With only you holding..."},
            {"category": "growth_value", "score": 5.0, "insight": "Your specialized expertise..."}
        ]
    },
    "summary_result": None,
    "qa_result": None,
    "final_output": None,
    "industry": "Professional Services",
    "location": "Pacific/Western US",
    "revenue_range": "$1M-$5M",
    "exit_timeline": "1-2 years",
    "years_in_business": "10-20 years"
}

def test_enhanced_summary_node():
    """Test the enhanced summary node functionality"""
    print("\n" + "="*80)
    print("🧪 TESTING ENHANCED SUMMARY NODE WITH LLM GENERATION")
    print("="*80 + "\n")
    
    try:
        # Import after environment setup
        from workflow.nodes.summary import summary_node
        from workflow.state import WorkflowState
        
        log_result("imports_successful", True)
        print("✅ Successfully imported enhanced summary_node")
        
        # Check OpenAI API key
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        print(f"\n📡 OpenAI API Key: {'✅ Found' if has_openai else '❌ REQUIRED'}")
        log_result("has_openai_key", has_openai)
        
        if not has_openai:
            print("\n❌ ERROR: OpenAI API key is required for LLM generation")
            return
        
        # Use the state from scoring
        state = SAMPLE_STATE_AFTER_SCORING.copy()
        
        log_result("initial_state", state)
        print(f"\n📋 Testing with state - UUID: {state['uuid']}")
        print(f"   Overall Score: {state['scoring_result']['overall_score']}/10")
        print(f"   Readiness: {state['scoring_result']['readiness_level']}")
        print(f"   Primary Focus: {state['scoring_result']['focus_areas']['primary']['category']}")
        
        # Execute enhanced summary node
        print("\n🚀 Executing enhanced summary_node...")
        start_time = datetime.now()
        
        result_state = summary_node(state)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_result("execution_time", execution_time)
        log_result("result_state", result_state)
        
        print(f"\n⏱️  Execution completed in {execution_time:.2f} seconds")
        
        # Validate results
        print("\n🔍 Validating enhanced results...")
        
        summary_result = result_state.get("summary_result")
        
        # 1. Check summary result exists
        log_assertion(
            "Summary result populated",
            summary_result is not None,
            {"has_result": summary_result is not None}
        )
        
        if summary_result:
            # 2. Check all sections generated
            sections = ["executive_summary", "category_summaries", "recommendations", 
                       "industry_context", "next_steps", "final_report"]
            
            for section in sections:
                has_section = section in summary_result and summary_result[section]
                section_length = len(str(summary_result.get(section, "")))
                
                log_assertion(
                    f"{section} generated",
                    has_section and section_length > 100,
                    {"has_section": has_section, "length": section_length}
                )
            
            # 3. Check category summaries
            category_summaries = summary_result.get("category_summaries", {})
            expected_categories = 5
            
            log_assertion(
                "All category summaries generated",
                len(category_summaries) == expected_categories,
                {"generated": len(category_summaries), "expected": expected_categories}
            )
            
            # 4. Check LLM generation flag
            has_llm = summary_result.get("report_metadata", {}).get("has_llm_generation", False)
            log_assertion(
                "LLM generation flag set",
                has_llm,
                {"has_llm_generation": has_llm}
            )
            
            # 5. Check word count
            word_count = summary_result.get("report_metadata", {}).get("word_count", 0)
            log_assertion(
                "Report word count sufficient",
                word_count > 2000,
                {"word_count": word_count}
            )
            
            # 6. Check personalization (should mention specific scores/insights)
            exec_summary = summary_result.get("executive_summary", "")
            has_score_ref = "4.3" in exec_summary or "Needs Work" in exec_summary
            has_personalization = "Professional Services" in exec_summary
            
            log_assertion(
                "Executive summary personalized",
                has_score_ref and has_personalization,
                {"has_score": has_score_ref, "has_industry": has_personalization}
            )
            
            # 7. Check execution time (should be 30-60s for 6 LLM calls)
            log_assertion(
                "Execution time reasonable for LLM generation",
                20 < execution_time < 70,
                {"execution_time": execution_time}
            )
            
            # 8. Display samples
            print("\n📊 Sample Enhanced Results:")
            print(f"\n   Executive Summary Preview:")
            print(f"   \"{exec_summary[:200]}...\"")
            
            print(f"\n   Report Stats:")
            print(f"   - Word Count: {word_count}")
            print(f"   - Sections: {len([s for s in sections if s in summary_result])}")
            print(f"   - Categories: {len(category_summaries)}")
        
        # Summary
        print("\n📈 Test Summary:")
        total_assertions = len(_test_data["assertions"])
        passed_assertions = sum(1 for a in _test_data["assertions"] if a["passed"])
        
        print(f"   Total Assertions: {total_assertions}")
        print(f"   Passed: {passed_assertions}")
        print(f"   Failed: {total_assertions - passed_assertions}")
        
        if passed_assertions == total_assertions:
            print("\n✨ All enhanced summary tests passed! 🎉")
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
        
        # Log final summary
        log_result("test_summary", {
            "total_assertions": total_assertions,
            "passed": passed_assertions,
            "failed": total_assertions - passed_assertions,
            "success_rate": (passed_assertions/total_assertions)*100 if total_assertions > 0 else 0,
            "word_count": word_count if summary_result else 0,
            "has_llm_generation": has_llm if summary_result else False
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
    filename = f"output_test_enhanced_summary_{timestamp}.json"
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete test output saved to: {filename}")
    
    # Also create a summary file
    summary = {
        "test": "enhanced_summary_node",
        "timestamp": _test_data["timestamp"],
        "execution_time": _test_data["results"].get("execution_time"),
        "assertions": {
            "total": len(_test_data["assertions"]),
            "passed": sum(1 for a in _test_data["assertions"] if a["passed"]),
            "failed": sum(1 for a in _test_data["assertions"] if not a["passed"])
        },
        "errors": len(_test_data["errors"]),
        "has_openai_key": _test_data["results"].get("has_openai_key"),
        "word_count": _test_data["results"].get("test_summary", {}).get("word_count"),
        "has_llm_generation": _test_data["results"].get("test_summary", {}).get("has_llm_generation")
    }
    
    summary_filename = f"summary_test_enhanced_summary_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Test summary saved to: {summary_filename}")


if __name__ == "__main__":
    try:
        test_enhanced_summary_node()
    finally:
        save_test_output()