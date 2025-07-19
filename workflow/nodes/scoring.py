"""
Scoring node for LangGraph workflow.
Enhanced with LLM interpretation for each category.
Uses pure functions from core modules plus intelligent analysis.
FIXED: Industry extraction and response counting.
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

# FIXED: Import LLM utilities
from workflow.core.llm_utils import get_llm_with_fallback, ensure_json_response
from langchain.schema import SystemMessage, HumanMessage

# Import enhanced scoring functions from the correct location
from workflow.core.scoring_logic import (
    score_owner_dependence,
    score_revenue_quality,
    score_financial_readiness,
    score_operational_resilience,
    score_growth_value,
    calculate_overall_score,
    identify_focus_areas,
    extract_industry_benchmarks  # Import the benchmark extraction function
)

logger = logging.getLogger(__name__)


def generate_category_insights(
    category: str,
    score_data: Dict[str, Any],
    responses: Dict[str, Any],
    research_data: Dict[str, Any],
    llm
) -> str:
    """Generate 2-3 sentences of intelligent commentary for a scoring category"""
    
    # Extract industry-specific benchmarks for context
    industry = responses.get("industry", "Professional Services")
    benchmarks = extract_industry_benchmarks(research_data, industry)
    
    # Create context-specific prompts for each category
    category_prompts = {
        "owner_dependence": f"""Analyze this owner dependence score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}
Industry benchmark: Business should run {benchmarks.get('owner_independence_days', 14)}+ days without owner
Industry impact: {benchmarks.get('owner_dependence_discount', '20-30%')} discount for high dependence

Key responses:
- Role: "{responses.get('q1', '')[:100]}..."
- Time away: "{responses.get('q2', '')}"

Industry context from research: {score_data.get('industry_context', {}).get('benchmark', '')}

Provide insight about what this score means for their exit readiness in the {industry} industry.""",

        "revenue_quality": f"""Analyze this revenue quality score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}
Industry benchmark: <{benchmarks.get('concentration_threshold', 25)}% customer concentration
Recurring revenue expectation: {benchmarks.get('recurring_threshold', 60)}%+ for {benchmarks.get('recurring_premium', '1.5-2.0x')} premium

Key responses:
- Revenue model: "{responses.get('q3', '')[:100]}..."
- Customer concentration: "{responses.get('q4', '')}"

Market data: {research_data.get('valuation_benchmarks', {}).get('recurring_revenue', {}).get('premium', 'Premium for recurring revenue')}
Industry context: {score_data.get('industry_context', {}).get('benchmark', '')}

Provide insight about how their revenue structure affects valuation in {industry}.""",

        "financial_readiness": f"""Analyze this financial readiness score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}
Expected margins: {benchmarks.get('expected_margin', '15-20%')} EBITDA for {industry}

Key responses:
- Clean financials confidence: "{responses.get('q5', '')}"
- Profit margins: "{responses.get('q6', '')}"

Industry context: {score_data.get('industry_context', {}).get('benchmark', '')}

Provide insight about their financial preparedness for due diligence in the {industry} sector.""",

        "operational_resilience": f"""Analyze this operational resilience score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}

Key responses:
- Critical dependencies: "{responses.get('q7', '')[:100]}..."
- Documentation level: "{responses.get('q8', '')}"

Industry expectation: {score_data.get('industry_context', {}).get('benchmark', '')}

Provide insight about operational transferability and buyer confidence for a {industry} business.""",

        "growth_value": f"""Analyze this growth value score and provide 2-3 sentences of insight.

Score: {score_data['score']}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}

Key responses:
- Unique value: "{responses.get('q9', '')[:100]}..."
- Growth potential: "{responses.get('q10', '')}"

Market trend: {research_data.get('market_conditions', {}).get('key_trend', {}).get('trend', 'Technology integration valued')}
Industry drivers: {score_data.get('industry_context', {}).get('key_value_drivers', [])}

Provide insight about their competitive positioning and growth story in {industry}."""
    }
    
    prompt = category_prompts.get(category, "Provide 2-3 sentences of insight about this score.")
    
    try:
        # Log before LLM call
        logger.debug(f"Generating insights for {category} with score {score_data['score']}")
        
        messages = [
            SystemMessage(content="You are an M&A advisor providing insights on business exit readiness. Be concise and specific. Reference industry-specific benchmarks where relevant."),
            HumanMessage(content=prompt)
        ]
        
        # FIXED: Direct text response, no JSON needed
        response = llm.invoke(messages)
        insight = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Log after LLM call
        logger.debug(f"Generated insight for {category}: {insight[:100]}...")
        
        return insight
    except Exception as e:
        logger.error(f"LLM insight generation failed for {category}: {e}")
        # Fallback to template-based insight
        if score_data['score'] >= 7:
            return f"Strong performance in {category.replace('_', ' ')} positions you well for exit in {industry}. {score_data.get('strengths', [''])[0]}."
        elif score_data['score'] >= 4:
            return f"Moderate {category.replace('_', ' ')} requires targeted improvements for {industry} standards. Focus on addressing: {score_data.get('gaps', [''])[0]}."
        else:
            return f"Significant gaps in {category.replace('_', ' ')} could impact valuation in {industry}. {score_data.get('gaps', [''])[0]}."


def scoring_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced scoring node with LLM interpretation for each category.
    Now uses dynamic industry benchmarking from research data.
    FIXED: Industry extraction and response counting.
    
    This node:
    1. Uses mechanical scoring with industry-specific benchmarks
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
        
        # FIXED: Initialize LLM for insights with proper model name and temperature
        insight_llm = get_llm_with_fallback("gpt-4.1-mini", temperature=0.3)
        
        # Get data from previous stages
        anonymized_data = state.get("anonymized_data", {})
        research_result = state.get("research_result", {})
        
        # FIXED: Extract only the actual question responses (q1-q10)
        question_responses = {}
        all_responses = anonymized_data.get("responses", {})
        for key, value in all_responses.items():
            if key.startswith('q') and key[1:].isdigit():
                question_responses[key] = value
        
        # FIXED: Get business context from state, not from responses
        # The industry should come from the anonymized_data or state, not responses
        industry = anonymized_data.get("industry") or state.get("industry") or "Professional Services"
        revenue_range = anonymized_data.get("revenue_range") or state.get("revenue_range") or "$1M-$5M"
        years_in_business = anonymized_data.get("years_in_business") or state.get("years_in_business") or "5-10 years"
        exit_timeline = anonymized_data.get("exit_timeline") or state.get("exit_timeline") or "1-2 years"
        
        # Create responses dict with question responses plus business context
        responses = question_responses.copy()
        responses["industry"] = industry
        responses["revenue_range"] = revenue_range
        responses["years_in_business"] = years_in_business
        responses["exit_timeline"] = exit_timeline
        
        logger.info(f"Scoring {len(question_responses)} question responses for {industry}")
        logger.info(f"Business context - Industry: {industry}, Revenue: {revenue_range}")
        
        # Ensure research_data is properly structured
        if not isinstance(research_result, dict):
            logger.error(f"research_result is not a dict: {type(research_result)}")
            research_result = {}
        
        # Extract research data - ensure it has the right structure
        research_data = {
            "valuation_benchmarks": research_result.get("valuation_benchmarks", {}),
            "improvement_strategies": research_result.get("improvement_strategies", {}),
            "market_conditions": research_result.get("market_conditions", {}),
            "industry_context": research_result.get("industry_context", {}),
            "industry_specific_thresholds": research_result.get("industry_specific_thresholds", {}),
            "citations": research_result.get("citations", [])
        }
        
        # Log extracted benchmarks for debugging
        benchmarks = extract_industry_benchmarks(research_data, industry)
        logger.info(f"Extracted benchmarks for {industry}: {benchmarks}")
        
        # Score each category with dynamic benchmarks
        category_scores = {}
        
        # 1. Score Owner Dependence (with industry-specific days threshold)
        logger.info("Scoring owner dependence with dynamic benchmarks...")
        logger.debug(f"Calling score_owner_dependence with responses: {list(responses.keys())}")
        owner_score = score_owner_dependence(responses, research_data)
        logger.debug(f"Owner dependence score returned: {owner_score['score']}")
        
        # Add LLM insight
        owner_insight = generate_category_insights(
            "owner_dependence", owner_score, responses, research_data, insight_llm
        )
        owner_score["insight"] = owner_insight
        
        category_scores["owner_dependence"] = owner_score
        logger.info(f"Owner dependence: {owner_score['score']}/10 (threshold: {benchmarks['owner_independence_days']} days)")
        
        # 2. Score Revenue Quality (with industry-specific concentration threshold)
        logger.info("Scoring revenue quality with dynamic benchmarks...")
        logger.debug("Calling score_revenue_quality")
        revenue_score = score_revenue_quality(responses, research_data)
        logger.debug(f"Revenue quality score returned: {revenue_score['score']}")
        
        # Add LLM insight
        revenue_insight = generate_category_insights(
            "revenue_quality", revenue_score, responses, research_data, insight_llm
        )
        revenue_score["insight"] = revenue_insight
        
        category_scores["revenue_quality"] = revenue_score
        logger.info(f"Revenue quality: {revenue_score['score']}/10 (concentration threshold: {benchmarks['concentration_threshold']}%)")
        
        # 3. Score Financial Readiness (with industry-specific margin expectations)
        logger.info("Scoring financial readiness with dynamic benchmarks...")
        logger.debug("Calling score_financial_readiness")
        financial_score = score_financial_readiness(responses, research_data)
        logger.debug(f"Financial readiness score returned: {financial_score['score']}")
        
        # Add LLM insight
        financial_insight = generate_category_insights(
            "financial_readiness", financial_score, responses, research_data, insight_llm
        )
        financial_score["insight"] = financial_insight
        
        category_scores["financial_readiness"] = financial_score
        logger.info(f"Financial readiness: {financial_score['score']}/10 (expected margins: {benchmarks['expected_margin']})")
        
        # 4. Score Operational Resilience (with industry-specific documentation standards)
        logger.info("Scoring operational resilience with dynamic benchmarks...")
        logger.debug("Calling score_operational_resilience")
        operational_score = score_operational_resilience(responses, research_data)
        logger.debug(f"Operational resilience score returned: {operational_score['score']}")
        
        # Add LLM insight
        operational_insight = generate_category_insights(
            "operational_resilience", operational_score, responses, research_data, insight_llm
        )
        operational_score["insight"] = operational_insight
        
        category_scores["operational_resilience"] = operational_score
        logger.info(f"Operational resilience: {operational_score['score']}/10")
        
        # 5. Score Growth Value (with industry-specific value drivers)
        logger.info("Scoring growth value with dynamic benchmarks...")
        logger.debug("Calling score_growth_value")
        growth_score = score_growth_value(responses, research_data)
        logger.debug(f"Growth value score returned: {growth_score['score']}")
        
        # Add LLM insight
        growth_insight = generate_category_insights(
            "growth_value", growth_score, responses, research_data, insight_llm
        )
        growth_score["insight"] = growth_insight
        
        category_scores["growth_value"] = growth_score
        logger.info(f"Growth value: {growth_score['score']}/10")
        
        # Add assertion checks after scoring
        assert len(category_scores) == 5, f"Expected 5 category scores, got {len(category_scores)}"
        for cat_name, cat_data in category_scores.items():
            assert 'score' in cat_data, f"Missing score for {cat_name}"
            assert 1.0 <= cat_data['score'] <= 10.0, f"Score {cat_data['score']} out of range for {cat_name}"
            logger.debug(f"Category {cat_name} validated: score={cat_data['score']}")
        
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
            
            # Collect insights with industry context
            if insight:
                key_insights.append({
                    "category": category,
                    "score": data.get('score'),
                    "insight": insight,
                    "industry_context": data.get('industry_context', {})
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
            "industry_benchmarks_applied": benchmarks,  # Include applied benchmarks
            "scoring_metadata": {
                "total_categories": len(category_scores),
                "highest_score": max(d['score'] for d in category_scores.values()),
                "lowest_score": min(d['score'] for d in category_scores.values()),
                "research_quality": research_result.get("citation_quality", {}).get("source", "unknown"),
                "has_llm_insights": True,
                "has_dynamic_benchmarks": True,
                "industry": industry,
                "question_responses_count": len(question_responses)
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
            f"Insights: {len(key_insights)}, "
            f"Industry: {industry}"
        )
        
        logger.info(f"=== ENHANCED SCORING NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced scoring node: {str(e)}", exc_info=True)
        state["error"] = f"Scoring failed: {str(e)}"
        state["messages"].append(f"ERROR in scoring: {str(e)}")
        state["current_stage"] = "scoring_error"
        return state