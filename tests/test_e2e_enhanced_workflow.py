#!/usr/bin/env python3
"""
End-to-end test for enhanced LangGraph workflow.
Tests all nodes with LLM intelligence working together.
Updated with fixes for timeline assertions and LangGraph state structure.
"""

import os
import sys
import json
import logging
from datetime import datetime
from io import StringIO
from pathlib import Path
import asyncio
import re

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
    "test_name": "test_e2e_enhanced_workflow.py",
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

# Sample form data for end-to-end test - REAL EXAMPLE FORMAT
SAMPLE_FORM_DATA = {
    "uuid": "test-e2e-enhanced-001",
    "timestamp": "2025-07-15T14:32:55.000Z",
    "name": "Test 02",
    "email": "Respondee@test2.com",
    "industry": "Manufacturing & Production",
    "years_in_business": "5-10 years",
    "revenue_range": "$10M-$25M",
    "location": "Northeast US",
    "exit_timeline": "1-2 years",
    "age_range": "55-64",
    "responses": {
        "q1": "Quality control final sign-offs for our largest automotive client - they require my personal certification on all batches due to safety requirements.",
        "q2": "3-7 days",
        "q3": "Automotive parts manufacturing (60%), Custom fabrication services (30%), Equipment maintenance contracts (10%)",
        "q4": "40-60%",
        "q5": "6",
        "q6": "Stayed flat",
        "q7": "Programming and setup of our CNC machines - Tom has 15 years experience but he's the only one who knows the systems.",
        "q8": "6",
        "q9": "Our precision quality standards and 30-year reputation with automotive OEMs",
        "q10": "7"
    }
}


async def test_e2e_enhanced_workflow():
    """Test the complete enhanced workflow with all LLM improvements"""
    print("\n" + "="*80)
    print("🧪 TESTING END-TO-END ENHANCED LANGGRAPH WORKFLOW")
    print("="*80 + "\n")
    
    try:
        # Check environment
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_perplexity = bool(os.getenv("PERPLEXITY_API_KEY"))
        
        log_result("has_openai_key", has_openai)
        log_result("has_perplexity_key", has_perplexity)
        
        print("📡 API Keys Status:")
        print(f"   OpenAI: {'✅ Found' if has_openai else '❌ Missing'}")
        print(f"   Perplexity: {'✅ Found' if has_perplexity else '❌ Missing'}")
        
        if not has_openai:
            print("\n❌ Cannot run test without OpenAI API key")
            return
        
        # Import the workflow
        from workflow.graph import process_assessment_async
        
        print(f"\n🎯 Executing full assessment pipeline...")
        print(f"   UUID: {SAMPLE_FORM_DATA['uuid']}")
        print(f"   Business: {SAMPLE_FORM_DATA['industry']} / {SAMPLE_FORM_DATA['revenue_range']}")
        print(f"   Timeline: {SAMPLE_FORM_DATA['exit_timeline']}")
        
        start_time = datetime.now()
        
        # Run the complete workflow
        result = await process_assessment_async(SAMPLE_FORM_DATA)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_result("execution_time", execution_time)
        log_result("workflow_result", result)
        
        print(f"\n⏱️  Total execution time: {execution_time:.2f} seconds")
        
        # Validate results
        print("\n🔍 Validating workflow results...")
        
        # 1. Check workflow completed
        log_assertion(
            "Workflow completed successfully",
            result.get("status") == "completed" and not result.get("error"),
            {"status": result.get("status"), "error": result.get("error")}
        )
        
        # 2. Check all required fields in the API response format
        required_fields = [
            "uuid", "status", "owner_name", "email", "industry", 
            "location", "locale", "scores", "executive_summary",
            "category_summaries", "recommendations", "next_steps"
        ]
        
        for field in required_fields:
            log_assertion(
                f"Result contains {field}",
                field in result and result[field] is not None,
                {field: result.get(field) is not None}
            )
        
        # 3. Check scores structure
        scores = result.get("scores", {})
        score_categories = [
            "overall", "owner_dependence", "revenue_quality",
            "financial_readiness", "operational_resilience", "growth_value"
        ]
        
        for category in score_categories:
            log_assertion(
                f"Scores contain {category}",
                category in scores,
                {"has_score": category in scores, "value": scores.get(category)}
            )
        
        # Check score ranges
        for category, score in scores.items():
            log_assertion(
                f"{category} score is valid",
                isinstance(score, (int, float)) and 1 <= score <= 10,
                {"score": score}
            )
        
        # 4. Check processing metadata
        metadata = result.get("metadata", {})
        log_assertion(
            "Metadata contains stages completed",
            "stages_completed" in metadata,
            {"stages": metadata.get("stages_completed", [])}
        )
        
        # 5. Check LLM-generated content quality
        exec_summary = result.get("executive_summary", "")
        log_assertion(
            "Executive summary is substantial (>200 chars)",
            len(exec_summary) > 200,
            {"length": len(exec_summary)}
        )
        
        # 6. Check category summaries structure
        category_summaries = result.get("category_summaries", {})
        log_assertion(
            "Category summaries is a dictionary",
            isinstance(category_summaries, dict),
            {"type": type(category_summaries).__name__}
        )
        
        if isinstance(category_summaries, dict):
            for category in ["owner_dependence", "revenue_quality", "financial_readiness", 
                           "operational_resilience", "growth_value"]:
                log_assertion(
                    f"Category summary exists for {category}",
                    category in category_summaries,
                    {"has_summary": category in category_summaries}
                )
        
        # 7. Check recommendations structure
        recommendations = result.get("recommendations", {})
        if isinstance(recommendations, dict):
            log_assertion(
                "Recommendations contain quick_wins",
                "quick_wins" in recommendations,
                {"has_quick_wins": "quick_wins" in recommendations}
            )
            log_assertion(
                "Recommendations contain strategic_priorities",
                "strategic_priorities" in recommendations,
                {"has_strategic": "strategic_priorities" in recommendations}
            )
        
        # 8. Check timeline in next steps (FIXED: Use regex pattern)
        next_steps = result.get("next_steps", "")
        
        # Accept various timeline formats
        timeline_patterns = [
            r"1-2 years?",
            r"12-24 months?",
            r"one to two years?",
            r"18-24 months?",
            r"next 1-2 years?"
        ]
        
        timeline_found = any(re.search(pattern, next_steps, re.IGNORECASE) for pattern in timeline_patterns)
        
        log_assertion(
            "Next steps contain timeline reference",
            timeline_found,
            {"timeline_found": timeline_found, "next_steps_preview": next_steps[:200] + "..."}
        )
        
        # 9. Check outcome framing (should use "typically/often" language)
        outcome_framing_words = ["typically", "often", "generally", "on average", "businesses like yours"]
        framing_count = sum(1 for word in outcome_framing_words if word in exec_summary.lower())
        
        log_assertion(
            "Executive summary uses proper outcome framing",
            framing_count >= 2,
            {"framing_words_found": framing_count}
        )
        
        # Check recommendations for outcome framing
        if isinstance(recommendations, str):
            rec_framing_count = sum(1 for word in outcome_framing_words if word in recommendations.lower())
        else:
            rec_text = str(recommendations)
            rec_framing_count = sum(1 for word in outcome_framing_words if word in rec_text.lower())
        
        log_assertion(
            "Recommendations use proper outcome framing",
            rec_framing_count >= 1,
            {"framing_words_found": rec_framing_count}
        )
        
        # 10. Check execution time is reasonable
        log_assertion(
            "Total execution under 3 minutes",
            execution_time < 180,
            {"time": execution_time}
        )
        
        # 11. Check for any promise language (should not exist)
        promise_words = ["will increase", "will achieve", "guaranteed", "ensure your", "definitely"]
        promises_found = [word for word in promise_words if word in str(result).lower()]
        
        log_assertion(
            "No promise language found",
            len(promises_found) == 0,
            {"promises_found": promises_found}
        )
        
        # Display key results
        print(f"\n📊 Assessment Results:")
        print(f"   Overall Score: {scores.get('overall', 'N/A')}/10")
        print(f"   Owner Name: {result.get('owner_name', 'N/A')}")
        print(f"   Email: {result.get('email', 'N/A')}")
        print(f"   Industry: {result.get('industry', 'N/A')}")
        print(f"   Total Processing Time: {execution_time:.1f}s")
        
        if metadata.get("stage_timings"):
            print(f"\n   Stage Breakdown:")
            for stage, time in metadata["stage_timings"].items():
                print(f"   - {stage}: {time:.1f}s")
        
        print(f"\n   Executive Summary Preview:")
        print(f"   {exec_summary[:200]}...")
        
        # Summary
        print("\n📈 Test Summary:")
        total_assertions = len(_test_data["assertions"])
        passed_assertions = sum(1 for a in _test_data["assertions"] if a["passed"])
        
        print(f"   Total Assertions: {total_assertions}")
        print(f"   Passed: {passed_assertions}")
        print(f"   Failed: {total_assertions - passed_assertions}")
        
        if passed_assertions == total_assertions:
            print("\n✨ All end-to-end tests passed! LangGraph workflow is ready! 🎉")
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
            # Print failed assertions
            print("\nFailed assertions:")
            for assertion in _test_data["assertions"]:
                if not assertion["passed"]:
                    print(f"   - {assertion['description']}")
                    if assertion.get("details"):
                        print(f"     Details: {assertion['details']}")
        
        log_result("test_summary", {
            "total_assertions": total_assertions,
            "passed": passed_assertions,
            "failed": total_assertions - passed_assertions,
            "success_rate": (passed_assertions/total_assertions)*100 if total_assertions > 0 else 0,
            "execution_time": execution_time,
            "overall_score": scores.get("overall", "N/A")
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
    filename = f"output_test_e2e_enhanced_{timestamp}.json"
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(_test_data, f, indent=2, default=str)
    
    print(f"\n💾 Complete test output saved to: {filename}")
    
    # Also create a summary file
    summary = {
        "test": "e2e_enhanced_workflow",
        "timestamp": _test_data["timestamp"],
        "execution_time": _test_data["results"].get("execution_time"),
        "assertions": {
            "total": len(_test_data["assertions"]),
            "passed": sum(1 for a in _test_data["assertions"] if a["passed"]),
            "failed": sum(1 for a in _test_data["assertions"] if not a["passed"])
        },
        "errors": len(_test_data["errors"]),
        "has_openai_key": _test_data["results"].get("has_openai_key"),
        "has_perplexity_key": _test_data["results"].get("has_perplexity_key"),
        "overall_score": _test_data["results"].get("test_summary", {}).get("overall_score"),
        "success_rate": _test_data["results"].get("test_summary", {}).get("success_rate")
    }
    
    summary_filename = f"summary_test_e2e_enhanced_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📄 Test summary saved to: {summary_filename}")


def run_async_test():
    """Run the async test with proper event loop handling"""
    try:
        asyncio.run(test_e2e_enhanced_workflow())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            # We're in a notebook or already have a loop
            loop = asyncio.get_event_loop()
            loop.run_until_complete(test_e2e_enhanced_workflow())
        else:
            raise


if __name__ == "__main__":
    try:
        run_async_test()
    finally:
        save_test_output()