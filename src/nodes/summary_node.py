"""
Summary node for LangGraph implementation.
Generates executive summary, recommendations, and final report structure.
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from langchain_openai import ChatOpenAI

# Import all tools from existing summary agent
from src.agents.summary_agent import (
    generate_category_summary,
    create_executive_summary,
    generate_recommendations,
    create_industry_context,
    structure_final_report,
    # Helper functions that exist in the file
    format_category_title,
    interpret_score_meaning,
    generate_category_recommendations,
    get_overall_score_interpretation
)

logger = logging.getLogger(__name__)


def summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summary node that generates comprehensive report from all previous analyses.
    
    Uses existing summary agent tools to create:
    1. Executive summary
    2. Category-specific summaries
    3. Recommendations and action plans
    4. Industry context
    5. Structured final report
    """
    try:
        logger.info(f"=== SUMMARY NODE STARTED ===")
        logger.info(f"Processing assessment for UUID: {state.get('uuid')}")
        
        start_time = datetime.now()
        
        # Extract data from previous stages
        intake_result = state.get("intake_result", {})
        research_result = state.get("research_result", {})
        scoring_result = state.get("scoring_result", {})
        
        # Extract key data
        anonymized_data = state.get("anonymized_data", {})
        responses = anonymized_data.get("responses", {})
        
        # Business info
        business_info = {
            "industry": state.get("industry", "Not specified"),
            "location": state.get("location", "Not specified"),
            "revenue_range": state.get("revenue_range", "Not specified"),
            "exit_timeline": state.get("exit_timeline", "Not specified"),
            "years_in_business": state.get("years_in_business", "Not specified"),
            "locale": state.get("locale", "us")
        }
        
        # Get scoring data
        category_scores = scoring_result.get("category_scores", {})
        overall_results = scoring_result.get("overall_results", {})
        focus_areas = scoring_result.get("focus_areas", {})
        
        # Initialize LLM for this node
        llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.3,
            max_tokens=4000
        )
        
        # 1. Generate Executive Summary
        logger.info("Generating executive summary...")
        exec_summary_data = {
            "overall_score": overall_results.get("overall_score", 5.0),
            "readiness_level": overall_results.get("readiness_level", "Needs Significant Work"),
            "category_scores": category_scores,
            "focus_areas": focus_areas,
            "industry_context": research_result.get("industry_trends", {}),
            "business_info": business_info
        }
        
        exec_summary_result = create_executive_summary._run(
            assessment_data=json.dumps(exec_summary_data)
        )
        
        # 2. Generate Category Summaries
        logger.info("Generating category summaries...")
        category_summaries = {}
        
        for category, score_data in category_scores.items():
            category_data = {
                "category": category,
                "score_data": score_data,
                "industry_context": research_result.get("benchmarks", {}).get(category, {}),
                "locale_terms": {"locale": state.get("locale", "us")}
            }
            
            summary = generate_category_summary._run(
                category_data=json.dumps(category_data)
            )
            category_summaries[category] = summary
        
        # 3. Generate Recommendations
        logger.info("Generating recommendations...")
        recommendations_data = {
            "focus_areas": focus_areas,
            "category_scores": category_scores,
            "business_info": business_info
        }
        
        recommendations_result = generate_recommendations._run(
            full_assessment=json.dumps(recommendations_data)
        )
        
        # 4. Generate Industry Context
        logger.info("Generating industry context...")
        industry_data = {
            "research_findings": research_result,
            "business_info": business_info,
            "scores": overall_results
        }
        
        industry_context_result = create_industry_context._run(
            industry_data=json.dumps(industry_data)
        )
        
        # 5. Structure Final Report
        logger.info("Structuring final report...")
        complete_data = {
            "executive_summary": exec_summary_result,
            "category_summaries": category_summaries,
            "recommendations": recommendations_result,
            "industry_context": industry_context_result,
            "business_info": business_info
        }
        
        final_report = structure_final_report._run(
            complete_data=json.dumps(complete_data)
        )
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Update state with results
        state["summary_result"] = {
            "executive_summary": exec_summary_result,
            "category_summaries": category_summaries,
            "recommendations": recommendations_result,
            "industry_context": industry_context_result,
            "final_report": final_report,
            "processing_time": processing_time
        }
        
        # Add processing time
        state["processing_time"]["summary"] = processing_time
        
        # Update current stage
        state["current_stage"] = "summary_complete"
        
        # Add debug message
        state["messages"].append(
            f"Summary node completed in {processing_time:.2f}s - "
            f"Generated executive summary, {len(category_summaries)} category analyses, "
            f"and comprehensive recommendations"
        )
        
        logger.info(f"=== SUMMARY NODE COMPLETED in {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in summary node: {str(e)}", exc_info=True)
        state["error"] = f"Summary node error: {str(e)}"
        state["current_stage"] = "summary_failed"
        state["messages"].append(f"Summary node failed: {str(e)}")
        return state