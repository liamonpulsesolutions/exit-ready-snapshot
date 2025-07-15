"""
Summary node for LangGraph workflow.
Enhanced with LLM generation replacing template formatters.
Creates personalized, intelligent report sections.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
import json

# Load environment variables if not already loaded
from dotenv import load_dotenv
if not os.getenv('OPENAI_API_KEY'):
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from workflow.core.prompts import get_locale_terms

logger = logging.getLogger(__name__)


def generate_executive_summary_llm(
    overall_score: float,
    readiness_level: str,
    category_scores: Dict[str, Dict],
    business_info: Dict[str, str],
    focus_areas: Dict[str, Any],
    key_insights: List[Dict],
    research_data: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate executive summary using LLM instead of template"""
    
    # Find highest and lowest scoring categories
    sorted_scores = sorted(category_scores.items(), key=lambda x: x[1].get('score', 0))
    lowest = sorted_scores[0] if sorted_scores else None
    highest = sorted_scores[-1] if sorted_scores else None
    
    prompt = f"""Create a compelling 250-300 word executive summary for this Exit Ready Snapshot assessment.

Business Context:
- Industry: {business_info.get('industry')}
- Location: {business_info.get('location')}
- Revenue: {business_info.get('revenue_range')}
- Years in Business: {business_info.get('years_in_business')}
- Exit Timeline: {business_info.get('exit_timeline')}

Assessment Results:
- Overall Score: {overall_score}/10 ({readiness_level})
- Strongest Area: {highest[0]} ({highest[1].get('score')}/10) - {highest[1].get('insight', '')}
- Biggest Gap: {lowest[0]} ({lowest[1].get('score')}/10) - {lowest[1].get('insight', '')}

Primary Focus: {focus_areas.get('primary', {}).get('category')}

Market Context:
- Current multiples: {research_data.get('valuation_benchmarks', {}).get('base_EBITDA', '4-6x')}
- Key trend: {research_data.get('market_conditions', {}).get('key_trend', 'Technology integration valued')}

Write an executive summary that:
1. Opens with a warm, personalized greeting acknowledging their business journey
2. Presents their overall readiness in context (not just the score)
3. Highlights their strongest asset and biggest opportunity
4. Quantifies the value enhancement potential (use 20-40% if score <6, else 15-25%)
5. Creates urgency based on their timeline
6. Ends with an inspiring but realistic path forward

Use "you/your" throughout. Be specific to their situation. Balance honesty with encouragement."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a trusted M&A advisor writing personalized assessment summaries. Be warm but professional, specific but concise."),
            HumanMessage(content=prompt)
        ])
        return response.content.strip()
    except Exception as e:
        logger.error(f"LLM executive summary generation failed: {e}")
        # Fallback to basic template
        return f"""Thank you for completing the Exit Ready Snapshot. Your overall score of {overall_score}/10 indicates your business is {readiness_level}.

Your strongest area is {highest[0]} ({highest[1].get('score')}/10), while your biggest opportunity for improvement is {lowest[0]} ({lowest[1].get('score')}/10).

Based on your assessment, focused improvements could increase your business value by 20-40%. Given your {business_info.get('exit_timeline')} timeline, we recommend prioritizing {focus_areas.get('primary', {}).get('category')}."""


def generate_category_summary_llm(
    category: str,
    score_data: Dict[str, Any],
    responses: Dict[str, Any],
    research_data: Dict[str, Any],
    business_info: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate category-specific summary using LLM"""
    
    # Map category to user-friendly title
    category_titles = {
        'owner_dependence': 'Owner Dependence',
        'revenue_quality': 'Revenue Quality & Predictability',
        'financial_readiness': 'Financial Readiness',
        'operational_resilience': 'Operational Resilience',
        'growth_value': 'Growth Potential & Unique Value'
    }
    
    title = category_titles.get(category, category.replace('_', ' ').title())
    
    # Get relevant responses for this category
    category_responses = {
        'owner_dependence': {'q1': responses.get('q1'), 'q2': responses.get('q2')},
        'revenue_quality': {'q3': responses.get('q3'), 'q4': responses.get('q4')},
        'financial_readiness': {'q5': responses.get('q5'), 'q6': responses.get('q6')},
        'operational_resilience': {'q7': responses.get('q7'), 'q8': responses.get('q8')},
        'growth_value': {'q9': responses.get('q9'), 'q10': responses.get('q10')}
    }
    
    prompt = f"""Create a compelling category analysis section for {title}.

Score: {score_data.get('score')}/10
Strengths: {', '.join(score_data.get('strengths', [])[:3])}
Gaps: {', '.join(score_data.get('gaps', [])[:3])}
Insight: {score_data.get('insight', '')}

Their Responses:
{json.dumps(category_responses.get(category, {}), indent=2)}

Industry Context:
- Benchmark: {score_data.get('industry_context', {}).get('benchmark', 'Industry standards')}
- Impact: {score_data.get('industry_context', {}).get('impact', 'Standard valuation impact')}
- {category} improvement strategy: {research_data.get('improvement_strategies', {}).get(category, {}).get('strategy', 'Focus on key improvements')}

Create a 200-250 word analysis that:
1. Opens with what their score means in practical terms
2. Celebrates specific strengths using their actual responses
3. Addresses gaps honestly but constructively
4. Provides 3 specific, timebound action items
5. Connects to industry benchmarks with citations
6. Ends with the value impact of improvements

Format with clear sections: Score interpretation, Strengths, Gaps, Action Plan, Industry Context.
Use "you/your" throughout. Reference their specific situation."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are an M&A advisor providing detailed category analysis. Be specific, actionable, and encouraging."),
            HumanMessage(content=prompt)
        ])
        return response.content.strip()
    except Exception as e:
        logger.error(f"LLM category summary generation failed for {category}: {e}")
        # Fallback
        return f"""{title.upper()} ANALYSIS

SCORE: {score_data.get('score')}/10

Your score indicates {score_data.get('insight', 'performance in this area')}.

STRENGTHS: {', '.join(score_data.get('strengths', ['Building foundation'])[:2])}

GAPS: {', '.join(score_data.get('gaps', ['Room for improvement'])[:2])}

Focus on addressing the identified gaps to improve your score and business value."""


def generate_recommendations_llm(
    focus_areas: Dict[str, Any],
    category_scores: Dict[str, Dict],
    exit_timeline: str,
    research_data: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate personalized recommendations section using LLM"""
    
    # Identify quick wins (high impact, low effort)
    quick_wins = []
    for category, data in category_scores.items():
        if data.get('score', 0) < 7:
            for gap in data.get('gaps', [])[:1]:
                quick_wins.append({'category': category, 'gap': gap, 'score': data.get('score')})
    
    prompt = f"""Create a comprehensive recommendations section for this business assessment.

Exit Timeline: {exit_timeline}
Primary Focus: {focus_areas.get('primary', {}).get('category')} (score: {category_scores.get(focus_areas.get('primary', {}).get('category'), {}).get('score')})

All Category Scores:
{json.dumps({k: v.get('score') for k, v in category_scores.items()}, indent=2)}

Key Insights from Scoring:
{json.dumps([{'category': k, 'insight': v.get('insight', '')} for k, v in category_scores.items()], indent=2)}

Market Research:
- Improvement strategies with timelines and impacts: {json.dumps(research_data.get('improvement_strategies', {}), indent=2)}

Create a 400-500 word recommendations section with:

1. QUICK WINS (Next 30 Days) - 3 specific actions they can start immediately
2. CRITICAL FOCUS (Next 90 Days) - Deep dive on their primary improvement area
3. STRATEGIC PRIORITIES (Next 6-12 Months) - Long-term value builders

For each recommendation:
- Be ultra-specific (not "improve systems" but "implement weekly team meetings")
- Include expected impact on valuation
- Reference market data where relevant
- Consider their timeline urgency

End with a motivating call-to-action that acknowledges their journey and next steps.

Use "you/your" throughout. Make it feel like personalized advice from a trusted advisor."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a strategic M&A advisor providing actionable exit readiness recommendations. Be specific, practical, and motivating."),
            HumanMessage(content=prompt)
        ])
        return response.content.strip()
    except Exception as e:
        logger.error(f"LLM recommendations generation failed: {e}")
        return f"""RECOMMENDATIONS

Based on your assessment, focus on {focus_areas.get('primary', {}).get('category')} to maximize value.

QUICK WINS (30 Days): Address immediate gaps
CRITICAL FOCUS (90 Days): Implement systematic improvements
STRATEGIC PRIORITIES (6-12 Months): Build long-term value

Contact us for personalized guidance on your exit journey."""


def generate_industry_context_llm(
    research_findings: Dict[str, Any],
    business_info: Dict[str, str],
    scores: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate industry context section using LLM"""
    
    prompt = f"""Create a compelling industry context section that positions this business within their market.

Business Profile:
- Industry: {business_info.get('industry')}
- Location: {business_info.get('location')}
- Revenue: {business_info.get('revenue_range')}
- Overall Score: {scores.get('overall_score')}/10

Market Research Data:
- Valuation benchmarks: {json.dumps(research_findings.get('valuation_benchmarks', {}), indent=2)}
- Market conditions: {json.dumps(research_findings.get('market_conditions', {}), indent=2)}
- Industry trends: {research_findings.get('industry_context', {})}

Citations available: {', '.join(research_findings.get('citations', [])[:5])}

Create a 200-250 word industry context section that:
1. Opens with current market dynamics for their industry/size
2. Positions their score against market expectations
3. Identifies 2-3 specific market opportunities or threats
4. Quantifies valuation implications using research data
5. References at least 3 citations naturally in the text

Format: Flowing prose (not bullets). Use citations like "buyers are paying premium multiples for recurring revenue (per DealStats 2025)."

Make it feel like insider intelligence that gives them an edge."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a market research analyst providing industry intelligence for M&A. Use data and citations to build credibility."),
            HumanMessage(content=prompt)
        ])
        return response.content.strip()
    except Exception as e:
        logger.error(f"LLM industry context generation failed: {e}")
        return f"""INDUSTRY & MARKET CONTEXT

Your {business_info.get('industry')} business operates in a market where valuations typically range from {research_findings.get('valuation_benchmarks', {}).get('base_EBITDA', '4-6x EBITDA')}.

Current buyer priorities include {', '.join(research_findings.get('market_conditions', {}).get('buyer_priorities', ['recurring revenue', 'systematic operations'])[:2])}.

Market conditions suggest {research_findings.get('market_conditions', {}).get('average_sale_time', '9-12 months')} for well-prepared businesses."""


def generate_next_steps_llm(
    exit_timeline: str,
    primary_focus: Optional[Dict],
    overall_score: float,
    business_info: Dict[str, str],
    llm: ChatOpenAI
) -> str:
    """Generate next steps section using LLM"""
    
    prompt = f"""Create an action-oriented next steps section for this business owner.

Exit Timeline: {exit_timeline}
Overall Score: {overall_score}/10
Primary Focus Area: {primary_focus.get('category') if primary_focus else 'General improvements'}
Business: {business_info.get('revenue_range')} {business_info.get('industry')} business

Create a 250-300 word next steps section that:

1. Opens with timeline-appropriate urgency (urgent if <2 years, strategic if longer)
2. Provides a week-by-week action plan for the first month
3. Outlines 90-day milestones
4. Suggests when to seek professional help
5. Ends with contact information and a compelling call-to-action

Structure:
- IMMEDIATE ACTIONS (This Week)
- 30-DAY SPRINT
- 90-DAY TRANSFORMATION
- PROFESSIONAL SUPPORT OPTIONS

Make it feel achievable and exciting. Use checkbox format (□) for actions.
Include: "Contact us at success@onpulsesolutions.com"

Tone: Motivating coach who believes in their success."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are an implementation coach helping business owners take action on their exit readiness. Be specific, motivating, and practical."),
            HumanMessage(content=prompt)
        ])
        return response.content.strip()
    except Exception as e:
        logger.error(f"LLM next steps generation failed: {e}")
        return f"""NEXT STEPS

{'URGENT ACTION REQUIRED' if '1-2 years' in exit_timeline or 'Already' in exit_timeline else 'STRATEGIC OPPORTUNITY'}

□ Review this report with your team
□ Commit to your primary focus area
□ Schedule time for improvements

Contact us at success@onpulsesolutions.com for personalized guidance."""


def summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced summary node that generates personalized report using LLM.
    
    This node:
    1. Creates compelling executive summary
    2. Generates detailed category analyses
    3. Produces actionable recommendations
    4. Provides market context with citations
    5. Outlines clear next steps
    
    Args:
        state: Current workflow state with all previous results
        
    Returns:
        Updated state with intelligent report sections
    """
    start_time = datetime.now()
    logger.info(f"=== ENHANCED SUMMARY NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "summary"
        state["messages"].append(f"Enhanced summary started at {start_time.isoformat()}")
        
        # Initialize LLM for generation
        summary_llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.4)
        
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
        key_insights = scoring_result.get("key_insights", [])
        
        logger.info(f"Generating intelligent report for {overall_score}/10 - {readiness_level}")
        
        # 1. Generate Executive Summary
        logger.info("Generating LLM executive summary...")
        executive_summary = generate_executive_summary_llm(
            overall_score=overall_score,
            readiness_level=readiness_level,
            category_scores=category_scores,
            business_info=business_info,
            focus_areas=focus_areas,
            key_insights=key_insights,
            research_data=research_result,
            llm=summary_llm
        )
        
        # 2. Generate Category Summaries
        logger.info("Generating LLM category summaries...")
        category_summaries = {}
        responses = anonymized_data.get("responses", {})
        
        for category, score_data in category_scores.items():
            summary = generate_category_summary_llm(
                category=category,
                score_data=score_data,
                responses=responses,
                research_data=research_result,
                business_info=business_info,
                llm=summary_llm
            )
            category_summaries[category] = summary
        
        # 3. Generate Recommendations
        logger.info("Generating LLM recommendations...")
        recommendations = generate_recommendations_llm(
            focus_areas=focus_areas,
            category_scores=category_scores,
            exit_timeline=business_info.get("exit_timeline", ""),
            research_data=research_result,
            llm=summary_llm
        )
        
        # 4. Generate Industry Context
        logger.info("Generating LLM industry context...")
        industry_context = generate_industry_context_llm(
            research_findings=research_result,
            business_info=business_info,
            scores={
                "overall_score": overall_score,
                "readiness_level": readiness_level,
                "category_scores": category_scores
            },
            llm=summary_llm
        )
        
        # 5. Generate Next Steps
        logger.info("Generating LLM next steps...")
        next_steps = generate_next_steps_llm(
            exit_timeline=business_info.get("exit_timeline", ""),
            primary_focus=focus_areas.get("primary"),
            overall_score=overall_score,
            business_info=business_info,
            llm=summary_llm
        )
        
        # 6. Structure Final Report
        logger.info("Structuring final report...")
        final_report = f"""EXIT READY SNAPSHOT ASSESSMENT REPORT

{'='*60}

EXECUTIVE SUMMARY

{executive_summary}

{'='*60}

YOUR EXIT READINESS SCORE

Overall Score: {overall_score}/10
Readiness Level: {readiness_level}

{'='*60}

DETAILED ANALYSIS BY CATEGORY

"""
        
        # Add category summaries
        for category, summary in category_summaries.items():
            final_report += f"{summary}\n\n{'='*60}\n\n"
        
        final_report += f"""PERSONALIZED RECOMMENDATIONS

{recommendations}

{'='*60}

INDUSTRY & MARKET CONTEXT

{industry_context}

{'='*60}

YOUR NEXT STEPS

{next_steps}

{'='*60}

CONFIDENTIAL BUSINESS ASSESSMENT
Prepared by: On Pulse Solutions
Report Date: [REPORT_DATE]
Valid for: 90 days

This report contains proprietary analysis and recommendations specific to your business. 
The insights and strategies outlined are based on your assessment responses and current market conditions.

© On Pulse Solutions - Exit Ready Snapshot"""
        
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
                "word_count": len(final_report.split()),
                "has_llm_generation": True
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
            f"Enhanced summary completed in {processing_time:.2f}s - "
            f"Generated intelligent report: {summary_result['report_metadata']['word_count']} words"
        )
        
        logger.info(f"=== ENHANCED SUMMARY NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced summary node: {str(e)}", exc_info=True)
        state["error"] = f"Summary failed: {str(e)}"
        state["messages"].append(f"ERROR in summary: {str(e)}")
        state["current_stage"] = "summary_error"
        return state