from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Type
import logging
import json
import re

logger = logging.getLogger(__name__)

# Helper functions
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

# Tool Input Schemas
class GenerateCategorySummaryInput(BaseModel):
    category_data: str = Field(
        default="{}",
        description="JSON string containing category, score_data, industry_context, and locale_terms"
    )

class CreateExecutiveSummaryInput(BaseModel):
    assessment_data: str = Field(
        default="{}",
        description="JSON string containing overall_score, readiness_level, category_scores, focus_areas, industry_context, business_info"
    )

class GenerateRecommendationsInput(BaseModel):
    full_assessment: str = Field(
        default="{}",
        description="JSON string containing focus_areas, category_scores, and business_info"
    )

class CreateIndustryContextInput(BaseModel):
    industry_data: str = Field(
        default="{}",
        description="JSON string containing research_findings, business_info, and scores"
    )

class StructureFinalReportInput(BaseModel):
    complete_data: str = Field(
        default="{}",
        description="JSON string containing all report components"
    )

# Tool Classes
class GenerateCategorySummaryTool(BaseTool):
    name: str = "generate_category_summary"
    description: str = """
    Generate a comprehensive 150-200 word summary for a specific scoring category.
    
    Input should be JSON string containing:
    {"category": "owner_dependence", "score_data": {"score": 6.5, "strengths": [...], "gaps": [...]}, "industry_context": {...}, "locale_terms": {...}}
    
    Returns formatted category analysis as text.
    """
    args_schema: Type[BaseModel] = GenerateCategorySummaryInput
    
    def _run(self, category_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== GENERATE CATEGORY SUMMARY CALLED ===")
            logger.info(f"Input type: {type(category_data)}")
            logger.info(f"Input preview: {str(category_data)[:200] if category_data else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not category_data or category_data == "{}":
                logger.warning("No category data provided - using default summary")
                return """CATEGORY SUMMARY ERROR: No data provided

Please provide:
- category: The category to summarize
- score_data: The scoring results
- industry_context: Industry benchmarks
- locale_terms: Locale-specific terminology

Cannot generate summary without this data."""
            
            data = json.loads(category_data) if isinstance(category_data, str) else category_data
            category = data.get('category', '')
            score_data = data.get('score_data', {})
            industry_context = data.get('industry_context', {})
            locale_terms = data.get('locale_terms', {})
            
            # Extract key data
            category_title = format_category_title(category)
            score = score_data.get('score', 5.0)
            strengths = score_data.get('strengths', [])
            gaps = score_data.get('gaps', [])
            
            # Generate recommendations
            recommendations = generate_category_recommendations(category, score, gaps, strengths)
            
            # Format the summary as readable text
            summary_text = f"""
{category_title.upper()} ANALYSIS

SCORE: {score}/10

{interpret_score_meaning(score, category, industry_context)}

STRENGTHS WE IDENTIFIED:
{chr(10).join(f'• {s}' for s in strengths[:3]) if strengths else '• Limited strengths identified in current state'}

CRITICAL GAPS:
{chr(10).join(f'• {g}' for g in gaps[:3]) if gaps else '• No critical gaps identified'}

YOUR ACTION PLAN:

{chr(10).join(f'{i+1}. {r["timeframe"].upper()}: {r["action"]}' + chr(10) + f'   Impact: {r["impact"]}' for i, r in enumerate(recommendations[:3]))}

INDUSTRY BENCHMARK: {score_data.get('industry_context', {}).get('benchmark', 'Industry standard expectations')}

VALUATION IMPACT: {score_data.get('industry_context', {}).get('impact', 'Standard market impact')}

This analysis shows {'significant improvement potential' if score < 6 else 'solid positioning'} in {category_title.lower()}, which is {'critical' if category in ['owner_dependence', 'revenue_quality'] else 'important'} for achieving optimal exit value."""
            
            return summary_text
            
        except Exception as e:
            logger.error(f"Error generating category summary: {str(e)}")
            return f"""CATEGORY SUMMARY ERROR: Generation failed

Error: {str(e)}

Please check the input data format and try again."""

class CreateExecutiveSummaryTool(BaseTool):
    name: str = "create_executive_summary"
    description: str = """
    Create a compelling 200-250 word executive summary that captures the key insights.
    
    Input should be JSON string containing:
    {"overall_score": 6.5, "readiness_level": "Approaching Ready", "category_scores": {...}, "focus_areas": {...}, "industry_context": {...}, "business_info": {...}}
    
    Returns formatted executive summary text.
    """
    args_schema: Type[BaseModel] = CreateExecutiveSummaryInput
    
    def _run(self, assessment_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== CREATE EXECUTIVE SUMMARY CALLED ===")
            logger.info(f"Input type: {type(assessment_data)}")
            logger.info(f"Input preview: {str(assessment_data)[:200] if assessment_data else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not assessment_data or assessment_data == "{}":
                logger.warning("No assessment data provided - using default executive summary")
                return """EXECUTIVE SUMMARY ERROR: No assessment data provided

Cannot create executive summary without:
- overall_score
- readiness_level
- category_scores
- focus_areas
- business_info

Please complete the assessment first."""
            
            data = json.loads(assessment_data) if isinstance(assessment_data, str) else assessment_data
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
            
            # Format executive summary as readable text
            executive_summary = f"""EXECUTIVE SUMMARY

Thank you for completing the Exit Ready Snapshot assessment. As a {business_info.get('industry', 'business')} owner in {business_info.get('location', 'your region')} with {business_info.get('years_in_business', 'your years')} of experience, you're taking an important step toward maximizing your business value.

OVERALL ASSESSMENT: {overall_score}/10 - {readiness_level}

{get_overall_score_interpretation(overall_score)}

KEY FINDINGS:

Your Strongest Area: {format_category_title(highest_score[0]) if highest_score else 'To be determined'} ({highest_score[1].get('score', 0)}/10)
{'- ' + (highest_score[1].get('strengths', ['Strong foundation'])[0] if highest_score[1].get('strengths') else 'Strong foundation') if highest_score else ''}

Your Biggest Opportunity: {format_category_title(lowest_score[0]) if lowest_score else 'To be determined'} ({lowest_score[1].get('score', 10)}/10)
{'- ' + (lowest_score[1].get('gaps', ['Improvement needed'])[0] if lowest_score[1].get('gaps') else 'Improvement needed') if lowest_score else ''}

VALUE PROPOSITION:
Based on your assessment, your business is currently positioned for a {current_multiple} EBITDA multiple. With focused improvements in {format_category_title(primary_focus.get('category', '')) if primary_focus else 'key areas'}, you could achieve {potential_multiple} - a potential {'20-40%' if overall_score < 6 else '15-25%'} increase in sale value.

YOUR EXIT TIMELINE: {business_info.get('exit_timeline', 'Not specified')}
{'⚠️  URGENT: Your timeline requires immediate action on critical improvements.' if '1-2 years' in business_info.get('exit_timeline', '') or 'Already' in business_info.get('exit_timeline', '') else 'You have time to optimize value before exit.'}

The path forward is clear: focus on {format_category_title(primary_focus.get('category', '')) if primary_focus else 'your highest-impact improvements'} to unlock significant value. Your business has {'strong potential' if overall_score >= 5 else 'clear opportunities'} for enhancement that buyers will reward."""
            
            return executive_summary
            
        except Exception as e:
            logger.error(f"Error creating executive summary: {str(e)}")
            return f"""EXECUTIVE SUMMARY ERROR: Generation failed

Error: {str(e)}

Please ensure assessment data is complete before creating summary."""
        
 class GenerateRecommendationsTool(BaseTool):
    name: str = "generate_recommendations"
    description: str = """
    Generate comprehensive recommendations section with Quick Wins, Strategic Priorities, and Critical Focus.
    
    Input should be JSON string containing:
    {"focus_areas": {"primary_focus": {...}, "secondary_focus": {...}}, "category_scores": {...}, "business_info": {"exit_timeline": "1-2 years"}}
    
    Returns formatted recommendations text with actionable advice.
    """
    args_schema: Type[BaseModel] = GenerateRecommendationsInput
    
    def _run(self, full_assessment: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== GENERATE RECOMMENDATIONS CALLED ===")
            logger.info(f"Input type: {type(full_assessment)}")
            logger.info(f"Input preview: {str(full_assessment)[:200] if full_assessment else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not full_assessment or full_assessment == "{}":
                logger.warning("No assessment data provided - using default recommendations")
                return """RECOMMENDATIONS ERROR: No assessment data provided

Cannot generate recommendations without:
- focus_areas (from scoring)
- category_scores
- business_info

Using generic recommendations:

QUICK WINS (30 DAYS):
1. Schedule process documentation sessions
2. Review client contract terms
3. Identify delegation opportunities

STRATEGIC PRIORITIES (3-6 MONTHS):
1. Implement systematic improvements
2. Reduce owner dependence
3. Improve financial documentation

Please complete assessment for personalized recommendations."""
            
            data = json.loads(full_assessment) if isinstance(full_assessment, str) else full_assessment
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
            
            # Format recommendations as readable text
            recommendations_text = f"""YOUR PERSONALIZED ACTION PLAN

{'⚠️  TIMELINE ALERT: ' + exit_timeline if 'Already' in exit_timeline or '1-2' in exit_timeline else 'EXIT TIMELINE: ' + exit_timeline}

QUICK WINS (NEXT 30 DAYS)
These high-impact actions can be implemented immediately:

{chr(10).join(f'{i+1}. {qw["action"]}' + chr(10) + f'   Category: {qw["category"]}' + chr(10) + f'   Impact: {qw["impact"]}' + chr(10) for i, qw in enumerate(quick_wins[:3]))}

STRATEGIC PRIORITIES (3-6 MONTHS)
Major initiatives that will transform your business value:

{chr(10).join(f'{i+1}. {sp["initiative"]}' + chr(10) + f'   Timeline: {sp["timeline"]}' + chr(10) + f'   Expected Outcome: {sp["expected_outcome"]}' + chr(10) + f'   First Step: {sp["first_steps"]}' + chr(10) for i, sp in enumerate(strategic_priorities[:3]))}

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
Resource Needs: {estimate_resource_needs(strategic_priorities)}
Expected ROI: {calculate_expected_roi(focus_areas)}

Remember: Consistent execution of these recommendations will position your business for maximum value at exit. Start with your critical focus area TODAY."""
            
            return recommendations_text
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return f"""RECOMMENDATIONS ERROR: Generation failed

Error: {str(e)}

Please ensure assessment is complete before generating recommendations."""

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

class CreateIndustryContextTool(BaseTool):
    name: str = "create_industry_context"
    description: str = """
    Create industry context section using research data.
    
    Input should be JSON string containing:
    {"research_findings": {...}, "business_info": {"industry": "Manufacturing", "location": "Northeast US"}, "scores": {...}}
    
    Returns formatted industry context and market positioning text.
    """
    args_schema: Type[BaseModel] = CreateIndustryContextInput
    
    def _run(self, industry_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== CREATE INDUSTRY CONTEXT CALLED ===")
            logger.info(f"Input type: {type(industry_data)}")
            logger.info(f"Input preview: {str(industry_data)[:200] if industry_data else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not industry_data or industry_data == "{}":
                logger.warning("No industry data provided - using default context")
                return """INDUSTRY CONTEXT ERROR: No data provided

Cannot create industry context without:
- research_findings
- business_info
- scores

Using generic market context:

MARKET CONDITIONS:
- Current multiples: 4-6x EBITDA (varies by industry)
- Buyer priorities: Recurring revenue, systematic operations, growth potential
- Average sale time: 9-12 months

Please provide research data for personalized context."""
            
            data = json.loads(industry_data) if isinstance(industry_data, str) else industry_data
            research_findings = data.get('research_findings', {})
            business_info = data.get('business_info', {})
            scores = data.get('scores', {})
            
            # Format industry context as readable text
            context_text = f"""INDUSTRY & MARKET CONTEXT

YOUR MARKET: {business_info.get('industry', 'Your Industry')} in {business_info.get('location', 'Your Region')}
REVENUE RANGE: {business_info.get('revenue_range', 'Not specified')}

CURRENT MARKET CONDITIONS:

Valuation Benchmarks:
• EBITDA Multiples: {research_findings.get('valuation_benchmarks', {}).get('base_EBITDA', '4-6x')}
• Revenue Multiples: {research_findings.get('valuation_benchmarks', {}).get('base_revenue', '1.2-2.0x')}
• Premium for {research_findings.get('valuation_benchmarks', {}).get('recurring_threshold', '60%')}+ recurring revenue: {research_findings.get('valuation_benchmarks', {}).get('recurring_premium', '1-2x additional')}

Buyer Priorities (in order):
{chr(10).join(f'{i+1}. {priority}' for i, priority in enumerate(research_findings.get('buyer_priorities', ['Recurring revenue', 'Systematic operations', 'Growth potential'])[:3]))}

Market Dynamics:
• Average Time to Sell: {research_findings.get('average_sale_time', '9-12 months')}
• Key Trend: {research_findings.get('key_trend', 'Buyers increasingly value technology integration')}

YOUR COMPETITIVE POSITION:

Strengths vs Market:
{chr(10).join(f'• {s}' for s in identify_market_strengths(scores, research_findings)[:3])}

Gaps vs Market Expectations:
{chr(10).join(f'• {g}' for g in identify_market_gaps(scores, research_findings)[:3])}

Overall Position: {assess_competitive_position(scores, research_findings)}

VALUE ENHANCEMENT OPPORTUNITY:
{calculate_enhancement_potential(scores, research_findings)}

TIMELINE CONSIDERATIONS:
{assess_timeline_reality(business_info.get('exit_timeline', ''), scores)}

KEY TAKEAWAY: {generate_market_insight(scores, research_findings, business_info)}"""
            
            return context_text
            
        except Exception as e:
            logger.error(f"Error creating industry context: {str(e)}")
            return f"""INDUSTRY CONTEXT ERROR: Generation failed

Error: {str(e)}

Please ensure research data is available before creating context."""

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

def generate_market_insight(scores: Dict, research: Dict, business_info: Dict) -> str:
    """Generate key market insight"""
    overall = scores.get('overall_score', 5.0)
    industry = business_info.get('industry', 'your industry')
    
    if overall >= 7:
        return f"Your business is well-positioned in the {industry} market. Focus on maximizing premium through strategic improvements."
    elif overall >= 5:
        return f"The {industry} market rewards systematic businesses. Your improvement plan aligns with buyer priorities."
    else:
        return f"Current {industry} buyers are selective. Significant improvements needed to compete effectively."

class StructureFinalReportTool(BaseTool):
    name: str = "structure_final_report"
    description: str = """
    Structure all components into final report format for PDF generation.
    
    Input should be JSON string containing all report components:
    {"executive_summary": "...", "category_summaries": {...}, "recommendations": "...", "industry_context": "...", "business_info": {...}}
    
    Returns complete structured report text ready for delivery.
    """
    args_schema: Type[BaseModel] = StructureFinalReportInput
    
    def _run(self, complete_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== STRUCTURE FINAL REPORT CALLED ===")
            logger.info(f"Input type: {type(complete_data)}")
            logger.info(f"Input preview: {str(complete_data)[:200] if complete_data else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not complete_data or complete_data == "{}":
                logger.warning("No complete data provided - using default report structure")
                return """REPORT STRUCTURE ERROR: No data provided

Cannot structure report without:
- executive_summary
- category_summaries
- recommendations
- industry_context
- next_steps

Please ensure all report sections are generated first."""
            
            data = json.loads(complete_data) if isinstance(complete_data, str) else complete_data
            
            # Extract all components
            executive_summary = data.get('executive_summary', '')
            category_summaries = data.get('category_summaries', {})
            recommendations = data.get('recommendations', '')
            industry_context = data.get('industry_context', '')
            next_steps = data.get('next_steps', '')
            overall_score = data.get('overall_score', 0)
            readiness_level = data.get('readiness_level', '')
            
            # Default next steps if not provided
            if not next_steps:
                next_steps = """NEXT STEPS

Your Exit Ready Snapshot has identified clear opportunities to enhance your business value. Here's how to move forward:

1. IMMEDIATE ACTION (This Week):
   □ Review this report with your leadership team
   □ Commit to your primary focus area
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
• Exit Value Growth Plan: Deep-dive analysis with personalized roadmap
• Implementation Support: Hands-on help with critical improvements
• M&A Advisory: When you're ready for the exit process

Remember: Every improvement you make increases your business value and exit options.

Contact us at success@onpulsesolutions.com to discuss your personalized Exit Value Growth Plan."""
            
            # Structure the complete report
            report_structure = f"""EXIT READY SNAPSHOT ASSESSMENT REPORT

{'='*60}

{executive_summary}

{'='*60}

YOUR EXIT READINESS SCORE

Overall Score: {overall_score}/10
Readiness Level: {readiness_level}

{'='*60}

DETAILED ANALYSIS BY CATEGORY

{chr(10).join(f'{summary}' + chr(10) + ('='*60) for summary in category_summaries.values()) if category_summaries else 'Category analysis not available'}

{'='*60}

{recommendations}

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

© On Pulse Solutions - Exit Ready Snapshot Assessment"""
            
            return report_structure
            
        except Exception as e:
            logger.error(f"Error structuring final report: {str(e)}")
            return f"""REPORT STRUCTURE ERROR: Assembly failed

Error: {str(e)}

Please ensure all report sections are complete before final assembly."""

# Create tool instances
generate_category_summary = GenerateCategorySummaryTool()
create_executive_summary = CreateExecutiveSummaryTool()
generate_recommendations = GenerateRecommendationsTool()
create_industry_context = CreateIndustryContextTool()
structure_final_report = StructureFinalReportTool()

def create_summary_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the enhanced summary agent"""
    
    config = prompts.get('summary_agent', {})
    
    # Create tools list using instances
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