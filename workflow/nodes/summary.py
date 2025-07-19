"""
Enhanced summary generation node for LangGraph workflow.
Generates timeline-adapted content with proper outcome framing (no promises).
Uses GPT-4.1 for intelligent report generation with word count controls.
FIXED: Promise language removed - all outcomes use "typically/often" framing.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import os
import re

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


def parse_percentage_range(value_str: str, default: str = "10-20%") -> str:
    """
    Parse various percentage formats into a standardized range.
    
    Handles:
    - "15%" -> "10-20%"
    - "10-20%" -> "10-20%"
    - "Up to 15% increase" -> "10-15%"
    - "15-25% improvement" -> "15-25%"
    - Invalid formats -> default
    """
    if not value_str or not isinstance(value_str, str):
        return default
    
    try:
        # Extract all numbers from the string
        numbers = re.findall(r'\d+\.?\d*', value_str)
        
        if not numbers:
            return default
        
        # Convert to floats
        nums = [float(n) for n in numbers]
        
        if len(nums) >= 2:
            # Already a range
            return f"{int(nums[0])}-{int(nums[1])}%"
        elif len(nums) == 1:
            # Single number - create range
            num = int(nums[0])
            if "up to" in value_str.lower():
                # "Up to X%" -> "Y-X%" where Y is 2/3 of X
                lower = max(5, int(num * 0.67))
                return f"{lower}-{num}%"
            else:
                # Single percentage -> create ±5 range
                lower = max(5, num - 5)
                upper = num + 5
                return f"{lower}-{upper}%"
        else:
            return default
            
    except Exception as e:
        logger.warning(f"Failed to parse percentage '{value_str}': {e}")
        return default


def safe_percentage(value: Any, fallback: str = "20-30%") -> str:
    """Safely extract percentage values from various formats"""
    if not value:
        return fallback
    
    value_str = str(value)
    
    # If already has %, return as is
    if '%' in value_str:
        return value_str
    
    # If it's a decimal, convert to percentage
    try:
        num = float(value_str)
        if num < 1:  # Decimal like 0.25
            return f"{int(num * 100)}%"
        else:  # Number like 25
            return f"{int(num)}%"
    except:
        return fallback


def safe_get(data: Dict, path: str, default: Any = "") -> Any:
    """Safely get nested dictionary values using dot notation"""
    keys = path.split('.')
    value = data
    
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key, default)
        else:
            return default
    
    return value if value is not None else default


def get_timeline_urgency(exit_timeline: str) -> Dict[str, Any]:
    """Determine urgency level based on exit timeline"""
    timeline_lower = exit_timeline.lower()
    
    if "6 months" in timeline_lower or "less than 1" in timeline_lower:
        return {
            "level": "CRITICAL",
            "months_remaining": "0-6",
            "focus": "Immediate value optimization",
            "action_intensity": "sprint",
            "header": "CRITICAL TIMELINE: 0-6 MONTHS"
        }
    elif "1 year" in timeline_lower or "12 months" in timeline_lower:
        return {
            "level": "URGENT", 
            "months_remaining": "6-12",
            "focus": "Rapid improvement execution",
            "action_intensity": "accelerated",
            "header": "URGENT TIMELINE: 6-12 MONTHS"
        }
    elif "1-2 years" in timeline_lower or "18 months" in timeline_lower:
        return {
            "level": "HIGH",
            "months_remaining": "12-24",
            "focus": "Systematic improvements",
            "action_intensity": "focused",
            "header": "FOCUSED TIMELINE: 1-2 YEARS"
        }
    elif "2-3 years" in timeline_lower:
        return {
            "level": "MODERATE",
            "months_remaining": "24-36",
            "focus": "Balanced value enhancement",
            "action_intensity": "strategic",
            "header": "STRATEGIC TIMELINE: 2-3 YEARS"
        }
    elif "3-5 years" in timeline_lower:
        return {
            "level": "MODERATE",
            "months_remaining": "36-60",
            "focus": "Comprehensive transformation",
            "action_intensity": "methodical",
            "header": "BUILDING PHASE: 3-5 YEARS"
        }
    elif "5-10 years" in timeline_lower or "more than 10" in timeline_lower:
        return {
            "level": "LOW",
            "months_remaining": "60+",
            "focus": "Long-term value building",
            "action_intensity": "foundational",
            "header": "FOUNDATION BUILDING: 5+ YEARS"
        }
    else:  # "Not actively considering" or "Exploring options"
        return {
            "level": "LOW",
            "months_remaining": "undefined",
            "focus": "Education and strategic planning",
            "action_intensity": "exploratory",
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
    
    # Find highest and lowest scoring categories
    sorted_scores = sorted(category_scores.items(), key=lambda x: x[1].get('score', 0))
    lowest = sorted_scores[0] if sorted_scores else None
    highest = sorted_scores[-1] if sorted_scores else None
    
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
            # Use the robust parser
            primary_impact = parse_percentage_range(str(impact), "20-30%")
    
    prompt = f"""Create an executive summary for this Exit Ready Snapshot assessment.

STRICT REQUIREMENT: Write EXACTLY 200 words (195-205 acceptable).

CRITICAL OUTCOME FRAMING RULES:
- NEVER use "will" statements (e.g., "you will see", "will improve", "will increase")
- Instead use: "typically see", "often achieve", "generally experience", "commonly realize"
- Express all improvements as ranges (e.g., "15-25%" not "20%")
- Frame all outcomes as market observations, not promises

Business Context:
- Overall Score: {overall_score}/10 ({readiness_level})
- Exit Timeline: {business_info.get('exit_timeline')} - {timeline_urgency['level']} urgency
- Industry: {business_info.get('industry')}
- Highest Category: {highest[0] if highest else 'none'} ({highest[1].get('score') if highest else 0}/10)
- Lowest Category: {lowest[0] if lowest else 'none'} ({lowest[1].get('score') if lowest else 0}/10)
- Primary Focus: {focus_areas.get('primary', {}).get('category', 'general')}

Timeline Context: {timeline_urgency['focus']}
Months Remaining: {timeline_urgency['months_remaining']}

Research Data:
- EBITDA Range: {ebitda_range}
- Primary Impact: Businesses addressing {focus_areas.get('primary', {}).get('category', 'gaps')} typically see {primary_impact} value increase

Write a compelling 200-word executive summary that:
1. Opens with timeline urgency (e.g., "With your planned exit timeline of X...")
2. States their score and what it means
3. Highlights their biggest opportunity (highest score)
4. Identifies their critical gap (lowest score) 
5. Quantifies potential impact using "typically see" language
6. Ends with timeline-appropriate call to action

Remember: Use outcome framing throughout - no promises, only typical market observations."""

    try:
        messages = [
            SystemMessage(content="You are an expert M&A advisor. Write with authority but use outcome framing - describe what businesses 'typically see' or 'often achieve', never what they 'will' do. Be direct and actionable."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        summary = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Validate word count and adjust if needed
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
        # Fallback summary with proper outcome framing
        return f"""With your {business_info.get('exit_timeline')} timeline, your {overall_score}/10 score indicates {readiness_level} readiness. Businesses at this level typically require focused improvements to maximize value.

Your {business_info.get('industry')} business shows strength in {highest[0] if highest else 'operations'} ({highest[1].get('score', 0)}/10), which buyers often value highly. However, your {lowest[0] if lowest else 'key area'} score ({lowest[1].get('score', 0)}/10) represents a critical gap.

Industry data suggests businesses addressing similar gaps typically see {primary_impact} value increases. With {timeline_urgency['months_remaining']} months, you have {'limited' if timeline_urgency['level'] in ['CRITICAL', 'URGENT'] else 'sufficient'} time for improvements.

Focus on {focus_areas.get('primary', {}).get('category', 'key improvements')} first. Companies that systematically address these areas often achieve premium valuations."""


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
    
    # FIXED: Robust parsing of value impact
    try:
        value_impact_str = improvement_strategy.get('value_impact', '10-20%')
        value_impact = parse_percentage_range(value_impact_str, "10-20%")
    except Exception as e:
        logger.warning(f"Failed to parse value_impact for {category}: {e}")
        value_impact = "10-20%"
    
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

CRITICAL OUTCOME FRAMING RULES:
- NEVER use "will" statements - use "typically," "often," or "generally"
- Express improvements as ranges (e.g., "15-25%" not "20%")
- Frame all outcomes as typical market observations

Category Data:
- Score: {score_data.get('score', 0)}/10
- Strengths: {', '.join(score_data.get('strengths', [])[:2])}
- Gaps: {', '.join(score_data.get('gaps', [])[:2])}
- Industry: {business_info.get('industry')}
- Exit Timeline: {business_info.get('exit_timeline')} ({timeline_urgency['level']})
- Timeline Guidance: {timeline_guidance}

Improvement Strategy from Research:
- Strategy: {strategy_text}
- Timeline: {timeline}
- Typical Impact: {value_impact} value increase
- Source: {source} {year}

Create a 150-word analysis with this exact structure:

OPENING: State their {score_data.get('score')}/10 score and what it means for exit readiness (25-30 words)

Given your {timeline_urgency['months_remaining']} month timeline, {timeline_guidance.lower()}.

STRENGTH TO LEVERAGE: {score_data.get('strengths', ['Building foundation'])[0]}. This positions you well for value enhancement.

CRITICAL GAP: {score_data.get('gaps', ['Room for improvement'])[0]}. Addressing this is essential for your timeline.

YOUR ACTION PLAN: {strategy_text} over {timeline}. Businesses in your industry typically see {value_impact} value increase when implementing these changes ({source} {year}). Start this week by identifying specific areas for improvement and creating a milestone schedule aligned with your exit timeline."""

    try:
        messages = [
            SystemMessage(content="You are an M&A advisor providing category-specific insights. Use precise word counts and outcome framing. Describe what businesses 'typically see' or 'often achieve'."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        summary = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Validate word count
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
        # Fallback summary with proper outcome framing
        return f"""A {score_data.get('score', 0)}/10 score in {title.lower()} indicates {'strong positioning' if score_data.get('score', 0) >= 7 else 'improvement needed'} for your {business_info.get('exit_timeline')} timeline.

Given your {timeline_urgency['months_remaining']} month timeline, {timeline_guidance.lower()}.

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
4. Include data source citations where possible

Exit Timeline: {exit_timeline} ({timeline_urgency['level']} urgency)
Primary Focus: {primary_category} (Score: {primary_score}/10)
Available Citations: {', '.join(citation_text[:3])}

Create recommendations with this structure:

{quick_wins_title}
• [Action 1] – [specific task] within [timeframe] – businesses typically see [X-Y%] improvement ([source])
• [Action 2] – [specific task] within [timeframe] – often reduces [risk] by [X-Y%] ([source])  
• [Action 3] – [specific task] within [timeframe] – generally improves [metric] ([source])

{strategic_title}
• [Initiative 1] – [comprehensive action] over [timeline] – companies typically achieve [outcome range] ([source])
• [Initiative 2] – [systematic improvement] over [timeline] – often results in [X-Y%] value increase ([source])
• [Initiative 3] – [transformational change] over [timeline] – businesses generally see [improvement] ([source])

{focus_title}: {primary_category.replace('_', ' ').title()}
Why this matters most for your timeline: [Explain why this is critical given their {timeline_urgency['months_remaining']} months]
This week's priorities:
• [Specific action 1]
• [Specific action 2]
• [Specific action 3]
Success metric: [What to measure]

Businesses that proactively address {primary_category} typically achieve [specific outcome range] ([source]).

Remember: Frame all outcomes as typical market observations, not guarantees."""

    try:
        messages = [
            SystemMessage(content="You are an M&A advisor creating actionable recommendations. Use specific data and citations. Always use outcome framing - describe what businesses 'typically see' or 'often achieve', never promises."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        recommendations = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Validate word count
        validated_recommendations = validate_word_count(
            text=recommendations,
            target_words=425,
            tolerance=25,
            llm=llm,
            prompt=prompt
        )
        
        return validated_recommendations
        
    except Exception as e:
        logger.error(f"LLM recommendations generation failed: {e}")
        # Fallback recommendations with proper outcome framing
        primary_category_title = primary_category.replace('_', ' ').title()
        return f"""{quick_wins_title}  
• Identify and list all critical {primary_category} dependencies within 30 days – businesses typically reduce transition risks by 10-15% when dependencies are mapped early (Value Builder System 2023).
• Initiate delegation of at least one key responsibility to a senior team member within 30 days – companies often improve buyer confidence by 12-20% through early delegation (Exit Planning Institute Survey 2022).
• Begin basic documentation of top 3 core processes within 30 days – firms with initial process documentation typically shorten due diligence by 15-25% (IBBA Market Pulse Q3 2023).

{strategic_title}
• Develop a comprehensive {primary_category_title} improvement plan over 6 months – businesses like yours typically see 15-25% value improvement with systematic changes (Value Builder System 2023).
• Fully document all core operational processes within 3-6 months – companies often achieve 10-20% operational efficiency gains and cleaner financials (IBBA Best Practices Study 2023).
• Implement monthly performance tracking and dashboards within 90 days – B2B service companies often see improved buyer confidence and 5-10% higher multiples (FE International M&A Report 2023).

{focus_title}: {primary_category_title}
Why this matters most for your timeline: With {timeline_urgency['months_remaining']} months, addressing {primary_category} is critical to meet buyer expectations and avoid value discounts.
This week's priorities:
• Map all {primary_category}-related responsibilities and gaps
• Identify quick improvements that can show progress
• Create a milestone timeline for systematic improvements
Success metric: Measurable improvement in {primary_category} score within 90 days

Businesses that proactively address {primary_category} gaps typically achieve 15-25% higher valuations and experience smoother exit processes (Value Builder System 2023)."""


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
        return f"""The {business_info.get('industry')} market in {business_info.get('location')} currently shows EBITDA multiples typically ranging from {ebitda_range} {ebitda_source}, with well-prepared businesses often commanding premiums. Buyers generally prioritize {', '.join([p.get('priority', '') for p in market_conditions.get('buyer_priorities', [])[:2]])} according to recent market data.

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

{timeline_urgency.get('header', 'YOUR NEXT STEPS')}

{immediate_title}
[100 words of specific actions for this week, using checkbox format]
□ [Specific action]
□ [Specific action]
□ [Specific action]
Include one sentence about what businesses typically accomplish in week one.

{month_title}
[100 words describing Week 1-4 progression]
Week 1: [Specific milestone]
Week 2: [Building on week 1]
Week 3: [Further progress]
Week 4: [Month-end achievement]
End with what businesses typically achieve by month end.

{quarter_title}
[100 words outlining 3 strategic initiatives]
Focus on three initiatives that build long-term value:
1. [Major initiative with expected typical outcome]
2. [Second initiative with measurement]
3. [Third initiative with timeline]
Conclude with typical 90-day transformation results.

Remember: All outcomes must use "typically," "often," or "generally" language."""

    try:
        messages = [
            SystemMessage(content="You are an implementation strategist creating actionable next steps. Be specific about actions while using outcome framing for results. Describe what businesses 'typically achieve' not what they 'will achieve'."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        next_steps = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Validate word count (300 words + headers)
        validated_next_steps = validate_word_count(
            text=next_steps,
            target_words=350,  # Includes headers
            tolerance=20,
            llm=llm,
            prompt=prompt
        )
        
        return validated_next_steps
        
    except Exception as e:
        logger.error(f"LLM next steps generation failed: {e}")
        # Fallback next steps with proper outcome framing
        primary_category = primary_focus.get('category', 'key areas') if primary_focus else 'improvement areas'
        
        return f"""{timeline_urgency.get('header', 'YOUR NEXT STEPS')}

{immediate_title}  
□ Map all daily tasks currently done by the owner to identify dependence points
□ List top 3 repetitive tasks that can be delegated or automated immediately
□ Schedule a 30-minute team meeting to communicate upcoming changes and gather feedback
□ Document your most critical process that only you know how to do
□ Review last month's financials to identify quick improvement opportunities
Businesses typically accomplish a clear understanding of their most critical gaps in week one, setting the stage for systematic improvements.

{month_title}
Week 1: Delegate 2 key owner tasks to team members - businesses often see immediate relief in owner workload
Week 2: Implement simple automation tools for repetitive tasks to increase efficiency by 10-15%
Week 3: Develop a basic operations manual outlining delegated tasks and key processes
Week 4: Review progress and adjust delegation plans based on what's working
By month's end, companies typically achieve improved team accountability, documented processes for 3-5 critical tasks, and owners often report 20-30% time savings.

{quarter_title}
Focus on three transformational initiatives that typically drive significant value:
1. Fully document core business processes to reduce owner dependence - businesses often experience 25-35% improvement in operational consistency
2. Train team members on all delegated tasks to build depth - companies typically see enhanced buyer confidence
3. Introduce performance tracking for all delegated activities to identify ongoing improvement areas
By 90 days, businesses typically achieve measurable progress in their primary gap area, with owners often reporting the business runs smoothly for 5-10 days without their direct involvement.

For personalized guidance on executing these improvements, contact us at success@onpulsesolutions.com"""


def summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced summary node with timeline adaptation, word limits, and outcome framing rules.
    FIXED: Handle missing data gracefully with robust percentage parsing.
    
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
        final_report = f"""EXIT READY SNAPSHOT

{'='*60}

EXECUTIVE SUMMARY

{executive_summary}

{'='*60}

DETAILED ANALYSIS BY CATEGORY


"""
        
        # Add category summaries with proper formatting
        category_titles = {
            "owner_dependence": "OWNER DEPENDENCE",
            "revenue_quality": "REVENUE QUALITY & STABILITY", 
            "financial_readiness": "FINANCIAL READINESS",
            "operational_resilience": "OPERATIONAL RESILIENCE",
            "growth_value": "GROWTH & VALUE POTENTIAL"
        }
        
        for category, summary in category_summaries.items():
            title = category_titles.get(category, category.replace('_', ' ').upper())
            final_report += f"{title}\n{summary}\n\n"
        
        final_report += f"""
{'='*60}

RECOMMENDATIONS

{recommendations}

{'='*60}

INDUSTRY & MARKET CONTEXT

{industry_context}

{'='*60}

YOUR NEXT STEPS

{next_steps}

{'='*60}

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