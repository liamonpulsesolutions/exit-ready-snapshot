#!/usr/bin/env python3
"""
Test script for the enhanced scoring node with LLM insights.
Validates mechanical scoring plus intelligent interpretation.
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
    "test_name": "test_enhanced_scoring_node.py",
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

# Sample state after research with citations
SAMPLE_STATE_AFTER_RESEARCH = {
    "uuid": "test-enhanced-scoring-001",
    "form_data": {},
    "locale": "us",
    "current_stage": "research",
    "error": None,
    "processing_time": {"intake": 0.5, "research": 26.5},
    "messages": ["Intake completed", "Enhanced research completed"],
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
            "q1": "I am the CEO and founder. I handle all major client relationships and make all strategic decisions.",
            "q2": "Less than 3 days",
            "q3": "Consulting 60%, Training 40%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Improved slightly",
            "q7": "Client relationships and my industry expertise. Only I have the key certifications.",
            "q8": "4",
            "q9": "Long-term clients, specialized expertise, industry certifications",
            "q10": "8"
        }
    },
    "pii_mapping": {
        "[OWNER_NAME]": "John Smith",
        "[EMAIL]": "john@techcorp.com",
        "[UUID]": "test-scoring-001",
        "[LOCATION]": "Pacific/Western US"
    },
    "research_result": {
        "industry": "Professional Services",
        "location": "Pacific/Western US",
        "revenue_range": "$1M-$5M",
        "timestamp": "2025-07-15T22:00:00",
        "data_source": "live",
        "valuation_benchmarks": {
            "base_EBITDA": "4-6x for well-run businesses (per BizBuySell 2025)",
            "base_revenue": "1.2-2.0x depending on recurring revenue (per IBBA Market Pulse 2025)",
            "recurring_threshold": "60% creates premium valuations (per PitchBook 2025)",
            "recurring_premium": "1-2x additional EBITDA multiple (per Axial 2025)",
            "owner_dependence_impact": "20-30% discount if owner critical (per M&A Source 2025)",
            "concentration_impact": "20-30% discount if >30% from one client (per DealStats 2025)"
        },
        "improvement_strategies": {
            "owner_dependence": {
                "strategy": "Delegate key decisions and client relationships",
                "timeline": "6 months",
                "value_impact": "15-20% increase (per Exit Planning Institute 2025)"
            },
            "operations": {
                "strategy": "Document processes and implement management systems",
                "timeline": "3 months",
                "value_impact": "10-15% increase (per Value Builder System 2025)"
            },
            "revenue_quality": {
                "strategy": "Convert to contracts and diversify client base",
                "timeline": "12 months",
                "value_impact": "20-30% increase (per EBITDA Catalyst 2025)"
            }
        },
        "market_conditions": {
            "buyer_priorities": ["Recurring revenue", "Systematic operations", "Growth potential"],
            "average_sale_time": "9-12 months for prepared businesses (per BizBuySell 2025)",
            "key_trend": "Technology integration increasingly valued (per GF Data 2025)"
        },
        "citations": [
            "BizBuySell 2025", "IBBA Market Pulse 2025", "PitchBook 2025",
            "Axial 2025", "M&A Source 2025", "DealStats 2025",
            "Exit Planning Institute 2025"
        ],
        "industry_context": {
            "key_factors": "Client relationships, recurring contracts, knowledge transfer",
            "typical_multiples": "4-6x EBITDA for established firms",
            "buyer_concerns": "Client concentration, key person dependency"
        }
    },
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

def test_enhanced_scoring_node():
    """Test the enhanced scoring node functionality"""
    print("\n" + "="*80)
    print("🧪 TESTING ENHANCED SCORING NODE WITH LLM INSIGHTS")
    print("="*80 + "\n")
    
    try:
        # Import after environment setup
        from workflow.nodes.scoring import scoring_node
        from workflow.state import WorkflowState
        
        log_result("imports_successful", True)
        print("✅ Successfully imported enhanced scoring_node")
        
        # Check OpenAI API key
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        print(f"\n📡 OpenAI API Key: {'✅ Found' if has_openai else '❌ REQUIRED'}")
        log_result("has_openai_key", has_openai)
        
        if not has_openai:
            print("\n❌ ERROR: OpenAI API key is required for LLM insights")
            return
        
        # Use the state from research
        state = SAMPLE_STATE_AFTER_RESEARCH.copy()
        
        log_result("initial_state", state)
        print(f"\n📋 Testing with state - UUID: {state['uuid']}")
        print(f"   Industry: {state['industry']}")
        print(f"   Revenue: {state['revenue_range']}")
        print(f"   Exit Timeline: {state['exit_timeline']}")
        
        # Execute enhanced scoring node
        print("\n🚀 Executing enhanced scoring_node...")
        start_time = datetime.now()
        
        result_state = scoring_node(state)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_result("execution_time", execution_time)
        log_result("result_state", result_state)
        
        print(f"\n⏱️  Execution completed in {execution_time:.2f} seconds")
        
        # Validate results
        print("\n🔍 Validating enhanced results...")
        
        scoring_result = result_state.get("scoring_result")
        
        # 1. Check basic scoring worked
        log_assertion(
            "Scoring result populated",
            scoring_result is not None,
            {"has_result": scoring_result is not None}
        )
        
        # 2. Check overall score
        overall_score = scoring_result.get("overall_score") if scoring_result else None
        log_assertion(
            "Overall score calculated",
            overall_score is not None and 0 <= overall_score <= 10,
            {"score": overall_score}
        )
        
        # 3. Check all categories scored
        category_scores = scoring_result.get("category_scores", {}) if scoring_result else {}
        expected_categories = ["owner_dependence", "revenue_quality", "financial_readiness", 
                             "operational_resilience", "growth_value"]
        
        for category in expected_categories:
            has_category = category in category_scores
            has_insight = category_scores.get(category, {}).get("insight") is not None
            
            log_assertion(
                f"{category} scored with insight",
                has_category and has_insight,
                {
                    "has_score": has_category,
                    "has_insight": has_insight,
                    "score": category_scores.get(category, {}).get("score"),
                    "insight_preview": category_scores.get(category, {}).get("insight", "")[:50] + "..."
                }
            )
        
        # 4. Check LLM insights metadata
        has_llm_insights = scoring_result.get("scoring_metadata", {}).get("has_llm_insights", False)
        log_assertion(
            "LLM insights flag set",
            has_llm_insights,
            {"has_llm_insights": has_llm_insights}
        )
        
        # 5. Check key insights collected
        key_insights = scoring_result.get("key_insights", []) if scoring_result else []
        log_assertion(
            "Key insights collected",
            len(key_insights) == 5,  # One per category
            {"insight_count": len(key_insights)}
        )
        
        # 6. Check execution time reasonable (should be 10-20s with LLM)
        log_assertion(
            "Execution time reasonable for LLM processing",
            5 < execution_time < 25,
            {"execution_time": execution_time}
        )
        
        # 7. Display sample results
        if scoring_result:
            print("\n📊 Sample Enhanced Results:")
            print(f"   Overall Score: {overall_score}/10 - {scoring_result.get('readiness_level')}")
            print(f"   Primary Focus: {scoring_result.get('focus_areas', {}).get('primary', {}).get('category')}")
            
            # Show a sample insight
            if key_insights:
                sample = key_insights[0]
                print(f"\n   Sample Insight ({sample['category']}):")
                print(f"   Score: {sample['score']}/10")
                print(f"   \"{sample['insight']}\"")
            
            # Show scoring distribution
            if category_scores:
                print(f"\n   Category Scores:")
                for cat, data in category_scores.items():
                    print(f"   - {cat}: {data.get('score')}/10")
        
        # Summary
        print("\n📈 Test Summary:")
        total_assertions = len(_test_data["assertions"])
        passed_assertions = sum(1 for a in _test_data["assertions"] if a["passed"])
        
        print(f"   Total Assertions: {total_assertions}")
        print(f"   Passed: {passed_assertions}")
        print(f"   Failed: {total_assertions - passed_assertions}")
        
        if passed_assertions == total_assertions:
            print("\n✨ All enhanced scoring tests passed! 🎉")
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
        
        # Log final summary
        log_result("test_summary", {
            "total_assertions": total_assertions,
            "passed": passed_assertions,
            "failed": total_assertions - passed_assertions,
            "success_rate": (passed_assertions/total_assertions)*100 if total_assertions > 0 else 0,
            "overall_score": overall_score,
            "insight_count": len(key_insights),
            "has_llm_insights": has_llm_insights
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
    filename = f"output_test_enhanced_scoring_{timestamp}.json"
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete test output saved to: {filename}")
    
    # Also create a summary file
    summary = {
        "test": "enhanced_scoring_node",
        "timestamp": _test_data["timestamp"],
        "execution_time": _test_data["results"].get("execution_time"),
        "assertions": {
            "total": len(_test_data["assertions"]),
            "passed": sum(1 for a in _test_data["assertions"] if a["passed"]),
            "failed": sum(1 for a in _test_data["assertions"] if not a["passed"])
        },
        "errors": len(_test_data["errors"]),
        "has_openai_key": _test_data["results"].get("has_openai_key"),
        "overall_score": _test_data["results"].get("test_summary", {}).get("overall_score"),
        "insight_count": _test_data["results"].get("test_summary", {}).get("insight_count"),
        "has_llm_insights": _test_data["results"].get("test_summary", {}).get("has_llm_insights")
    }
    
    summary_filename = f"summary_test_enhanced_scoring_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Test summary saved to: {summary_filename}")


if __name__ == "__main__":
    try:
        test_enhanced_scoring_node()
    finally:
        save_test_output()