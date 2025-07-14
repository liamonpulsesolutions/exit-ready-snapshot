"""
QA node for LangGraph workflow.
Performs quality assurance checks on the generated report.
Reuses all existing QA tools from the CrewAI QA agent.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any

# Import the state type
from src.workflow import AssessmentState

# Import ALL existing tools from the CrewAI QA agent
from src.agents.qa_agent import (
    check_scoring_consistency,
    verify_content_quality,
    scan_for_pii,
    validate_report_structure
)

# Import utilities
from src.utils.json_helper import safe_parse_json

logger = logging.getLogger(__name__)


def qa_node(state: AssessmentState) -> AssessmentState:
    """
    QA node that validates the assessment output.
    
    This node:
    1. Checks scoring consistency
    2. Verifies content quality
    3. Scans for any remaining PII
    4. Validates report structure
    
    Args:
        state: Current workflow state with all previous results
        
    Returns:
        Updated state with QA validation results
    """
    start_time = datetime.now()
    logger.info(f"=== QA NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "quality_assurance"
        state["messages"].append(f"QA validation started at {start_time.isoformat()}")
        
        # Get data from previous stages
        scoring_result = state.get("scoring_result", {})
        summary_result = state.get("summary_result", {})
        
        # Initialize validation results
        qa_results = {
            "scoring_consistency": None,
            "content_quality": None,
            "pii_compliance": None,
            "structure_validation": None,
            "overall_quality_score": 0,
            "issues_found": [],
            "approved": True,
            "ready_for_delivery": True
        }
        
        # Step 1: Check Scoring Consistency
        logger.info("Checking scoring consistency...")
        scoring_data = {
            "scores": scoring_result.get("category_scores", {}),
            "justifications": {},  # Would need to extract from category data
            "responses": state.get("anonymized_data", {}).get("responses", {})
        }
        
        consistency_result = check_scoring_consistency._run(
            scoring_data=json.dumps(scoring_data)
        )
        qa_results["scoring_consistency"] = consistency_result
        
        # Check if there are consistency issues
        if "Issues Found" in consistency_result:
            qa_results["issues_found"].append("Scoring consistency issues detected")
        
        # Step 2: Verify Content Quality
        logger.info("Verifying content quality...")
        content_data = {
            "summary": summary_result.get("executive_summary", ""),
            "recommendations": summary_result.get("recommendations", ""),
            "category_summaries": summary_result.get("category_summaries", {})
        }
        
        quality_result = verify_content_quality._run(
            content_data=json.dumps(content_data)
        )
        qa_results["content_quality"] = quality_result
        
        # Check for quality issues
        if "Needs Revision" in quality_result:
            qa_results["issues_found"].append("Content quality issues detected")
            qa_results["approved"] = False
        
        # Step 3: Scan for PII
        logger.info("Scanning for PII compliance...")
        
        # Combine all content for PII scan
        all_content = {
            "executive_summary": summary_result.get("executive_summary", ""),
            "category_summaries": summary_result.get("category_summaries", {}),
            "recommendations": summary_result.get("recommendations", ""),
            "industry_context": summary_result.get("industry_context", ""),
            "final_report": summary_result.get("final_report", "")
        }
        
        pii_result = scan_for_pii._run(
            full_content=json.dumps(all_content)
        )
        qa_results["pii_compliance"] = pii_result
        
        # Check for PII violations
        if "Failed" in pii_result and "PRIVACY VIOLATION" in pii_result:
            qa_results["issues_found"].append("PII detected in report")
            qa_results["approved"] = False
            qa_results["ready_for_delivery"] = False
        
        # Step 4: Validate Report Structure
        logger.info("Validating report structure...")
        report_data = {
            "executive_summary": summary_result.get("executive_summary", ""),
            "category_scores": scoring_result.get("category_scores", {}),
            "category_summaries": summary_result.get("category_summaries", {}),
            "recommendations": summary_result.get("recommendations", ""),
            "next_steps": "Schedule a consultation to discuss your Exit Value Growth Plan"  # Default
        }
        
        structure_result = validate_report_structure._run(
            report_data=json.dumps(report_data)
        )
        qa_results["structure_validation"] = structure_result
        
        # Check for structure issues
        if "Failed" in structure_result:
            qa_results["issues_found"].append("Report structure incomplete")
            qa_results["approved"] = False
        
        # Calculate overall quality score
        total_checks = 4
        passed_checks = 0
        
        if "Passed" in consistency_result:
            passed_checks += 1
        if "Acceptable" in quality_result or "Excellent" in quality_result:
            passed_checks += 1
        if "Passed" in pii_result:
            passed_checks += 1
        if "Passed" in structure_result:
            passed_checks += 1
        
        qa_results["overall_quality_score"] = round((passed_checks / total_checks) * 10, 1)
        
        # Determine final approval status
        if qa_results["overall_quality_score"] < 7:
            qa_results["approved"] = False
            qa_results["ready_for_delivery"] = False
        
        # Update state
        state["qa_result"] = qa_results
        
        # Add processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        state["processing_time"]["qa"] = processing_time
        
        # Add status message
        status = "approved" if qa_results["approved"] else "needs revision"
        state["messages"].append(
            f"QA completed in {processing_time:.2f}s - "
            f"Quality score: {qa_results['overall_quality_score']}/10, "
            f"Status: {status}, "
            f"Issues: {len(qa_results['issues_found'])}"
        )
        
        logger.info(f"=== QA NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in QA node: {str(e)}", exc_info=True)
        state["error"] = f"QA failed: {str(e)}"
        state["messages"].append(f"ERROR in QA: {str(e)}")
        
        # Set safe defaults on error
        state["qa_result"] = {
            "approved": False,
            "ready_for_delivery": False,
            "error": str(e)
        }
        
        return state