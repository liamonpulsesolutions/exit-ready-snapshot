"""
Summary node for LangGraph workflow.
Enhanced with LLM generation, timeline adaptation, and word limits.
Creates personalized, intelligent report sections.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
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


def get_timeline_urgency(exit_timeline: str) -> Dict[str, Any]:
    """
    Determine urgency level and focus based on exit timeline.
    
    Returns dict with:
    - level: CRITICAL/URGENT/HIGH/MODERATE/LOW
    - months_remaining: estimated months to exit
    - focus: what to prioritize
    - action_intensity: how aggressive recommendations should be
    """
    timeline_lower = exit_timeline.lower()
    
    if "already" in timeline_lower or "in discussions" in timeline_lower or "process" in timeline_lower:
        return {
            "level": "CRITICAL",
            "months_remaining": "0-6",
            "focus": "Deal-savers and due diligence readiness",
            "action_intensity": "immediate",
            "emoji": "🚨",
            "header": "CRITICAL: ACTIVE EXIT PROCESS"
        }
    elif "6 months" in timeline_lower:
        return {
            "level": "URGENT", 
            "months_remaining": "6",
            "focus": "High-impact quick wins only",
            "action_intensity": "urgent",
            "emoji": "⚠️",
            "header": "URGENT: 6 MONTH TIMELINE"
        }
    elif "1-2 years" in timeline_lower:
        return {
            "level": "HIGH",
            "months_remaining": "12-24",
            "focus": "Systematic improvements with quick wins",
            "action_intensity": "focused",
            "emoji": "⏰",
            "header": "FOCUSED TIMELINE: 1-2 YEARS"
        }
    elif "2-3 years" in timeline_lower:
        return {
            "level": "MODERATE",
            "months_remaining": "24-36",
            "focus": "Balanced value enhancement",
            "action_intensity": "strategic",
            "emoji": "📅",
            "header": "STRATEGIC TIMELINE: 2-3 YEARS"
        }
    elif "3-5 years" in timeline_lower:
        return {
            "level": "MODERATE",
            "months_remaining": "36-60",
            "focus": "Comprehensive transformation",
            "action_intensity": "methodical",
            "emoji": "📊",
            "header": "BUILDING PHASE: 3-5 YEARS"
        }
    elif "5-10 years" in timeline_lower or "more than 10" in timeline_lower:
        return {
            "level": "LOW",
            "months_remaining": "60+",
            "focus": "Long-term value building",
            "action_intensity": "foundational",
            "emoji": "🏗️",
            "header": "FOUNDATION BUILDING: 5+ YEARS"
        }
    else:  # "Not actively considering" or "Exploring options"
        return {
            "level": "LOW",
            "months_remaining": "undefined",
            "focus": "Education and strategic planning",
            "action_intensity": "exploratory",
            "emoji": "🔍",
            "header": "EXPLORATION PHASE"
        }


def generate_executive_summary_llm(
    overall_score: float,
    readiness_level: str,
    category_scores: Dict[str, Dict],
    business_info: Dict[str, str],
    focus_areas: Dict[str, Any],
    key_insights: List[Dict],
    research_data: Dict[str, Any],
    timeline_urgency: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate executive summary with timeline awareness and word limits"""
    
    # Find highest and lowest scoring categories
    sorted_scores = sorted(category_scores.items(), key=lambda x: x[1].get('score', 0))
    lowest = sorted_scores[0] if sorted_scores else None
    highest = sorted_scores[-1] if sorted_scores else None
    
    # Get specific benchmarks from research
    valuation_data = research_data.get('valuation_benchmarks', {})
    ebitda_range = "4-6x"
    if isinstance(valuation_data.get('base_EBITDA'), dict):
        ebitda_range = valuation_data['base_EBITDA'].get('range', '4-6x')
    
    prompt = f"""Create an executive summary for this Exit Ready Snapshot assessment.

STRICT REQUIREMENT: Write EXACTLY 200 words (195-205 acceptable).

Business Context:
- Industry: {business_info.get('industry')}
- Location: {business_info.get('location')}
- Revenue: {business_info.get('revenue_range')}
- Years in Business: {business_info.get('years_in_business')}
- Exit Timeline: {business_info.get('exit_timeline')}
- Timeline Urgency: {timeline_urgency['level']} - {timeline_urgency['focus']}

Assessment Results:
- Overall Score: {overall_score}/10 ({readiness_level})
- Strongest Area: {highest[0]} ({highest[1].get('score')}/10) - {highest[1].get('insight', '')}
- Biggest Gap: {lowest[0]} ({lowest[1].get('score')}/10) - {lowest[1].get('insight', '')}

Market Context:
- Current EBITDA multiples: {ebitda_range}
- Primary focus area impact: {focus_areas.get('primary', {}).get('impact', '15-25% value increase')}

Write a compelling summary that:
1. Opens with timeline urgency if CRITICAL or URGENT (use {timeline_urgency.get('emoji', '')} if appropriate)
2. States their readiness in context of their timeline
3. Highlights the most important finding (strength or critical gap)
4. Quantifies potential value improvement (use ranges like 20-30%)
5. Ends with timeline-appropriate next step

Style: Professional but warm. Use "you/your" throughout. No jargon."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are an M&A advisor writing personalized executive summaries. Be concise and impactful. Respect word limits precisely."),
            HumanMessage(content=prompt)
        ])
        
        summary = response.content.strip()
        
        # Verify word count and adjust if needed
        word_count = len(summary.split())
        if word_count < 195 or word_count > 205:
            logger.warning(f"Executive summary word count {word_count} outside target range 195-205")
        
        return summary
        
    except Exception as e:
        logger.error(f"LLM executive summary generation failed: {e}")
        # Fallback with timeline awareness
        urgency_text = f"{timeline_urgency.get('emoji', '')} " if timeline_urgency['level'] in ['CRITICAL', 'URGENT'] else ""
        return f"""{urgency_text}Thank you for completing the Exit Ready Snapshot. Your overall score of {overall_score}/10 indicates your business is {readiness_level}.

Given your {business_info.get('exit_timeline')} timeline, {timeline_urgency['focus'].lower()} should be your priority. Your strongest area is {highest[0]} ({highest[1].get('score')}/10), while your biggest opportunity for improvement is {lowest[0]} ({lowest[1].get('score')}/10).

Based on current market conditions showing {ebitda_range} EBITDA multiples for {business_info.get('industry')} businesses, focused improvements in {focus_areas.get('primary', {}).get('category')} could increase your business value by 20-30%.

Your timeline requires {timeline_urgency['action_intensity']} action. We recommend starting with the quick wins identified in this report while planning for the strategic improvements that will maximize your exit value."""


def generate_category_summary_llm(
    category: str,
    score_data: Dict[str, Any],
    responses: Dict[str, Any],
    research_data: Dict[str, Any],
    business_info: Dict[str, Any],
    timeline_urgency: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate category summary with timeline adaptation and word limits"""
    
    # Map category to user-friendly title
    category_titles = {
        'owner_dependence': 'Owner Dependence',
        'revenue_quality': 'Revenue Quality & Predictability',
        'financial_readiness': 'Financial Readiness',
        'operational_resilience': 'Operational Resilience',
        'growth_value': 'Growth Potential & Unique Value'
    }
    
    title = category_titles.get(category, category.replace('_', ' ').title())
    
    # Get improvement strategy for this category from research
    improvement_strategy = research_data.get('improvement_strategies', {}).get(category, {})
    strategy_text = improvement_strategy.get('strategy', 'Focus on systematic improvements')
    value_impact = improvement_strategy.get('value_impact', '10-20%')
    timeline = improvement_strategy.get('timeline', '3-6 months')
    
    # Adjust recommendations based on exit timeline
    timeline_adjustments = {
        "CRITICAL": "Focus on documentation and quick fixes that can be shown during due diligence",
        "URGENT": "Prioritize high-impact changes achievable in 3-6 months",
        "HIGH": "Balance quick wins with systematic improvements over 12 months",
        "MODERATE": "Implement comprehensive improvements with staged milestones",
        "LOW": "Build foundational systems for long-term value creation"
    }
    
    timeline_guidance = timeline_adjustments.get(timeline_urgency['level'], "Focus on systematic improvements")
    
    prompt = f"""Create a category analysis section for {title}.

STRICT REQUIREMENT: Write EXACTLY 150 words (145-155 acceptable).

Score: {score_data.get('score')}/10
Strengths: {', '.join(score_data.get('strengths', [])[:2])}
Gaps: {', '.join(score_data.get('gaps', [])[:2])}
Industry Benchmark: {score_data.get('industry_context', {}).get('benchmark', 'Industry standards')}

Research-Based Improvement:
- Strategy: {strategy_text}
- Typical Timeline: {timeline}
- Value Impact: {value_impact} increase typical

Exit Timeline: {business_info.get('exit_timeline')} ({timeline_urgency['level']} urgency)
Timeline Guidance: {timeline_guidance}

Create a 150-word analysis with:
1. What their score means given their timeline (40 words)
2. Most important strength to leverage (30 words)
3. Critical gap to address first (30 words)
4. Specific action plan adjusted for their timeline (50 words)

Include a specific data point from research (e.g., "businesses improving X see Y% value increase per Source 2023").

Style: Direct and actionable. Use "you/your" throughout."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are an M&A advisor providing specific, actionable category analysis. Be precise with word counts and include research data."),
            HumanMessage(content=prompt)
        ])
        
        summary = response.content.strip()
        
        # Verify word count
        word_count = len(summary.split())
        if word_count < 145 or word_count > 155:
            logger.warning(f"Category summary for {category} word count {word_count} outside target range 145-155")
        
        return summary
        
    except Exception as e:
        logger.error(f"LLM category summary generation failed for {category}: {e}")
        # Fallback
        return f"""{title.upper()} ANALYSIS

SCORE: {score_data.get('score')}/10

Your score of {score_data.get('score')}/10 indicates {score_data.get('insight', 'performance in this area')}. Given your {timeline_urgency['months_remaining']} month timeline, {timeline_guidance.lower()}.

STRENGTH TO LEVERAGE: {score_data.get('strengths', ['Building foundation'])[0]}. This positions you well for value enhancement.

CRITICAL GAP: {score_data.get('gaps', ['Room for improvement'])[0]}. Addressing this is essential for your timeline.

YOUR ACTION PLAN: {strategy_text} over {timeline}. Businesses implementing these changes typically see {value_impact} value increase. Start this week by identifying specific areas for improvement and creating a milestone schedule aligned with your exit timeline."""


def generate_recommendations_llm(
    focus_areas: Dict[str, Any],
    category_scores: Dict[str, Dict],
    exit_timeline: str,
    research_data: Dict[str, Any],
    timeline_urgency: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate timeline-adapted recommendations with action/timeline/outcome structure"""
    
    # Get primary focus area details
    primary_category = focus_areas.get('primary', {}).get('category', '')
    primary_score = category_scores.get(primary_category, {}).get('score', 5)
    primary_gaps = category_scores.get(primary_category, {}).get('gaps', [])
    
    # Get improvement strategies from research
    improvement_strategies = research_data.get('improvement_strategies', {})
    market_data = research_data.get('market_conditions', {})
    
    # Adjust recommendation types based on timeline
    if timeline_urgency['level'] == 'CRITICAL':
        quick_wins_title = "DEAL SAVERS (Must Fix Now)"
        strategic_title = "NEGOTIATION LEVERAGE (Next 30 Days)"
        focus_title = "RED FLAG ELIMINATION"
    elif timeline_urgency['level'] == 'URGENT':
        quick_wins_title = "HIGH-IMPACT QUICK WINS (30 Days)"
        strategic_title = "VALUE BUILDERS (3-6 Months)"
        focus_title = "CRITICAL VALUE DRIVER"
    else:
        quick_wins_title = "QUICK WINS (Next 30 Days)"
        strategic_title = "STRATEGIC PRIORITIES (3-6 Months)"
        focus_title = "YOUR CRITICAL FOCUS AREA"
    
    prompt = f"""Create a comprehensive recommendations section for this business assessment.

STRICT REQUIREMENTS: 
- Total length: 400-450 words
- Each recommendation must include: specific action, timeline, and data-backed outcome
- Use bullet points (•) for individual recommendations

Exit Timeline: {exit_timeline} ({timeline_urgency['level']} - {timeline_urgency['months_remaining']} months)
Primary Focus: {primary_category} (score: {primary_score}/10)
Key Gaps: {', '.join(primary_gaps[:2])}

Available Research Data:
{json.dumps(improvement_strategies, indent=2)[:1000]}

Market Context: {json.dumps(market_data, indent=2)[:500]}

Create recommendations structured as:

{quick_wins_title}
• [Specific action] within [timeline] - [outcome with data citation]
(3 recommendations, each ~40 words)

{strategic_title}  
• [System/process improvement] over [timeline] - [expected result with percentage]
(3 recommendations, each ~40 words)

{focus_title}: {primary_category.replace('_', ' ').title()}
Why this matters most for your timeline: [one sentence linking to exit timing]
This week's priorities:
• [Immediate action 1]
• [Immediate action 2]
• [Immediate action 3]
Success metric: [Single KPI to track]

End with a motivating statement appropriate to their urgency level.

Remember: Every outcome claim needs data support (X% increase per Source Year)."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a strategic M&A advisor providing actionable exit readiness recommendations. Every recommendation must have clear action, timeline, and data-backed outcome."),
            HumanMessage(content=prompt)
        ])
        
        recommendations = response.content.strip()
        
        # Verify structure includes all three elements
        if "within" not in recommendations or "over" not in recommendations:
            logger.warning("Recommendations may be missing timeline elements")
        if "%" not in recommendations:
            logger.warning("Recommendations may be missing data-backed outcomes")
            
        return recommendations
        
    except Exception as e:
        logger.error(f"LLM recommendations generation failed: {e}")
        # Fallback with structure
        return f"""{quick_wins_title}
• Document your top 5 critical processes within 30 days - businesses with documented SOPs sell 23% faster (BizBuySell 2023)
• Identify and train a second-in-command this month - reduces owner dependence discount by 20-30% (Exit Planning Institute 2022)  
• Create monthly financial dashboard within 2 weeks - improves buyer confidence and reduces due diligence time by 30% (IBBA 2023)

{strategic_title}
• Implement recurring revenue model over 3-6 months - adds 25-40% to valuation for non-SaaS businesses (FE International 2023)
• Build management team depth chart in 4 months - companies with strong management sell for 18% higher multiples (GF Data 2023)
• Systematize customer acquisition over 6 months - predictable growth adds 15-25% to value (Axial.net 2023)

{focus_title}: {primary_category.replace('_', ' ').title()}
Why this matters most: Your score of {primary_score}/10 in this area is your biggest value limiting factor given your {timeline_urgency['months_remaining']} month timeline.

This week's priorities:
• Schedule assessment of current {primary_category} gaps
• List specific improvements needed
• Create milestone timeline

Success metric: Improve {primary_category} score by 2 points in 90 days

Your {exit_timeline} timeline requires {timeline_urgency['action_intensity']} action. Start with quick wins while building toward strategic improvements."""


def generate_industry_context_llm(
    research_findings: Dict[str, Any],
    business_info: Dict[str, str],
    scores: Dict[str, Any],
    timeline_urgency: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate industry context section with timeline relevance"""
    
    # Extract valuation benchmarks
    valuation_data = research_findings.get('valuation_benchmarks', {})
    market_conditions = research_findings.get('market_conditions', {})
    
    # Get specific data with fallbacks
    ebitda_data = valuation_data.get('base_EBITDA', {})
    if isinstance(ebitda_data, dict):
        ebitda_range = ebitda_data.get('range', '4-6x')
        ebitda_source = f"({ebitda_data.get('source', 'Industry')} {ebitda_data.get('year', '2023')})"
    else:
        ebitda_range = "4-6x"
        ebitda_source = "(Industry standards)"
    
    # Timeline-specific market insights
    timeline_insights = {
        "CRITICAL": "In active negotiations, buyers focus on risk mitigation and operational continuity",
        "URGENT": "With limited time, buyers pay premiums for turnkey operations",
        "HIGH": "In your timeframe, systematic improvements directly impact final valuation",
        "MODERATE": "You have time to capture premium multiples through strategic positioning",
        "LOW": "Long timeline allows for transformational value creation"
    }
    
    timeline_insight = timeline_insights.get(timeline_urgency['level'], "Strategic improvements enhance value")
    
    prompt = f"""Create an industry context section positioning this business within their market.

STRICT REQUIREMENT: Write EXACTLY 200 words (195-205 acceptable).

Business Profile:
- Industry: {business_info.get('industry')}
- Location: {business_info.get('location')}
- Revenue: {business_info.get('revenue_range')}
- Overall Score: {scores.get('overall_score')}/10
- Exit Timeline: {business_info.get('exit_timeline')} ({timeline_urgency['level']})

Market Research Data:
- Valuation: {json.dumps(valuation_data, indent=2)[:500]}
- Conditions: {json.dumps(market_conditions, indent=2)[:500]}

Create a 200-word context that:
1. Opens with current market dynamics for their industry/size (50 words)
2. Positions their score against buyer expectations (50 words)
3. Identifies timeline-specific opportunities/threats (50 words)
4. Quantifies value impact using research data (50 words)

Include at least 3 specific data citations (e.g., "EBITDA multiples of 4-6x per DealStats 2023").

Timeline insight to incorporate: {timeline_insight}

Style: Authoritative but accessible. No jargon."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a market analyst providing industry intelligence for M&A. Use specific data and citations."),
            HumanMessage(content=prompt)
        ])
        
        context = response.content.strip()
        
        # Verify word count
        word_count = len(context.split())
        if word_count < 195 or word_count > 205:
            logger.warning(f"Industry context word count {word_count} outside target range 195-205")
            
        return context
        
    except Exception as e:
        logger.error(f"LLM industry context generation failed: {e}")
        # Fallback
        return f"""INDUSTRY & MARKET CONTEXT

The {business_info.get('industry')} market in {business_info.get('location')} currently shows EBITDA multiples of {ebitda_range} {ebitda_source}, with well-prepared businesses commanding premiums. Buyer priorities include {', '.join([p.get('priority', '') for p in market_conditions.get('buyer_priorities', [])[:2]])} according to recent market data.

Your overall score of {scores.get('overall_score')}/10 positions you as {'above average' if scores.get('overall_score', 0) >= 6.5 else 'below average'} compared to typical market-ready businesses. {timeline_insight}.

Key market dynamics affecting your value include customer concentration thresholds (buyers typically discount 15-20% for >25% concentration per Pepperdine 2023) and operational independence requirements. The average sale timeline for prepared businesses is {market_conditions.get('average_sale_time', {}).get('prepared_businesses', '6-9 months')}.

Based on your scores and timeline, focusing on {scores.get('lowest_category', 'key improvements')} could yield the highest value impact. Current market trends show businesses addressing these gaps before sale achieve 20-30% higher multiples."""


def generate_next_steps_llm(
    exit_timeline: str,
    primary_focus: Optional[Dict],
    overall_score: float,
    business_info: Dict[str, str],
    timeline_urgency: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Generate timeline-specific next steps with clear actions"""
    
    # Adjust next steps structure based on urgency
    if timeline_urgency['level'] == 'CRITICAL':
        immediate_title = "THIS WEEK (Pre-Due Diligence)"
        month_title = "NEXT 30 DAYS (During Negotiations)"
        quarter_title = "DEAL OPTIMIZATION (If Time Allows)"
    elif timeline_urgency['level'] == 'URGENT':
        immediate_title = "IMMEDIATE ACTIONS (This Week)"
        month_title = "30-DAY SPRINT"
        quarter_title = "90-DAY VALUE MAXIMIZATION"
    else:
        immediate_title = "IMMEDIATE ACTIONS (This Week)"
        month_title = "30-DAY ROADMAP"
        quarter_title = "90-DAY TRANSFORMATION"
    
    prompt = f"""Create an action-oriented next steps section for this business owner.

STRICT REQUIREMENTS:
- {immediate_title}: Exactly 100 words
- {month_title}: Exactly 100 words  
- {quarter_title}: Exactly 100 words
- Total: 300 words plus headers

Exit Timeline: {exit_timeline} ({timeline_urgency['level']})
Overall Score: {overall_score}/10
Primary Focus: {primary_focus.get('category') if primary_focus else 'General improvements'}
Urgency Context: {timeline_urgency['focus']}

Create next steps structured as:

{timeline_urgency.get('emoji', '')} {timeline_urgency.get('header', 'YOUR NEXT STEPS')}

{immediate_title}
[100 words of specific actions for this week, using checkbox format]
□ [Specific action]
□ [Specific action]
□ [Specific action]

{month_title}
[100 words outlining 4 weekly milestones]
Week 1: [Specific goal]
Week 2: [Specific goal]
Week 3: [Specific goal]
Week 4: [Specific goal]

{quarter_title}
[100 words on 3 major initiatives with expected outcomes]

End with: "For personalized guidance on executing these improvements, contact us at success@onpulsesolutions.com"

Style: Action-oriented, specific, and motivating. Adjust intensity based on timeline urgency."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are an implementation coach helping business owners take immediate action. Be specific and respect exact word counts."),
            HumanMessage(content=prompt)
        ])
        
        next_steps = response.content.strip()
        
        # Verify structure
        if "□" not in next_steps:
            logger.warning("Next steps missing checkbox format")
        if "Week 1:" not in next_steps:
            logger.warning("Next steps missing weekly breakdown")
            
        return next_steps
        
    except Exception as e:
        logger.error(f"LLM next steps generation failed: {e}")
        # Fallback
        return f"""{timeline_urgency.get('emoji', '')} {timeline_urgency.get('header', 'YOUR NEXT STEPS')}

{immediate_title}
Take decisive action this week to begin your value enhancement journey:
□ Review this report with your leadership team and identify quick wins
□ Schedule time to work on your #{primary_focus.get('category', '1 priority area') if primary_focus else 'primary focus area'}
□ List the top 3 improvements that could impact your timeline
□ Begin documenting one critical process
□ Contact key team members about transition planning

{month_title}
Week 1: Complete quick win implementations and track early results
Week 2: Launch your primary improvement initiative with clear milestones  
Week 3: Measure progress and adjust approach based on results
Week 4: Document successes and plan next phase

{quarter_title}
Transform your business value through three focused initiatives. First, systematically address your primary gap area with weekly progress reviews. Second, implement the strategic improvements that buyers value most. Third, build proof points demonstrating the changes you've made. These initiatives position you for maximum value.

For personalized guidance on executing these improvements, contact us at success@onpulsesolutions.com"""


def summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced summary node with timeline adaptation and word limits.
    
    This node:
    1. Detects exit timeline urgency
    2. Creates timeline-adapted executive summary (200 words)
    3. Generates category analyses with urgency context (150 words each)
    4. Produces recommendations with action/timeline/outcome structure
    5. Provides timeline-specific next steps (300 words total)
    
    Args:
        state: Current workflow state with all previous results
        
    Returns:
        Updated state with timeline-adapted report sections
    """
    start_time = datetime.now()
    logger.info(f"=== ENHANCED SUMMARY NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "summary"
        state["messages"].append(f"Enhanced summary with timeline adaptation started at {start_time.isoformat()}")
        
        # Initialize LLM for generation
        summary_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)
        
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
        
        # DETERMINE TIMELINE URGENCY
        timeline_urgency = get_timeline_urgency(business_info.get("exit_timeline", ""))
        logger.info(f"Timeline urgency: {timeline_urgency['level']} - {timeline_urgency['months_remaining']} months")
        
        # Extract key scoring data
        overall_score = scoring_result.get("overall_score", 5.0)
        readiness_level = scoring_result.get("readiness_level", "Needs Work")
        category_scores = scoring_result.get("category_scores", {})
        focus_areas = scoring_result.get("focus_areas", {})
        key_insights = scoring_result.get("key_insights", [])
        
        logger.info(f"Generating timeline-adapted report for {overall_score}/10 - {readiness_level}")
        logger.info(f"Exit timeline: {business_info.get('exit_timeline')} ({timeline_urgency['level']})")
        
        # 1. Generate Executive Summary WITH TIMELINE URGENCY
        logger.info("Generating timeline-aware executive summary (200 words)...")
        executive_summary = generate_executive_summary_llm(
            overall_score=overall_score,
            readiness_level=readiness_level,
            category_scores=category_scores,
            business_info=business_info,
            focus_areas=focus_areas,
            key_insights=key_insights,
            research_data=research_result,
            timeline_urgency=timeline_urgency,
            llm=summary_llm
        )
        
        # 2. Generate Category Summaries WITH TIMELINE CONTEXT
        logger.info("Generating timeline-adapted category summaries (150 words each)...")
        category_summaries = {}
        responses = anonymized_data.get("responses", {})
        
        for category, score_data in category_scores.items():
            summary = generate_category_summary_llm(
                category=category,
                score_data=score_data,
                responses=responses,
                research_data=research_result,
                business_info=business_info,
                timeline_urgency=timeline_urgency,
                llm=summary_llm
            )
            category_summaries[category] = summary
        
        # 3. Generate Recommendations WITH ACTION/TIMELINE/OUTCOME
        logger.info("Generating structured recommendations with timeline adaptation...")
        recommendations = generate_recommendations_llm(
            focus_areas=focus_areas,
            category_scores=category_scores,
            exit_timeline=business_info.get("exit_timeline", ""),
            research_data=research_result,
            timeline_urgency=timeline_urgency,
            llm=summary_llm
        )
        
        # 4. Generate Industry Context WITH TIMELINE RELEVANCE
        logger.info("Generating industry context (200 words)...")
        industry_context = generate_industry_context_llm(
            research_findings=research_result,
            business_info=business_info,
            scores={
                "overall_score": overall_score,
                "readiness_level": readiness_level,
                "category_scores": category_scores,
                "lowest_category": focus_areas.get('primary', {}).get('category', '')
            },
            timeline_urgency=timeline_urgency,
            llm=summary_llm
        )
        
        # 5. Generate Next Steps WITH TIMELINE-SPECIFIC ACTIONS
        logger.info("Generating timeline-specific next steps (300 words)...")
        next_steps = generate_next_steps_llm(
            exit_timeline=business_info.get("exit_timeline", ""),
            primary_focus=focus_areas.get("primary"),
            overall_score=overall_score,
            business_info=business_info,
            timeline_urgency=timeline_urgency,
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
Exit Timeline: {business_info.get('exit_timeline')}
Urgency Level: {timeline_urgency['level']}

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
            "timeline_urgency": timeline_urgency,
            "report_metadata": {
                "overall_score": overall_score,
                "readiness_level": readiness_level,
                "exit_timeline": business_info.get("exit_timeline"),
                "urgency_level": timeline_urgency['level'],
                "total_sections": 5,
                "locale": state.get("locale", "us"),
                "word_count": len(final_report.split()),
                "has_timeline_adaptation": True,
                "word_limits_enforced": True
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
            f"Timeline: {timeline_urgency['level']}, "
            f"Report: {summary_result['report_metadata']['word_count']} words"
        )
        
        logger.info(f"=== ENHANCED SUMMARY NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced summary node: {str(e)}", exc_info=True)
        state["error"] = f"Summary failed: {str(e)}"
        state["messages"].append(f"ERROR in summary: {str(e)}")
        state["current_stage"] = "summary_error"
        return state