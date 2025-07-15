"""
Scoring node for LangGraph workflow.
Handles sophisticated multi-factor business assessment.
Directly uses scoring functions without CrewAI tools.
"""

import logging
import json
from datetime import datetime
import time
from typing import Dict, Any, List

# Only import the actual scoring functions - NO TOOLS
from src.agents.scoring_agent import (
    score_financial_performance,
    score_revenue_stability,
    score_operations_efficiency,
    score_growth_value,
    score_exit_readiness
)

# Import utilities
from src.utils.json_helper import safe_parse_json

logger = logging.getLogger(__name__)


def parse_years_in_business(years_range: str) -> int:
    """
    Parse years in business range to a numeric value.
    Examples:
    - "Under 2 years" -> 1
    - "2-5 years" -> 3
    - "5-10 years" -> 7
    - "10-20 years" -> 15
    - "Over 20 years" -> 25
    """
    if "Under 2" in years_range:
        return 1
    elif "2-5" in years_range:
        return 3
    elif "5-10" in years_range:
        return 7
    elif "10-20" in years_range:
        return 15
    elif "Over 20" in years_range:
        return 25
    else:
        # Try to extract first number
        import re
        match = re.search(r'\d+', years_range)
        return int(match.group()) if match else 5


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
    start_time = time.time()
    logger.info(f"=== SCORING NODE STARTED - UUID: {state.get('uuid')} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "scoring"
        state["messages"].append(f"Scoring started at {datetime.now().isoformat()}")
        
        # Get data from previous stages
        anonymized_data = state.get("anonymized_data", {})
        research_result = state.get("research_result", {})
        
        if not anonymized_data:
            logger.warning("No anonymized data from intake stage - using form_data directly")
            # Fallback to form_data if anonymized_data is missing
            form_data = state.get("form_data", {})
            anonymized_data = {
                "responses": form_data.get("responses", {}),
                "industry": form_data.get("industry", "Professional Services"),
                "revenue_range": form_data.get("revenue_range", "$1M-$5M"),
                "years_in_business": form_data.get("years_in_business", "5-10 years"),
                "exit_timeline": form_data.get("exit_timeline", "1-2 years")
            }
        
        # Extract responses and business info
        responses = anonymized_data.get("responses", {})
        industry = state.get("industry") or anonymized_data.get("industry", "Professional Services")
        revenue_range = state.get("revenue_range") or anonymized_data.get("revenue_range", "$1M-$5M")
        years_in_business = state.get("years_in_business") or anonymized_data.get("years_in_business", "5-10 years")
        exit_timeline = state.get("exit_timeline") or anonymized_data.get("exit_timeline", "1-2 years")
        
        # Extract research data
        research_data = research_result.get("structured_findings", {})
        
        logger.info(f"Scoring for: {industry}, Revenue: {revenue_range}, Timeline: {exit_timeline}")
        logger.info(f"Number of responses: {len(responses)}")
        
        # Step 1: Score each category using the sophisticated scoring functions
        category_scores = {}
        
        # Score Financial Performance
        logger.info("Calling score_financial_performance...")
        financial_score = score_financial_performance(responses, research_data)
        category_scores["financial_performance"] = financial_score
        logger.info(f"Financial score: {financial_score.get('score')}/10")
        
        # Score Revenue Stability
        logger.info("Calling score_revenue_stability...")
        # Add revenue_range and years_in_business to responses for the scoring function
        enhanced_responses = responses.copy()
        enhanced_responses["revenue_range"] = revenue_range
        
        # Parse years_in_business range to get a numeric value for scoring only
        years_numeric = parse_years_in_business(years_in_business)
        enhanced_responses["years_in_business"] = str(years_numeric)
        enhanced_responses["industry"] = industry
        
        revenue_score = score_revenue_stability(enhanced_responses, research_data)
        category_scores["revenue_stability"] = revenue_score
        # Store the original range string for display
        category_scores["revenue_stability"]["years_in_business_display"] = years_in_business
        logger.info(f"Revenue stability score: {revenue_score.get('score')}/10")
        
        # Score Operations Efficiency
        logger.info("Calling score_operations_efficiency...")
        operations_score = score_operations_efficiency(responses, research_data)
        category_scores["operations_efficiency"] = operations_score
        logger.info(f"Operations score: {operations_score.get('score')}/10")
        
        # Score Growth Value
        logger.info("Calling score_growth_value...")
        growth_score = score_growth_value(responses, research_data)
        category_scores["growth_value"] = growth_score
        logger.info(f"Growth value score: {growth_score.get('score')}/10")
        
        # Score Exit Readiness
        logger.info("Calling score_exit_readiness...")
        enhanced_responses["exit_timeline"] = exit_timeline
        exit_score = score_exit_readiness(enhanced_responses, research_data)
        category_scores["exit_readiness"] = exit_score
        logger.info(f"Exit readiness score: {exit_score.get('score')}/10")
        
        # Step 2: Calculate overall score manually
        logger.info("Calculating overall score...")
        
        # Calculate weighted average
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for category, score_data in category_scores.items():
            score = score_data.get('score', 0)
            weight = score_data.get('weight', 0.2)
            weighted = score * weight
            
            total_weighted_score += weighted
            total_weight += weight
            
            logger.info(f"{category}: {score}/10 x {weight} = {weighted}")
        
        overall_score = round(total_weighted_score / total_weight, 1) if total_weight > 0 else 5.0
        
        # Determine readiness level
        if overall_score >= 8.1:
            readiness_level = "Exit Ready"
        elif overall_score >= 6.6:
            readiness_level = "Approaching Ready"
        elif overall_score >= 4.1:
            readiness_level = "Conditionally Ready"
        else:
            readiness_level = "Not Ready"
        
        logger.info(f"Overall score: {overall_score}/10 - {readiness_level}")
        
        # Step 3: Identify focus areas
        logger.info("Identifying focus areas...")
        
        # Sort categories by score (lowest first)
        sorted_categories = sorted(
            category_scores.items(),
            key=lambda x: x[1].get('score', 10)
        )
        
        focus_areas = {}
        if len(sorted_categories) >= 1:
            lowest = sorted_categories[0]
            focus_areas["primary_focus"] = {
                "category": lowest[0],
                "current_score": lowest[1].get('score'),
                "reasoning": f"Lowest score at {lowest[1].get('score')}/10",
                "is_value_killer": lowest[1].get('score', 10) < 4,
                "typical_timeline_months": 6
            }
        
        if len(sorted_categories) >= 2:
            focus_areas["secondary_focus"] = {
                "category": sorted_categories[1][0],
                "reasoning": "Second lowest score"
            }
        
        if len(sorted_categories) >= 3:
            focus_areas["tertiary_focus"] = {
                "category": sorted_categories[2][0],
                "reasoning": "Third priority area"
            }
        
        # Extract top strengths and critical gaps
        all_strengths = []
        critical_gaps = []
        
        for category, score_data in category_scores.items():
            if 'strengths' in score_data:
                all_strengths.extend(score_data['strengths'])
            if 'gaps' in score_data and score_data.get('score', 10) < 5:
                critical_gaps.extend(score_data['gaps'])
        
        # Prepare scoring result
        scoring_result = {
            "status": "success",
            "overall_score": overall_score,
            "readiness_level": readiness_level,
            "category_scores": category_scores,
            "focus_areas": focus_areas,
            "timeline_urgency": "HIGH" if "1-2 years" in exit_timeline or "Already" in exit_timeline else "MODERATE",
            "total_categories": len(category_scores),
            "strengths": all_strengths[:5],  # Top 5 strengths
            "critical_gaps": critical_gaps[:3],  # Top 3 critical gaps
            "business_context_display": {
                "years_in_business": years_in_business,
                "revenue_range": revenue_range,
                "industry": industry,
                "exit_timeline": exit_timeline
            }
        }
        
        # Update state
        state["scoring_result"] = scoring_result
        state["current_stage"] = "scoring_complete"
        
        # Add timing
        execution_time = time.time() - start_time
        state["processing_time"]["scoring"] = execution_time
        
        # Add message
        state["messages"].append(
            f"Scoring completed in {execution_time:.2f}s - Overall: {overall_score}/10 ({readiness_level}), Focus: {focus_areas.get('primary_focus', {}).get('category', 'none')}"
        )
        
        logger.info(f"=== SCORING NODE COMPLETED in {execution_time:.2f}s ===")
        logger.info(f"Overall Score: {overall_score}/10 - {readiness_level}")
        logger.info(f"Primary Focus: {focus_areas.get('primary_focus', {}).get('category', 'none')}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in scoring node: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        state["error"] = f"Scoring failed: {str(e)}"
        state["current_stage"] = "scoring_error"
        
        # Add default scoring result on error
        state["scoring_result"] = {
            "status": "error",
            "overall_score": 5.0,
            "readiness_level": "Unable to Score",
            "category_scores": {},
            "error": str(e)
        }
        
        return state