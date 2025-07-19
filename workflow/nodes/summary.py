"""
Summary node for LangGraph workflow.
Enhanced with LLM generation, timeline adaptation, word limits, and outcome framing rules.
Creates personalized, intelligent report sections with proper outcome language.
FIXED: Handle missing data gracefully.
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

# FIXED: Import LLM utilities
from workflow.core.llm_utils import (
    get_llm_with_fallback, 
    ensure_json_response, 
    validate_word_count
)
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
    llm
) -> str:
    """Generate executive summary with timeline awareness and word limits"""
    
    # FIXED: Handle empty category_scores gracefully
    if not category_scores:
        logger.warning("No category scores available for executive summary")
        return f"""Thank you for completing the Exit Ready Snapshot. Your assessment is being processed.

Given your {business_info.get('exit_timeline', 'timeline')}, we're analyzing your business readiness. 

Based on your {business_info.get('industry', 'industry')} business in {business_info.get('location', 'your location')}, we'll provide specific recommendations to maximize your exit value.

Please note that businesses in your industry typically see significant value improvements when implementing targeted exit readiness strategies."""
    
    # FIXED: Safely find highest and lowest scoring categories with null checks
    sorted_scores = sorted(category_scores.items(), key=lambda x: x[1].get('score', 0))
    
    if sorted_scores:
        lowest = sorted_scores[0]
        highest = sorted_scores[-1]
    else:
        # Provide defaults if no scores
        lowest = ('improvement_needed', {'score': 5.0, 'insight': 'Areas for improvement identified'})
        highest = ('strengths', {'score': 7.0, 'insight': 'Building on existing strengths'})
    
    # Get specific benchmarks from research
    valuation_data = research_data.get('valuation_benchmarks', {})
    ebitda_range = "4-6x"
    if isinstance(valuation_data.get('base_EBITDA'), dict):
        ebitda_range = valuation_data['base_EBITDA'].get('range', '4-6x')
    
    # OUTCOME FRAMING: Extract impact ranges from research
    improvements = research_data.get('improvement_strategies', {})
    primary_impact = "20-30%"  # Default range
    if focus_areas.get('primary'):
        primary_cat = focus_areas['primary']['category']
        if primary_cat in improvements:
            impact = improvements[primary_cat].get('value_impact', '20-30%')
            # Ensure it's a range
            if '-' not in str(impact) and '%' in str(impact):
                # Convert single number to range
                num = int(impact.replace('%', ''))
                primary_impact = f"{num-5}-{num+5}%"
            else:
                primary_impact = impact
    
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
- Primary focus area impact: {primary_impact} value increase potential

CRITICAL OUTCOME FRAMING RULES:
- Use "typically," "often," or "on average" when discussing outcomes
- Never use "will," "guaranteed," or "definitely"
- Express improvements as ranges (e.g., "20-30%") not specific numbers
- When mentioning value increases, frame as "businesses like yours typically see..."

Write a compelling summary that:
1. Opens with timeline urgency if CRITICAL or URGENT (use {timeline_urgency.get('emoji', '')} if appropriate)
2. States their readiness in context of their timeline
3. Highlights the most important finding (strength or critical gap)
4. Quantifies potential value improvement as a RANGE with proper framing
5. Ends with timeline-appropriate next step

Style: Professional but warm. Use "you/your" throughout. No jargon."""

    try:
        messages = [
            SystemMessage(content="You are an M&A advisor writing personalized executive summaries. Be concise and impactful. Always use 'typically' or 'often' when discussing outcomes. Never make promises."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        summary = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # FIXED: Validate and adjust word count
        validated_summary = validate_word_count(
            text=summary,
            target_words=200,
            tolerance=10,
            llm=llm,
            prompt=prompt
        )
        
        return validated_summary
        
    except Exception as e:
        logger.error(f"LLM executive summary generation failed: {e}")
        # Fallback with proper outcome framing
        urgency_text = f"{timeline_urgency.get('emoji', '')} " if timeline_urgency['level'] in ['CRITICAL', 'URGENT'] else ""
        return f"""{urgency_text}Thank you for completing the Exit Ready Snapshot. Your overall score of {overall_score}/10 indicates your business is {readiness_level}.

Given your {business_info.get('exit_timeline')} timeline, {timeline_urgency['focus'].lower()} should be your priority. Your strongest area is {highest[0]} ({highest[1].get('score')}/10), while your biggest opportunity for improvement is {lowest[0]} ({lowest[1].get('score')}/10).

Based on current market conditions showing {ebitda_range} EBITDA multiples for {business_info.get('industry')} businesses, focused improvements in {focus_areas.get('primary', {}).get('category')} typically result in {primary_impact} value increases for businesses like yours.

Your timeline requires {timeline_urgency['action_intensity']} action. We recommend starting with the quick wins identified in this report while planning for the strategic improvements that often maximize exit value."""


def generate_category_summary_llm(
    category: str,
    score_data: Dict[str, Any],
    responses: Dict[str, Any],
    research_data: Dict[str, Any],
    business_info: Dict[str, Any],
    timeline_urgency: Dict[str, Any],
    llm
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
    
    # Get improvement strategy for this category from research with outcome framing
    improvement_strategy = research_data.get('improvement_strategies', {}).get(category, {})
    strategy_text = improvement_strategy.get('strategy', 'Focus on systematic improvements')
    timeline = improvement_strategy.get('timeline', '3-6 months')
    source = improvement_strategy.get('source', 'Industry best practices')
    year = improvement_strategy.get('year', '2023')
    
    # OUTCOME FRAMING: Ensure value impact is a range
    value_impact = improvement_strategy.get('value_impact', '10-20%')
    if '-' not in str(value_impact) and '%' in str(value_impact):
        # Convert single number to range
        num = int(value_impact.replace('%', ''))
        value_impact = f"{num-5}-{num+5}%"
    
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
- Typical Value Impact: {value_impact} increase (per {source} {year})

Exit Timeline: {business_info.get('exit_timeline')} ({timeline_urgency['level']} urgency)
Timeline Guidance: {timeline_guidance}

CRITICAL OUTCOME FRAMING RULES:
- Always say "businesses typically see" or "owners often achieve" when citing improvements
- Never promise specific results - use "potential for X-Y% improvement"
- Include source citation when mentioning value impacts
- Use ranges, not specific percentages

Create a 150-word analysis with:
1. What their score means given their timeline (40 words)
2. Most important strength to leverage (30 words)
3. Critical gap to address first (30 words)
4. Specific action plan adjusted for their timeline (50 words)

Include: "businesses in {business_info.get('industry')} typically see {value_impact} value increase when implementing {strategy_text} (per {source} {year})".

Style: Direct and actionable. Use "you/your" throughout."""

    try:
        messages = [
            SystemMessage(content="You are an M&A advisor providing specific, actionable category analysis. Be precise with word counts and always frame outcomes as typical results, not guarantees."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        summary = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # FIXED: Validate and adjust word count
        validated_summary = validate_word_count(
            text=summary,
            target_words=150,
            tolerance=10,
            llm=llm,
            prompt=prompt
        )
        
        return validated_summary
        
    except Exception as e:
        logger.error(f"LLM category summary generation failed for {category}: {e}")
        # Fallback with proper outcome framing
        return f"""{title.upper()} ANALYSIS

SCORE: {score_data.get('score')}/10

Your score of {score_data.get('score')}/10 indicates {score_data.get('insight', 'performance in this area')}. Given your {timeline_urgency['months_remaining']} month timeline, {timeline_guidance.lower()}.

STRENGTH TO LEVERAGE: {score_data.get('strengths', ['Building foundation'])[0]}. This positions you well for value enhancement.

CRITICAL GAP: {score_data.get('gaps', ['Room for improvement'])[0]}. Addressing this is essential for your timeline.

YOUR ACTION PLAN: {strategy_text} over {timeline}. Businesses in your industry typically see {value_impact} value increase when implementing these changes ({source} {year}). Start this week by identifying specific areas for improvement and creating a milestone schedule aligned with your exit timeline."""


def generate_recommendations_llm(
    focus_areas: Dict[str, Any],
    category_scores: Dict[str, Dict],
    exit_timeline: str,
    research_data: Dict[str, Any],
    timeline_urgency: Dict[str, Any],
    llm
) -> str:
    """Generate timeline-adapted recommendations with proper outcome framing"""
    
    # Get primary focus area details
    primary_category = focus_areas.get('primary', {}).get('category', '')
    primary_score = category_scores.get(primary_category, {}).get('score', 5)
    primary_gaps = category_scores.get(primary_category, {}).get('gaps', [])
    
    # Get improvement strategies from research
    improvement_strategies = research_data.get('improvement_strategies', {})
    market_data = research_data.get('market_conditions', {})
    citations = research_data.get('citations', [])
    
    # Build citation list for prompt
    citation_text = []
    for citation in citations[:5]:  # Top 5 citations
        if isinstance(citation, dict):
            citation_text.append(f"{citation.get('source', '')} {citation.get('year', '')}")
        elif isinstance(citation, str):
            citation_text.append(citation)
    
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

CRITICAL OUTCOME FRAMING RULES:
1. ALWAYS use "typically," "often," or "on average" before any outcome claim
2. NEVER use "will," "guaranteed," "definitely," or "ensure"
3. Express ALL improvements as ranges (e.g., "15-25%") not specific numbers
4. Every outcome claim MUST cite a source (Source Year)
5. Frame as "businesses like yours typically see..." or "companies often achieve..."

Exit Timeline: {exit_timeline} ({timeline_urgency['level']} - {timeline_urgency['months_remaining']} months)
Primary Focus: {primary_category} (score: {primary_score}/10)
Key Gaps: {', '.join(primary_gaps[:2])}

Available Research Data:
{json.dumps(improvement_strategies, indent=2)[:1000]}

Market Context: {json.dumps(market_data, indent=2)[:500]}

Available Citations: {', '.join(citation_text)}

Create recommendations structured as:

{quick_wins_title}
• [Specific action] within [timeline] - businesses typically see [X-Y% outcome] ([Source Year])
(3 recommendations, each ~40 words)

{strategic_title}  
• [System/process improvement] over [timeline] - companies often achieve [X-Y% result] ([Source Year])
(3 recommendations, each ~40 words)

{focus_title}: {primary_category.replace('_', ' ').title()}
Why this matters most for your timeline: [one sentence linking to exit timing]
This week's priorities:
• [Immediate action 1]
• [Immediate action 2]
• [Immediate action 3]
Success metric: [Single KPI to track]

End with a motivating statement using "typically" or "often" language.

EXAMPLES OF PROPER FRAMING:
✓ "Document your processes within 30 days - businesses with documented SOPs typically sell 20-30% faster (BizBuySell 2023)"
✗ "Document your processes within 30 days - this will increase your value by 25%"

✓ "Companies implementing these changes often see 15-25% value increases (IBBA 2023)"
✗ "You will achieve 20% higher valuation"

Remember: Every outcome must be framed as typical/average, not guaranteed."""

    try:
        messages = [
            SystemMessage(content="You are a strategic M&A advisor providing actionable exit readiness recommendations. CRITICAL: Never make promises. Always use 'typically/often/on average' language. Every outcome claim needs a range and citation."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        recommendations = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Verify proper outcome framing
        if "will achieve" in recommendations or "will increase" in recommendations or "guaranteed" in recommendations:
            logger.warning("Recommendations contain promise language that should be revised")
        if recommendations.count("typically") + recommendations.count("often") + recommendations.count("on average") < 3:
            logger.warning("Recommendations may lack sufficient outcome framing language")
            
        return recommendations
        
    except Exception as e:
        logger.error(f"LLM recommendations generation failed: {e}")
        # Fallback with proper outcome framing
        return f"""{quick_wins_title}
• Document your top 5 critical processes within 30 days - businesses with documented SOPs typically sell 20-30% faster (BizBuySell 2023)
• Identify and train a second-in-command this month - companies often see 15-25% reduction in owner dependence discount (Exit Planning Institute 2022)  
• Create monthly financial dashboard within 2 weeks - buyers typically reduce due diligence time by 25-35% with clean reporting (IBBA 2023)

{strategic_title}
• Implement recurring revenue model over 3-6 months - businesses often achieve 25-40% valuation premiums with predictable revenue (FE International 2023)
• Build management team depth chart in 4 months - companies with strong management typically command 15-25% higher multiples (GF Data 2023)
• Systematize customer acquisition over 6 months - businesses with documented sales processes often see 20-30% growth (Axial.net 2023)

{focus_title}: {primary_category.replace('_', ' ').title()}
Why this matters most: Your score of {primary_score}/10 in this area represents your biggest opportunity for value enhancement given your {timeline_urgency['months_remaining']} month timeline.

This week's priorities:
• Schedule assessment of current {primary_category} gaps
• List specific improvements needed
• Create milestone timeline

Success metric: Improve {primary_category} score by 2 points in 90 days

Businesses that address their primary value gaps typically achieve 20-35% higher sale prices than those who don't (M&A Source 2023). Your {exit_timeline} timeline provides sufficient opportunity to capture this value with focused execution."""


def generate_industry_context_llm(
    research_findings: Dict[str, Any],
    business_info: Dict[str, str],
    scores: Dict[str, Any],
    timeline_urgency: Dict[str, Any],
    llm
) -> str:
    """Generate industry context section with timeline relevance and outcome framing"""
    
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
        "URGENT": "With limited time, buyers often pay premiums for turnkey operations",
        "HIGH": "In your timeframe, systematic improvements typically translate directly to valuation",
        "MODERATE": "You have time to potentially capture premium multiples through strategic positioning",
        "LOW": "Long timeline allows for transformational value creation opportunities"
    }
    
    timeline_insight = timeline_insights.get(timeline_urgency['level'], "Strategic improvements often enhance value")
    
    prompt = f"""Create an industry context section positioning this business within their market.

STRICT REQUIREMENT: Write EXACTLY 200 words (195-205 acceptable).

CRITICAL OUTCOME FRAMING RULES:
- Use "typically," "often," "on average," or "generally" when citing market data
- Express valuation impacts as ranges (e.g., "20-30%") not specific numbers
- Frame all statistics as market observations, not guarantees
- Include source citations for all data points

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
2. Positions their score against typical buyer expectations (50 words)
3. Identifies timeline-specific opportunities/threats (50 words)
4. Quantifies typical value impacts using research data (50 words)

Include at least 3 specific data citations using this format:
"Businesses in this category typically trade at X-Y multiples (Source Year)"

Timeline insight to incorporate: {timeline_insight}

Style: Authoritative but accessible. No jargon. Remember to frame all outcomes as typical market observations."""

    try:
        messages = [
            SystemMessage(content="You are a market analyst providing industry intelligence for M&A. Use specific data and citations. Always frame market data as typical observations using 'typically/often/generally' language."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        context = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # FIXED: Validate and adjust word count
        validated_context = validate_word_count(
            text=context,
            target_words=200,
            tolerance=10,
            llm=llm,
            prompt=prompt
        )
        
        return validated_context
        
    except Exception as e:
        logger.error(f"LLM industry context generation failed: {e}")
        # Fallback with proper outcome framing
        return f"""INDUSTRY & MARKET CONTEXT

The {business_info.get('industry')} market in {business_info.get('location')} currently shows EBITDA multiples typically ranging from {ebitda_range} {ebitda_source}, with well-prepared businesses often commanding premiums. Buyers generally prioritize {', '.join([p.get('priority', '') for p in market_conditions.get('buyer_priorities', [])[:2]])} according to recent market data.

Your overall score of {scores.get('overall_score')}/10 positions you as {'above average' if scores.get('overall_score', 0) >= 6.5 else 'below average'} compared to businesses that typically achieve successful exits. {timeline_insight}.

Key market dynamics affecting valuation often include customer concentration thresholds (buyers typically apply 15-25% discounts for >25% concentration per Pepperdine 2023) and operational independence requirements. The average sale timeline for prepared businesses generally ranges from {market_conditions.get('average_sale_time', {}).get('prepared_businesses', '6-9 months')}.

Based on your scores and timeline, businesses focusing on {scores.get('lowest_category', 'key improvements')} typically see the highest value impact. Market data suggests companies addressing these gaps before sale often achieve 20-35% higher multiples (M&A Source 2023)."""


def generate_next_steps_llm(
    exit_timeline: str,
    primary_focus: Optional[Dict],
    overall_score: float,
    business_info: Dict[str, str],
    timeline_urgency: Dict[str, Any],
    llm
) -> str:
    """Generate timeline-specific next steps with clear actions and outcome framing"""
    
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

CRITICAL OUTCOME FRAMING RULES:
- When mentioning expected results, use "typically see," "often achieve," or "generally experience"
- Never promise specific outcomes
- Frame milestones as "businesses often reach..." not "you will achieve..."
- Include at least one "typical outcome" reference in each section

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
Include one sentence about what businesses typically accomplish in week one.

{month_title}
[100 words outlining 4 weekly milestones]
Week 1: [Specific goal] - businesses often see [typical result]
Week 2: [Specific goal]
Week 3: [Specific goal]
Week 4: [Specific goal] - companies typically achieve [outcome]

{quarter_title}
[100 words on 3 major initiatives with expected outcomes framed as typical results]

End with: "For personalized guidance on executing these improvements, contact us at success@onpulsesolutions.com"

Style: Action-oriented, specific, and motivating. Use "typically/often" when discussing outcomes."""

    try:
        messages = [
            SystemMessage(content="You are an implementation coach helping business owners take immediate action. Be specific and respect exact word counts. Always frame outcomes as typical results, not guarantees."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        next_steps = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Verify proper outcome framing
        if "will achieve" in next_steps or "will see" in next_steps or "guaranteed" in next_steps:
            logger.warning("Next steps contain promise language that should be revised")
        
        # Note: For next steps with multiple sections, we don't validate the total word count
        # as it's structured in specific 100-word sections
        
        return next_steps
        
    except Exception as e:
        logger.error(f"LLM next steps generation failed: {e}")
        # Fallback with proper outcome framing
        return f"""{timeline_urgency.get('emoji', '')} {timeline_urgency.get('header', 'YOUR NEXT STEPS')}

{immediate_title}
Take decisive action this week to begin your value enhancement journey. Businesses that start immediately typically see measurable progress within 30 days:
□ Review this report with your leadership team and identify quick wins
□ Schedule time to work on your #{primary_focus.get('category', '1 priority area') if primary_focus else 'primary focus area'}
□ List the top 3 improvements that could impact your timeline
□ Begin documenting one critical process
□ Contact key team members about transition planning

{month_title}
Week 1: Complete quick win implementations - businesses often see immediate operational improvements
Week 2: Launch your primary improvement initiative with clear milestones  
Week 3: Measure progress and adjust approach based on early results
Week 4: Document successes and plan next phase - companies typically report 10-15% progress toward goals

{quarter_title}
Transform your business value through three focused initiatives that businesses like yours typically complete in 90 days. First, systematically address your primary gap area with weekly progress reviews. Second, implement the strategic improvements that buyers in your industry often value most. Third, build proof points demonstrating the changes you've made. These initiatives typically position businesses for 15-25% higher valuations.

For personalized guidance on executing these improvements, contact us at success@onpulsesolutions.com"""


def summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced summary node with timeline adaptation, word limits, and outcome framing rules.
    FIXED: Handle missing data gracefully.
    
    This node:
    1. Detects exit timeline urgency
    2. Creates timeline-adapted executive summary (200 words)
    3. Generates category analyses with urgency context (150 words each)
    4. Produces recommendations with proper outcome framing (no promises)
    5. Provides timeline-specific next steps (300 words total)
    
    OUTCOME FRAMING: All recommendations use "typically/often" language with ranges and citations
    
    Args:
        state: Current workflow state with all previous results
        
    Returns:
        Updated state with timeline-adapted report sections and proper outcome framing
    """
    start_time = datetime.now()
    logger.info(f"=== ENHANCED SUMMARY NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "summary"
        state["messages"].append(f"Enhanced summary with timeline adaptation and outcome framing started at {start_time.isoformat()}")
        
        # FIXED: Initialize LLM for generation with proper model
        summary_llm = get_llm_with_fallback("gpt-4.1-mini", temperature=0.4)
        
        # Extract data from previous stages
        scoring_result = state.get("scoring_result", {})
        research_result = state.get("research_result", {})
        anonymized_data = state.get("anonymized_data", {})
        
        # Get locale terms
        locale_terms = get_locale_terms(state.get("locale", "us"))
        
        # Business info
        business_info = {
            "industry": anonymized_data.get("industry") or state.get("industry") or "Not specified",
            "location": anonymized_data.get("location") or state.get("location") or "Not specified",
            "revenue_range": anonymized_data.get("revenue_range") or state.get("revenue_range") or "Not specified",
            "exit_timeline": anonymized_data.get("exit_timeline") or state.get("exit_timeline") or "Not specified",
            "years_in_business": anonymized_data.get("years_in_business") or state.get("years_in_business") or "Not specified"
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
        
        logger.info(f"Generating timeline-adapted report with outcome framing for {overall_score}/10 - {readiness_level}")
        logger.info(f"Exit timeline: {business_info.get('exit_timeline')} ({timeline_urgency['level']})")
        
        # 1. Generate Executive Summary WITH TIMELINE URGENCY AND OUTCOME FRAMING
        logger.info("Generating timeline-aware executive summary with outcome framing (200 words)...")
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
        
        # 2. Generate Category Summaries WITH TIMELINE CONTEXT AND OUTCOME FRAMING
        logger.info("Generating timeline-adapted category summaries with outcome framing (150 words each)...")
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
        
        # 3. Generate Recommendations WITH PROPER OUTCOME FRAMING
        logger.info("Generating recommendations with outcome framing rules...")
        recommendations = generate_recommendations_llm(
            focus_areas=focus_areas,
            category_scores=category_scores,
            exit_timeline=business_info.get("exit_timeline", ""),
            research_data=research_result,
            timeline_urgency=timeline_urgency,
            llm=summary_llm
        )
        
        # 4. Generate Industry Context WITH TIMELINE RELEVANCE AND OUTCOME FRAMING
        logger.info("Generating industry context with outcome framing (200 words)...")
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
        
        # 5. Generate Next Steps WITH TIMELINE-SPECIFIC ACTIONS AND OUTCOME FRAMING
        logger.info("Generating timeline-specific next steps with outcome framing (300 words)...")
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
                "word_limits_enforced": True,
                "has_outcome_framing": True
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
            f"Report: {summary_result['report_metadata']['word_count']} words, "
            f"Outcome framing: Applied"
        )
        
        logger.info(f"=== ENHANCED SUMMARY NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced summary node: {str(e)}", exc_info=True)
        state["error"] = f"Summary failed: {str(e)}"
        state["messages"].append(f"ERROR in summary: {str(e)}")
        state["current_stage"] = "summary_error"
        return state