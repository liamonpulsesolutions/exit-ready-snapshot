"""
PII Reinsertion node for LangGraph workflow.
Handles final personalization by reinserting PII into the report.
Uses pure functions from core modules.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from workflow.core.pii_handler import (
    retrieve_pii_mapping,
    reinsert_pii,
    validate_pii_reinsertion
)

logger = logging.getLogger(__name__)


def pii_reinsertion_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    PII Reinsertion node that personalizes the final report.
    
    This node:
    1. Retrieves stored PII mapping
    2. Reinserts personal information into report
    3. Validates reinsertion was successful
    4. Prepares final output for delivery
    
    Args:
        state: Current workflow state with QA-approved report
        
    Returns:
        Updated state with personalized final output
    """
    start_time = datetime.now()
    logger.info(f"=== PII REINSERTION NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "pii_reinsertion"
        state["messages"].append(f"PII reinsertion started at {start_time.isoformat()}")
        
        # Get QA result and check if approved
        qa_result = state.get("qa_result", {})
        if not qa_result.get("ready_for_delivery", False):
            logger.warning("Report not approved for delivery - proceeding with warnings")
        
        # Get UUID and retrieve PII mapping
        uuid = state.get("uuid")
        logger.info(f"Retrieving PII mapping for UUID: {uuid}")
        
        pii_mapping = retrieve_pii_mapping(uuid)
        
        if not pii_mapping:
            # Critical error - no PII mapping found
            error_msg = f"No PII mapping found for UUID: {uuid}"
            logger.error(error_msg)
            state["error"] = error_msg
            state["current_stage"] = "pii_reinsertion_error"
            return state
        
        logger.info(f"Retrieved PII mapping with {len(pii_mapping)} entries")
        
        # Get the final report from summary
        summary_result = state.get("summary_result", {})
        final_report = summary_result.get("final_report", "")
        
        if not final_report:
            error_msg = "No final report found to personalize"
            logger.error(error_msg)
            state["error"] = error_msg
            state["current_stage"] = "pii_reinsertion_error"
            return state
        
        # Reinsert PII into all report sections
        logger.info("Personalizing report sections...")
        
        # Personalize each section
        personalized_sections = {}
        
        # Executive Summary
        exec_summary = summary_result.get("executive_summary", "")
        personalized_sections["executive_summary"] = reinsert_pii(exec_summary, pii_mapping)
        
        # Category Summaries
        category_summaries = summary_result.get("category_summaries", {})
        personalized_categories = {}
        for category, summary in category_summaries.items():
            personalized_categories[category] = reinsert_pii(summary, pii_mapping)
        personalized_sections["category_summaries"] = personalized_categories
        
        # Recommendations
        recommendations = summary_result.get("recommendations", "")
        personalized_sections["recommendations"] = reinsert_pii(recommendations, pii_mapping)
        
        # Industry Context
        industry_context = summary_result.get("industry_context", "")
        personalized_sections["industry_context"] = reinsert_pii(industry_context, pii_mapping)
        
        # Next Steps
        next_steps = summary_result.get("next_steps", "")
        personalized_sections["next_steps"] = reinsert_pii(next_steps, pii_mapping)
        
        # Final Report
        personalized_report = reinsert_pii(final_report, pii_mapping)
        
        # Add report date
        from datetime import date
        personalized_report = personalized_report.replace("[REPORT_DATE]", date.today().strftime("%B %d, %Y"))
        
        # Validate reinsertion
        logger.info("Validating PII reinsertion...")
        validation = validate_pii_reinsertion(personalized_report)
        
        if not validation.get("is_complete", True):
            logger.warning(f"Incomplete PII reinsertion - {validation.get('total_remaining', 0)} placeholders remain")
        
        # Extract key metadata
        owner_name = pii_mapping.get("[OWNER_NAME]", "Business Owner")
        email = pii_mapping.get("[EMAIL]", "")
        company_name = pii_mapping.get("[COMPANY_NAME]", "")
        
        # Prepare final output
        final_output = {
            "status": "completed",
            "owner_name": owner_name,
            "email": email,
            "company_name": company_name,
            "personalized_report": personalized_report,
            "personalized_sections": personalized_sections,
            "scores": {
                "overall": state.get("scoring_result", {}).get("overall_score", 0),
                "owner_dependence": state.get("scoring_result", {}).get("category_scores", {}).get("owner_dependence", {}).get("score", 0),
                "revenue_quality": state.get("scoring_result", {}).get("category_scores", {}).get("revenue_quality", {}).get("score", 0),
                "financial_readiness": state.get("scoring_result", {}).get("category_scores", {}).get("financial_readiness", {}).get("score", 0),
                "operational_resilience": state.get("scoring_result", {}).get("category_scores", {}).get("operational_resilience", {}).get("score", 0),
                "growth_value": state.get("scoring_result", {}).get("category_scores", {}).get("growth_value", {}).get("score", 0)
            },
            "executive_summary": personalized_sections["executive_summary"],
            "category_summaries": personalized_sections["category_summaries"],
            "recommendations": personalized_sections["recommendations"],
            "next_steps": personalized_sections["next_steps"],
            "content": personalized_report,
            "metadata": {
                "pii_entries_reinserted": len(pii_mapping),
                "validation_status": validation,
                "qa_approved": qa_result.get("approved", False),
                "quality_score": qa_result.get("overall_quality_score", 0)
            }
        }
        
        # Update state
        state["final_output"] = final_output
        state["current_stage"] = "completed"
        
        # Add processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        state["processing_time"]["pii_reinsertion"] = processing_time
        
        # Add final status message
        state["messages"].append(
            f"PII reinsertion completed in {processing_time:.2f}s - "
            f"Report personalized for {owner_name}, "
            f"Validation: {'✓' if validation.get('is_complete', True) else '⚠️'}"
        )
        
        # Log total workflow time
        total_time = sum(state["processing_time"].values())
        state["messages"].append(f"Total workflow completed in {total_time:.2f}s")
        
        logger.info(f"=== PII REINSERTION NODE COMPLETED - {processing_time:.2f}s ===")
        logger.info(f"=== TOTAL WORKFLOW TIME: {total_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in PII reinsertion node: {str(e)}", exc_info=True)
        state["error"] = f"PII reinsertion failed: {str(e)}"
        state["messages"].append(f"ERROR in PII reinsertion: {str(e)}")
        state["current_stage"] = "pii_reinsertion_error"
        return state