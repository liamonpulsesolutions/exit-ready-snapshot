"""
Scoring node for LangGraph workflow.
Handles sophisticated multi-factor business assessment.
Uses pure functions from core modules.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Tuple

from workflow.core.scoring_logic import (
    score_owner_dependence,
    score_revenue_quality,
    score_financial_readiness,
    score_operational_resilience,
    score_growth_value,
    calculate_overall_score,
    identify_focus_areas
)

logger = logging.getLogger(__name__)


def scoring_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scoring node that performs comprehensive exit readiness evaluation.
    
    This node:
    1. Uses anonymized responses from intake
    2. Incorporates industry research findings
    3. Applies sophisticated scoring algorithms
    4. Identifies focus areas and improvements
    
    Args:
        state: Current workflow state with intake and research results
        
    Returns:
        Updated state with comprehensive scoring results
    """
    start_time = datetime.now()
    logger.info(f"=== SCORING NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "scoring"
        state["messages"].append(f"Scoring started at {start_time.isoformat()}")
        
        # Get data from previous stages
        anonymized_data = state.get("anonymized_data", {})
        research_result = state.get("research_result", {})
        
        # Extract responses and business info
        responses = anonymized_data.get("responses", {})
        
        # Add business context to responses for scoring functions
        responses["industry"] = state.get("industry", "Professional Services")
        responses["revenue_range"] = state.get("revenue_range", "$1M-$5M")
        responses["years_in_business"] = state.get("years_in_business", "5-10 years")
        responses["exit_timeline"] = state.get("exit_timeline", "1-2 years")
        
        logger.info(f"Scoring {len(responses)} responses for {responses['industry']}")
        
        # Extract research data
        research_data = {
            "valuation_benchmarks": research_result.get("valuation_benchmarks", {}),
            "improvement_strategies": research_result.get("improvement_strategies", {}),
            "market_conditions": research_result.get("market_conditions", {}),
            "industry_context": research_result.get("industry_context", {})
        }
        
        # Score each category
        category_scores = {}
        
        # 1. Score Owner Dependence (Q1, Q2)
        logger.info("Scoring owner dependence...")
        owner_score = score_owner_dependence(responses, research_data)
        category_scores["owner_dependence"] = owner_score
        logger.info(f"Owner dependence: {owner_score['score']}/10")
        
        # 2. Score Revenue Quality (Q3, Q4)
        logger.info("Scoring revenue quality...")
        revenue_score = score_revenue_quality(responses, research_data)
        category_scores["revenue_quality"] = revenue_score
        logger.info(f"Revenue quality: {revenue_score['score']}/10")
        
        # 3. Score Financial Readiness (Q5, Q6)
        logger.info("Scoring financial readiness...")
        financial_score = score_financial_readiness(responses, research_data)
        category_scores["financial_readiness"] = financial_score
        logger.info(f"Financial readiness: {financial_score['score']}/10")
        
        # 4. Score Operational Resilience (Q7, Q8)
        logger.info("Scoring operational resilience...")
        operational_score = score_operational_resilience(responses, research_data)
        category_scores["operational_resilience"] = operational_score
        logger.info(f"Operational resilience: {operational_score['score']}/10")
        
        # 5. Score Growth Value (Q9, Q10)
        logger.info("Scoring growth value...")
        growth_score = score_growth_value(responses, research_data)
        category_scores["growth_value"] = growth_score
        logger.info(f"Growth value: {growth_score['score']}/10")
        
        # Calculate overall score
        overall_score, readiness_level = calculate_overall_score(category_scores)
        logger.info(f"Overall score: {overall_score}/10 - {readiness_level}")
        
        # Identify focus areas
        focus_areas = identify_focus_areas(
            category_scores,
            responses.get("exit_timeline", "1-2 years")
        )
        
        # Extract top insights
        all_strengths = []
        critical_gaps = []
        
        for category, data in category_scores.items():
            strengths = data.get('strengths', [])
            gaps = data.get('gaps', [])
            
            # Collect top strengths
            all_strengths.extend(strengths[:2])
            
            # Collect critical gaps (from low-scoring categories)
            if data.get('score', 10) < 5:
                critical_gaps.extend(gaps[:2])
        
        # Prepare scoring result
        scoring_result = {
            "status": "success",
            "overall_score": overall_score,
            "readiness_level": readiness_level,
            "category_scores": category_scores,
            "focus_areas": focus_areas,
            "top_strengths": all_strengths[:5],
            "critical_gaps": critical_gaps[:3],
            "scoring_metadata": {
                "total_categories": len(category_scores),
                "highest_score": max(d['score'] for d in category_scores.values()),
                "lowest_score": min(d['score'] for d in category_scores.values()),
                "research_quality": research_result.get("data_source", "unknown")
            }
        }
        
        # Update state
        state["scoring_result"] = scoring_result
        
        # Add processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        state["processing_time"]["scoring"] = processing_time
        
        # Add status message
        state["messages"].append(
            f"Scoring completed in {processing_time:.2f}s - "
            f"Overall: {overall_score}/10 ({readiness_level}), "
            f"Focus: {focus_areas.get('primary', {}).get('category', 'none')}"
        )
        
        logger.info(f"=== SCORING NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in scoring node: {str(e)}", exc_info=True)
        state["error"] = f"Scoring failed: {str(e)}"
        state["messages"].append(f"ERROR in scoring: {str(e)}")
        state["current_stage"] = "scoring_error"
        return state