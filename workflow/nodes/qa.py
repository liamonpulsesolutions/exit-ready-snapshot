"""
QA node for LangGraph workflow.
Performs quality assurance checks on the generated report.
Uses pure functions from core modules.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from workflow.core.validators import (
    validate_scoring_consistency,
    validate_content_quality,
    scan_for_pii,
    validate_report_structure
)

logger = logging.getLogger(__name__)


def qa_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    QA node that validates the complete assessment report.
    
    This node:
    1. Checks scoring consistency
    2. Validates content quality
    3. Scans for PII compliance
    4. Validates report structure
    
    Args:
        state: Current workflow state with summary results
        
    Returns:
        Updated state with QA validation results
    """
    start_time = datetime.now()
    logger.info(f"=== QA NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "qa"
        state["messages"].append(f"QA started at {start_time.isoformat()}")
        
        # Get data from previous stages
        scoring_result = state.get("scoring_result", {})
        summary_result = state.get("summary_result", {})
        anonymized_data = state.get("anonymized_data", {})
        
        # Initialize QA results
        qa_issues = []
        qa_warnings = []
        quality_scores = {}
        
        # 1. Check Scoring Consistency
        logger.info("Checking scoring consistency...")
        scoring_consistency = validate_scoring_consistency(
            scores=scoring_result.get("category_scores", {}),
            responses=anonymized_data.get("responses", {})
        )
        
        quality_scores["scoring_consistency"] = scoring_consistency
        
        if not scoring_consistency.get("is_consistent", True):
            qa_issues.extend(scoring_consistency.get("issues", []))
        qa_warnings.extend(scoring_consistency.get("warnings", []))
        
        # 2. Validate Content Quality
        logger.info("Validating content quality...")
        content_quality = validate_content_quality({
            "executive_summary": summary_result.get("executive_summary", ""),
            "recommendations": summary_result.get("recommendations", ""),
            "category_summaries": summary_result.get("category_summaries", {})
        })
        
        quality_scores["content_quality"] = content_quality
        
        if not content_quality.get("passed", True):
            qa_issues.extend(content_quality.get("issues", []))
        qa_warnings.extend(content_quality.get("warnings", []))
        
        # 3. Scan for PII
        logger.info("Scanning for PII compliance...")
        pii_scan = scan_for_pii(summary_result.get("final_report", ""))
        
        quality_scores["pii_compliance"] = pii_scan
        
        if pii_scan.get("has_pii", False):
            qa_issues.append(f"PII detected: {pii_scan.get('total_items', 0)} items found")
            for pii_item in pii_scan.get("pii_found", []):
                qa_issues.append(f"- {pii_item['type']}: {pii_item['count']} instances")
        
        # 4. Validate Report Structure
        logger.info("Validating report structure...")
        structure_validation = validate_report_structure({
            "executive_summary": summary_result.get("executive_summary", ""),
            "category_scores": scoring_result.get("category_scores", {}),
            "category_summaries": summary_result.get("category_summaries", {}),
            "recommendations": summary_result.get("recommendations", ""),
            "next_steps": summary_result.get("next_steps", "")
        })
        
        quality_scores["structure_validation"] = structure_validation
        
        if not structure_validation.get("is_valid", True):
            qa_issues.extend(structure_validation.get("missing_sections", []))
            qa_issues.extend(structure_validation.get("incomplete_sections", []))
        
        # Calculate overall QA score
        overall_quality_score = calculate_overall_qa_score(quality_scores)
        
        # Determine approval status
        approved = len(qa_issues) == 0 and overall_quality_score >= 7.0
        ready_for_delivery = approved and not pii_scan.get("has_pii", False)
        
        # Prepare QA result
        qa_result = {
            "status": "success",
            "approved": approved,
            "ready_for_delivery": ready_for_delivery,
            "overall_quality_score": overall_quality_score,
            "quality_scores": quality_scores,
            "issues": qa_issues,
            "warnings": qa_warnings,
            "validation_summary": {
                "total_checks": 4,
                "passed_checks": sum(1 for score in quality_scores.values() 
                                   if score.get("passed", False) or 
                                   score.get("is_consistent", False) or 
                                   not score.get("has_pii", True)),
                "critical_issues": len(qa_issues),
                "warnings": len(qa_warnings)
            }
        }
        
        # Update state
        state["qa_result"] = qa_result
        
        # Add processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        state["processing_time"]["qa"] = processing_time
        
        # Add status message
        status_icon = "✓" if approved else "⚠️"
        state["messages"].append(
            f"QA completed in {processing_time:.2f}s - "
            f"{status_icon} Quality: {overall_quality_score:.1f}/10, "
            f"Issues: {len(qa_issues)}, Ready: {'Yes' if ready_for_delivery else 'No'}"
        )
        
        logger.info(f"=== QA NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in QA node: {str(e)}", exc_info=True)
        state["error"] = f"QA failed: {str(e)}"
        state["messages"].append(f"ERROR in QA: {str(e)}")
        state["current_stage"] = "qa_error"
        return state


def calculate_overall_qa_score(quality_scores: Dict[str, Dict]) -> float:
    """Calculate overall QA score from individual checks"""
    total_score = 0.0
    total_weight = 0.0
    
    # Scoring weights
    weights = {
        "scoring_consistency": 0.25,
        "content_quality": 0.35,
        "pii_compliance": 0.25,
        "structure_validation": 0.15
    }
    
    for check_name, check_result in quality_scores.items():
        weight = weights.get(check_name, 0.25)
        
        # Extract score based on check type
        if check_name == "content_quality":
            score = check_result.get("quality_score", 5.0)
        elif check_name == "structure_validation":
            score = check_result.get("completeness_score", 5.0)
        elif check_name == "pii_compliance":
            score = 10.0 if not check_result.get("has_pii", False) else 0.0
        elif check_name == "scoring_consistency":
            score = 10.0 if check_result.get("is_consistent", True) else 5.0
        else:
            score = 5.0
        
        total_score += score * weight
        total_weight += weight
    
    return round(total_score / total_weight, 1) if total_weight > 0 else 5.0