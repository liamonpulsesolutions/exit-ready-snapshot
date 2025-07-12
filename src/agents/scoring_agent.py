from crewai import Agent
from crewai.tools import tool
from typing import Dict, Any, List
import logging
import json

logger = logging.getLogger(__name__)

@tool("calculate_category_score")
def calculate_category_score(category_data: str) -> str:
    """
    Calculate score for a specific category based on rubric criteria.
    Input should be JSON with category name, responses, and rubric.
    """
    try:
        data = json.loads(category_data)
        category = data.get('category')
        responses = data.get('responses', {})
        rubric = data.get('rubric', {})
        
        # Extract the specific category rubric
        category_rubric = rubric.get('categories', {}).get(category, {})
        if not category_rubric:
            return json.dumps({
                "error": f"No rubric found for category: {category}",
                "score": 5.0
            })
        
        # This is a simplified scoring logic - in production, this would be more sophisticated
        score = 5.0  # Default middle score
        justifications = []
        
        # Get the questions for this category
        question_ids = category_rubric.get('questions', [])
        
        # Analyze responses for scoring indicators
        high_risk_indicators = category_rubric.get('scoring_criteria', {}).get('high_risk', {}).get('indicators', [])
        low_risk_indicators = category_rubric.get('scoring_criteria', {}).get('low_risk', {}).get('indicators', [])
        
        # Simple scoring based on response analysis
        # In reality, this would use NLP to match responses to indicators
        for q_id in question_ids:
            response = responses.get(f'q{q_id}', '')
            
            # Check for high risk indicators
            if any(indicator.lower() in response.lower() for indicator in ['cannot', 'no', 'none', 'never']):
                score -= 1.0
                justifications.append(f"Q{q_id} indicates high risk")
            
            # Check for low risk indicators  
            if any(indicator.lower() in response.lower() for indicator in ['automated', 'documented', 'system', 'process']):
                score += 1.0
                justifications.append(f"Q{q_id} shows positive indicators")
        
        # Bound the score between 1 and 10
        score = max(1.0, min(10.0, score))
        
        return json.dumps({
            "category": category,
            "score": score,
            "justifications": justifications,
            "questions_evaluated": question_ids
        })
        
    except Exception as e:
        logger.error(f"Error calculating category score: {str(e)}")
        return json.dumps({
            "error": str(e),
            "score": 5.0
        })

@tool("aggregate_final_scores")
def aggregate_final_scores(all_scores: str) -> str:
    """
    Calculate weighted overall score from category scores.
    Input should be JSON with category scores and weights.
    """
    try:
        data = json.loads(all_scores)
        category_scores = data.get('category_scores', {})
        weights = data.get('weights', {})
        
        # Calculate weighted average
        total_weight = 0
        weighted_sum = 0
        
        for category, score in category_scores.items():
            weight = weights.get(category, 0.2)  # Default weight if not specified
            weighted_sum += score * weight
            total_weight += weight
        
        overall_score = weighted_sum / total_weight if total_weight > 0 else 5.0
        
        # Determine readiness level based on thresholds
        if overall_score >= 8.1:
            readiness_level = "exit_ready"
        elif overall_score >= 6.6:
            readiness_level = "approaching_ready"
        elif overall_score >= 4.1:
            readiness_level = "needs_work"
        else:
            readiness_level = "not_ready"
        
        return json.dumps({
            "overall_score": round(overall_score, 1),
            "readiness_level": readiness_level,
            "category_scores": category_scores,
            "weights_used": weights
        })
        
    except Exception as e:
        logger.error(f"Error aggregating scores: {str(e)}")
        return json.dumps({
            "error": str(e),
            "overall_score": 5.0,
            "readiness_level": "needs_work"
        })

@tool("interpret_response_quality")
def interpret_response_quality(response_data: str) -> str:
    """
    Analyze the quality and depth of responses to adjust scoring confidence.
    Returns insights about response quality.
    """
    try:
        data = json.loads(response_data)
        responses = data.get('responses', {})
        
        quality_metrics = {
            "total_responses": len(responses),
            "avg_response_length": 0,
            "empty_responses": 0,
            "detailed_responses": 0,
            "vague_responses": 0
        }
        
        total_length = 0
        for q_id, response in responses.items():
            response_length = len(response.split())
            total_length += response_length
            
            if response_length == 0:
                quality_metrics["empty_responses"] += 1
            elif response_length < 5:
                quality_metrics["vague_responses"] += 1
            elif response_length > 20:
                quality_metrics["detailed_responses"] += 1
        
        quality_metrics["avg_response_length"] = total_length / len(responses) if responses else 0
        
        # Determine overall quality
        if quality_metrics["avg_response_length"] > 15 and quality_metrics["empty_responses"] == 0:
            quality_assessment = "high"
        elif quality_metrics["avg_response_length"] > 8:
            quality_assessment = "medium"
        else:
            quality_assessment = "low"
        
        return json.dumps({
            "quality_assessment": quality_assessment,
            "metrics": quality_metrics,
            "confidence_adjustment": 1.0 if quality_assessment == "high" else 0.8
        })
        
    except Exception as e:
        logger.error(f"Error interpreting response quality: {str(e)}")
        return json.dumps({
            "quality_assessment": "unknown",
            "error": str(e)
        })

def create_scoring_agent(llm, prompts: Dict[str, Any], scoring_rubric: Dict[str, Any]) -> Agent:
    """Create the scoring agent for exit readiness evaluation"""
    
    # Get agent configuration from prompts
    config = prompts.get('scoring_agent', {})
    
    # Create tools list
    tools = [
        calculate_category_score,
        aggregate_final_scores,
        interpret_response_quality
    ]
    
    # Create agent WITHOUT trying to add scoring_rubric attribute
    agent = Agent(
        role=config.get('role'),
        goal=config.get('goal'),
        backstory=config.get('backstory'),
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )
    
    # Note: The scoring rubric will be passed through the task context instead
    return agent