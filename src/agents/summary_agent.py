from crewai import Agent
from crewai.tools import tool
from typing import Dict, Any, List
import logging
import json

logger = logging.getLogger(__name__)

@tool("generate_category_summary")
def generate_category_summary(category_data: str) -> str:
    """
    Generate a human-friendly summary for a specific scoring category.
    Input should include category name, score, and relevant responses.
    """
    try:
        data = json.loads(category_data)
        category = data.get('category', '')
        score = data.get('score', 5.0)
        responses = data.get('responses', {})
        justifications = data.get('justifications', [])
        
        # This tool helps structure the summary generation
        # The actual writing will be done by the LLM
        summary_structure = {
            "category": category,
            "score": score,
            "score_interpretation": interpret_score(score),
            "relevant_responses": responses,
            "justifications": justifications,
            "summary_needed": True
        }
        
        return json.dumps(summary_structure)
        
    except Exception as e:
        logger.error(f"Error generating category summary: {str(e)}")
        return json.dumps({"error": str(e)})

def interpret_score(score: float) -> str:
    """Helper function to interpret numerical scores"""
    if score >= 8.0:
        return "Strong - Well positioned for exit"
    elif score >= 6.5:
        return "Good - Some improvements needed"
    elif score >= 4.5:
        return "Moderate - Significant work required"
    else:
        return "Needs Attention - Critical improvements required"

@tool("create_executive_summary")
def create_executive_summary(assessment_data: str) -> str:
    """
    Create a high-level executive summary of the entire assessment.
    Focuses on the most important findings and overall readiness.
    """
    try:
        data = json.loads(assessment_data)
        overall_score = data.get('overall_score', 5.0)
        readiness_level = data.get('readiness_level', 'needs_work')
        category_scores = data.get('category_scores', {})
        
        # Identify highest and lowest scoring areas
        if category_scores:
            sorted_categories = sorted(category_scores.items(), key=lambda x: x[1])
            weakest_area = sorted_categories[0] if sorted_categories else None
            strongest_area = sorted_categories[-1] if sorted_categories else None
        else:
            weakest_area = None
            strongest_area = None
        
        summary_data = {
            "overall_score": overall_score,
            "readiness_level": readiness_level,
            "strongest_area": strongest_area,
            "weakest_area": weakest_area,
            "key_message": determine_key_message(overall_score)
        }
        
        return json.dumps(summary_data)
        
    except Exception as e:
        logger.error(f"Error creating executive summary: {str(e)}")
        return json.dumps({"error": str(e)})

def determine_key_message(score: float) -> str:
    """Determine the key message based on overall score"""
    if score >= 8.0:
        return "Your business shows strong exit readiness with excellent fundamentals."
    elif score >= 6.5:
        return "Your business has a solid foundation with clear opportunities for value enhancement."
    elif score >= 4.5:
        return "Your business has potential but needs focused improvements to maximize exit value."
    else:
        return "Your business requires significant preparation to achieve a successful exit."

@tool("generate_recommendations")
def generate_recommendations(full_assessment: str) -> str:
    """
    Generate prioritized recommendations based on the full assessment.
    Returns quick wins, strategic priorities, and critical focus area.
    """
    try:
        data = json.loads(full_assessment)
        category_scores = data.get('category_scores', {})
        responses = data.get('responses', {})
        
        # Structure for recommendation generation
        recommendations_structure = {
            "quick_wins": [],  # Will be filled by LLM based on analysis
            "strategic_priorities": [],
            "critical_focus_area": identify_critical_area(category_scores),
            "score_data": category_scores,
            "response_context": responses
        }
        
        return json.dumps(recommendations_structure)
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        return json.dumps({"error": str(e)})

def identify_critical_area(category_scores: Dict[str, float]) -> str:
    """Identify the most critical area for improvement"""
    if not category_scores:
        return "overall business systemization"
    
    # Find the lowest scoring category
    lowest_category = min(category_scores.items(), key=lambda x: x[1])
    
    critical_areas = {
        "owner_dependence": "reducing owner dependence",
        "revenue_quality": "improving revenue quality and diversification",
        "financial_readiness": "strengthening financial documentation",
        "operational_resilience": "building operational resilience",
        "growth_value": "enhancing growth potential and unique value"
    }
    
    return critical_areas.get(lowest_category[0], "overall business improvement")

@tool("format_for_pdf")
def format_for_pdf(summary_content: str) -> str:
    """
    Format the complete summary content for PDF generation.
    Ensures consistent structure and formatting.
    """
    try:
        data = json.loads(summary_content)
        
        # Structure the content for PDF generation
        pdf_structure = {
            "executive_summary": data.get('executive_summary', ''),
            "category_summaries": data.get('category_summaries', {}),
            "recommendations": {
                "quick_wins": data.get('quick_wins', []),
                "strategic_priorities": data.get('strategic_priorities', []),
                "critical_focus": data.get('critical_focus', '')
            },
            "next_steps": data.get('next_steps', ''),
            "formatted": True
        }
        
        return json.dumps(pdf_structure)
        
    except Exception as e:
        logger.error(f"Error formatting for PDF: {str(e)}")
        return json.dumps({"error": str(e)})

def create_summary_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the summary agent for report generation"""
    
    # Get agent configuration from prompts
    config = prompts.get('summary_agent', {})
    
    # Create tools list
    tools = [
        generate_category_summary,
        create_executive_summary,
        generate_recommendations,
        format_for_pdf
    ]
    
    return Agent(
        role=config.get('role'),
        goal=config.get('goal'),
        backstory=config.get('backstory'),
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )