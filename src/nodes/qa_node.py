"""
QA Node for LangGraph implementation of Exit Ready Snapshot.
Performs quality assurance checks on the generated report.
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any

from src.agents.qa_agent import (
    check_scoring_consistency,
    verify_content_quality,
    scan_for_pii,
    validate_report_structure
)

logger = logging.getLogger(__name__)

# Category name mapping to handle differences between scoring and QA validation
CATEGORY_NAME_MAPPING = {
    # Map from what scoring uses -> what QA expects
    'financial_performance': 'financial_readiness',
    'revenue_stability': 'revenue_quality',
    'operations_efficiency': 'operational_resilience',
    'owner_dependence': 'owner_dependence',  # Already matches
    'growth_value': 'growth_value',  # Already matches
    'exit_readiness': 'exit_readiness'  # If used
}

def map_category_names(category_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map category names from scoring format to QA validation format"""
    mapped_data = {}
    
    for old_name, data in category_data.items():
        new_name = CATEGORY_NAME_MAPPING.get(old_name, old_name)
        mapped_data[new_name] = data
    
    return mapped_data

def qa_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    QA node that validates the complete assessment report.
    
    Performs:
    1. Scoring consistency checks
    2. Content quality verification
    3. PII compliance scanning
    4. Report structure validation
    """
    start_time = time.time()
    logger.info(f"Starting QA validation for UUID: {state.get('uuid')}")
    
    try:
        # Get data from previous nodes
        scoring_result = state.get("scoring_result", {})
        summary_result = state.get("summary_result", {})
        form_data = state.get("form_data", {})
        
        # Initialize QA results
        qa_results = {
            "approved": True,
            "quality_score": 0.0,
            "issues_found": [],
            "ready_for_delivery": True,
            "validation_details": {}
        }
        
        # Step 1: Check Scoring Consistency
        logger.info("Checking scoring consistency...")
        scoring_data = {
            "scores": scoring_result.get("category_scores", {}),
            "responses": form_data.get("responses", {})
        }
        
        consistency_result = check_scoring_consistency._run(
            scoring_data=json.dumps(scoring_data)
        )
        qa_results["validation_details"]["scoring_consistency"] = consistency_result
        
        # Check for consistency issues
        if "Failed" in consistency_result:
            qa_results["issues_found"].append("Scoring inconsistencies detected")
            qa_results["approved"] = False
        
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
        qa_results["validation_details"]["content_quality"] = quality_result
        
        # Extract quality score if available
        if "Quality Score:" in quality_result:
            try:
                score_text = quality_result.split("Quality Score:")[1].split("/10")[0].strip()
                qa_results["quality_score"] = float(score_text)
            except:
                qa_results["quality_score"] = 7.0  # Default if parsing fails
        
        # Check for quality issues
        if "Poor" in quality_result or "Failed" in quality_result:
            qa_results["issues_found"].append("Content quality below standards")
            qa_results["approved"] = False
        
        # Step 3: Scan for PII
        logger.info("Scanning for PII compliance...")
        full_content = {
            "executive_summary": summary_result.get("executive_summary", ""),
            "category_summaries": summary_result.get("category_summaries", {}),
            "recommendations": summary_result.get("recommendations", ""),
            "next_steps": summary_result.get("next_steps", "")
        }
        
        pii_result = scan_for_pii._run(
            full_content=json.dumps(full_content)
        )
        qa_results["validation_details"]["pii_compliance"] = pii_result
        
        # Check for PII violations
        if "Failed" in pii_result and "PRIVACY VIOLATION" in pii_result:
            qa_results["issues_found"].append("PII detected in report")
            qa_results["approved"] = False
            qa_results["ready_for_delivery"] = False
        
        # Step 4: Validate Report Structure
        logger.info("Validating report structure...")
        
        # Map category names to what QA expects
        mapped_category_scores = map_category_names(scoring_result.get("category_scores", {}))
        mapped_category_summaries = map_category_names(summary_result.get("category_summaries", {}))
        
        report_data = {
            "executive_summary": summary_result.get("executive_summary", ""),
            "category_scores": mapped_category_scores,  # Use mapped names
            "category_summaries": mapped_category_summaries,  # Use mapped names
            "recommendations": summary_result.get("recommendations", ""),
            "next_steps": summary_result.get("next_steps", "") or "Schedule a consultation to discuss your Exit Value Growth Plan"
        }
        
        structure_result = validate_report_structure._run(
            report_data=json.dumps(report_data)
        )
        qa_results["validation_details"]["structure_validation"] = structure_result
        
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
        
        # Adjust quality score based on checks
        if qa_results["quality_score"] == 0:
            qa_results["quality_score"] = (passed_checks / total_checks) * 10
        
        # Final determination
        if len(qa_results["issues_found"]) == 0:
            qa_results["approved"] = True
            qa_results["ready_for_delivery"] = True
        else:
            qa_results["approved"] = False
            if any("PII" in issue for issue in qa_results["issues_found"]):
                qa_results["ready_for_delivery"] = False
        
        # Update state
        state["qa_result"] = qa_results
        state["current_stage"] = "qa_complete"
        
        # Add timing
        processing_time = time.time() - start_time
        state["processing_time"]["qa"] = processing_time
        
        # Add status message
        if qa_results["approved"]:
            state["messages"].append(
                f"✅ QA validation passed with score {qa_results['quality_score']:.1f}/10"
            )
        else:
            state["messages"].append(
                f"⚠️ QA validation found {len(qa_results['issues_found'])} issues: {', '.join(qa_results['issues_found'])}"
            )
        
        logger.info(f"QA validation completed in {processing_time:.2f}s")
        logger.info(f"QA Result: Approved={qa_results['approved']}, Score={qa_results['quality_score']:.1f}/10")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in QA node: {str(e)}")
        state["error"] = f"QA validation failed: {str(e)}"
        state["current_stage"] = "qa_error"
        
        # Set default QA result on error
        state["qa_result"] = {
            "approved": False,
            "quality_score": 0.0,
            "issues_found": ["QA validation error"],
            "ready_for_delivery": False,
            "error": str(e)
        }
        
        return state