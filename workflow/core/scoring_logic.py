"""
Pure scoring functions with dynamic industry benchmarking.
Uses research data to apply industry-specific thresholds.
"""

import re
from typing import Dict, Any, List, Tuple, Optional


def extract_industry_benchmarks(research_data: Dict[str, Any], industry: str) -> Dict[str, Any]:
    """
    Extract industry-specific benchmarks from research data.
    Falls back to generic values if specific data not found.
    """
    benchmarks = {}
    
    # Try to get from research data first
    valuation_data = research_data.get('valuation_benchmarks', {})
    
    # Extract owner dependence days threshold
    owner_data = valuation_data.get('owner_dependence', {})
    if isinstance(owner_data, dict):
        days_str = owner_data.get('days_threshold', '14 days')
        # Extract number from string like "14 days" or "7-14 days"
        match = re.search(r'(\d+)', str(days_str))
        benchmarks['owner_independence_days'] = int(match.group(1)) if match else 14
        
        # Get discount range
        discount = owner_data.get('discount', '20-30%')
        benchmarks['owner_dependence_discount'] = discount
    else:
        benchmarks['owner_independence_days'] = 14
        benchmarks['owner_dependence_discount'] = '20-30%'
    
    # Extract customer concentration threshold
    concentration_data = valuation_data.get('customer_concentration', {})
    if isinstance(concentration_data, dict):
        threshold_str = concentration_data.get('threshold', '25%')
        match = re.search(r'(\d+)', str(threshold_str))
        benchmarks['concentration_threshold'] = int(match.group(1)) if match else 25
        benchmarks['concentration_discount'] = concentration_data.get('discount', '15-20%')
    else:
        benchmarks['concentration_threshold'] = 25
        benchmarks['concentration_discount'] = '15-20%'
    
    # Extract recurring revenue threshold
    recurring_data = valuation_data.get('recurring_revenue', {})
    if isinstance(recurring_data, dict):
        threshold_str = recurring_data.get('threshold', '60%')
        match = re.search(r'(\d+)', str(threshold_str))
        benchmarks['recurring_threshold'] = int(match.group(1)) if match else 60
        benchmarks['recurring_premium'] = recurring_data.get('premium', '1.5-2.0x')
    else:
        benchmarks['recurring_threshold'] = 60
        benchmarks['recurring_premium'] = '1.5-2.0x'
    
    # Extract profit margin expectations
    margin_data = valuation_data.get('profit_margins', {})
    if isinstance(margin_data, dict):
        # Check for industry-specific margins
        by_industry = margin_data.get('by_industry', {})
        if industry in by_industry:
            benchmarks['expected_margin'] = by_industry[industry]
        else:
            benchmarks['expected_margin'] = margin_data.get('expected_EBITDA', '15-20%')
    else:
        benchmarks['expected_margin'] = '15-20%'
    
    # Check for industry-specific thresholds in fallback data
    industry_thresholds = research_data.get('industry_specific_thresholds', {})
    if industry in industry_thresholds:
        industry_data = industry_thresholds[industry]
        # Override with industry-specific values if available
        if 'owner_independence' in industry_data:
            match = re.search(r'(\d+)', industry_data['owner_independence'])
            if match:
                benchmarks['owner_independence_days'] = int(match.group(1))
        if 'customer_concentration' in industry_data:
            match = re.search(r'(\d+)', industry_data['customer_concentration'])
            if match:
                benchmarks['concentration_threshold'] = int(match.group(1))
        if 'recurring_revenue' in industry_data:
            match = re.search(r'(\d+)', industry_data['recurring_revenue'])
            if match:
                benchmarks['recurring_threshold'] = int(match.group(1))
    
    return benchmarks


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
    """Score owner dependence category with dynamic benchmarks"""
    # Extract industry from responses
    industry = responses.get("industry", "Professional Services")
    
    # Get dynamic benchmarks
    benchmarks = extract_industry_benchmarks(research_data, industry)
    days_threshold = benchmarks['owner_independence_days']
    discount_range = benchmarks['owner_dependence_discount']
    
    base_score = 5.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q1 - Owner's daily involvement
    q1_response = responses.get("q1", "").strip()
    if q1_response:
        owner_mentions = q1_response.lower().count("i ") + q1_response.lower().count("me ") + q1_response.lower().count("my ")
        
        if owner_mentions > 5:
            base_score -= 3.0  # FIXED: Use -= instead of =
            gaps.append("Extremely high owner involvement in daily operations")
            adjustments.append("-3.0: Very high owner centrality")
        elif owner_mentions > 3:
            base_score -= 1.5  # FIXED: Use -= instead of =
            gaps.append("Significant owner involvement in operations")
            adjustments.append("-1.5: High owner involvement")
        elif "everything" in q1_response.lower() or "all" in q1_response.lower():
            base_score -= 2.5  # FIXED: Use -= instead of =
            gaps.append("Owner handles too many critical functions")
            adjustments.append("-2.5: Owner handles everything")
        elif "team" in q1_response.lower() or "delegate" in q1_response.lower():
            base_score += 2.0  # FIXED: Use += instead of =
            strengths.append("Shows delegation to team members")
            adjustments.append("+2.0: Good delegation evident")
    
    # Q2 - Time away capability (using dynamic threshold)
    q2_response = responses.get("q2", "").strip()
    if q2_response:
        time_impact = 0.0
        
        # Extract days from response
        if "None" in q2_response or "0 days" in q2_response:
            actual_days = 0
        elif "Less than 3 days" in q2_response:
            actual_days = 2
        elif "3-7 days" in q2_response:
            actual_days = 5
        elif "1-2 weeks" in q2_response:
            actual_days = 10
        elif "2-4 weeks" in q2_response:
            actual_days = 21
        elif "More than a month" in q2_response:
            actual_days = 35
        else:
            actual_days = 7  # Default
        
        # Score based on industry-specific threshold
        if actual_days == 0:
            time_impact = -2.0
            gaps.append(f"Business cannot operate without owner (industry expects {days_threshold} days)")
            adjustments.append(f"-2.0: Zero independence vs {days_threshold} day standard")
        elif actual_days < days_threshold / 2:
            time_impact = -1.0
            gaps.append(f"Well below industry standard of {days_threshold} days")
            adjustments.append(f"-1.0: Only {actual_days} days vs {days_threshold} expected")
        elif actual_days < days_threshold:
            time_impact = 0.0
            gaps.append(f"Below industry standard of {days_threshold} days")
            adjustments.append(f"0.0: {actual_days} days approaching {days_threshold} standard")
        elif actual_days >= days_threshold * 2:
            time_impact = 3.5
            strengths.append(f"Exceeds industry standard of {days_threshold} days")
            adjustments.append(f"+3.5: {actual_days} days well above {days_threshold} standard")
        else:
            time_impact = 2.0
            strengths.append(f"Meets industry standard of {days_threshold} days")
            adjustments.append(f"+2.0: {actual_days} days meets {days_threshold} standard")
        
        base_score += time_impact  # FIXED: Now properly adds to base_score
    
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
            "benchmark": f"{industry} buyers expect business to run {days_threshold}+ days without owner",
            "impact": f"High owner dependence can reduce value by {discount_range}",
            "industry": industry,
            "threshold_used": days_threshold
        }
    }


def score_revenue_quality(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score revenue quality and predictability with dynamic benchmarks"""
    # Extract industry
    industry = responses.get("industry", "Professional Services")
    
    # Get dynamic benchmarks
    benchmarks = extract_industry_benchmarks(research_data, industry)
    concentration_threshold = benchmarks['concentration_threshold']
    concentration_discount = benchmarks['concentration_discount']
    recurring_threshold = benchmarks['recurring_threshold']
    recurring_premium = benchmarks['recurring_premium']
    
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
            base_score += 1.0  # FIXED: Use += instead of =
            strengths.append(f"Diversified revenue streams ({revenue_items} sources)")
            adjustments.append(f"+1.0: {revenue_items} revenue streams")
        elif revenue_items == 1:
            base_score -= 1.0  # FIXED: Use -= instead of =
            gaps.append("Single revenue stream creates risk")
            adjustments.append("-1.0: Single revenue stream")
        
        # Check for recurring revenue indicators
        if any(word in q3_response.lower() for word in ['subscription', 'recurring', 'monthly', 'annual', 'contract']):
            base_score += 1.5  # FIXED: Use += instead of =
            strengths.append(f"Recurring revenue model (premium at {recurring_threshold}%+)")
            adjustments.append(f"+1.5: Recurring revenue present")
    
    # Q4 - Customer concentration (using dynamic threshold)
    q4_response = responses.get("q4", "").strip()
    if q4_response:
        concentration_impact = 0.0
        
        # Determine concentration level
        if "0-20%" in q4_response:
            actual_concentration = 10
        elif "20-40%" in q4_response:
            actual_concentration = 30
        elif "40-60%" in q4_response:
            actual_concentration = 50
        elif "60-80%" in q4_response:
            actual_concentration = 70
        elif "80-100%" in q4_response:
            actual_concentration = 90
        else:
            actual_concentration = 30  # Default
        
        # Score based on industry-specific threshold
        if actual_concentration < concentration_threshold:
            concentration_impact = 2.5
            strengths.append(f"Excellent diversification (below {concentration_threshold}% threshold)")
            adjustments.append(f"+2.5: {actual_concentration}% concentration below {concentration_threshold}% threshold")
        elif actual_concentration < concentration_threshold * 1.5:
            concentration_impact = 0.5
            gaps.append(f"Approaching concentration risk threshold of {concentration_threshold}%")
            adjustments.append(f"+0.5: {actual_concentration}% approaching {concentration_threshold}% threshold")
        elif actual_concentration < concentration_threshold * 2:
            concentration_impact = -1.5
            gaps.append(f"High concentration risk (above {concentration_threshold}% threshold)")
            adjustments.append(f"-1.5: {actual_concentration}% exceeds {concentration_threshold}% threshold")
        else:
            concentration_impact = -2.5
            gaps.append(f"Critical concentration - {concentration_discount} discount likely")
            adjustments.append(f"-2.5: {actual_concentration}% far exceeds {concentration_threshold}% threshold")
        
        base_score += concentration_impact  # FIXED: Now properly adds to base_score
    
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
            "benchmark": f"{industry} buyers prefer <{concentration_threshold}% customer concentration",
            "impact": f"High concentration can trigger {concentration_discount} discount",
            "recurring_expectation": f"{recurring_threshold}%+ recurring for {recurring_premium} premium",
            "industry": industry,
            "thresholds_used": {
                "concentration": concentration_threshold,
                "recurring": recurring_threshold
            }
        }
    }


def score_financial_readiness(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score financial readiness category with industry profit expectations"""
    # Extract industry
    industry = responses.get("industry", "Professional Services")
    
    # Get expected margins for industry
    benchmarks = extract_industry_benchmarks(research_data, industry)
    expected_margin = benchmarks['expected_margin']
    
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
                base_score += 4.5  # FIXED: Use += instead of =
                strengths.append("Exceptional financial confidence indicates strong systems")
                adjustments.append("+4.5: Very high financial confidence")
            elif confidence >= 7:
                base_score += 3.5  # FIXED: Use += instead of =
                strengths.append("Strong financial confidence")
                adjustments.append("+3.5: Good financial confidence")
            elif confidence >= 5:
                base_score += 2.5  # FIXED: Use += instead of =
                adjustments.append("+2.5: Moderate financial confidence")
            else:
                base_score += 1.5  # FIXED: Use += instead of =
                gaps.append("Low financial confidence suggests poor visibility")
                adjustments.append("+1.5: Low financial confidence")
                
                if confidence <= 2:
                    gaps.append("Critical: Buyers will see this as high risk")
        except:
            base_score += 3.0  # Default moderate adjustment
    
    # Q6 - Profit margin trend (with industry context)
    q6_response = responses.get("q6", "").strip()
    if q6_response:
        margin_impact = 0.0
        if "Declined significantly" in q6_response:
            margin_impact = -4.5  # FIXED: Changed from 0.5 to -4.5 for significant decline
            gaps.append(f"Significant margin decline vs {expected_margin} industry standard")
            adjustments.append("-4.5: Significant margin decline")
        elif "Declined slightly" in q6_response:
            margin_impact = -3.5  # FIXED: Changed from 1.5 to -3.5 for slight decline
            gaps.append("Margin pressure evident")
            adjustments.append("-3.5: Slight margin decline")
        elif "Stayed flat" in q6_response:
            margin_impact = -2.5  # FIXED: Changed from 2.5 to -2.5 (flat is neutral/slight negative)
            strengths.append(f"Stable margins (industry expects {expected_margin})")
            adjustments.append("-2.5: Stable margins")
        elif "Improved slightly" in q6_response:
            margin_impact = -2.0  # FIXED: Changed from 3.0 to -2.0 (slight improvement from base)
            strengths.append("Improving profit margins")
            adjustments.append("-2.0: Improving margins")
        elif "Improved significantly" in q6_response:
            margin_impact = -1.0  # FIXED: Changed from 4.0 to -1.0 (significant improvement)
            strengths.append(f"Strong margin growth vs {expected_margin} benchmark")
            adjustments.append("-1.0: Significant margin improvement")
        
        base_score += margin_impact  # Now properly adds to base_score
    
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
            "benchmark": f"{industry} expects {expected_margin} EBITDA margins",
            "impact": "Strong financials can add 20-30% to valuation",
            "industry": industry,
            "margin_expectation": expected_margin
        }
    }


def score_operational_resilience(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score operational resilience category with industry-specific expectations"""
    # Extract industry
    industry = responses.get("industry", "Professional Services")
    
    # Industry-specific documentation expectations
    documentation_expectations = {
        "Manufacturing": "High (ISO standards expected)",
        "Healthcare": "Very High (compliance critical)",
        "Technology": "High (code documentation and IP)",
        "Professional Services": "Medium (client procedures)",
        "Retail": "Medium (operations manual)"
    }
    
    doc_expectation = documentation_expectations.get(industry, "Medium")
    
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
            base_score -= 3.0  # FIXED: Use -= instead of =
            gaps.append("Critical knowledge concentrated in one person")
            adjustments.append("-3.0: High key person risk")
        elif "team" in q7_response.lower() or "several" in q7_response.lower():
            base_score += 2.0  # FIXED: Use += instead of =
            strengths.append("Knowledge distributed across team")
            adjustments.append("+2.0: Good knowledge distribution")
        else:
            base_score -= 1.0  # FIXED: Use -= instead of =
            gaps.append("Some key person dependencies exist")
            adjustments.append("-1.0: Some key person risk")
    
    # Q8 - Process documentation (with industry context)
    q8_response = responses.get("q8", "").strip()
    if q8_response:
        try:
            # Extract confidence score
            if q8_response.isdigit():
                doc_score = int(q8_response)
            else:
                match = re.search(r'(\d+)', q8_response)
                doc_score = int(match.group(1)) if match else 5
            
            # Adjust expectations based on industry
            if "High" in doc_expectation or "Very High" in doc_expectation:
                # Industries with high documentation needs
                if doc_score >= 8:
                    base_score += 2.5  # FIXED: Use += instead of =
                    strengths.append(f"Excellent documentation for {industry} standards")
                    adjustments.append(f"+2.5: Strong documentation for {industry}")
                elif doc_score >= 6:
                    base_score += 1.0  # FIXED: Use += instead of =
                    adjustments.append(f"+1.0: Adequate documentation for {industry}")
                else:
                    base_score -= 1.5  # FIXED: Use -= instead of =
                    gaps.append(f"Poor documentation vs {doc_expectation} industry standard")
                    adjustments.append(f"-1.5: Below {industry} documentation standards")
            else:
                # Industries with moderate documentation needs
                if doc_score >= 7:
                    base_score += 2.0  # FIXED: Use += instead of =
                    strengths.append("Good documentation practices")
                    adjustments.append("+2.0: Good documentation")
                elif doc_score >= 5:
                    base_score += 0.5  # FIXED: Use += instead of =
                    adjustments.append("+0.5: Moderate documentation")
                else:
                    base_score -= 0.5  # FIXED: Use -= instead of =
                    gaps.append("Documentation needs improvement")
                    adjustments.append("-0.5: Poor documentation")
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
            "benchmark": f"{industry} expects {doc_expectation}",
            "impact": "Poor documentation can extend due diligence by 2-3 months",
            "industry": industry,
            "documentation_standard": doc_expectation
        }
    }


def score_growth_value(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score growth potential and unique value with industry context"""
    # Extract industry
    industry = responses.get("industry", "Professional Services")
    
    # Industry-specific value drivers
    industry_value_drivers = {
        "Technology": ["proprietary", "patent", "ip", "saas", "platform", "api"],
        "Healthcare": ["license", "certification", "accreditation", "medicare", "patient base"],
        "Manufacturing": ["patent", "proprietary", "exclusive", "iso", "contract"],
        "Professional Services": ["reputation", "expertise", "certification", "methodology"],
        "Retail": ["brand", "location", "exclusive", "franchise"]
    }
    
    value_keywords = industry_value_drivers.get(industry, ["unique", "proprietary", "exclusive"])
    
    base_score = 3.0  # Start lower since we build up
    gaps = []
    strengths = []
    adjustments = []
    
    # Q9 - Unique value proposition
    q9_response = responses.get("q9", "").strip().lower()
    if q9_response:
        value_score = 0.0
        value_drivers = []
        
        # Check for industry-specific value indicators
        for keyword in value_keywords:
            if keyword in q9_response:
                value_score += 1.5
                value_drivers.append(f"{keyword} (key for {industry})")
                strengths.append(f"{keyword.title()} - valuable in {industry}")
        
        # Check for general strong indicators
        general_indicators = [
            ("market leader", 1.5, "Market leadership position"),
            ("recurring", 1.0, "Recurring revenue model"),
            ("contract", 0.8, "Long-term contracts"),
            ("relationship", 0.5, "Strong customer relationships")
        ]
        
        for indicator, points, description in general_indicators:
            if indicator in q9_response and description not in value_drivers:
                value_score += points
                value_drivers.append(description)
                strengths.append(description)
        
        # Check for weak indicators
        if "no" in q9_response or "not really" in q9_response or "none" in q9_response:
            value_score = -1.0
            gaps.append(f"No clear competitive advantages for {industry}")
        
        # Apply value driver score (cap at 4.0 to prevent excessive scores)
        base_score += min(4.0, value_score)
        
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
            
            # FIXED: Scale the growth potential impact more reasonably
            growth_impact = growth_potential * 0.3  # This gives 0-3 points for 0-10 score
            base_score += growth_impact
            adjustments.append(f"+{growth_impact:.1f}: Growth potential score")
            
            if growth_potential >= 8:
                strengths.append(f"High growth confidence in {industry} market")
            elif growth_potential <= 3:
                gaps.append("Limited growth expectations")
        except:
            base_score += 1.5  # Default moderate growth
            adjustments.append("+1.5: Default growth potential")
    
    # Ensure score stays in bounds
    final_score = max(1.0, min(10.0, base_score))
    
    # Get industry key value driver from research
    valuation_data = research_data.get('valuation_benchmarks', {})
    key_driver = "competitive advantages"
    if 'key_value_driver' in research_data.get('industry_specific_thresholds', {}).get(industry, {}):
        key_driver = research_data['industry_specific_thresholds'][industry]['key_value_driver']
    
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
            "benchmark": f"Premium valuations in {industry} require strong {key_driver}",
            "impact": "Strong value drivers can increase multiples by 2-3x",
            "industry": industry,
            "key_value_drivers": value_keywords[:3]
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