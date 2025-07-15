"""
Pure formatting functions extracted from CrewAI agents.
No tool wrappers, just business logic for report generation.
"""

from typing import Dict, Any, List, Optional
import re


def format_category_title(category: str) -> str:
    """Convert category key to readable title"""
    titles = {
        'owner_dependence': 'Owner Dependence',
        'revenue_quality': 'Revenue Quality & Predictability',
        'financial_readiness': 'Financial Readiness',
        'operational_resilience': 'Operational Resilience',
        'growth_value': 'Growth Potential & Unique Value'
    }
    return titles.get(category, category.replace('_', ' ').title())


def format_score_interpretation(score: float, category: str) -> str:
    """Generate nuanced interpretation of what the score means"""
    if score >= 8.0:
        base = "exceptional and well above buyer expectations"
    elif score >= 6.5:
        base = "solid with some room for improvement"
    elif score >= 4.5:
        base = "below average and needs focused attention"
    else:
        base = "concerning and requires immediate action"
    
    # Add category-specific context
    if category == 'owner_dependence' and score < 4:
        base += ". This level of owner dependence will likely deter most buyers"
    elif category == 'revenue_quality' and score > 7:
        base += ". Your recurring revenue model is highly attractive to buyers"
    elif category == 'financial_readiness' and score < 5:
        base += ". Expect extended due diligence and potential deal delays"
    
    return f"Your score of {score}/10 is {base}"


def format_executive_summary(
    overall_score: float,
    readiness_level: str,
    category_scores: Dict[str, Dict],
    business_info: Dict[str, str],
    focus_areas: Dict[str, Any]
) -> str:
    """Format executive summary section"""
    
    # Get overall interpretation
    if overall_score >= 8.1:
        interpretation = "Your business shows exceptional exit readiness with strong fundamentals across all key areas"
    elif overall_score >= 6.6:
        interpretation = "Your business has a solid foundation with specific areas that, once addressed, will significantly enhance value"
    elif overall_score >= 4.1:
        interpretation = "Your business needs focused improvements but has clear potential for value enhancement"
    else:
        interpretation = "Your business requires substantial preparation, but with dedication can be transformed into an attractive acquisition"
    
    # Identify highest and lowest scores
    if category_scores:
        sorted_scores = sorted(category_scores.items(), key=lambda x: x[1].get('score', 0))
        lowest = sorted_scores[0] if sorted_scores else None
        highest = sorted_scores[-1] if sorted_scores else None
    else:
        lowest = highest = None
    
    # Value proposition
    if overall_score < 6:
        value_increase = "20-40%"
    else:
        value_increase = "15-25%"
    
    # Timeline urgency
    timeline = business_info.get('exit_timeline', 'Not specified')
    if '1-2 years' in timeline or 'Already' in timeline:
        timeline_message = "⚠️  URGENT: Your timeline requires immediate action on critical improvements."
    else:
        timeline_message = "You have time to optimize value before exit."
    
    summary = f"""Thank you for completing the Exit Ready Snapshot assessment. As a {business_info.get('industry', 'business')} owner in {business_info.get('location', 'your region')} with {business_info.get('years_in_business', 'your years')} of experience, you're taking an important step toward maximizing your business value.

OVERALL ASSESSMENT: {overall_score}/10 - {readiness_level}

{interpretation}

KEY FINDINGS:"""
    
    if highest:
        summary += f"""
Your Strongest Area: {format_category_title(highest[0])} ({highest[1].get('score', 0)}/10)
- {highest[1].get('strengths', ['Strong foundation'])[0] if highest[1].get('strengths') else 'Strong foundation'}"""
    
    if lowest:
        summary += f"""
Your Biggest Opportunity: {format_category_title(lowest[0])} ({lowest[1].get('score', 0)}/10)
- {lowest[1].get('gaps', ['Improvement needed'])[0] if lowest[1].get('gaps') else 'Improvement needed'}"""
    
    summary += f"""

VALUE PROPOSITION:
Based on your assessment, your business is currently positioned for a 4-6x EBITDA multiple. With focused improvements in {format_category_title(focus_areas.get('primary', {}).get('category', '')) if focus_areas.get('primary') else 'key areas'}, you could achieve 5-7x - a potential {value_increase} increase in sale value.

YOUR EXIT TIMELINE: {timeline}
{timeline_message}

The path forward is clear: focus on {format_category_title(focus_areas.get('primary', {}).get('category', '')) if focus_areas.get('primary') else 'your highest-impact improvements'} to unlock significant value. Your business has {'strong potential' if overall_score >= 5 else 'clear opportunities'} for enhancement that buyers will reward."""
    
    return summary


def format_category_summary(
    category: str,
    score_data: Dict[str, Any],
    locale_terms: Dict[str, str] = None
) -> str:
    """Format individual category analysis"""
    
    category_title = format_category_title(category)
    score = score_data.get('score', 5.0)
    strengths = score_data.get('strengths', [])
    gaps = score_data.get('gaps', [])
    breakdown = score_data.get('scoring_breakdown', {})
    industry_context = score_data.get('industry_context', {})
    
    # Generate recommendations based on gaps and score
    recommendations = generate_category_recommendations(category, score, gaps, strengths)
    
    summary = f"""{category_title.upper()} ANALYSIS

SCORE: {score}/10

{format_score_interpretation(score, category)}

STRENGTHS WE IDENTIFIED:
{chr(10).join(f'• {s}' for s in strengths[:3]) if strengths else '• Limited strengths identified in current state'}

CRITICAL GAPS:
{chr(10).join(f'• {g}' for g in gaps[:3]) if gaps else '• No critical gaps identified'}

YOUR ACTION PLAN:"""
    
    for i, rec in enumerate(recommendations[:3], 1):
        summary += f"""
{i}. {rec['timeframe'].upper()}: {rec['action']}
   Impact: {rec['impact']}"""
    
    summary += f"""

INDUSTRY BENCHMARK: {industry_context.get('benchmark', 'Industry standard expectations')}

VALUATION IMPACT: {industry_context.get('impact', 'Standard market impact')}

This analysis shows {'significant improvement potential' if score < 6 else 'solid positioning'} in {category_title.lower()}, which is {'critical' if category in ['owner_dependence', 'revenue_quality'] else 'important'} for achieving optimal exit value."""
    
    return summary


def generate_category_recommendations(
    category: str,
    score: float,
    gaps: List[str],
    strengths: List[str]
) -> List[Dict[str, str]]:
    """Generate specific, actionable recommendations based on gaps and score"""
    
    recommendations = []
    
    # Category-specific recommendation logic
    if category == 'owner_dependence':
        if any('certification' in gap.lower() for gap in gaps):
            recommendations.append({
                "timeframe": "30 days",
                "action": "Identify and enroll a senior team member in certification training",
                "impact": "Removes a critical bottleneck for buyers"
            })
        if any('client' in gap.lower() for gap in gaps):
            recommendations.append({
                "timeframe": "90 days",
                "action": "Create a client transition plan introducing key accounts to senior team members",
                "impact": "Reduces relationship risk concerns"
            })
        if score < 4:
            recommendations.append({
                "timeframe": "6 months",
                "action": "Implement a formal delegation program with documented authority levels",
                "impact": "Can improve valuation by 20-30%"
            })
    
    elif category == 'revenue_quality':
        if any('concentration' in gap.lower() for gap in gaps):
            recommendations.append({
                "timeframe": "30 days",
                "action": "Develop a customer diversification strategy targeting 5 new major clients",
                "impact": "Reduces concentration risk discount"
            })
        if any('month-to-month' in gap.lower() for gap in gaps):
            recommendations.append({
                "timeframe": "90 days",
                "action": "Convert top clients to annual contracts with auto-renewal",
                "impact": "Improves revenue predictability score"
            })
        if score < 5:
            recommendations.append({
                "timeframe": "6 months",
                "action": "Implement subscription or retainer model for suitable services",
                "impact": "Increases recurring revenue percentage"
            })
    
    elif category == 'financial_readiness':
        if any('confidence' in gap.lower() for gap in gaps):
            recommendations.append({
                "timeframe": "30 days",
                "action": "Engage a CPA experienced in M&A to review and clean up financials",
                "impact": "Ensures smooth due diligence process"
            })
        if any('margin' in gap.lower() and 'decline' in gap.lower() for gap in gaps):
            recommendations.append({
                "timeframe": "90 days",
                "action": "Conduct margin analysis and implement cost reduction plan",
                "impact": "Improves profitability metrics"
            })
        else:
            recommendations.append({
                "timeframe": "90 days",
                "action": "Prepare 3-year audited financials and monthly management reports",
                "impact": "Builds buyer confidence"
            })
    
    elif category == 'operational_resilience':
        if score < 5:
            recommendations.append({
                "timeframe": "30 days",
                "action": "Document your top 5 critical processes using standard operating procedure templates",
                "impact": "Reduces knowledge transfer risk"
            })
        if any('key person' in gap.lower() for gap in gaps):
            recommendations.append({
                "timeframe": "90 days",
                "action": "Cross-train backup personnel for each critical role",
                "impact": "Eliminates single points of failure"
            })
        else:
            recommendations.append({
                "timeframe": "6 months",
                "action": "Create comprehensive operations manual and training program",
                "impact": "Enables smooth ownership transition"
            })
    
    elif category == 'growth_value':
        if any('quantif' in gap.lower() for gap in gaps):
            recommendations.append({
                "timeframe": "30 days",
                "action": "Create a value proposition document with specific metrics and proof points",
                "impact": "Helps buyers understand premium value"
            })
        if len(strengths) < 2:
            recommendations.append({
                "timeframe": "90 days",
                "action": "Conduct competitive analysis to identify and document unique advantages",
                "impact": "Justifies higher multiples"
            })
        recommendations.append({
            "timeframe": "6 months",
            "action": "Develop and test 2-3 new revenue streams or market expansions",
            "impact": "Demonstrates growth trajectory"
        })
    
    # Ensure we have at least 2 recommendations
    while len(recommendations) < 2:
        recommendations.append({
            "timeframe": "90 days",
            "action": f"Address '{gaps[0] if gaps else 'improvement areas'}'",
            "impact": "Improves buyer confidence"
        })
    
    return recommendations[:3]  # Return top 3


def format_recommendations_section(
    focus_areas: Dict[str, Any],
    category_scores: Dict[str, Dict],
    exit_timeline: str
) -> str:
    """Format the complete recommendations section"""
    
    # Extract focus areas
    primary = focus_areas.get('primary', {})
    secondary = focus_areas.get('secondary', {})
    urgency = focus_areas.get('urgency', 'MODERATE')
    
    # Timeline alert
    if 'Already' in exit_timeline or '1-2' in exit_timeline:
        timeline_alert = f"⚠️  TIMELINE ALERT: {exit_timeline}"
    else:
        timeline_alert = f"EXIT TIMELINE: {exit_timeline}"
    
    # Generate quick wins
    quick_wins = generate_quick_wins(category_scores, primary)
    
    # Generate strategic priorities
    strategic_priorities = generate_strategic_priorities(primary, secondary, category_scores)
    
    # Critical focus area
    critical_focus = format_critical_focus(primary, exit_timeline)
    
    # Resource needs
    resource_needs = estimate_resource_needs(strategic_priorities)
    
    # Expected ROI
    expected_roi = calculate_expected_roi(primary, secondary)
    
    recommendations = f"""YOUR PERSONALIZED ACTION PLAN

{timeline_alert}

QUICK WINS (NEXT 30 DAYS)
These high-impact actions can be implemented immediately:
"""
    
    for i, qw in enumerate(quick_wins[:3], 1):
        recommendations += f"""
{i}. {qw['action']}
   Category: {qw['category']}
   Impact: {qw['impact']}
"""
    
    recommendations += """
STRATEGIC PRIORITIES (3-6 MONTHS)
Major initiatives that will transform your business value:
"""
    
    for i, sp in enumerate(strategic_priorities[:3], 1):
        recommendations += f"""
{i}. {sp['initiative']}
   Timeline: {sp['timeline']}
   Expected Outcome: {sp['expected_outcome']}
   First Step: {sp['first_steps']}
"""
    
    recommendations += f"""
🎯 YOUR CRITICAL FOCUS AREA: {critical_focus['area']}
{'⚠️  THIS IS A VALUE KILLER - MUST ADDRESS IMMEDIATELY' if critical_focus['is_value_killer'] else ''}

WHY THIS MATTERS MOST:
{critical_focus['why_critical']}

TIMELINE FIT: {critical_focus['timeline_alignment']}

THIS WEEK'S ACTIONS:
{chr(10).join(f'□ {action}' for action in critical_focus['first_week_actions'][:3])}

SUCCESS METRICS TO TRACK:
{chr(10).join(f'• {metric}' for metric in critical_focus['success_metrics'][:3])}

IMPLEMENTATION GUIDANCE:
Resource Needs: {resource_needs}
Expected ROI: {expected_roi}

Remember: Consistent execution of these recommendations will position your business for maximum value at exit. Start with your critical focus area TODAY."""
    
    return recommendations


def generate_quick_wins(category_scores: Dict[str, Dict], primary_focus: Dict) -> List[Dict[str, str]]:
    """Generate quick win recommendations"""
    quick_wins = []
    
    # From primary focus area if it has quick actions
    if primary_focus and primary_focus.get('score', 10) < 6:
        quick_wins.append({
            "action": f"Schedule assessment of {format_category_title(primary_focus.get('category', ''))}",
            "category": format_category_title(primary_focus.get('category', '')),
            "impact": "High-impact improvement"
        })
    
    # Add quick wins from low-scoring areas
    for cat_name, cat_data in category_scores.items():
        if len(quick_wins) < 3 and cat_data.get('score', 10) < 6:
            gaps = cat_data.get('gaps', [])
            if gaps:
                quick_wins.append({
                    "action": f"Address: {gaps[0]}",
                    "category": format_category_title(cat_name),
                    "impact": "Quick improvement opportunity"
                })
    
    # Default quick wins if needed
    while len(quick_wins) < 3:
        quick_wins.append({
            "action": "Schedule comprehensive business assessment",
            "category": "General",
            "impact": "Identify additional opportunities"
        })
    
    return quick_wins


def generate_strategic_priorities(primary: Dict, secondary: Dict, category_scores: Dict) -> List[Dict[str, str]]:
    """Generate strategic priority initiatives"""
    priorities = []
    
    if primary:
        priorities.append({
            "initiative": f"Transform {format_category_title(primary.get('category', ''))}",
            "timeline": "6 months",
            "expected_outcome": primary.get('impact', '15% value increase'),
            "first_steps": "Begin detailed assessment and planning"
        })
    
    if secondary and len(priorities) < 3:
        priorities.append({
            "initiative": f"Improve {format_category_title(secondary.get('category', ''))}",
            "timeline": "4-6 months",
            "expected_outcome": "10-15% value increase",
            "first_steps": "Develop improvement roadmap"
        })
    
    # Add third priority
    if len(priorities) < 3:
        for cat_name, cat_data in category_scores.items():
            if cat_name not in [primary.get('category'), secondary.get('category')] and cat_data.get('score', 10) < 7:
                priorities.append({
                    "initiative": f"Enhance {format_category_title(cat_name)}",
                    "timeline": "3-6 months",
                    "expected_outcome": "5-10% value increase",
                    "first_steps": "Create action plan"
                })
                break
    
    return priorities[:3]


def format_critical_focus(primary_focus: Dict, exit_timeline: str) -> Dict[str, Any]:
    """Format critical focus area details"""
    if not primary_focus:
        return {
            "area": "Business Systematization",
            "why_critical": "This area has the highest impact on your exit value",
            "is_value_killer": False,
            "timeline_alignment": "Sufficient time for implementation",
            "first_week_actions": ["Schedule strategic planning session"],
            "success_metrics": ["Track improvement progress"]
        }
    
    category = primary_focus.get('category', '')
    score = primary_focus.get('score', 5)
    
    # First week actions based on category
    first_week_actions = {
        'owner_dependence': [
            "List all tasks only you can do",
            "Identify potential delegates for each task",
            "Schedule meetings with key team members"
        ],
        'revenue_quality': [
            "Analyze customer concentration report",
            "List all month-to-month clients",
            "Draft contract conversion strategy"
        ],
        'financial_readiness': [
            "Gather last 3 years financial statements",
            "List known issues or inconsistencies",
            "Research M&A-experienced CPAs"
        ],
        'operational_resilience': [
            "Identify top 5 critical processes",
            "Download SOP templates",
            "Assign process documentation owners"
        ],
        'growth_value': [
            "List all competitive advantages",
            "Gather proof points and metrics",
            "Research competitor offerings"
        ]
    }
    
    # Success metrics based on category
    success_metrics = {
        'owner_dependence': [
            "Days business can operate without you",
            "Number of decisions delegated monthly",
            "Percentage of clients who know your team"
        ],
        'revenue_quality': [
            "Percentage of revenue under contract",
            "Customer concentration percentage",
            "Average contract length"
        ],
        'financial_readiness': [
            "Clean monthly P&L production time",
            "Number of audit adjustments",
            "Margin trend (monthly)"
        ],
        'operational_resilience': [
            "Number of documented processes",
            "Cross-trained employees per role",
            "Process deviation incidents"
        ],
        'growth_value': [
            "Quantified value propositions",
            "Win rate vs competitors",
            "Premium pricing ability"
        ]
    }
    
    # Timeline alignment
    if "Already" in exit_timeline:
        timeline_alignment = "Must show improvement plan to buyers"
    elif "1-2 years" in exit_timeline:
        timeline_alignment = "Achievable with immediate action"
    else:
        timeline_alignment = "Sufficient time for full implementation"
    
    return {
        "area": format_category_title(category),
        "why_critical": f"Lowest score at {score}/10 - biggest value improvement opportunity",
        "is_value_killer": score < 4,
        "timeline_alignment": timeline_alignment,
        "first_week_actions": first_week_actions.get(category, ["Schedule strategic planning session"]),
        "success_metrics": success_metrics.get(category, ["Track improvement progress"])
    }


def estimate_resource_needs(priorities: List[Dict]) -> str:
    """Estimate resource requirements"""
    total_months = sum(6 for p in priorities)  # Assume 6 months average
    
    if total_months <= 6:
        return "Low: Can be managed with existing team and minimal outside help"
    elif total_months <= 12:
        return "Moderate: May need part-time consultant or dedicated internal resource"
    else:
        return "Significant: Consider full-time project manager or consulting team"


def calculate_expected_roi(primary: Dict, secondary: Dict) -> str:
    """Calculate expected ROI from improvements"""
    if not primary:
        return "Significant value increase expected"
    
    # Simple calculation based on impact estimates
    primary_impact = 20 if primary.get('score', 5) < 4 else 15
    secondary_impact = 10 if secondary and secondary.get('score', 5) < 5 else 5
    
    total = primary_impact + (secondary_impact * 0.7)
    
    if total >= 25:
        return f"High: Potential {total:.0f}% increase in business value"
    elif total >= 15:
        return f"Strong: Potential {total:.0f}% increase in business value"
    else:
        return f"Moderate: Potential {total:.0f}% increase in business value"


def format_industry_context(
    research_findings: Dict[str, Any],
    business_info: Dict[str, str],
    scores: Dict[str, Any]
) -> str:
    """Format industry and market context section"""
    
    industry = business_info.get('industry', 'Your Industry')
    location = business_info.get('location', 'Your Region')
    revenue_range = business_info.get('revenue_range', 'Not specified')
    
    # Extract benchmarks
    benchmarks = research_findings.get('valuation_benchmarks', {})
    conditions = research_findings.get('market_conditions', {})
    
    # Competitive position
    overall_score = scores.get('overall_score', 5.0)
    if overall_score >= 7.5:
        position = "Top quartile - attractive to multiple buyers"
    elif overall_score >= 6.0:
        position = "Above average - competitive with improvements"
    elif overall_score >= 4.5:
        position = "Below average - needs work to compete"
    else:
        position = "Significant gaps - major improvements needed"
    
    context = f"""INDUSTRY & MARKET CONTEXT

YOUR MARKET: {industry} in {location}
REVENUE RANGE: {revenue_range}

CURRENT MARKET CONDITIONS:

Valuation Benchmarks:
- EBITDA Multiples: {benchmarks.get('base_EBITDA', '4-6x')}
- Revenue Multiples: {benchmarks.get('base_revenue', '1.2-2.0x')}
- Premium for 60%+ recurring revenue: {benchmarks.get('recurring_premium', '1-2x additional')}

Buyer Priorities (in order):
1. Recurring revenue models
2. Systematic operations
3. Growth potential

Market Dynamics:
- Average Time to Sell: {conditions.get('average_sale_time', '9-12 months')}
- Key Trend: Technology integration and remote capabilities increasingly valued

YOUR COMPETITIVE POSITION:

Overall Position: {position}

Strengths vs Market:
{chr(10).join(f'• {s}' for s in identify_market_strengths(scores)[:3])}

Gaps vs Market Expectations:
{chr(10).join(f'• {g}' for g in identify_market_gaps(scores)[:3])}

VALUE ENHANCEMENT OPPORTUNITY:
{calculate_enhancement_potential(scores)}

KEY TAKEAWAY: {'Your business is well-positioned for a premium exit with targeted improvements.' if overall_score >= 6 else 'Significant value can be unlocked through systematic improvements.'}"""
    
    return context


def identify_market_strengths(scores: Dict[str, Any]) -> List[str]:
    """Identify strengths relative to market"""
    strengths = []
    
    category_scores = scores.get('category_scores', {})
    
    if category_scores.get('revenue_quality', {}).get('score', 0) > 7:
        strengths.append("Revenue quality exceeds typical SME standards")
    
    if category_scores.get('operational_resilience', {}).get('score', 0) > 7:
        strengths.append("Documentation and systems above market average")
    
    if category_scores.get('financial_readiness', {}).get('score', 0) > 7:
        strengths.append("Financial systems meet institutional buyer standards")
    
    return strengths if strengths else ["Building toward market standards"]


def identify_market_gaps(scores: Dict[str, Any]) -> List[str]:
    """Identify gaps relative to market expectations"""
    gaps = []
    
    category_scores = scores.get('category_scores', {})
    
    if category_scores.get('owner_dependence', {}).get('score', 0) < 5:
        gaps.append("Owner dependence exceeds buyer comfort levels")
    
    if category_scores.get('revenue_quality', {}).get('score', 0) < 5:
        gaps.append("Revenue concentration above market risk thresholds")
    
    if category_scores.get('growth_value', {}).get('score', 0) < 5:
        gaps.append("Limited differentiation vs market alternatives")
    
    return gaps if gaps else ["Minor gaps vs market leaders"]


def calculate_enhancement_potential(scores: Dict[str, Any]) -> str:
    """Calculate value enhancement potential"""
    overall = scores.get('overall_score', 5.0)
    gap_to_premium = 8.0 - overall
    
    if gap_to_premium <= 1:
        return "Limited: Already near premium valuations (5-10% upside)"
    elif gap_to_premium <= 3:
        return "Moderate: Clear path to 15-25% value increase"
    else:
        return "High: Potential for 30-50% value increase with focused execution"


def format_next_steps(exit_timeline: str, primary_focus: Optional[Dict] = None) -> str:
    """Format next steps section"""
    
    # Timeline-based urgency
    if "Already" in exit_timeline:
        urgency = "IMMEDIATE ACTION REQUIRED"
        timeline_note = "Given your active discussions, focus on quick wins that can be communicated to buyers."
    elif "6 months" in exit_timeline:
        urgency = "URGENT TIMELINE"
        timeline_note = "With only 6 months, prioritize high-impact improvements that can be completed quickly."
    elif "1-2 years" in exit_timeline:
        urgency = "FOCUSED EXECUTION NEEDED"
        timeline_note = "Your 1-2 year timeline allows for meaningful improvements if you start now."
    else:
        urgency = "STRATEGIC OPPORTUNITY"
        timeline_note = "You have time to maximize value through systematic improvements."
    
    next_steps = f"""NEXT STEPS

{urgency}
{timeline_note}

1. IMMEDIATE ACTION (This Week):
   □ Review this report with your leadership team
   □ Commit to your primary focus area{f': {format_category_title(primary_focus.get("category"))}' if primary_focus else ''}
   □ Schedule time for your first week actions

2. SHORT TERM (Next 30 Days):
   □ Complete all Quick Win initiatives
   □ Begin implementing your Critical Focus Area improvements
   □ Track progress using the success metrics provided

3. STRATEGIC PLANNING (Next 90 Days):
   □ Launch your Strategic Priority initiatives
   □ Consider professional guidance for complex improvements
   □ Re-assess progress quarterly

PROFESSIONAL SUPPORT OPTIONS:
- Exit Value Growth Plan: Deep-dive analysis with personalized roadmap
- Implementation Support: Hands-on help with critical improvements
- M&A Advisory: When you're ready for the exit process

Remember: Every improvement you make increases your business value and exit options.

Contact us at success@onpulsesolutions.com to discuss your personalized Exit Value Growth Plan."""
    
    return next_steps


def structure_final_report(
    executive_summary: str,
    category_summaries: Dict[str, str],
    recommendations: str,
    industry_context: str,
    next_steps: str,
    overall_score: float,
    readiness_level: str
) -> str:
    """Structure all components into final report format"""
    
    report = f"""EXIT READY SNAPSHOT ASSESSMENT REPORT

{'='*60}

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
        report += f"{summary}\n\n{'='*60}\n\n"
    
    report += f"""{recommendations}

{'='*60}

{industry_context}

{'='*60}

{next_steps}

{'='*60}

CONFIDENTIAL BUSINESS ASSESSMENT
Prepared by: On Pulse Solutions
Report Date: [REPORT_DATE]
Valid for: 90 days

This report contains proprietary analysis and recommendations specific to your business. 
The insights and strategies outlined are based on your assessment responses and current market conditions.

© On Pulse Solutions - Exit Ready Snapshot"""
    
    return report