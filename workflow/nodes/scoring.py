"""
Scoring node for LangGraph workflow.
Enhanced with LLM interpretation for each category.
Uses pure functions from core modules plus intelligent analysis.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Tuple
from pathlib import Path
import os

# Load environment variables if not already loaded
from dotenv import load_dotenv
if not os.getenv('OPENAI_API_KEY'):
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

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


def generate_category_insights(
    category: str,
    score_data: Dict[str, Any],
    responses: Dict[str, Any],
    research_data: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate 2-3 sentences of intelligent commentary for a scoring category"""
    
    # Create context-specific prompts for each category
    category_prompts = {
        "owner_dependence": f"""Analyze this owner dependence score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}
Industry benchmark: Business should run 14+ days without owner

Key responses:
- Role: "{responses.get('q1', '')[:100]}..."
- Time away: "{responses.get('q2', '')}"

Provide insight about what this score means for their exit readiness. Be specific to their situation.""",

        "revenue_quality": f"""Analyze this revenue quality score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}
Industry benchmark: 60%+ recurring revenue for premium valuations

Key responses:
- Revenue model: "{responses.get('q3', '')[:100]}..."
- Customer concentration: "{responses.get('q4', '')}"

Market data: {research_data.get('valuation_benchmarks', {}).get('recurring_premium', 'Premium for recurring revenue')}

Provide insight about how their revenue structure affects valuation.""",

        "financial_readiness": f"""Analyze this financial readiness score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}

Key responses:
- Clean financials confidence: "{responses.get('q5', '')}"
- Profit margins: "{responses.get('q6', '')}"

Industry context: Buyers expect 15-20% EBITDA margins for {responses.get('industry', 'this industry')}

Provide insight about their financial preparedness for due diligence.""",

        "operational_resilience": f"""Analyze this operational resilience score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}

Key responses:
- Critical dependencies: "{responses.get('q7', '')[:100]}..."
- Documentation level: "{responses.get('q8', '')}"

Provide insight about operational transferability and buyer confidence.""",

        "growth_value": f"""Analyze this growth value score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}

Key responses:
- Unique value: "{responses.get('q9', '')[:100]}..."
- Growth potential: "{responses.get('q10', '')}"

Market trend: {research_data.get('market_conditions', {}).get('key_trend', 'Technology integration valued')}

Provide insight about their competitive positioning and growth story."""
    }
    
    prompt = category_prompts.get(category, "Provide 2-3 sentences of insight about this score.")
    
    try:
        response = llm.invoke([
            SystemMessage(content="You are an M&A advisor providing insights on business exit readiness. Be concise and specific."),
            HumanMessage(content=prompt)
        ])
        
        return response.content.strip()
    except Exception as e:
        logger.error(f"LLM insight generation failed for {category}: {e}")
        # Fallback to template-based insight
        if score_data['score'] >= 7:
            return f"Strong performance in {category.replace('_', ' ')} positions you well for exit. {score_data.get('strengths', [''])[0]}."
        elif score_data['score'] >= 4:
            return f"Moderate {category.replace('_', ' ')} requires targeted improvements. Focus on addressing: {score_data.get('gaps', [''])[0]}."
        else:
            return f"Significant gaps in {category.replace('_', ' ')} could impact valuation. {score_data.get('gaps', [''])[0]}."


def scoring_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced scoring node with LLM interpretation for each category.
    
    This node:
    1. Uses mechanical scoring for accuracy
    2. Adds LLM interpretation for each category
    3. Maintains all existing scoring logic
    4. Provides richer insights for downstream nodes
    
    Args:
        state: Current workflow state with intake and research results
        
    Returns:
        Updated state with scores and intelligent insights
    """
    start_time = datetime.now()
    logger.info(f"=== ENHANCED SCORING NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "scoring"
        state["messages"].append(f"Enhanced scoring started at {start_time.isoformat()}")
        
        # Initialize LLM for insights
        insight_llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3)
        
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
            "industry_context": research_result.get("industry_context", {}),
            "citations": research_result.get("citations", [])
        }
        
        # Score each category with LLM insights
        category_scores = {}
        
        # 1. Score Owner Dependence
        logger.info("Scoring owner dependence...")
        owner_score = score_owner_dependence(responses, research_data)
        
        # Add LLM insight
        owner_insight = generate_category_insights(
            "owner_dependence", owner_score, responses, research_data, insight_llm
        )
        owner_score["insight"] = owner_insight
        
        category_scores["owner_dependence"] = owner_score
        logger.info(f"Owner dependence: {owner_score['score']}/10")
        
        # 2. Score Revenue Quality
        logger.info("Scoring revenue quality...")
        revenue_score = score_revenue_quality(responses, research_data)
        
        # Add LLM insight
        revenue_insight = generate_category_insights(
            "revenue_quality", revenue_score, responses, research_data, insight_llm
        )
        revenue_score["insight"] = revenue_insight
        
        category_scores["revenue_quality"] = revenue_score
        logger.info(f"Revenue quality: {revenue_score['score']}/10")
        
        # 3. Score Financial Readiness
        logger.info("Scoring financial readiness...")
        financial_score = score_financial_readiness(responses, research_data)
        
        # Add LLM insight
        financial_insight = generate_category_insights(
            "financial_readiness", financial_score, responses, research_data, insight_llm
        )
        financial_score["insight"] = financial_insight
        
        category_scores["financial_readiness"] = financial_score
        logger.info(f"Financial readiness: {financial_score['score']}/10")
        
        # 4. Score Operational Resilience
        logger.info("Scoring operational resilience...")
        operational_score = score_operational_resilience(responses, research_data)
        
        # Add LLM insight
        operational_insight = generate_category_insights(
            "operational_resilience", operational_score, responses, research_data, insight_llm
        )
        operational_score["insight"] = operational_insight
        
        category_scores["operational_resilience"] = operational_score
        logger.info(f"Operational resilience: {operational_score['score']}/10")
        
        # 5. Score Growth Value
        logger.info("Scoring growth value...")
        growth_score = score_growth_value(responses, research_data)
        
        # Add LLM insight
        growth_insight = generate_category_insights(
            "growth_value", growth_score, responses, research_data, insight_llm
        )
        growth_score["insight"] = growth_insight
        
        category_scores["growth_value"] = growth_score
        logger.info(f"Growth value: {growth_score['score']}/10")
        
        # Calculate overall score (mechanical calculation preserved)
        overall_score, readiness_level = calculate_overall_score(category_scores)
        logger.info(f"Overall score: {overall_score}/10 - {readiness_level}")
        
        # Identify focus areas (mechanical logic preserved)
        focus_areas = identify_focus_areas(
            category_scores,
            responses.get("exit_timeline", "1-2 years")
        )
        
        # Extract top insights from all categories
        all_strengths = []
        critical_gaps = []
        key_insights = []
        
        for category, data in category_scores.items():
            strengths = data.get('strengths', [])
            gaps = data.get('gaps', [])
            insight = data.get('insight', '')
            
            # Collect top strengths
            all_strengths.extend(strengths[:2])
            
            # Collect critical gaps (from low-scoring categories)
            if data.get('score', 10) < 5:
                critical_gaps.extend(gaps[:2])
            
            # Collect insights
            if insight:
                key_insights.append({
                    "category": category,
                    "score": data.get('score'),
                    "insight": insight
                })
        
        # Prepare enhanced scoring result
        scoring_result = {
            "status": "success",
            "overall_score": overall_score,
            "readiness_level": readiness_level,
            "category_scores": category_scores,
            "focus_areas": focus_areas,
            "top_strengths": all_strengths[:5],
            "critical_gaps": critical_gaps[:3],
            "key_insights": key_insights,
            "scoring_metadata": {
                "total_categories": len(category_scores),
                "highest_score": max(d['score'] for d in category_scores.values()),
                "lowest_score": min(d['score'] for d in category_scores.values()),
                "research_quality": research_result.get("data_source", "unknown"),
                "has_llm_insights": True
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
            f"Enhanced scoring completed in {processing_time:.2f}s - "
            f"Overall: {overall_score}/10 ({readiness_level}), "
            f"Focus: {focus_areas.get('primary', {}).get('category', 'none')}, "
            f"Insights: {len(key_insights)}"
        )
        
        logger.info(f"=== ENHANCED SCORING NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced scoring node: {str(e)}", exc_info=True)
        state["error"] = f"Scoring failed: {str(e)}"
        state["messages"].append(f"ERROR in scoring: {str(e)}")
        state["current_stage"] = "scoring_error"
        return state