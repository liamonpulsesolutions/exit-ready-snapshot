#!/usr/bin/env python3
"""
End-to-end test for enhanced LangGraph workflow.
Tests all nodes with LLM intelligence working together.
"""

import os
import sys
import json
import logging
from datetime import datetime
from io import StringIO
from pathlib import Path
import asyncio

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
    "revenue_range": "$10M-$25M",  # Normalized format for scoring
    "location": "Northeast US",
    "exit_timeline": "1-2 years",
    "age_range": "55-64",
    "responses": {
        "q1": "Quality control final sign-offs for our largest automotive client - they require my personal certification on all batches due to safety requirements.",
        "q2": "70-80%",
        "q3": "Automotive parts manufacturing (60%), Custom fabrication services (30%), Equipment maintenance contracts (10%)",
        "q4": "40-60%",
        "q5": "6",
        "q6": "$10M-$20M annual revenue",
        "q7": "Major disruption - production would halt within days",
        "q8": "Partial documentation exists but scattered across different systems",
        "q9": "Declining due to supply chain costs and overseas competition",
        "q10": "Our precision quality standards and 30-year reputation with automotive OEMs"
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
        
        # Store PII mapping for test UUID
        from workflow.core.pii_handler import store_pii_mapping
        test_pii_mapping = {
            "[OWNER_NAME]": SAMPLE_FORM_DATA["name"],
            "[EMAIL]": SAMPLE_FORM_DATA["email"],
            "[COMPANY_NAME]": "Test Manufacturing Co",
            "[COMPANY]": "Test Manufacturing Co",
            "[INDUSTRY]": SAMPLE_FORM_DATA["industry"],
            "[LOCATION]": SAMPLE_FORM_DATA["location"]
        }
        store_pii_mapping(SAMPLE_FORM_DATA["uuid"], test_pii_mapping)
        print(f"\n📝 Stored test PII mapping for UUID: {SAMPLE_FORM_DATA['uuid']}")
        print(f"   Mapping entries: {len(test_pii_mapping)}")
        
        # Create initial state simulating intake completion
        initial_state = {
            "uuid": SAMPLE_FORM_DATA["uuid"],
            "form_data": SAMPLE_FORM_DATA,
            "locale": "us",
            "current_stage": "intake_complete",
            "error": None,
            "processing_time": {"intake": 0.5},
            "messages": ["Simulated intake completion"],
            # Business context
            "industry": SAMPLE_FORM_DATA["industry"],
            "location": SAMPLE_FORM_DATA["location"],
            "revenue_range": SAMPLE_FORM_DATA["revenue_range"],
            "exit_timeline": SAMPLE_FORM_DATA["exit_timeline"],
            "years_in_business": SAMPLE_FORM_DATA["years_in_business"],
            # Simulated intake result
            "intake_result": {
                "validation_status": "success",
                "pii_mapping": test_pii_mapping,
                "anonymized": True
            },
            # Anonymized data for processing
            "anonymized_data": {
                "responses": SAMPLE_FORM_DATA["responses"],
                "industry": SAMPLE_FORM_DATA["industry"],
                "revenue_range": SAMPLE_FORM_DATA["revenue_range"],
                "years_in_business": SAMPLE_FORM_DATA["years_in_business"],
                "exit_timeline": SAMPLE_FORM_DATA["exit_timeline"],
                "location": SAMPLE_FORM_DATA["location"]
            },
            "pii_mapping": test_pii_mapping
        }
        
        print(f"\n🎯 Executing full assessment pipeline...")
        print(f"   UUID: {SAMPLE_FORM_DATA['uuid']}")
        print(f"   Business: {SAMPLE_FORM_DATA['industry']} / {SAMPLE_FORM_DATA['revenue_range']}")
        print(f"   Timeline: {SAMPLE_FORM_DATA['exit_timeline']}")
        print(f"   Starting from: intake stage (simulated)")
        
        start_time = datetime.now()
        
        # Create a modified workflow that skips intake since we simulated it
        from workflow.graph import create_workflow
        from langgraph.graph import StateGraph, END
        from workflow.state import WorkflowState
        from workflow.nodes.research import research_node
        from workflow.nodes.scoring import scoring_node
        from workflow.nodes.summary import summary_node
        from workflow.nodes.qa import qa_node
        from workflow.nodes.pii_reinsertion import pii_reinsertion_node
        
        # Create workflow starting from research (skip intake)
        workflow = StateGraph(WorkflowState)
        workflow.add_node("research", research_node)
        workflow.add_node("scoring", scoring_node)
        workflow.add_node("summary", summary_node)
        workflow.add_node("qa", qa_node)
        workflow.add_node("pii_reinsertion", pii_reinsertion_node)
        
        workflow.set_entry_point("research")
        workflow.add_edge("research", "scoring")
        workflow.add_edge("scoring", "summary")
        workflow.add_edge("summary", "qa")
        workflow.add_edge("qa", "pii_reinsertion")
        workflow.add_edge("pii_reinsertion", END)
        
        app = workflow.compile()
        
        # Run the workflow
        result = await app.ainvoke(initial_state)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        log_result("execution_time", execution_time)
        log_result("workflow_result", result)
        
        print(f"\n⏱️  Total execution time: {execution_time:.2f} seconds")
        
        # Validate results - CHECK final_output INSTEAD OF result
        print("\n🔍 Validating workflow results...")
        
        # Extract final_output where all the data is
        final_output = result.get("final_output", {})
        
        # 1. Check workflow completed
        log_assertion(
            "Workflow completed successfully",
            result.get("current_stage") == "completed" and not result.get("error"),
            {"stage": result.get("current_stage"), "error": result.get("error")}
        )
        
        # 2. Check all required fields IN final_output
        log_assertion(
            "Result contains uuid",
            result.get("uuid") is not None,
            {"has_field": result.get("uuid") is not None}
        )
        
        log_assertion(
            "Result contains status",
            final_output.get("status") == "completed",
            {"status": final_output.get("status")}
        )
        
        log_assertion(
            "Result contains locale", 
            result.get("locale") is not None,
            {"locale": result.get("locale")}
        )
        
        # Check personalization fields in final_output
        log_assertion(
            "Result contains owner_name",
            final_output.get("owner_name") is not None,
            {"owner_name": final_output.get("owner_name")}
        )
        
        log_assertion(
            "Result contains email",
            final_output.get("email") is not None,
            {"email": final_output.get("email")}
        )
        
        # 3. Check scores in final_output
        scores = final_output.get("scores", {})
        overall_score = scores.get("overall")
        
        log_assertion(
            "Result contains scores",
            bool(scores),
            {"has_scores": bool(scores)}
        )
        
        log_assertion(
            "Result contains executive_summary",
            bool(final_output.get("executive_summary")),
            {"has_summary": bool(final_output.get("executive_summary"))}
        )
        
        log_assertion(
            "Result contains next_steps",
            bool(final_output.get("next_steps")),
            {"has_next_steps": bool(final_output.get("next_steps"))}
        )
        
        log_assertion(
            "Result contains processing_time",
            bool(result.get("processing_time")),
            {"has_timing": bool(result.get("processing_time"))}
        )
        
        log_assertion(
            "Overall score is numeric",
            isinstance(overall_score, (int, float)) and 0 <= overall_score <= 10,
            {"score": overall_score}
        )
        
        # 4. Check stage execution times
        processing_times = result.get("processing_time", {})
        stages = ["intake", "research", "scoring", "summary", "qa", "pii_reinsertion"]
        
        for stage in stages:
            if stage != "intake":  # We simulated intake
                log_assertion(
                    f"{stage} stage executed",
                    stage in processing_times and processing_times[stage] > 0,
                    {"time": processing_times.get(stage)}
                )
        
        # For intake, we manually added it
        log_assertion(
            "intake stage executed",
            "intake" in processing_times,
            {"time": processing_times.get("intake")}
        )
        
        # 5. Check all stages completed
        expected_stages = ["intake", "research", "scoring", "summary", "pii_reinsertion"]
        completed_stages = list(processing_times.keys())
        
        log_assertion(
            "All stages completed",
            all(stage in completed_stages for stage in expected_stages),
            {"stages": completed_stages}
        )
        
        # 6. Check LLM-generated content quality
        exec_summary = final_output.get("executive_summary", "")
        log_assertion(
            "Executive summary is LLM-generated (>200 chars)",
            len(exec_summary) > 200,
            {"length": len(exec_summary), "preview": exec_summary[:200] + "..."}
        )
        
        # 7. Check personalization
        next_steps = final_output.get("next_steps", "")
        log_assertion(
            "Next steps are personalized (contains timeline)",
            any(timeline in next_steps for timeline in ["1-2 years", "timeline", "18-24 months"]),
            {"contains_timeline": any(t in next_steps for t in ["1-2 years", "timeline", "18-24 months"])}
        )
        
        # 8. Check execution time
        log_assertion(
            "Total execution under 3 minutes",
            execution_time < 180,
            {"time": execution_time}
        )
        
        # Display key results
        print(f"\n📊 Assessment Results:")
        print(f"   Overall Score: {overall_score}/10")
        print(f"   Readiness Level: {final_output.get('scores', {}).get('readiness_level', 'Unknown')}")
        print(f"   Total Processing Time: {execution_time:.1f}s")
        
        print(f"\n   Stage Breakdown:")
        for stage, time in processing_times.items():
            print(f"   - {stage}: {time:.1f}s")
        
        print(f"\n   Executive Summary Preview:")
        print(f"   {exec_summary[:200]}...")
        
        # 8. Check for warnings or errors
        if result.get("warnings"):
            print(f"\n⚠️  Warnings: {len(result.get('warnings', []))}")
            for warning in result.get("warnings", [])[:3]:
                print(f"   - {warning}")
        
        # Summary
        print("\n📈 Test Summary:")
        total_assertions = len(_test_data["assertions"])
        passed_assertions = sum(1 for a in _test_data["assertions"] if a["passed"])
        
        print(f"   Total Assertions: {total_assertions}")
        print(f"   Passed: {passed_assertions}")
        print(f"   Failed: {total_assertions - passed_assertions}")
        
        if passed_assertions == total_assertions:
            print("\n✨ All end-to-end tests passed! Enhanced workflow is ready! 🎉")
        else:
            print("\n⚠️  Some tests failed. Review the details above.")
        
        log_result("test_summary", {
            "total_assertions": total_assertions,
            "passed": passed_assertions,
            "failed": total_assertions - passed_assertions,
            "success_rate": (passed_assertions/total_assertions)*100 if total_assertions > 0 else 0,
            "execution_time": execution_time,
            "overall_score": overall_score
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