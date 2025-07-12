from crewai import Agent
from crewai.tools import tool
from typing import Dict, Any, List
import logging
import json
import re

logger = logging.getLogger(__name__)

@tool("generate_category_summary")
def generate_category_summary(category_data: str) -> str:
    """
    Generate a comprehensive 150-200 word summary for a specific scoring category.
    """
    try:
        data = json.loads(category_data)
        category = data.get('category', '')
        score_data = data.get('score_data', {})
        industry_context = data.get('industry_context', {})
        locale_terms = data.get('locale_terms', {})
        
        # Structure the summary components
        summary_structure = {
            "category": category,
            "category_title": format_category_title(category),
            "score": score_data.get('score', 5.0),
            "score_interpretation": interpret_score_meaning(
                score_data.get('score', 5.0),
                category,
                industry_context
            ),
            "strengths": score_data.get('strengths', []),
            "gaps": score_data.get('gaps', []),
            "industry_benchmark": score_data.get('industry_context', {}).get('benchmark', ''),
            "impact": score_data.get('industry_context', {}).get('impact', ''),
            "improvement_timeline": score_data.get('improvement_potential', {}).get('timeline', '6-9 months'),
            "improvement_impact": score_data.get('improvement_potential', {}).get('impact', '10-15% value increase'),
            "specific_recommendations": generate_category_recommendations(
                category,
                score_data.get('score', 5.0),
                score_data.get('gaps', []),
                score_data.get('strengths', [])
            )
        }
        
        return json.dumps(summary_structure)
        
    except Exception as e:
        logger.error(f"Error generating category summary: {str(e)}")
        return json.dumps({"error": str(e)})

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

def interpret_score_meaning(score: float, category: str, industry_context: Dict) -> str:
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

def generate_category_recommendations(category: str, score: float, gaps: List[str], strengths: List[str]) -> List[Dict[str, str]]:
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
    
    # Ensure we have at least 2 recommendations
    while len(recommendations) < 2:
        recommendations.append({
            "timeframe": "90 days",
            "action": f"Address '{gaps[0] if gaps else 'improvement areas'}'",
            "impact": "Improves buyer confidence"
        })
    
    return recommendations[:3]  # Return top 3

@tool("create_executive_summary")
def create_executive_summary(assessment_data: str) -> str:
    """
    Create a compelling 200-250 word executive summary that captures the key insights.
    """
    try:
        data = json.loads(assessment_data)
        overall_score = data.get('overall_score', 5.0)
        readiness_level = data.get('readiness_level', 'Needs Work')
        category_scores = data.get('category_scores', {})
        focus_areas = data.get('focus_areas', {})
        industry_context = data.get('industry_context', {})
        business_info = data.get('business_info', {})
        
        # Identify key insights
        highest_score = max(category_scores.items(), key=lambda x: x[1].get('score', 0)) if category_scores else None
        lowest_score = min(category_scores.items(), key=lambda x: x[1].get('score', 10)) if category_scores else None
        primary_focus = focus_areas.get('primary_focus', {})
        
        # Value proposition calculation
        current_multiple = industry_context.get('current_multiple_estimate', '4-6x')
        potential_multiple = industry_context.get('improved_multiple_estimate', '5-7x')
        
        # Structure for LLM to expand
        summary_structure = {
            "opening_context": {
                "industry": business_info.get('industry', 'your industry'),
                "location": business_info.get('location', 'your region'),
                "years_in_business": business_info.get('years_in_business', ''),
                "exit_timeline": business_info.get('exit_timeline', '')
            },
            "overall_assessment": {
                "score": overall_score,
                "readiness_level": readiness_level,
                "score_meaning": get_overall_score_interpretation(overall_score)
            },
            "key_findings": {
                "strongest_area": {
                    "category": highest_score[0] if highest_score else '',
                    "score": highest_score[1].get('score', 0) if highest_score else 0,
                    "significance": highest_score[1].get('strengths', [''])[0] if highest_score else ''
                },
                "weakest_area": {
                    "category": lowest_score[0] if lowest_score else '',
                    "score": lowest_score[1].get('score', 10) if lowest_score else 10,
                    "impact": lowest_score[1].get('gaps', [''])[0] if lowest_score else ''
                },
                "critical_insight": primary_focus.get('reasoning', '') if primary_focus else ''
            },
            "value_proposition": {
                "current_state": f"Currently positioned for {current_multiple} EBITDA multiple",
                "potential_state": f"Could achieve {potential_multiple} with improvements",
                "key_lever": primary_focus.get('category', '') if primary_focus else ''
            },
            "call_to_action": {
                "timeline": business_info.get('exit_timeline', ''),
                "urgency": "high" if "1-2 years" in business_info.get('exit_timeline', '') else "moderate"
            }
        }
        
        return json.dumps(summary_structure)
        
    except Exception as e:
        logger.error(f"Error creating executive summary: {str(e)}")
        return json.dumps({"error": str(e)})

def get_overall_score_interpretation(score: float) -> str:
    """Provide nuanced interpretation of overall score"""
    if score >= 8.1:
        return "Your business shows exceptional exit readiness with strong fundamentals across all key areas"
    elif score >= 6.6:
        return "Your business has a solid foundation with specific areas that, once addressed, will significantly enhance value"
    elif score >= 4.1:
        return "Your business needs focused improvements but has clear potential for value enhancement"
    else:
        return "Your business requires substantial preparation, but with dedication can be transformed into an attractive acquisition"

@tool("generate_recommendations")
def generate_recommendations(full_assessment: str) -> str:
    """
    Generate comprehensive recommendations section with Quick Wins, Strategic Priorities, and Critical Focus.
    """
    try:
        data = json.loads(full_assessment)
        focus_areas = data.get('focus_areas', {})
        category_scores = data.get('category_scores', {})
        exit_timeline = data.get('business_info', {}).get('exit_timeline', '')
        
        # Extract focus areas
        primary = focus_areas.get('primary_focus', {})
        secondary = focus_areas.get('secondary_focus', {})
        tertiary = focus_areas.get('tertiary_focus', {})
        
        # Generate Quick Wins (30-day actions)
        quick_wins = []
        
        # From primary focus area
        if primary and primary.get('is_quick_win'):
            quick_actions = primary.get('quick_actions', [])
            for action in quick_actions[:2]:
                quick_wins.append({
                    "action": action,
                    "category": format_category_title(primary.get('category', '')),
                    "impact": "High-impact improvement"
                })
        
        # Add quick wins from other areas
        for cat_name, cat_data in category_scores.items():
            if len(quick_wins) < 3:
                gaps = cat_data.get('gaps', [])
                if gaps and cat_data.get('score', 10) < 6:
                    quick_wins.append({
                        "action": f"Address: {gaps[0]}",
                        "category": format_category_title(cat_name),
                        "impact": "Quick improvement opportunity"
                    })
        
        # Ensure we have 3 quick wins
        while len(quick_wins) < 3:
            quick_wins.append({
                "action": "Schedule comprehensive business assessment",
                "category": "General",
                "impact": "Identify additional opportunities"
            })
        
        # Generate Strategic Priorities (3-6 month initiatives)
        strategic_priorities = []
        
        # Primary focus as first priority
        if primary:
            strategic_priorities.append({
                "initiative": f"Transform {format_category_title(primary.get('category', ''))}",
                "description": primary.get('reasoning', ''),
                "timeline": f"{primary.get('typical_timeline_months', 6)} months",
                "expected_outcome": primary.get('expected_impact', '15% value increase'),
                "first_steps": primary.get('quick_actions', ['Begin assessment'])[0] if primary.get('quick_actions') else 'Begin assessment'
            })
        
        # Add secondary focus
        if secondary and len(strategic_priorities) < 3:
            strategic_priorities.append({
                "initiative": f"Improve {format_category_title(secondary.get('category', ''))}",
                "description": secondary.get('reasoning', ''),
                "timeline": f"{secondary.get('typical_timeline_months', 6)} months",
                "expected_outcome": secondary.get('expected_impact', '10% value increase'),
                "first_steps": secondary.get('quick_actions', ['Develop plan'])[0] if secondary.get('quick_actions') else 'Develop plan'
            })
        
        # Add tertiary or other important areas
        if tertiary and len(strategic_priorities) < 3:
            strategic_priorities.append({
                "initiative": f"Enhance {format_category_title(tertiary.get('category', ''))}",
                "description": tertiary.get('reasoning', ''),
                "timeline": f"{tertiary.get('typical_timeline_months', 6)} months",
                "expected_outcome": tertiary.get('expected_impact', '10% value increase'),
                "first_steps": tertiary.get('quick_actions', ['Create roadmap'])[0] if tertiary.get('quick_actions') else 'Create roadmap'
            })
        
        # Determine Critical Focus Area
        critical_focus = {
            "area": format_category_title(primary.get('category', '')) if primary else 'Business Systematization',
            "why_critical": primary.get('reasoning', 'This area has the highest impact on your exit value') if primary else 'Critical for exit readiness',
            "is_value_killer": primary.get('is_value_killer', False) if primary else False,
            "timeline_alignment": assess_timeline_fit(
                primary.get('typical_timeline_months', 6) if primary else 6,
                exit_timeline
            ),
            "first_week_actions": generate_first_week_actions(primary) if primary else ['Schedule strategic planning session'],
            "success_metrics": generate_success_metrics(primary.get('category', '')) if primary else ['Track improvement progress']
        }
        
        recommendations_structure = {
            "quick_wins": quick_wins[:3],
            "strategic_priorities": strategic_priorities[:3],
            "critical_focus": critical_focus,
            "implementation_guidance": {
                "timeline": exit_timeline,
                "resource_needs": estimate_resource_needs(strategic_priorities),
                "expected_roi": calculate_expected_roi(focus_areas)
            }
        }
        
        return json.dumps(recommendations_structure)
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        return json.dumps({"error": str(e)})

def assess_timeline_fit(improvement_months: int, exit_timeline: str) -> str:
    """Assess if improvement timeline fits with exit plans"""
    if "Already in discussions" in exit_timeline:
        if improvement_months <= 3:
            return "Achievable even during sale process"
        else:
            return "May need to disclose improvement plan to buyers"
    elif "1-2 years" in exit_timeline:
        if improvement_months <= 12:
            return "Good fit with your timeline"
        else:
            return "Needs immediate action to complete before exit"
    else:
        return "Sufficient time for full implementation"

def generate_first_week_actions(focus_area: Dict) -> List[str]:
    """Generate specific actions for the first week"""
    category = focus_area.get('category', '')
    
    first_week = {
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
    
    return first_week.get(category, ["Schedule strategic planning session"])

def generate_success_metrics(category: str) -> List[str]:
    """Generate measurable success metrics"""
    metrics = {
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
    
    return metrics.get(category, ["Monthly progress reviews"])

def estimate_resource_needs(priorities: List[Dict]) -> str:
    """Estimate resource needs for implementation"""
    total_months = sum(int(p.get('timeline', '6 months').split()[0]) for p in priorities)
    
    if total_months <= 6:
        return "Low: Can be managed with existing team and minimal outside help"
    elif total_months <= 12:
        return "Moderate: May need part-time consultant or dedicated internal resource"
    else:
        return "Significant: Consider full-time project manager or consulting team"

def calculate_expected_roi(focus_areas: Dict) -> str:
    """Calculate expected ROI from improvements"""
    primary = focus_areas.get('primary_focus', {})
    secondary = focus_areas.get('secondary_focus', {})
    
    primary_impact = primary.get('expected_impact', '10%')
    secondary_impact = secondary.get('expected_impact', '5%') if secondary else '0%'
    
    # Extract percentages
    try:
        p1 = int(primary_impact.replace('%', ''))
        p2 = int(secondary_impact.replace('%', ''))
        total = p1 + (p2 * 0.7)  # Secondary impact is typically 70% realized
        
        if total >= 30:
            return f"High: Potential {total:.0f}% increase in business value"
        elif total >= 20:
            return f"Strong: Potential {total:.0f}% increase in business value"
        else:
            return f"Moderate: Potential {total:.0f}% increase in business value"
    except:
        return "Significant value increase expected"

@tool("create_industry_context")
def create_industry_context(industry_data: str) -> str:
    """
    Create industry context section using research data.
    """
    try:
        data = json.loads(industry_data)
        research_findings = data.get('research_findings', {})
        business_info = data.get('business_info', {})
        scores = data.get('scores', {})
        
        context_structure = {
            "industry": business_info.get('industry', ''),
            "location": business_info.get('location', ''),
            "revenue_range": business_info.get('revenue_range', ''),
            "market_conditions": {
                "current_multiples": research_findings.get('valuation_benchmarks', {}).get('base_EBITDA', '4-6x'),
                "buyer_priorities": research_findings.get('buyer_priorities', []),
                "average_sale_time": research_findings.get('average_sale_time', '9-12 months'),
                "key_trend": research_findings.get('key_trend', '')
            },
            "your_position": {
                "strengths_vs_market": identify_market_strengths(scores, research_findings),
                "gaps_vs_market": identify_market_gaps(scores, research_findings),
                "competitive_position": assess_competitive_position(scores, research_findings)
            },
            "opportunity_analysis": {
                "value_enhancement_potential": calculate_enhancement_potential(scores, research_findings),
                "timeline_reality": assess_timeline_reality(business_info.get('exit_timeline', ''), scores),
                "market_timing": research_findings.get('market_timing', 'Stable M&A environment')
            }
        }
        
        return json.dumps(context_structure)
        
    except Exception as e:
        logger.error(f"Error creating industry context: {str(e)}")
        return json.dumps({"error": str(e)})

def identify_market_strengths(scores: Dict, research: Dict) -> List[str]:
    """Identify strengths relative to market"""
    strengths = []
    
    # Check recurring revenue
    if scores.get('revenue_quality', {}).get('score', 0) > 7:
        threshold = research.get('valuation_benchmarks', {}).get('recurring_threshold', '60%')
        strengths.append(f"Recurring revenue exceeds market threshold of {threshold}")
    
    # Check operational systems
    if scores.get('operational_resilience', {}).get('score', 0) > 7:
        strengths.append("Documentation exceeds typical SME standards")
    
    # Check unique value
    if scores.get('growth_value', {}).get('score', 0) > 6:
        value_strengths = scores.get('growth_value', {}).get('strengths', [])
        if any('certif' in str(s).lower() for s in value_strengths):
            strengths.append("Certifications create competitive barriers")
    
    return strengths[:3] if strengths else ["Building strong fundamentals"]

def identify_market_gaps(scores: Dict, research: Dict) -> List[str]:
    """Identify gaps relative to market expectations"""
    gaps = []
    
    # Owner dependence check
    od_score = scores.get('owner_dependence', {}).get('score', 10)
    if od_score < 5:
        benchmark = research.get('owner_dependence_threshold', '14 days')
        gaps.append(f"Below market expectation of {benchmark} independent operation")
    
    # Revenue concentration
    rq_gaps = scores.get('revenue_quality', {}).get('gaps', [])
    if any('concentration' in gap for gap in rq_gaps):
        gaps.append("Customer concentration exceeds buyer comfort levels")
    
    return gaps[:3] if gaps else ["Minor gaps vs market standards"]

def assess_competitive_position(scores: Dict, research: Dict) -> str:
    """Assess overall competitive position"""
    overall = scores.get('overall_score', 5.0)
    
    if overall >= 7.5:
        return "Top quartile - attractive to multiple buyers"
    elif overall >= 6.0:
        return "Above average - competitive with improvements"
    elif overall >= 4.5:
        return "Below average - needs work to compete"
    else:
        return "Significant gaps - major improvements needed"

def calculate_enhancement_potential(scores: Dict, research: Dict) -> str:
    """Calculate value enhancement potential"""
    improvements = research.get('improvements', {})
    
    total_potential = 0
    for category, data in improvements.items():
        current_score = scores.get(category, {}).get('score', 5)
        if current_score < 7:
            impact = data.get('value_impact', 0.1)
            total_potential += impact * (7 - current_score) / 2
    
    if total_potential > 0.3:
        return f"High: {int(total_potential * 100)}% potential value increase"
    elif total_potential > 0.15:
        return f"Moderate: {int(total_potential * 100)}% potential value increase"
    else:
        return f"Limited: {int(total_potential * 100)}% potential value increase"

def assess_timeline_reality(exit_timeline: str, scores: Dict) -> str:
    """Assess if timeline is realistic given current state"""
    overall = scores.get('overall_score', 5.0)
    
    if "Already in discussions" in exit_timeline:
        if overall < 6:
            return "Warning: Current readiness may impact negotiation position"
        else:
            return "Adequate readiness for active discussions"
    elif "1-2 years" in exit_timeline:
        if overall < 5:
            return "Aggressive timeline - requires immediate action"
        else:
            return "Achievable with focused improvements"
    else:
        return "Sufficient time for systematic improvements"

@tool("structure_final_report")
def structure_final_report(complete_data: str) -> str:
    """
    Structure all components into final report format for PDF generation.
    """
    try:
        data = json.loads(complete_data)
        
        # Extract all components
        executive_summary = data.get('executive_summary', {})
        category_summaries = data.get('category_summaries', {})
        recommendations = data.get('recommendations', {})
        industry_context = data.get('industry_context', {})
        next_steps = data.get('next_steps', {})
        
        # Structure for PDF generation
        report_structure = {
            "metadata": {
                "report_type": "Exit Ready Snapshot Assessment",
                "generation_date": data.get('timestamp', ''),
                "business_info": data.get('business_info', {}),
                "overall_score": data.get('overall_score', 0),
                "readiness_level": data.get('readiness_level', '')
            },
            "sections": [
                {
                    "type": "executive_summary",
                    "title": "Executive Summary",
                    "content": executive_summary,
                    "word_count": 200
                },
                {
                    "type": "score_overview",
                    "title": "Your Exit Readiness Score",
                    "content": {
                        "overall_score": data.get('overall_score', 0),
                        "readiness_level": data.get('readiness_level', ''),
                        "category_scores": format_category_scores_for_display(data.get('category_scores', {}))
                    }
                },
                {
                    "type": "category_analysis",
                    "title": "Detailed Analysis",
                    "subsections": category_summaries
                },
                {
                    "type": "recommendations",
                    "title": "Your Action Plan",
                    "content": recommendations
                },
                {
                    "type": "industry_context",
                    "title": "Market Context",
                    "content": industry_context
                },
                {
                    "type": "next_steps",
                    "title": "Next Steps",
                    "content": next_steps
                }
            ],
            "formatting_instructions": {
                "font": "Professional sans-serif",
                "colors": {
                    "primary": "#2C3E50",
                    "accent": "#3498DB",
                    "success": "#27AE60",
                    "warning": "#F39C12",
                    "danger": "#E74C3C"
                },
                "score_colors": get_score_color_mapping()
            }
        }
        
        return json.dumps(report_structure)
        
    except Exception as e:
        logger.error(f"Error structuring final report: {str(e)}")
        return json.dumps({"error": str(e)})

def format_category_scores_for_display(category_scores: Dict) -> List[Dict]:
    """Format category scores for visual display"""
    formatted = []
    category_order = ['owner_dependence', 'revenue_quality', 'financial_readiness', 
                     'operational_resilience', 'growth_value']
    
    for category in category_order:
        if category in category_scores:
            score_data = category_scores[category]
            formatted.append({
                "category": format_category_title(category),
                "score": score_data.get('score', 0),
                "weight": f"{int(score_data.get('weight', 0.2) * 100)}%",
                "color": get_score_color(score_data.get('score', 0))
            })
    
    return formatted

def get_score_color(score: float) -> str:
    """Get color for score display"""
    if score >= 8:
        return "#27AE60"  # Green
    elif score >= 6.5:
        return "#F39C12"  # Orange
    elif score >= 4.5:
        return "#E74C3C"  # Red
    else:
        return "#C0392B"  # Dark Red

def get_score_color_mapping() -> Dict[str, str]:
    """Get score range to color mapping"""
    return {
        "excellent": "#27AE60",
        "good": "#F39C12", 
        "needs_work": "#E74C3C",
        "critical": "#C0392B"
    }

def create_summary_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the enhanced summary agent"""
    
    config = prompts.get('summary_agent', {})
    
    tools = [
        generate_category_summary,
        create_executive_summary,
        generate_recommendations,
        create_industry_context,
        structure_final_report
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