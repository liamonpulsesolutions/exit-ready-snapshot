"""
Summary node for LangGraph workflow.
Generates executive summary, recommendations, and final report structure.
Uses pure functions from core modules.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from langchain_openai import ChatOpenAI

from workflow.core.formatters import (
    format_executive_summary,
    format_category_summary,
    format_recommendations_section,
    format_industry_context,
    format_next_steps,
    structure_final_report
)
from workflow.core.prompts import get_locale_terms

logger = logging.getLogger(__name__)


def summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summary node that generates comprehensive report from all previous analyses.
    
    This node:
    1. Creates executive summary
    2. Generates category-specific summaries
    3. Produces recommendations and action plans
    4. Formats industry context
    5. Structures final report
    
    Args:
        state: Current workflow state with all previous results
        
    Returns:
        Updated state with complete report sections
    """
    start_time = datetime.now()
    logger.info(f"=== SUMMARY NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "summary"
        state["messages"].append(f"Summary started at {start_time.isoformat()}")
        
        # Extract data from previous stages
        scoring_result = state.get("scoring_result", {})
        research_result = state.get("research_result", {})
        anonymized_data = state.get("anonymized_data", {})
        
        # Get locale terms
        locale_terms = get_locale_terms(state.get("locale", "us"))
        
        # Business info
        business_info = {
            "industry": state.get("industry", "Not specified"),
            "location": state.get("location", "Not specified"),
            "revenue_range": state.get("revenue_range", "Not specified"),
            "exit_timeline": state.get("exit_timeline", "Not specified"),
            "years_in_business": state.get("years_in_business", "Not specified")
        }
        
        # Extract key scoring data
        overall_score = scoring_result.get("overall_score", 5.0)
        readiness_level = scoring_result.get("readiness_level", "Needs Work")
        category_scores = scoring_result.get("category_scores", {})
        focus_areas = scoring_result.get("focus_areas", {})
        
        logger.info(f"Generating report for {overall_score}/10 - {readiness_level}")
        
        # 1. Generate Executive Summary
        logger.info("Generating executive summary...")
        executive_summary = format_executive_summary(
            overall_score=overall_score,
            readiness_level=readiness_level,
            category_scores=category_scores,
            business_info=business_info,
            focus_areas=focus_areas
        )
        
        # 2. Generate Category Summaries
        logger.info("Generating category summaries...")
        category_summaries = {}
        
        for category, score_data in category_scores.items():
            summary = format_category_summary(
                category=category,
                score_data=score_data,
                locale_terms=locale_terms
            )
            category_summaries[category] = summary
        
        # 3. Generate Recommendations
        logger.info("Generating recommendations...")
        recommendations = format_recommendations_section(
            focus_areas=focus_areas,
            category_scores=category_scores,
            exit_timeline=business_info.get("exit_timeline", "")
        )
        
        # 4. Generate Industry Context
        logger.info("Generating industry context...")
        industry_context = format_industry_context(
            research_findings=research_result,
            business_info=business_info,
            scores={
                "overall_score": overall_score,
                "readiness_level": readiness_level,
                "category_scores": category_scores
            }
        )
        
        # 5. Generate Next Steps
        logger.info("Generating next steps...")
        next_steps = format_next_steps(
            exit_timeline=business_info.get("exit_timeline", ""),
            primary_focus=focus_areas.get("primary")
        )
        
        # 6. Structure Final Report
        logger.info("Structuring final report...")
        final_report = structure_final_report(
            executive_summary=executive_summary,
            category_summaries=category_summaries,
            recommendations=recommendations,
            industry_context=industry_context,
            next_steps=next_steps,
            overall_score=overall_score,
            readiness_level=readiness_level
        )
        
        # Prepare summary result
        summary_result = {
            "status": "success",
            "executive_summary": executive_summary,
            "category_summaries": category_summaries,
            "recommendations": recommendations,
            "industry_context": industry_context,
            "next_steps": next_steps,
            "final_report": final_report,
            "report_metadata": {
                "overall_score": overall_score,
                "readiness_level": readiness_level,
                "total_sections": 5,
                "locale": state.get("locale", "us"),
                "word_count": len(final_report.split())
            }
        }
        
        # Update state
        state["summary_result"] = summary_result
        
        # Add processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        state["processing_time"]["summary"] = processing_time
        
        # Add status message
        state["messages"].append(
            f"Summary completed in {processing_time:.2f}s - "
            f"Report generated: {summary_result['report_metadata']['word_count']} words"
        )
        
        logger.info(f"=== SUMMARY NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in summary node: {str(e)}", exc_info=True)
        state["error"] = f"Summary failed: {str(e)}"
        state["messages"].append(f"ERROR in summary: {str(e)}")
        state["current_stage"] = "summary_error"
        return state