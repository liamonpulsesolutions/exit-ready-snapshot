from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Type
import logging
import json
from ..utils.json_helper import safe_parse_json

logger = logging.getLogger(__name__)

# Tool Input Schemas
class CalculateCategoryScoreInput(BaseModel):
    score_data: str = Field(
        default="{}",
        description="JSON string containing category name and assessment responses"
    )

class AggregateFinalScoresInput(BaseModel):
    all_scores: str = Field(
        default="{}",
        description="JSON string containing all category scores"
    )

class CalculateFocusAreasInput(BaseModel):
    score_results: str = Field(
        default="{}",
        description="JSON string containing scores and business context"
    )

# Helper functions for scoring calculations
def calculate_time_impact(years_in_business: int) -> float:
    """Calculate score adjustment based on years in business"""
    if years_in_business >= 10:
        return 1.0  # Mature business bonus
    elif years_in_business >= 5:
        return 0.5
    elif years_in_business >= 3:
        return 0.0
    else:
        return -0.5  # Young business penalty

def calculate_revenue_impact(revenue_range: str) -> float:
    """Calculate score adjustment based on revenue"""
    revenue_impacts = {
        "Under $500K": -1.0,
        "$500K-$1M": -0.5,
        "$1M-$5M": 0.0,
        "$5M-$10M": 0.5,
        "$10M-$25M": 1.0,
        "$25M-$50M": 1.5,
        "Over $50M": 2.0
    }
    return revenue_impacts.get(revenue_range, 0.0)

def calculate_growth_trajectory(revenue_trend: str, profit_trend: str) -> float:
    """Calculate growth trajectory score"""
    growth_score = 0.0
    
    # Revenue trend impact
    if "significantly" in revenue_trend and "increased" in revenue_trend:
        growth_score += 2.0
    elif "increased" in revenue_trend:
        growth_score += 1.0
    elif "stayed flat" in revenue_trend:
        growth_score += 0.0
    else:
        growth_score -= 1.0
    
    # Profit trend impact
    if "improved significantly" in profit_trend:
        growth_score += 1.5
    elif "improved" in profit_trend:
        growth_score += 0.5
    elif "stayed flat" in profit_trend:
        growth_score += 0.0
    else:
        growth_score -= 0.5
    
    return growth_score

# Scoring functions for each category
def score_financial_performance(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score financial performance category with sophisticated analysis"""
    # Initialize
    base_score = 5.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q5 - Financial confidence (60% weight)
    q5_response = responses.get("q5", "").strip()
    if q5_response:
        try:
            # Handle both numeric and text responses
            if q5_response.isdigit():
                confidence = int(q5_response)
            else:
                # Extract number from text like "7 - Strong confidence"
                import re
                match = re.search(r'(\d+)', q5_response)
                confidence = int(match.group(1)) if match else 5
            
            # Sophisticated confidence mapping
            if confidence >= 9:
                base_score = 4.5
                strengths.append("Exceptional financial confidence indicates strong systems")
                adjustments.append("+4.5: Very high financial confidence")
            elif confidence >= 7:
                base_score = 3.5
                strengths.append("Strong financial confidence")
                adjustments.append("+3.5: Good financial confidence")
            elif confidence >= 5:
                base_score = 2.5
                adjustments.append("+2.5: Moderate financial confidence")
            else:
                base_score = 1.5
                gaps.append("Low financial confidence suggests poor visibility")
                adjustments.append("+1.5: Low financial confidence")
                
                # Additional context for very low scores
                if confidence <= 2:
                    gaps.append("Critical: Buyers will see this as high risk")
                    try:
                        # Safe parsing of potential additional context
                        if "don't track" in q5_response.lower() or "no system" in q5_response.lower():
                            gaps.append("No financial tracking system - major red flag for assessment")
                    except:
                        pass
        except:
            base_score = 3.0  # Default if parsing fails
    else:
        base_score = 3.0
        gaps.append("No financial confidence data provided")
    
    # Q6 - Profit margin trend (40% weight)
    q6_response = responses.get("q6", "").strip()
    if q6_response:
        margin_impact = 0.0
        if "Declined significantly" in q6_response:
            margin_impact = 0.5
            gaps.append("Significant margin decline - major concern")
            adjustments.append("+0.5: Significant margin decline")
        elif "Declined slightly" in q6_response:
            margin_impact = 1.5
            gaps.append("Margin pressure evident")
            adjustments.append("+1.5: Slight margin decline")
        elif "Stayed flat" in q6_response:
            margin_impact = 2.5
            strengths.append("Stable profit margins")
            adjustments.append("+2.5: Stable margins")
        elif "Improved slightly" in q6_response:
            margin_impact = 3.0
            strengths.append("Improving profit margins")
            adjustments.append("+3.0: Improving margins")
        elif "Improved significantly" in q6_response:
            margin_impact = 4.0
            strengths.append("Strong margin growth - very attractive")
            adjustments.append("+4.0: Significant margin improvement")
        elif "don't know" in q6_response.lower():
            margin_impact = 1.0
            gaps.append("Profit margins not tracked - red flag")
            adjustments.append("+1.0: Margins not tracked")
        
        base_score += margin_impact
    else:
        base_score += 2.0  # Neutral if no data
    
    # Ensure score stays in bounds
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.20,
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Unable to identify specific strengths"],
        "gaps": gaps if gaps else ["Limited financial data provided"],
        "industry_context": {
            "benchmark": "Industry expects 15-20% EBITDA margins",
            "impact": "Strong financials can add 20-30% to valuation"
        }
    }

def score_revenue_stability(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score revenue quality and predictability"""
    base_score = 5.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Extract business fundamentals
    revenue_range = responses.get("revenue_range", "$1M-$5M")
    years_in_business = int(responses.get("years_in_business", "5"))
    
    # Time in business impact
    time_impact = calculate_time_impact(years_in_business)
    base_score += time_impact
    if time_impact > 0:
        strengths.append(f"Established {years_in_business}+ year track record")
        adjustments.append(f"+{time_impact}: Mature business bonus")
    elif time_impact < 0:
        gaps.append("Limited operating history increases risk")
        adjustments.append(f"{time_impact}: Young business adjustment")
    
    # Revenue size impact
    revenue_impact = calculate_revenue_impact(revenue_range)
    base_score += revenue_impact
    if revenue_impact > 0:
        strengths.append(f"Strong revenue scale ({revenue_range})")
        adjustments.append(f"+{revenue_impact}: Revenue scale bonus")
    elif revenue_impact < 0:
        gaps.append("Small revenue base limits buyer pool")
        adjustments.append(f"{revenue_impact}: Limited revenue adjustment")
    
    # Industry-specific adjustments
    industry = responses.get("industry", "").lower()
    if "recurring" in industry or "saas" in industry or "subscription" in industry:
        base_score += 1.0
        strengths.append("Recurring revenue model highly valued")
        adjustments.append("+1.0: Recurring revenue bonus")
    elif "consulting" in industry or "project" in industry:
        base_score -= 0.5
        gaps.append("Project-based revenue less predictable")
        adjustments.append("-0.5: Project revenue adjustment")
    
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.20,
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Stable revenue base"],
        "gaps": gaps if gaps else ["No critical revenue issues identified"],
        "industry_context": {
            "benchmark": f"Typical {industry} multiples: 2-4x revenue",
            "impact": "Predictable revenue can increase multiples by 50%"
        }
    }

def score_operations_efficiency(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score operational maturity and scalability"""
    base_score = 5.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q7 - Team dependency (50% weight)
    q7_response = responses.get("q7", "").strip()
    if q7_response:
        if "Everything would stop" in q7_response or "Major disruption" in q7_response:
            base_score = 2.0
            gaps.append("Critical owner dependency - major exit barrier")
            adjustments.append("-3.0: High owner dependency")
        elif "Some disruption" in q7_response:
            base_score = 5.0
            gaps.append("Moderate owner dependency needs addressing")
            adjustments.append("0.0: Moderate dependency")
        elif "Minimal disruption" in q7_response:
            base_score = 7.0
            strengths.append("Good operational independence")
            adjustments.append("+2.0: Low dependency")
        elif "No disruption" in q7_response:
            base_score = 9.0
            strengths.append("Excellent operational independence - highly attractive")
            adjustments.append("+4.0: No owner dependency")
    
    # Q8 - Documentation (30% weight)
    q8_response = responses.get("q8", "").strip()
    if q8_response:
        doc_score = 0.0
        if "Comprehensive" in q8_response:
            doc_score = 2.0
            strengths.append("Excellent process documentation")
            adjustments.append("+2.0: Comprehensive documentation")
        elif "Good documentation" in q8_response:
            doc_score = 1.0
            strengths.append("Solid documentation foundation")
            adjustments.append("+1.0: Good documentation")
        elif "Some documentation" in q8_response:
            doc_score = 0.0
            gaps.append("Documentation needs improvement")
        elif "Little" in q8_response or "No documentation" in q8_response:
            doc_score = -2.0
            gaps.append("Poor documentation - significant weakness")
            adjustments.append("-2.0: Poor documentation")
        
        base_score += doc_score
    
    # Management structure bonus (20% weight)
    if "management team" in responses.get("q7", "").lower():
        base_score += 1.0
        strengths.append("Management team in place")
        adjustments.append("+1.0: Management structure bonus")
    else:
        gaps.append("No clear management structure")
    
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.15,
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Basic operational structure in place"],
        "gaps": gaps if gaps else ["Limited operational data provided"],
        "industry_context": {
            "benchmark": "Buyers expect documented processes and backup for key roles",
            "impact": "Poor documentation can extend due diligence by 2-3 months"
        }
    }

def score_growth_value(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score growth potential and unique value - sophisticated analysis"""
    # Initialize
    base_score = 3.0  # Start lower since we build up
    gaps = []
    strengths = []
    adjustments = []
    
    # Q10 - Growth potential self-assessment (only 30% weight!)
    q10_response = responses.get("q10", "").strip()
    if q10_response:
        try:
            growth_potential = float(q10_response)
            base_score += growth_potential * 0.3
            adjustments.append(f"+{growth_potential * 0.3:.1f}: Self-assessed growth potential")
            
            if growth_potential <= 3:
                gaps.append("Low growth expectations may indicate market/competitive issues")
            elif growth_potential >= 8:
                strengths.append("High growth confidence")
        except:
            base_score += 1.5  # Default
    else:
        base_score += 1.5
    
    # Q9 - Value drivers analysis (70% weight!)
    q9_response = responses.get("q9", "").strip().lower()
    if q9_response:
        value_score = 0.0
        value_drivers = []
        
        # Check for strong value indicators
        strong_indicators = [
            ("proprietary", 2.0, "Proprietary technology/IP"),
            ("patent", 2.0, "Patent protection"),
            ("exclusive", 1.5, "Exclusive agreements"),
            ("market leader", 1.5, "Market leadership position"),
            ("unique", 1.0, "Unique market position"),
            ("recurring", 1.0, "Recurring revenue model"),
            ("contract", 0.8, "Long-term contracts"),
            ("relationship", 0.5, "Strong customer relationships")
        ]
        
        for indicator, points, description in strong_indicators:
            if indicator in q9_response:
                value_score += points
                value_drivers.append(description)
                strengths.append(description)
        
        # Check for weak indicators
        if "no" in q9_response or "not really" in q9_response or "none" in q9_response:
            value_score = -1.0
            gaps.append("No clear competitive advantages identified")
        
        # Apply value driver score
        base_score += min(4.0, value_score)  # Cap at 4.0
        
        if value_drivers:
            adjustments.append(f"+{min(4.0, value_score):.1f}: {len(value_drivers)} value drivers")
        else:
            adjustments.append(f"+{value_score:.1f}: Limited value differentiation")
    
    # Growth trajectory from financial trends
    revenue_trend = responses.get("q4", "")
    profit_trend = responses.get("q6", "")
    trajectory_score = calculate_growth_trajectory(revenue_trend, profit_trend)
    base_score += trajectory_score * 0.5
    
    if trajectory_score > 1:
        strengths.append("Strong growth trajectory")
        adjustments.append(f"+{trajectory_score * 0.5:.1f}: Growth trajectory")
    elif trajectory_score < -0.5:
        gaps.append("Declining performance trend")
        adjustments.append(f"{trajectory_score * 0.5:.1f}: Negative trajectory")
    
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.25,
        "scoring_breakdown": {
            "base_score": 3.0,
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Some growth potential identified"],
        "gaps": gaps if gaps else ["Value proposition needs strengthening"],
        "industry_context": {
            "benchmark": "Premium valuations require clear competitive moats",
            "impact": "Strong value drivers can increase multiples by 2-3x"
        }
    }

def score_exit_readiness(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score structural and timeline readiness for exit"""
    base_score = 5.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q3 - Exit timeline (40% weight)
    q3_response = responses.get("q3", "").strip()
    timeline_score = 0.0
    
    if "Already in discussions" in q3_response:
        timeline_score = -1.0  # Urgency may hurt negotiation
        gaps.append("Active discussions without full preparation")
        adjustments.append("-1.0: Rushed timeline risk")
    elif "Within 6 months" in q3_response:
        timeline_score = 0.0
        gaps.append("Tight timeline limits improvement options")
    elif "6-12 months" in q3_response:
        timeline_score = 1.0
        strengths.append("Reasonable preparation timeline")
        adjustments.append("+1.0: Good preparation window")
    elif "1-2 years" in q3_response:
        timeline_score = 2.0
        strengths.append("Optimal timeline for value enhancement")
        adjustments.append("+2.0: Ideal preparation timeline")
    elif "2-5 years" in q3_response:
        timeline_score = 1.0
        strengths.append("Ample time for strategic improvements")
        adjustments.append("+1.0: Strategic timeline")
    else:  # 5+ years or just exploring
        timeline_score = 0.0
        
    base_score += timeline_score
    
    # Structural readiness indicators (60% weight)
    structural_score = 0.0
    
    # Clean books bonus
    if int(responses.get("q5", "5")) >= 7:
        structural_score += 1.0
        strengths.append("Financial confidence indicates clean books")
        adjustments.append("+1.0: Clean financials")
    
    # Documentation bonus
    if "Comprehensive" in responses.get("q8", "") or "Good documentation" in responses.get("q8", ""):
        structural_score += 1.0
        strengths.append("Documentation supports due diligence")
        adjustments.append("+1.0: Good documentation")
    
    # Independence bonus
    if "Minimal disruption" in responses.get("q7", "") or "No disruption" in responses.get("q7", ""):
        structural_score += 1.5
        strengths.append("Operational independence attractive to buyers")
        adjustments.append("+1.5: Low dependency")
    else:
        gaps.append("Owner dependency complicates transition")
    
    # Legal structure consideration
    years_in_business = int(responses.get("years_in_business", "5"))
    if years_in_business >= 5:
        structural_score += 0.5
        adjustments.append("+0.5: Established entity")
    
    base_score += structural_score
    
    # Market timing factor
    market_conditions = research_data.get('market_conditions', {})
    if market_conditions.get('favorable', False):
        base_score += 0.5
        strengths.append("Favorable market conditions")
    
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.20,
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Basic exit readiness framework exists"],
        "gaps": gaps if gaps else ["Some preparation areas to address"],
        "industry_context": {
            "benchmark": "Well-prepared businesses sell 25% faster and for 20% more",
            "impact": "Poor preparation can reduce value by 30-50%"
        }
    }

# Tool Classes
class CalculateCategoryScoreTool(BaseTool):
    name: str = "calculate_category_score"
    description: str = """
    Calculate sophisticated score for a specific assessment category.
    
    Input should be JSON string containing:
    {"category": "financial_performance", "responses": {...}, "research_data": {...}}
    
    Returns detailed scoring breakdown as formatted text.
    """
    args_schema: Type[BaseModel] = CalculateCategoryScoreInput
    
    def _run(self, score_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== CALCULATE CATEGORY SCORE CALLED ===")
            logger.info(f"Input preview: {str(score_data)[:200]}...")
            
            # Handle empty input
            if not score_data or score_data == "{}":
                return """CATEGORY SCORING: Failed ❌

No scoring data provided.

Required:
- Category name
- Assessment responses
- Research data (optional)

Action Required: Provide category and response data for scoring."""
            
            # Parse input data
            if isinstance(score_data, dict):
                data = score_data
            else:
                data = safe_parse_json(score_data, {}, "calculate_category_score")
                if not data:
                    return """CATEGORY SCORING: Failed ❌

Invalid JSON format for scoring data.
Please check the input format and retry."""
            
            category = data.get('category', '').lower()
            responses = data.get('responses', {})
            research_data = data.get('research_data', {})
            
            # Map categories to scoring functions
            scoring_functions = {
                'financial_performance': score_financial_performance,
                'revenue_stability': score_revenue_stability,
                'operations_efficiency': score_operations_efficiency,
                'growth_value': score_growth_value,
                'exit_readiness': score_exit_readiness
            }
            
            # Validate category
            if category not in scoring_functions:
                return f"""CATEGORY SCORING: Invalid Category ❌

Category '{category}' not recognized.

Valid categories:
- financial_performance
- revenue_stability
- operations_efficiency
- growth_value
- exit_readiness

Action Required: Use a valid category name."""
            
            # Calculate score
            scoring_function = scoring_functions[category]
            result = scoring_function(responses, research_data)
            
            # Format the result as readable text
            score = result['score']
            weight = result['weight']
            weighted_score = score * weight
            
            # Format strengths and gaps
            strengths_text = '\n'.join(f"  ✓ {s}" for s in result['strengths'])
            gaps_text = '\n'.join(f"  ⚠️ {g}" for g in result['gaps'])
            
            # Format scoring breakdown
            breakdown = result['scoring_breakdown']
            adjustments_text = '\n'.join(f"  • {adj}" for adj in breakdown['adjustments'])
            
            # Industry context
            context = result['industry_context']
            
            return f"""CATEGORY SCORING: {category.replace('_', ' ').title()} ✓

SCORE: {score}/10 (Weight: {int(weight*100)}%)
Weighted Contribution: {weighted_score:.1f} points

SCORING BREAKDOWN:
Base Score: {breakdown['base_score']}
Adjustments:
{adjustments_text}
Final Score: {breakdown['final_score']}

STRENGTHS IDENTIFIED:
{strengths_text}

GAPS TO ADDRESS:
{gaps_text}

INDUSTRY CONTEXT:
• Benchmark: {context['benchmark']}
• Impact: {context['impact']}

Category assessment complete. Score: {score}/10"""
            
        except Exception as e:
            logger.error(f"Error calculating category score: {str(e)}")
            return f"""CATEGORY SCORING: Error ❌

Failed to calculate category score.
Error: {str(e)}

Please check the input data and retry."""

class AggregateFinalScoresTool(BaseTool):
    name: str = "aggregate_final_scores"
    description: str = """
    Aggregate all category scores into final assessment results.
    
    Input should be JSON string containing all category scores:
    {"financial_performance": {...}, "revenue_stability": {...}, ...}
    
    Returns comprehensive scoring summary as formatted text.
    """
    args_schema: Type[BaseModel] = AggregateFinalScoresInput
    
    def _run(self, all_scores: str = "{}", **kwargs) -> str:
        try:
            logger.info("=== AGGREGATE FINAL SCORES CALLED ===")
            
            # Handle empty input
            if not all_scores or all_scores == "{}":
                return """SCORE AGGREGATION: Failed ❌

No category scores provided for aggregation.

Required: Scores for all 5 categories
Provided: None

Action Required: Calculate all category scores first."""
            
            # Parse input
            if isinstance(all_scores, dict):
                scores = all_scores
            else:
                scores = safe_parse_json(all_scores, {}, "aggregate_final_scores")
                if not scores:
                    return """SCORE AGGREGATION: Failed ❌

Invalid score data format.
Please provide valid category scores."""
            
            # Calculate overall score
            total_weighted_score = 0.0
            total_weight = 0.0
            category_summaries = []
            all_strengths = []
            all_gaps = []
            
            for category, score_data in scores.items():
                if isinstance(score_data, dict) and 'score' in score_data:
                    score = score_data['score']
                    weight = score_data.get('weight', 0.2)
                    weighted = score * weight
                    
                    total_weighted_score += weighted
                    total_weight += weight
                    
                    category_summaries.append(f"• {category.replace('_', ' ').title()}: {score}/10 (weight {int(weight*100)}%)")
                    
                    # Collect strengths and gaps
                    if 'strengths' in score_data:
                        all_strengths.extend(score_data['strengths'][:2])  # Top 2 per category
                    if 'gaps' in score_data:
                        all_gaps.extend(score_data['gaps'][:2])  # Top 2 per category
            
            # Validate we have all categories
            if total_weight < 0.95:  # Allow small rounding errors
                return f"""SCORE AGGREGATION: Incomplete ⚠️

Only {int(total_weight*100)}% of categories scored.
Missing categories detected.

Scores received:
{chr(10).join(category_summaries)}

Action Required: Complete scoring for all 5 categories."""
            
            # Calculate final score
            overall_score = round(total_weighted_score / total_weight, 1) if total_weight > 0 else 0
            
            # Determine readiness level
            if overall_score >= 8.0:
                readiness_level = "Premium Ready"
                readiness_desc = "Exceptionally well-prepared for a premium exit"
            elif overall_score >= 6.5:
                readiness_level = "Market Ready"
                readiness_desc = "Well-positioned for a successful exit"
            elif overall_score >= 5.0:
                readiness_level = "Conditionally Ready"
                readiness_desc = "Ready with specific improvements needed"
            elif overall_score >= 3.5:
                readiness_level = "Preparation Needed"
                readiness_desc = "Significant preparation required before exit"
            else:
                readiness_level = "Not Ready"
                readiness_desc = "Substantial work needed to prepare for exit"
            
            # Format top strengths and gaps
            top_strengths = list(dict.fromkeys(all_strengths))[:5]  # Remove duplicates, top 5
            top_gaps = list(dict.fromkeys(all_gaps))[:5]
            
            strengths_text = '\n'.join(f"  ✓ {s}" for s in top_strengths)
            gaps_text = '\n'.join(f"  ⚠️ {g}" for g in top_gaps)
            
            return f"""SCORE AGGREGATION: Complete ✓

OVERALL EXIT READINESS SCORE: {overall_score}/10
READINESS LEVEL: {readiness_level}
STATUS: {readiness_desc}

CATEGORY BREAKDOWN:
{chr(10).join(category_summaries)}

TOP STRENGTHS:
{strengths_text}

PRIORITY GAPS:
{gaps_text}

SCORE DISTRIBUTION:
• Excellent (8-10): {sum(1 for cat, data in scores.items() if data.get('score', 0) >= 8)} categories
• Good (6-7.9): {sum(1 for cat, data in scores.items() if 6 <= data.get('score', 0) < 8)} categories
• Fair (4-5.9): {sum(1 for cat, data in scores.items() if 4 <= data.get('score', 0) < 6)} categories
• Poor (1-3.9): {sum(1 for cat, data in scores.items() if data.get('score', 0) < 4)} categories

Final assessment complete. Overall score: {overall_score}/10 ({readiness_level})"""
            
        except Exception as e:
            logger.error(f"Error aggregating scores: {str(e)}")
            return f"""SCORE AGGREGATION: Error ❌

Failed to aggregate scores.
Error: {str(e)}

Please check score data format and retry."""

class CalculateFocusAreasTool(BaseTool):
    name: str = "calculate_focus_areas"
    description: str = """
    Identify top 3 focus areas and generate specific action items.
    
    Input should be JSON string containing:
    {"scores": {...}, "gaps": [...], "timeline": "...", "industry": "..."}
    
    Returns prioritized action plan as formatted text.
    """
    args_schema: Type[BaseModel] = CalculateFocusAreasInput
    
    def _run(self, score_results: str = "{}", **kwargs) -> str:
        try:
            logger.info("=== CALCULATE FOCUS AREAS CALLED ===")
            
            # Handle empty input
            if not score_results or score_results == "{}":
                return """FOCUS AREAS: Failed ❌

No score results provided for analysis.

Required:
- Category scores
- Identified gaps
- Exit timeline
- Industry context

Action Required: Provide complete scoring results."""
            
            # Parse input
            if isinstance(score_results, dict):
                data = score_results
            else:
                data = safe_parse_json(score_results, {}, "calculate_focus_areas")
                if not data:
                    return """FOCUS AREAS: Failed ❌

Invalid data format.
Please provide valid scoring results."""
            
            scores = data.get('scores', {})
            all_gaps = data.get('gaps', [])
            timeline = data.get('timeline', '1-2 years')
            industry = data.get('industry', 'General Business')
            
            # Find lowest scoring categories
            category_scores = []
            for category, score_data in scores.items():
                if isinstance(score_data, dict) and 'score' in score_data:
                    category_scores.append({
                        'category': category,
                        'score': score_data['score'],
                        'weight': score_data.get('weight', 0.2),
                        'gaps': score_data.get('gaps', [])
                    })
            
            # Sort by score (lowest first)
            category_scores.sort(key=lambda x: x['score'])
            
            # Determine timeline urgency
            if "Already in discussions" in timeline or "Within 6 months" in timeline:
                urgency = "IMMEDIATE"
                timeframe = "Next 30-60 days"
            elif "6-12 months" in timeline:
                urgency = "HIGH"
                timeframe = "Next 3-6 months"
            elif "1-2 years" in timeline:
                urgency = "MODERATE"
                timeframe = "Next 6-12 months"
            else:
                urgency = "STRATEGIC"
                timeframe = "Next 12-24 months"
            
            # Generate focus areas
            focus_areas = []
            
            # Top 3 lowest scoring categories
            for i, cat_data in enumerate(category_scores[:3]):
                category = cat_data['category']
                score = cat_data['score']
                gaps = cat_data['gaps']
                
                # Generate specific actions
                actions = generate_category_actions(category, gaps, score, timeline)
                
                focus_area = {
                    'priority': i + 1,
                    'category': category.replace('_', ' ').title(),
                    'current_score': score,
                    'target_score': min(score + 2.0, 8.0),
                    'impact': calculate_improvement_impact(category, score),
                    'actions': actions,
                    'timeline': get_action_timeline(urgency, i)
                }
                
                focus_areas.append(focus_area)
            
            # Format output
            output_lines = [f"FOCUS AREAS: Prioritized ✓",
                          f"",
                          f"EXIT TIMELINE: {timeline}",
                          f"URGENCY LEVEL: {urgency}",
                          f"ACTION TIMEFRAME: {timeframe}",
                          f""]
            
            for area in focus_areas:
                output_lines.extend([
                    f"PRIORITY {area['priority']}: {area['category']}",
                    f"Current Score: {area['current_score']}/10 → Target: {area['target_score']}/10",
                    f"Value Impact: {area['impact']}",
                    f"Timeline: {area['timeline']}",
                    f"",
                    f"Action Items:"
                ])
                
                for j, action in enumerate(area['actions'], 1):
                    output_lines.append(f"  {j}. {action}")
                
                output_lines.append("")
            
            # Add ROI summary
            total_impact = sum(float(area['impact'].split('%')[0].split()[-1]) for area in focus_areas if '%' in area['impact'])
            
            output_lines.extend([
                "EXPECTED OUTCOMES:",
                f"• Combined value increase potential: {int(total_impact)}%",
                f"• Readiness improvement: {len(focus_areas)} score points",
                f"• Time to implement: {timeframe}",
                "",
                "NEXT STEP:",
                "Begin with Priority 1 actions immediately for maximum impact."
            ])
            
            return '\n'.join(output_lines)
            
        except Exception as e:
            logger.error(f"Error calculating focus areas: {str(e)}")
            return f"""FOCUS AREAS: Error ❌

Failed to calculate focus areas.
Error: {str(e)}

Please check the scoring results and retry."""

# Helper functions for focus area calculations
def calculate_improvement_impact(category: str, current_score: float) -> str:
    """Calculate the value impact of improving a category"""
    
    impact_multipliers = {
        'financial_performance': 0.3,
        'revenue_stability': 0.25,
        'operations_efficiency': 0.2,
        'growth_value': 0.35,
        'exit_readiness': 0.15
    }
    
    multiplier = impact_multipliers.get(category, 0.2)
    improvement_potential = (8.0 - current_score) / 10.0
    impact = improvement_potential * multiplier * 100
    
    if impact > 20:
        return f"High - up to {int(impact)}% value increase"
    elif impact > 10:
        return f"Moderate - up to {int(impact)}% value increase"
    else:
        return f"Low - up to {int(impact)}% value increase"

def get_action_timeline(urgency: str, priority: int) -> str:
    """Get specific timeline for action based on urgency and priority"""
    
    timelines = {
        'IMMEDIATE': ['Next 30 days', 'Next 45 days', 'Next 60 days'],
        'HIGH': ['Next 90 days', 'Next 4 months', 'Next 6 months'],
        'MODERATE': ['Next 6 months', 'Next 9 months', 'Next 12 months'],
        'STRATEGIC': ['Year 1', 'Year 1-2', 'Year 2']
    }
    
    return timelines.get(urgency, ['Next 6 months', 'Next 9 months', 'Next 12 months'])[priority]

def generate_category_actions(category: str, gaps: List[str], score: float, timeline: str) -> List[str]:
    """Generate specific action items for a category"""
    
    actions = []
    
    # Category-specific actions
    if category == 'financial_performance':
        if score < 4:
            actions.append("Implement monthly financial reporting system immediately")
            actions.append("Engage fractional CFO for financial cleanup")
        else:
            actions.append("Upgrade to accrual-based accounting if not already")
            actions.append("Prepare 3-year audited/reviewed financials")
        
        if any('margin' in gap.lower() for gap in gaps):
            actions.append("Conduct detailed margin analysis and implement pricing optimization")
    
    elif category == 'revenue_stability':
        if score < 5:
            actions.append("Document and diversify customer base (no customer >20%)")
            actions.append("Implement customer contracts with auto-renewal terms")
        else:
            actions.append("Develop recurring revenue streams or subscription options")
        
        actions.append("Create 12-month revenue forecast with confidence intervals")
    
    elif category == 'operations_efficiency':
        if any('owner dependency' in gap.lower() for gap in gaps):
            actions.append("Hire and train operations manager for daily activities")
            actions.append("Document all critical processes (aim for 20 SOPs minimum)")
        
        if score < 6:
            actions.append("Implement project management system for visibility")
        else:
            actions.append("Create operations manual for seamless transition")
    
    elif category == 'growth_value':
        if score < 4:
            actions.append("Identify and document 3 unique value propositions")
            actions.append("Develop IP strategy (trademarks, trade secrets, processes)")
        else:
            actions.append("Create 5-year growth plan with specific milestones")
        
        actions.append("Build strategic partnership pipeline for growth acceleration")
    
    elif category == 'exit_readiness':
        if "Already in discussions" in timeline:
            actions.append("Engage M&A advisor immediately if not already done")
            actions.append("Prepare virtual data room with all critical documents")
        else:
            actions.append("Complete legal cleanup (contracts, corporate records)")
            actions.append("Resolve any outstanding litigation or compliance issues")
        
        actions.append("Develop transition plan for top 5 key employees")
    
    # Ensure we have 3 actions, add generic if needed
    while len(actions) < 3:
        if not actions:
            actions.append(f"Conduct detailed {category.replace('_', ' ')} assessment")
        elif len(actions) == 1:
            actions.append(f"Develop improvement plan for {category.replace('_', ' ')}")
        else:
            actions.append("Track progress monthly with KPI dashboard")
    
    return actions[:3]  # Return top 3 actions

# Create tool instances
calculate_category_score = CalculateCategoryScoreTool()
aggregate_final_scores = AggregateFinalScoresTool()
calculate_focus_areas = CalculateFocusAreasTool()

def create_scoring_agent(llm, prompts: Dict[str, Any], scoring_rubric: Dict[str, Any]) -> Agent:
    """Create the enhanced scoring agent"""
    
    config = prompts.get('scoring_agent', {})
    
    # Create tools list using instances
    tools = [
        calculate_category_score,
        aggregate_final_scores,
        calculate_focus_areas
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