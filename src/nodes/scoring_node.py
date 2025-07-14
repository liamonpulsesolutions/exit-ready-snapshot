"""
Scoring node for LangGraph workflow.
Handles sophisticated multi-factor business assessment.
Reuses all existing scoring functions from the CrewAI scoring agent.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List

# Import the state type
from src.workflow import AssessmentState

# Import ALL existing tools and functions from the CrewAI scoring agent
from src.agents.scoring_agent import (
    calculate_category_score,
    aggregate_final_scores,
    calculate_focus_areas,
    # Import the actual scoring functions directly
    score_financial_performance,
    score_revenue_stability,
    score_operations_efficiency,
    score_growth_value,
    score_exit_readiness,
    # Helper functions
    calculate_time_impact,
    calculate_revenue_impact,
    calculate_growth_trajectory,
    calculate_improvement_impact,
    get_action_timeline,
    generate_category_actions
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


def scoring_node(state: AssessmentState) -> AssessmentState:
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
        
        if not anonymized_data:
            raise ValueError("No anonymized data from intake stage")
        
        # Extract responses and business info
        responses = anonymized_data.get("responses", {})
        industry = anonymized_data.get("industry", "Professional Services")
        revenue_range = anonymized_data.get("revenue_range", "$1M-$5M")
        years_in_business = anonymized_data.get("years_in_business", "5-10 years")
        exit_timeline = anonymized_data.get("exit_timeline", "1-2 years")
        
        # Extract research data
        research_data = research_result.get("structured_findings", {})
        
        logger.info(f"Scoring for: {industry}, Revenue: {revenue_range}, Timeline: {exit_timeline}")
        
        # Step 1: Score each category using the sophisticated scoring functions
        category_scores = {}
        
        # Score Financial Performance
        logger.info("Scoring financial performance...")
        financial_score = score_financial_performance(responses, research_data)
        category_scores["financial_performance"] = financial_score
        
        # Score Revenue Stability
        logger.info("Scoring revenue stability...")
        # Add revenue_range and years_in_business to responses for the scoring function
        enhanced_responses = responses.copy()
        enhanced_responses["revenue_range"] = revenue_range
        
        # Parse years_in_business range to get a numeric value for scoring only
        years_numeric = parse_years_in_business(years_in_business)
        enhanced_responses["years_in_business"] = str(years_numeric)
        enhanced_responses["industry"] = industry
        
        revenue_score = score_revenue_stability(enhanced_responses, research_data)
        category_scores["revenue_stability"] = revenue_score
        
        # IMPORTANT: Store the original range string in the scoring result for display
        category_scores["revenue_stability"]["years_in_business_display"] = years_in_business
        
        # Score Operations Efficiency
        logger.info("Scoring operations efficiency...")
        operations_score = score_operations_efficiency(responses, research_data)
        category_scores["operations_efficiency"] = operations_score
        
        # Score Growth Value
        logger.info("Scoring growth value...")
        growth_score = score_growth_value(responses, research_data)
        category_scores["growth_value"] = growth_score
        
        # Score Exit Readiness
        logger.info("Scoring exit readiness...")
        enhanced_responses["exit_timeline"] = exit_timeline
        exit_score = score_exit_readiness(enhanced_responses, research_data)
        category_scores["exit_readiness"] = exit_score
        
        # Step 2: Calculate overall score
        logger.info("Calculating overall score...")
        
        # Prepare for aggregation
        all_scores_data = json.dumps(category_scores)
        aggregation_result = aggregate_final_scores._run(all_scores_data)
        
        # Parse the aggregation result
        overall_score = 0.0
        readiness_level = "Not Ready"
        
        # Extract overall score from the text result
        if "OVERALL EXIT READINESS SCORE:" in aggregation_result:
            score_line = aggregation_result.split("OVERALL EXIT READINESS SCORE:")[1].split("\n")[0]
            overall_score = float(score_line.split("/")[0].strip())
        
        if "READINESS LEVEL:" in aggregation_result:
            level_line = aggregation_result.split("READINESS LEVEL:")[1].split("\n")[0]
            readiness_level = level_line.strip()
        
        # Step 3: Calculate focus areas
        logger.info("Calculating focus areas...")
        
        focus_input = {
            "scores": category_scores,
            "gaps": [],  # Collect all gaps
            "timeline": exit_timeline,
            "industry": industry
        }
        
        # Collect all gaps from categories
        for cat, data in category_scores.items():
            focus_input["gaps"].extend(data.get("gaps", []))
        
        focus_result = calculate_focus_areas._run(json.dumps(focus_input))
        
        # Parse focus areas
        focus_areas = {
            "primary_focus": None,
            "secondary_focus": None,
            "tertiary_focus": None
        }
        
        # Extract focus areas from the text result
        if "PRIORITY 1:" in focus_result:
            lines = focus_result.split("\n")
            priority_count = 0
            
            for i, line in enumerate(lines):
                if "PRIORITY 1:" in line and priority_count == 0:
                    category = line.split(":")[1].strip()
                    # Look for score in next lines
                    score = 5.0
                    for j in range(i+1, min(i+5, len(lines))):
                        if "Current Score:" in lines[j]:
                            score = float(lines[j].split(":")[1].split("/")[0].strip())
                            break
                    
                    focus_areas["primary_focus"] = {
                        "category": category.lower().replace(" ", "_"),
                        "current_score": score,
                        "reasoning": f"Lowest score at {score}/10",
                        "is_value_killer": score < 4,
                        "typical_timeline_months": 6
                    }
                    priority_count += 1
                    
                elif "PRIORITY 2:" in line and priority_count == 1:
                    category = line.split(":")[1].strip()
                    focus_areas["secondary_focus"] = {
                        "category": category.lower().replace(" ", "_"),
                        "reasoning": "Second lowest score"
                    }
                    priority_count += 1
                    
                elif "PRIORITY 3:" in line and priority_count == 2:
                    category = line.split(":")[1].strip()
                    focus_areas["tertiary_focus"] = {
                        "category": category.lower().replace(" ", "_"),
                        "reasoning": "Third priority area"
                    }
                    break
        
        # Prepare scoring result
        scoring_result = {
            "status": "success",
            "overall_score": overall_score,
            "readiness_level": readiness_level,
            "category_scores": category_scores,
            "focus_areas": focus_areas,
            "aggregation_details": aggregation_result,
            "focus_details": focus_result,
            "timeline_urgency": "HIGH" if "1-2 years" in exit_timeline or "Already" in exit_timeline else "MODERATE",
            "total_categories": len(category_scores),
            "strengths": [],
            "critical_gaps": [],
            # IMPORTANT: Preserve original display values
            "business_context_display": {
                "years_in_business": years_in_business,  # Original range string
                "revenue_range": revenue_range,
                "industry": industry,
                "exit_timeline": exit_timeline
            }
        }
        
        # Identify top strengths and gaps
        for category, data in category_scores.items():
            if data["score"] >= 7:
                scoring_result["strengths"].extend(data.get("strengths", []))
            if data["score"] < 5:
                scoring_result["critical_gaps"].extend(data.get("gaps", []))
        
        # Limit to top items
        scoring_result["strengths"] = scoring_result["strengths"][:5]
        scoring_result["critical_gaps"] = scoring_result["critical_gaps"][:5]
        
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
            f"Focus: {focus_areas['primary_focus']['category'] if focus_areas['primary_focus'] else 'N/A'}"
        )
        
        logger.info(f"=== SCORING NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in scoring node: {str(e)}", exc_info=True)
        state["error"] = f"Scoring failed: {str(e)}"
        state["messages"].append(f"ERROR in scoring: {str(e)}")
        raise