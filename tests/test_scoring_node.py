#!/usr/bin/env python3
"""
Test script for the scoring node in LangGraph workflow.
Validates all scoring functionality including:
- Owner dependence scoring
- Revenue quality scoring
- Financial readiness scoring
- Operational resilience scoring
- Growth value scoring
- Overall score calculation
- Focus area identification
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
    "test_name": "test_scoring_node.py",
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

# Sample state after research node
SAMPLE_STATE_AFTER_RESEARCH = {
    "uuid": "test-scoring-001",
    "form_data": {
        "uuid": "test-scoring-001",
        "industry": "Professional Services",
        "revenue_range": "$1M-$5M",
        "years_in_business": "10-20 years",
        "age_range": "55-64",
        "exit_timeline": "1-2 years",
        "location": "Pacific/Western US",
        "responses": {
            "q1": "I handle all client meetings and final approvals",
            "q2": "Less than 3 days",
            "q3": "Consulting 60%, Training 30%, Software 10%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Improved slightly",
            "q7": "Client relationships and technical knowledge",
            "q8": "4",
            "q9": "Long-term clients, specialized expertise, location",
            "q10": "8"
        }
    },
    "locale": "us",
    "current_stage": "research",
    "processing_time": {
        "intake": 0.005,
        "research": 0.002
    },
    "messages": ["Intake completed", "Research completed"],
    "error": None,
    # From previous nodes
    "intake_result": {
        "validation_status": "success",
        "pii_entries": 4
    },
    "anonymized_data": {
        "industry": "Professional Services",
        "revenue_range": "$1M-$5M",
        "years_in_business": "10-20 years",
        "exit_timeline": "1-2 years",
        "responses": {
            "q1": "I handle all client meetings and final approvals",
            "q2": "Less than 3 days",
            "q3": "Consulting 60%, Training 30%, Software 10%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Improved slightly",
            "q7": "Client relationships and technical knowledge",
            "q8": "4",
            "q9": "Long-term clients, specialized expertise, location",
            "q10": "8"
        }
    },
    "research_result": {
        "industry": "Professional Services",
        "data_source": "fallback",
        "valuation_benchmarks": {
            "base_EBITDA": "4-6x",
            "base_revenue": "1.2-2.0x",
            "recurring_threshold": "60%",
            "owner_dependence_impact": "20-30% discount if high"
        },
        "improvement_strategies": {
            "owner_dependence": {
                "strategy": "Delegate key decisions",
                "timeline": "6 months",
                "value_impact": "15-20%"
            }
        },
        "market_conditions": {
            "buyer_priorities": ["Recurring revenue", "Systematic operations"],
            "average_sale_time": "9-12 months"
        },
        "industry_context": {
            "key_factors": "Client relationships, recurring contracts",
            "typical_multiples": "4-6x EBITDA"
        }
    },
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

def test_scoring_node():
    """Test the scoring node functionality"""
    print("\n" + "="*80)
    print("🧪 TESTING SCORING NODE")
    print("="*80 + "\n")
    
    try:
        # Import after environment setup
        from workflow.nodes.scoring import scoring_node
        from workflow.state import WorkflowState
        
        log_result("imports_successful", True)
        print("✅ Successfully imported scoring_node and WorkflowState")
        
        # Use state from research
        state = SAMPLE_STATE_AFTER_RESEARCH.copy()
        
        log_result("initial_state", state)
        print(f"\n📋 Using state from research node - UUID: {state['uuid']}")
        print(f"   Industry: {state['industry']}")
        print(f"   Revenue: {state['revenue_range']}")
        print(f"   Years in Business: {state['years_in_business']}")
        print(f"   Exit Timeline: {state['exit_timeline']}")
        
        # Execute scoring node
        print("\n🚀 Executing scoring_node...")
        start_time = datetime.now()
        
        result_state = scoring_node(state)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_result("execution_time", execution_time)
        log_result("result_state", result_state)
        
        print(f"\n⏱️  Execution completed in {execution_time:.2f} seconds")
        
        # Validate results
        print("\n🔍 Validating results...")
        
        # 1. Check stage updated
        log_assertion(
            "Stage updated to 'scoring'",
            result_state.get("current_stage") == "scoring",
            {"actual": result_state.get("current_stage"), "expected": "scoring"}
        )
        
        # 2. Check scoring_result exists
        scoring_result = result_state.get("scoring_result")
        log_assertion(
            "scoring_result populated",
            scoring_result is not None,
            {"has_result": scoring_result is not None}
        )
        
        if scoring_result:
            # 3. Check overall score
            overall_score = scoring_result.get("overall_score")
            log_assertion(
                "Overall score calculated",
                overall_score is not None and 0 <= overall_score <= 10,
                {"score": overall_score}
            )
            
            # 4. Check readiness level
            readiness_level = scoring_result.get("readiness_level")
            valid_levels = ["Needs Work", "Getting Ready", "Exit Ready", "Market Ready"]
            log_assertion(
                "Readiness level determined",
                readiness_level in valid_levels,
                {"level": readiness_level, "valid_levels": valid_levels}
            )
            
            # 5. Check category scores
            category_scores = scoring_result.get("category_scores", {})
            expected_categories = [
                "owner_dependence",
                "revenue_quality", 
                "financial_readiness",
                "operational_resilience",
                "growth_value"
            ]
            
            for category in expected_categories:
                log_assertion(
                    f"Category '{category}' scored",
                    category in category_scores,
                    {"has_category": category in category_scores}
                )
                
                if category in category_scores:
                    cat_data = category_scores[category]
                    score = cat_data.get("score")
                    log_assertion(
                        f"{category} score in valid range",
                        score is not None and 0 <= score <= 10,
                        {"score": score}
                    )
            
            # 6. Check focus areas
            focus_areas = scoring_result.get("focus_areas", {})
            log_assertion(
                "Focus areas identified",
                "primary" in focus_areas or len(focus_areas) > 0,
                {"focus_count": len(focus_areas)}
            )
            
            # 7. Check strengths and gaps
            log_assertion(
                "Top strengths identified",
                "top_strengths" in scoring_result and len(scoring_result.get("top_strengths", [])) > 0,
                {"strength_count": len(scoring_result.get("top_strengths", []))}
            )
            
            log_assertion(
                "Critical gaps identified",
                "critical_gaps" in scoring_result,
                {"gap_count": len(scoring_result.get("critical_gaps", []))}
            )
            
            # 8. Display scoring summary
            print(f"\n📊 Scoring Summary:")
            print(f"   Overall Score: {overall_score}/10")
            print(f"   Readiness Level: {readiness_level}")
            print(f"\n   Category Scores:")
            
            for category, data in category_scores.items():
                score = data.get('score', 0)
                print(f"     - {category}: {score}/10")
                
                # Check for strengths/gaps
                strengths = data.get('strengths', [])
                gaps = data.get('gaps', [])
                
                if strengths:
                    print(f"       Strengths: {len(strengths)} identified")
                if gaps:
                    print(f"       Gaps: {len(gaps)} identified")
            
            # Display focus areas
            if focus_areas:
                primary = focus_areas.get('primary', {})
                if primary:
                    print(f"\n   Primary Focus Area: {primary.get('category', 'Unknown')}")
                    print(f"   Urgency: {primary.get('urgency', 'Unknown')}")
        
        # 9. Check processing time
        log_assertion(
            "Processing time recorded",
            "scoring" in result_state.get("processing_time", {}),
            {"time": result_state.get("processing_time", {}).get("scoring")}
        )
        
        # 10. Check execution time is reasonable
        log_assertion(
            "Execution time under 5 seconds",
            execution_time < 5.0,
            {"actual_time": execution_time, "max_time": 5.0}
        )
        
        # 11. Check no errors
        log_assertion(
            "No errors occurred",
            result_state.get("error") is None,
            {"error": result_state.get("error")}
        )
        
        # 12. Validate score calculation logic
        if scoring_result and category_scores:
            # Check that overall score is weighted average
            total_weight = sum(data.get('weight', 0) for data in category_scores.values())
            log_assertion(
                "Total weights sum to 1.0",
                0.95 <= total_weight <= 1.05,  # Allow small rounding error
                {"total_weight": total_weight}
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
            "overall_score": overall_score if scoring_result else None,
            "readiness_level": readiness_level if scoring_result else None
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
    filename = f"output_test_scoring_node_{timestamp}.json"
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete test output saved to: {filename}")
    
    # Also create a summary file
    summary = {
        "test": "scoring_node",
        "timestamp": _test_data["timestamp"],
        "execution_time": _test_data["results"].get("execution_time"),
        "assertions": {
            "total": len(_test_data["assertions"]),
            "passed": sum(1 for a in _test_data["assertions"] if a["passed"]),
            "failed": sum(1 for a in _test_data["assertions"] if not a["passed"])
        },
        "errors": len(_test_data["errors"]),
        "key_results": {
            "stage": _test_data["results"].get("result_state", {}).get("current_stage"),
            "overall_score": _test_data["results"].get("test_summary", {}).get("overall_score"),
            "readiness_level": _test_data["results"].get("test_summary", {}).get("readiness_level"),
            "categories_scored": len(_test_data["results"].get("result_state", {}).get("scoring_result", {}).get("category_scores", {}))
        }
    }
    
    summary_filename = f"summary_test_scoring_node_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Test summary saved to: {summary_filename}")


if __name__ == "__main__":
    try:
        test_scoring_node()
    finally:
        save_test_output()