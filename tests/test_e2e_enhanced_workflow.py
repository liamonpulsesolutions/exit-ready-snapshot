#!/usr/bin/env python3
"""
End-to-End test of the complete enhanced LangGraph workflow.
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
        "q1": "Quality control final sign-offs for our largest automotive client - they require my personal certification on all batches due to safety requirements. 2) Pricing decisions and contract negotiations for orders over $50K - I have the cost knowledge and supplier relationships to ensure we maintain proper margins while staying competitive",
        "q2": "3-7 days",
        "q3": "Custom metal fabrication for automotive suppliers - about 70% of revenue. Long-term contracts with 4 main clients, typically 2-3 year agreements. 2) Specialty food processing equipment manufacturing - about 20% of revenue. Higher margin custom orders, usually $25K-$100K each. Remaining 10% is maintenance and repair services for existing equipment",
        "q4": "60-80%",
        "q5": "6",
        "q6": "Stayed flat",
        "q7": "Programming and setup of our CNC machines - Tom has 15 years experience with our specific equipment and knows every client's custom specifications by heart. 2) Supplier relationships and materials procurement - Jennifer manages all vendor relationships and knows which suppliers can deliver quality materials on tight deadlines at the best prices.",
        "q8": "8",
        "q9": "ISO 9001 and AS9100 aerospace certifications that took 3 years and $200K+ to achieve - only 12 companies in our region have both certifications, creating significant competitive moat for aerospace and automotive work. 2) $2M in specialized equipment including a rare 5-axis CNC machine that can handle parts our competitors can't manufacture. This equipment is fully paid off and would cost $3M+ to replace today, giving us 25-30% better margins on complex jobs",
        "q10": "4"
    },
    "_tallySubmissionId": "test-e2e-enhanced-001",
    "_tallyFormId": "3100Y4",
    "_tallyResponseId": "test-e2e-enhanced-001"
}

async def test_e2e_enhanced_workflow():
    """Test the complete enhanced workflow end-to-end"""
    print("\n" + "="*80)
    print("🚀 TESTING END-TO-END ENHANCED LANGGRAPH WORKFLOW")
    print("="*80 + "\n")
    
    try:
        # Import workflow components
        from workflow.graph import process_assessment_async
        from workflow.core.pii_handler import store_pii_mapping
        
        log_result("imports_successful", True)
        print("✅ Successfully imported LangGraph workflow")
        
        # Check required API keys
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_perplexity = bool(os.getenv("PERPLEXITY_API_KEY"))
        
        print(f"\n📡 API Keys Status:")
        print(f"   OpenAI: {'✅ Found' if has_openai else '❌ REQUIRED'}")
        print(f"   Perplexity: {'✅ Found' if has_perplexity else '⚠️  Optional (will use fallback)'}")
        
        log_result("has_openai_key", has_openai)
        log_result("has_perplexity_key", has_perplexity)
        
        if not has_openai:
            print("\n❌ ERROR: OpenAI API key is required for enhanced workflow")
            return
        
        # CRITICAL: Store PII mapping for the test UUID
        # This simulates what the intake node would do
        test_pii_mapping = {
            "[OWNER_NAME]": SAMPLE_FORM_DATA["name"],
            "[EMAIL]": SAMPLE_FORM_DATA["email"],
            "[LOCATION]": SAMPLE_FORM_DATA["location"],
            "[UUID]": SAMPLE_FORM_DATA["uuid"]
        }
        
        # Check responses for company name mentions
        all_responses = " ".join(str(v) for v in SAMPLE_FORM_DATA.get("responses", {}).values())
        # Look for patterns like "our automotive client", "Tom", "Jennifer" (employee names)
        if "Tom" in all_responses:
            test_pii_mapping["[EMPLOYEE_1]"] = "Tom"
        if "Jennifer" in all_responses:
            test_pii_mapping["[EMPLOYEE_2]"] = "Jennifer"
            
        store_pii_mapping(SAMPLE_FORM_DATA["uuid"], test_pii_mapping)
        print(f"\n📝 Stored test PII mapping for UUID: {SAMPLE_FORM_DATA['uuid']}")
        print(f"   Mapping entries: {len(test_pii_mapping)}")
        
        # Prepare initial state with simulated intake results
        # This is what the intake node would have produced
        anonymized_responses = {}
        for q_id, response in SAMPLE_FORM_DATA.get("responses", {}).items():
            # Anonymize the responses
            anonymized_response = response
            # Replace owner name
            if SAMPLE_FORM_DATA["name"] in response:
                anonymized_response = anonymized_response.replace(SAMPLE_FORM_DATA["name"], "[OWNER_NAME]")
            # Replace email
            if SAMPLE_FORM_DATA["email"] in response:
                anonymized_response = anonymized_response.replace(SAMPLE_FORM_DATA["email"], "[EMAIL]")
            # Replace employee names
            if "Tom" in response:
                anonymized_response = anonymized_response.replace("Tom", "[EMPLOYEE_1]")
            if "Jennifer" in response:
                anonymized_response = anonymized_response.replace("Jennifer", "[EMPLOYEE_2]")
            anonymized_responses[q_id] = anonymized_response
        
        initial_state = {
            "uuid": SAMPLE_FORM_DATA.get("uuid", "unknown"),
            "form_data": SAMPLE_FORM_DATA,
            "locale": "us",
            "current_stage": "intake",
            "processing_time": {"intake": 0.5},
            "messages": ["Assessment started", "Intake completed"],
            # Add all the data that intake node would have added
            "intake_result": {
                "validation_status": "success",
                "pii_entries": len(test_pii_mapping),
                "crm_logged": True,
                "responses_logged": True
            },
            "anonymized_data": {
                "name": "[OWNER_NAME]",
                "email": "[EMAIL]",
                "industry": SAMPLE_FORM_DATA["industry"],
                "revenue_range": SAMPLE_FORM_DATA["revenue_range"],  # Already normalized above
                "years_in_business": SAMPLE_FORM_DATA["years_in_business"],
                "age_range": SAMPLE_FORM_DATA["age_range"],
                "exit_timeline": SAMPLE_FORM_DATA["exit_timeline"],
                "location": SAMPLE_FORM_DATA["location"],
                "responses": anonymized_responses
            },
            "pii_mapping": test_pii_mapping,
            # Business context for easy access
            "industry": SAMPLE_FORM_DATA["industry"],
            "location": SAMPLE_FORM_DATA["location"],
            "revenue_range": SAMPLE_FORM_DATA["revenue_range"],
            "exit_timeline": SAMPLE_FORM_DATA["exit_timeline"],
            "years_in_business": SAMPLE_FORM_DATA["years_in_business"]
        }
        
        # Execute the complete workflow
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
        
        # Validate results
        print("\n🔍 Validating workflow results...")
        
        # 1. Check status
        log_assertion(
            "Workflow completed successfully",
            result.get("status") == "completed",
            {"status": result.get("status"), "error": result.get("error")}
        )
        
        # 2. Check all required fields
        required_fields = ["uuid", "status", "locale", "owner_name", "email", 
                         "scores", "executive_summary", "next_steps", "processing_time"]
        
        for field in required_fields:
            log_assertion(
                f"Result contains {field}",
                field in result,
                {"has_field": field in result}
            )
        
        # 3. Check scores are numeric
        scores = result.get("scores", {})
        overall_score = scores.get("overall_score")
        log_assertion(
            "Overall score is numeric",
            isinstance(overall_score, (int, float)) and 0 <= overall_score <= 10,
            {"score": overall_score}
        )
        
        # 4. Check each stage was executed
        processing_times = result.get("processing_time", {})
        expected_stages = ["intake", "research", "scoring", "summary", "qa", "pii_reinsertion"]
        
        for stage in expected_stages:
            stage_time = processing_times.get(stage)
            log_assertion(
                f"{stage} stage executed",
                stage_time is not None and stage_time > 0,
                {"time": stage_time}
            )
        
        # 5. Check LLM enhancements are present
        
        # Research should have citations
        metadata = result.get("metadata", {})
        stages_completed = metadata.get("stages_completed", [])
        
        log_assertion(
            "All stages completed",
            len(stages_completed) >= 6,
            {"stages": stages_completed}
        )
        
        # Executive summary should be substantial (LLM generated)
        exec_summary = result.get("executive_summary", "")
        log_assertion(
            "Executive summary is LLM-generated (>200 chars)",
            len(exec_summary) > 200,
            {"length": len(exec_summary), "preview": exec_summary[:100] + "..."}
        )
        
        # Next steps should be personalized
        next_steps = result.get("next_steps", "")
        log_assertion(
            "Next steps are personalized (contains timeline)",
            "1-2 year" in next_steps or "timeline" in next_steps.lower(),
            {"contains_timeline": "timeline" in next_steps.lower()}
        )
        
        # 6. Check performance targets
        log_assertion(
            "Total execution under 3 minutes",
            execution_time < 180,
            {"time": execution_time, "target": 180}
        )
        
        # 7. Display key results
        print(f"\n📊 Assessment Results:")
        print(f"   Overall Score: {overall_score}/10")
        print(f"   Readiness Level: {scores.get('readiness_level', 'Unknown')}")
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