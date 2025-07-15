"""
Pure scoring functions extracted from CrewAI agents.
No tool wrappers, just business logic.
"""

import re
from typing import Dict, Any, List, Tuple


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


def score_owner_dependence(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score owner dependence category"""
    base_score = 5.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q1 - Owner's daily involvement
    q1_response = responses.get("q1", "").strip()
    if q1_response:
        owner_mentions = q1_response.lower().count("i ") + q1_response.lower().count("me ") + q1_response.lower().count("my ")
        
        if owner_mentions > 5:
            base_score = 2.0
            gaps.append("Extremely high owner involvement in daily operations")
            adjustments.append("-3.0: Very high owner centrality")
        elif owner_mentions > 3:
            base_score = 3.5
            gaps.append("Significant owner involvement in operations")
            adjustments.append("-1.5: High owner involvement")
        elif "everything" in q1_response.lower() or "all" in q1_response.lower():
            base_score = 2.5
            gaps.append("Owner handles too many critical functions")
            adjustments.append("-2.5: Owner handles everything")
        elif "team" in q1_response.lower() or "delegate" in q1_response.lower():
            base_score = 7.0
            strengths.append("Shows delegation to team members")
            adjustments.append("+2.0: Good delegation evident")
    
    # Q2 - Time away capability
    q2_response = responses.get("q2", "").strip()
    if q2_response:
        time_impact = 0.0
        if "None" in q2_response or "0 days" in q2_response:
            time_impact = -2.0
            gaps.append("Business cannot operate without owner")
            adjustments.append("-2.0: Zero independence")
        elif "Less than 3 days" in q2_response:
            time_impact = -0.5
            gaps.append("Very limited operational independence")
            adjustments.append("-0.5: Less than 3 days independence")
        elif "1-2 weeks" in q2_response:
            time_impact = 1.0
            strengths.append("Moderate operational independence")
            adjustments.append("+1.0: 1-2 weeks independence")
        elif "2-4 weeks" in q2_response:
            time_impact = 2.5
            strengths.append("Good operational independence")
            adjustments.append("+2.5: Up to a month independence")
        elif "More than a month" in q2_response:
            time_impact = 3.5
            strengths.append("Excellent operational independence")
            adjustments.append("+3.5: Over a month independence")
        
        base_score += time_impact
    
    # Ensure score stays in bounds
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.25,
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Some delegation structure exists"],
        "gaps": gaps if gaps else ["No critical owner dependence issues identified"],
        "industry_context": {
            "benchmark": "Buyers expect business to run 14+ days without owner",
            "impact": "High owner dependence can reduce value by 30-50%"
        }
    }


def score_revenue_quality(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score revenue quality and predictability"""
    base_score = 5.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q3 - Revenue streams
    q3_response = responses.get("q3", "").strip()
    if q3_response:
        # Check for diversification
        revenue_items = len([x for x in q3_response.split(',') if x.strip()])
        if revenue_items >= 3:
            base_score += 1.0
            strengths.append(f"Diversified revenue streams ({revenue_items} sources)")
            adjustments.append(f"+1.0: {revenue_items} revenue streams")
        elif revenue_items == 1:
            base_score -= 1.0
            gaps.append("Single revenue stream creates risk")
            adjustments.append("-1.0: Single revenue stream")
        
        # Check for recurring revenue indicators
        if any(word in q3_response.lower() for word in ['subscription', 'recurring', 'monthly', 'annual', 'contract']):
            base_score += 1.5
            strengths.append("Recurring revenue model identified")
            adjustments.append("+1.5: Recurring revenue present")
    
    # Q4 - Customer concentration
    q4_response = responses.get("q4", "").strip()
    if q4_response:
        concentration_impact = 0.0
        if "0-20%" in q4_response:
            concentration_impact = 2.5
            strengths.append("Excellent customer diversification")
            adjustments.append("+2.5: Low concentration (<20%)")
        elif "20-40%" in q4_response:
            concentration_impact = 1.0
            strengths.append("Good customer diversification")
            adjustments.append("+1.0: Moderate concentration")
        elif "40-60%" in q4_response:
            concentration_impact = -1.0
            gaps.append("High customer concentration risk")
            adjustments.append("-1.0: High concentration")
        elif "60-80%" in q4_response or "80-100%" in q4_response:
            concentration_impact = -2.5
            gaps.append("Critical customer concentration - major risk")
            adjustments.append("-2.5: Critical concentration")
        
        base_score += concentration_impact
    
    # Ensure score stays in bounds
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.25,
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Basic revenue structure in place"],
        "gaps": gaps if gaps else ["No critical revenue quality issues"],
        "industry_context": {
            "benchmark": "Buyers prefer <30% customer concentration",
            "impact": "High concentration can reduce multiples by 20-40%"
        }
    }


def score_financial_readiness(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score financial readiness category"""
    base_score = 5.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q5 - Financial confidence
    q5_response = responses.get("q5", "").strip()
    if q5_response:
        try:
            # Handle both numeric and text responses
            if q5_response.isdigit():
                confidence = int(q5_response)
            else:
                # Extract number from text
                match = re.search(r'(\d+)', q5_response)
                confidence = int(match.group(1)) if match else 5
            
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
                
                if confidence <= 2:
                    gaps.append("Critical: Buyers will see this as high risk")
        except:
            base_score = 3.0
    
    # Q6 - Profit margin trend
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
        
        base_score += margin_impact
    
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
        "strengths": strengths if strengths else ["Financial systems in place"],
        "gaps": gaps if gaps else ["No critical financial readiness issues"],
        "industry_context": {
            "benchmark": "Industry expects 15-20% EBITDA margins",
            "impact": "Strong financials can add 20-30% to valuation"
        }
    }


def score_operational_resilience(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score operational resilience category"""
    base_score = 5.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q7 - Key person dependency
    q7_response = responses.get("q7", "").strip()
    if q7_response:
        # Check for critical dependencies
        if any(phrase in q7_response.lower() for phrase in 
               ['only i', 'only me', 'no one else', 'critical knowledge', 'specialized']):
            base_score = 2.0
            gaps.append("Critical knowledge concentrated in one person")
            adjustments.append("-3.0: High key person risk")
        elif "team" in q7_response.lower() or "several" in q7_response.lower():
            base_score = 7.0
            strengths.append("Knowledge distributed across team")
            adjustments.append("+2.0: Good knowledge distribution")
        else:
            base_score = 4.0
            gaps.append("Some key person dependencies exist")
    
    # Q8 - Process documentation
    q8_response = responses.get("q8", "").strip()
    if q8_response:
        try:
            # Extract confidence score
            if q8_response.isdigit():
                doc_score = int(q8_response)
            else:
                match = re.search(r'(\d+)', q8_response)
                doc_score = int(match.group(1)) if match else 5
            
            if doc_score >= 9:
                base_score += 2.5
                strengths.append("Excellent process documentation")
                adjustments.append("+2.5: Comprehensive documentation")
            elif doc_score >= 7:
                base_score += 1.5
                strengths.append("Good documentation practices")
                adjustments.append("+1.5: Good documentation")
            elif doc_score >= 5:
                base_score += 0.5
                adjustments.append("+0.5: Moderate documentation")
            else:
                base_score -= 1.0
                gaps.append("Poor process documentation")
                adjustments.append("-1.0: Poor documentation")
        except:
            pass
    
    # Ensure score stays in bounds
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.15,
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Basic operational structure exists"],
        "gaps": gaps if gaps else ["No critical operational issues"],
        "industry_context": {
            "benchmark": "Buyers expect documented processes and backup for key roles",
            "impact": "Poor documentation can extend due diligence by 2-3 months"
        }
    }


def score_growth_value(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score growth potential and unique value"""
    base_score = 3.0  # Start lower since we build up
    gaps = []
    strengths = []
    adjustments = []
    
    # Q9 - Unique value proposition
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
    
    # Q10 - Growth potential
    q10_response = responses.get("q10", "").strip()
    if q10_response:
        try:
            if q10_response.isdigit():
                growth_potential = int(q10_response)
            else:
                match = re.search(r'(\d+)', q10_response)
                growth_potential = int(match.group(1)) if match else 5
            
            base_score += growth_potential * 0.3
            adjustments.append(f"+{growth_potential * 0.3:.1f}: Growth potential score")
            
            if growth_potential >= 8:
                strengths.append("High growth confidence")
            elif growth_potential <= 3:
                gaps.append("Limited growth expectations")
        except:
            base_score += 1.5
    
    # Ensure score stays in bounds
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.15,
        "scoring_breakdown": {
            "base_score": 3.0,
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Some growth potential exists"],
        "gaps": gaps if gaps else ["Value proposition needs strengthening"],
        "industry_context": {
            "benchmark": "Premium valuations require clear competitive moats",
            "impact": "Strong value drivers can increase multiples by 2-3x"
        }
    }


def calculate_overall_score(category_scores: Dict[str, Dict]) -> Tuple[float, str]:
    """Calculate overall score and readiness level"""
    total_weighted = 0.0
    total_weight = 0.0
    
    for category, data in category_scores.items():
        score = data.get('score', 0)
        weight = data.get('weight', 0)
        total_weighted += score * weight
        total_weight += weight
    
    overall = round(total_weighted / total_weight, 1) if total_weight > 0 else 5.0
    
    # Determine readiness level
    if overall >= 8.1:
        level = "Exit Ready"
    elif overall >= 6.6:
        level = "Approaching Ready"
    elif overall >= 4.1:
        level = "Needs Work"
    else:
        level = "Not Ready"
    
    return overall, level


def identify_focus_areas(category_scores: Dict[str, Dict], exit_timeline: str) -> Dict[str, Any]:
    """Identify top focus areas based on scores and timeline"""
    # Sort by score (lowest first)
    sorted_cats = sorted(
        category_scores.items(),
        key=lambda x: x[1].get('score', 10)
    )
    
    focus_areas = {}
    
    # Primary focus (lowest score)
    if sorted_cats:
        primary = sorted_cats[0]
        focus_areas['primary'] = {
            'category': primary[0],
            'score': primary[1].get('score'),
            'gaps': primary[1].get('gaps', []),
            'impact': calculate_improvement_impact(primary[0], primary[1].get('score'))
        }
    
    # Secondary focus
    if len(sorted_cats) > 1:
        secondary = sorted_cats[1]
        focus_areas['secondary'] = {
            'category': secondary[0],
            'score': secondary[1].get('score'),
            'gaps': secondary[1].get('gaps', [])
        }
    
    # Timeline urgency
    if "Already" in exit_timeline or "6 months" in exit_timeline:
        focus_areas['urgency'] = 'CRITICAL'
    elif "1-2 years" in exit_timeline:
        focus_areas['urgency'] = 'HIGH'
    else:
        focus_areas['urgency'] = 'MODERATE'
    
    return focus_areas


def calculate_improvement_impact(category: str, current_score: float) -> str:
    """Calculate the value impact of improving a category"""
    impact_multipliers = {
        'owner_dependence': 0.3,
        'revenue_quality': 0.25,
        'financial_readiness': 0.2,
        'operational_resilience': 0.2,
        'growth_value': 0.35
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