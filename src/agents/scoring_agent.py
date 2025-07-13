from crewai import Agent
from crewai.tools import tool
from typing import Dict, Any, List, Tuple
import logging
from ..utils.json_helper import safe_parse_json
import json
import re

logger = logging.getLogger(__name__)

# Constants for scoring
MIN_ANSWER_LENGTH = 20
DEFAULT_SCORES = {
    "owner_dependence": 5.0,
    "revenue_quality": 5.0,
    "financial_readiness": 5.0,
    "operational_resilience": 5.0,
    "growth_value": 5.0
}

# Helper functions
def safe_pattern_match(text: str, pattern: str) -> bool:
    """Safely match pattern in text"""
    if not text or len(text) < 10:
        return False
    try:
        return bool(re.search(pattern, text, re.I))
    except:
        return False

def extract_percentages(text: str) -> List[int]:
    """Safely extract percentages from text"""
    if not text:
        return []
    try:
        percentages = re.findall(r'(\d+)%', text)
        return [int(p) for p in percentages if 0 <= int(p) <= 100]
    except:
        return []

def analyze_pronoun_usage(text: str) -> Dict[str, Any]:
    """Analyze I/me vs we/our language"""
    if not text or len(text) < MIN_ANSWER_LENGTH:
        return {"ratio": 1.0, "pattern": "neutral"}
    
    first_person = len(re.findall(r'\b(I|me|my|myself)\b', text, re.I))
    team_language = len(re.findall(r'\b(we|our|team|us)\b', text, re.I))
    
    if team_language > 0:
        ratio = first_person / (team_language + 1)
    else:
        ratio = first_person
    
    if ratio > 3:
        return {"ratio": ratio, "pattern": "highly_owner_centric"}
    elif ratio > 1.5:
        return {"ratio": ratio, "pattern": "owner_focused"}
    elif team_language > first_person:
        return {"ratio": ratio, "pattern": "team_oriented"}
    else:
        return {"ratio": ratio, "pattern": "balanced"}

@tool("calculate_category_score")
def calculate_category_score(category_data=None) -> str:
    """
    Calculate sophisticated score for a category using multiple factors
    """
    try:
        logger.info(f"=== CALCULATE CATEGORY SCORE CALLED ===")
        logger.info(f"Input type: {type(category_data)}")
        logger.info(f"Input preview: {str(category_data)[:200] if category_data else 'No data provided'}...")
        
        # Handle case where CrewAI doesn't pass any arguments
        if category_data is None:
            logger.warning("No category data provided - using default scoring")
            return json.dumps({
                "error": "No category data provided",
                "score": 5.0,
                "gaps": ["Unable to analyze - no data"],
                "strengths": []
            })
        
        # Use safe JSON parsing
        data = safe_parse_json(category_data, {}, "calculate_category_score")
        if not data:
            return json.dumps({
                "error": "No category data provided",
                "score": 5.0,
                "gaps": ["Unable to analyze - no data"],
                "strengths": []
            })
        
        category = data.get('category')
        responses = data.get('responses', {})
        rubric = data.get('rubric', {})
        research_data = data.get('research_data', {})
        
        # Route to appropriate scoring function
        if category == 'owner_dependence':
            result = score_owner_dependence(responses, research_data)
        elif category == 'revenue_quality':
            result = score_revenue_quality(responses, research_data)
        elif category == 'financial_readiness':
            result = score_financial_readiness(responses, research_data)
        elif category == 'operational_resilience':
            result = score_operational_resilience(responses, research_data)
        elif category == 'growth_value':
            result = score_growth_value(responses, research_data)
        else:
            result = {
                "score": DEFAULT_SCORES.get(category, 5.0),
                "error": f"Unknown category: {category}"
            }
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error calculating category score: {str(e)}")
        return json.dumps({
            "error": str(e),
            "score": 5.0,
            "gaps": ["Error in scoring"],
            "strengths": []
        })

def score_owner_dependence(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score owner dependence with sophisticated analysis"""
    # Initialize
    base_score = DEFAULT_SCORES['owner_dependence']
    gaps = []
    strengths = []
    adjustments = []
    
    # Q2 - Days without owner (40% weight)
    q2_response = responses.get("q2", "").strip()
    if q2_response:
        if "Less than 3 days" in q2_response:
            base_score = 2.0
        elif "3-7 days" in q2_response:
            base_score = 4.0
        elif "1-2 weeks" in q2_response:
            base_score = 6.0
        elif "2-4 weeks" in q2_response:
            base_score = 7.5
        elif "More than a month" in q2_response:
            base_score = 9.0
        
        # Industry comparison
        industry_threshold = research_data.get("owner_dependence_threshold", "14 days")
        if base_score < 6:
            gaps.append(f"Below industry standard of {industry_threshold} operation without owner")
    
    # Q1 - Critical tasks analysis (40% weight)
    q1_response = responses.get("q1", "").strip()
    if len(q1_response) > MIN_ANSWER_LENGTH:
        critical_tasks = q1_response.lower()
        
        # Pronoun analysis
        pronoun_analysis = analyze_pronoun_usage(critical_tasks)
        if pronoun_analysis["pattern"] == "highly_owner_centric":
            base_score -= 1.5
            adjustments.append("-1.5: Heavy 'I/me' language indicates owner-centric mindset")
            gaps.append("Owner-centric language throughout")
        elif pronoun_analysis["pattern"] == "team_oriented":
            base_score += 0.5
            adjustments.append("+0.5: Team-oriented language")
            strengths.append("Uses team-oriented language")
        
        # Control language patterns
        control_phrases = [
            (r"all\s+", "handles all aspects", -1.0),
            (r"every\s+", "controls every decision", -0.8),
            (r"only\s+I\s+", "only owner can perform", -1.0),
            (r"personally\s+", "requires personal involvement", -0.7),
            (r"have\s+to\s+check", "approval bottleneck", -0.8),
            (r"final\s+approval", "approval dependency", -0.6),
            (r"nobody\s+else", "no delegation", -1.0),
            (r"don't\s+trust", "trust issues with delegation", -1.2)
        ]
        
        for pattern, description, penalty in control_phrases:
            if safe_pattern_match(critical_tasks, pattern):
                base_score += penalty
                adjustments.append(f"{penalty}: {description}")
                gaps.append(description.capitalize())
        
        # Positive indicators
        if safe_pattern_match(critical_tasks, r"team|delegate|manager|supervisor"):
            base_score += 0.5
            adjustments.append("+0.5: Shows delegation awareness")
            strengths.append("Some delegation structure exists")
        
        # Client relationship dependency
        if "client" in critical_tasks and any(word in critical_tasks for word in ["meeting", "relationship", "expect"]):
            base_score -= 1.0
            adjustments.append("-1.0: Client relationships tied to owner")
            gaps.append("Client relationships dependent on owner")
    
    # Q7 - Key person risk compounds owner risk (20% weight)
    q7_response = responses.get("q7", "").strip()
    if len(q7_response) > MIN_ANSWER_LENGTH:
        key_employee = q7_response.lower()
        
        # Check for succession potential
        role_overlap_terms = [
            ("certif", "certif"),
            ("client", "relationship"),
            ("approv", "senior"),
            ("pric", "financ"),
            ("quality", "quality"),
            ("technical", "technical")
        ]
        
        succession_potential = 0
        if q1_response and q7_response:
            for task_term, employee_term in role_overlap_terms:
                if task_term in critical_tasks and employee_term in key_employee:
                    succession_potential += 1
            
            if succession_potential > 0:
                base_score += 0.5
                adjustments.append("+0.5: Key employee could potentially take over some owner tasks")
                strengths.append("Potential succession candidate identified")
            elif len(q7_response) > 50:
                gaps.append("Key employees' skills don't overlap with owner's critical tasks")
        
        # Long tenure risk
        if any(year in key_employee for year in ["10 year", "15 year", "20 year"]):
            base_score -= 0.3
            adjustments.append("-0.3: Long-tenured key person adds to dependency risk")
            gaps.append("Long-tenured key person dependency")
    
    # Ensure score stays in bounds
    final_score = max(1.0, min(10.0, base_score))
    
    # Get industry context
    expected_discount = research_data.get("owner_dependence_discount", "15-25%")
    if final_score < 4:
        impact = f"Expected {expected_discount} valuation discount"
    else:
        impact = "Acceptable to most buyers"
    
    return {
        "score": round(final_score, 1),
        "weight": 0.25,
        "scoring_breakdown": {
            "base_score": DEFAULT_SCORES['owner_dependence'],
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Unable to identify specific strengths from provided data"],
        "gaps": gaps if gaps else ["Limited data for detailed analysis"],
        "industry_context": {
            "benchmark": research_data.get("owner_dependence_threshold", "14+ days operation"),
            "current_position": q2_response if q2_response else "Not specified",
            "impact": impact
        }
    }

def score_revenue_quality(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score revenue quality with concentration and recurring analysis"""
    # Initialize
    base_score = DEFAULT_SCORES['revenue_quality']
    gaps = []
    strengths = []
    adjustments = []
    
    # Q4 - Recurring revenue percentage (50% weight)
    q4_response = responses.get("q4", "").strip()
    if q4_response:
        if "0-20%" in q4_response:
            base_score = 2.0
        elif "20-40%" in q4_response:
            base_score = 4.0
        elif "40-60%" in q4_response:
            base_score = 6.0
        elif "60-80%" in q4_response:
            base_score = 7.5
        elif "Over 80%" in q4_response:
            base_score = 9.0
        elif "Unsure" in q4_response:
            base_score = 3.0
            gaps.append("Recurring revenue not tracked")
        
        # Check against industry threshold
        recurring_threshold = research_data.get("recurring_revenue_threshold", "60%")
        if "60-80%" in q4_response or "Over 80%" in q4_response:
            strengths.append(f"Exceeds industry threshold of {recurring_threshold} recurring")
    
    # Q3 - Revenue mix analysis (50% weight)
    q3_response = responses.get("q3", "").strip()
    if len(q3_response) > MIN_ANSWER_LENGTH:
        revenue_mix = q3_response.lower()
        
        # Extract percentages
        percentages = extract_percentages(q3_response)
        if percentages:
            largest_concentration = max(percentages)
            
            # Concentration risk
            concentration_threshold = int(research_data.get("concentration_threshold", "30").replace("%", ""))
            if largest_concentration > concentration_threshold:
                penalty = (largest_concentration - concentration_threshold) * 0.05
                base_score -= penalty
                adjustments.append(f"-{penalty:.1f}: {largest_concentration}% concentration exceeds {concentration_threshold}% threshold")
                gaps.append(f"{largest_concentration}% revenue concentration (high risk)")
            
            # Diversification bonus
            if len(percentages) >= 4:
                base_score += 0.5
                adjustments.append("+0.5: Well-diversified revenue streams")
                strengths.append(f"Diversified across {len(percentages)} revenue sources")
            elif len(percentages) == 1:
                base_score -= 1.0
                adjustments.append("-1.0: Single revenue source")
                gaps.append("No revenue diversification")
        
        # Contract analysis
        contract_indicators = [
            (r"(\d+)[-\s]year\s+(?:contract|agreement)", "multi-year contracts", 0.8),
            (r"retainer", "retainer-based revenue", 0.5),
            (r"subscription", "subscription model", 0.7),
            (r"automatic\s+renewal", "auto-renewal contracts", 0.6),
            (r"month[-\s]to[-\s]month", "unstable month-to-month", -0.5)
        ]
        
        for pattern, description, impact in contract_indicators:
            if safe_pattern_match(revenue_mix, pattern):
                base_score += impact
                adjustments.append(f"{impact:+.1f}: {description}")
                if impact > 0:
                    strengths.append(description.capitalize())
                else:
                    gaps.append(description.capitalize())
        
        # Client relationship analysis
        if safe_pattern_match(revenue_mix, r"personal|prefer|relationship"):
            base_score -= 0.5
            adjustments.append("-0.5: Personal relationship dependency indicated")
            gaps.append("Revenue tied to personal relationships")
        
        # Sector concentration
        sectors = re.findall(r'(automotive|aerospace|defense|government|healthcare|retail|financial)', revenue_mix, re.I)
        if sectors and len(set(sectors)) == 1:
            base_score -= 0.5
            adjustments.append(f"-0.5: Single sector concentration ({sectors[0]})")
            gaps.append(f"Industry concentration risk: {sectors[0]}")
    
    # Ensure score stays in bounds
    final_score = max(1.0, min(10.0, base_score))
    
    # Industry context
    recurring_premium = research_data.get("recurring_revenue_premium", "15-25%")
    concentration_discount = research_data.get("concentration_discount", "20-30%")
    
    return {
        "score": round(final_score, 1),
        "weight": 0.25,
        "scoring_breakdown": {
            "base_score": DEFAULT_SCORES['revenue_quality'],
            "adjustments": adjustments,
            "final_score": round(final_score, 1)
        },
        "strengths": strengths if strengths else ["Unable to identify specific strengths"],
        "gaps": gaps if gaps else ["Limited data for analysis"],
        "industry_context": {
            "recurring_threshold": research_data.get("recurring_revenue_threshold", "60%"),
            "concentration_threshold": research_data.get("concentration_threshold", "30%"),
            "impact": f"Premium: {recurring_premium} | Risk: {concentration_discount} discount"
        }
    }

def score_financial_readiness(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score financial readiness and profitability trends"""
    # Initialize
    base_score = 0.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q5 - Financial confidence (60% weight)
    q5_response = responses.get("q5", "").strip()
    if q5_response:
        try:
            financial_confidence = float(q5_response)
            base_score = financial_confidence * 0.6
            
            if financial_confidence >= 8:
                strengths.append("High confidence in financial records")
            elif financial_confidence >= 6:
                strengths.append("Reasonable financial documentation")
            elif financial_confidence <= 4:
                gaps.append("Low confidence in financial records")
                gaps.append("Due diligence likely to uncover issues")
            
            # Cross-check with documentation score if available
            q8_response = responses.get("q8", "")
            if q8_response:
                try:
                    doc_score = float(q8_response)
                    if financial_confidence >= 8 and doc_score <= 4:
                        base_score *= 0.9
                        adjustments.append("-10%: High confidence despite poor documentation")
                        gaps.append("Potential overconfidence in financials")
                    elif financial_confidence <= 4 and doc_score >= 7:
                        base_score *= 1.1
                        adjustments.append("+10%: Conservative assessment despite good documentation")
                        strengths.append("Conservative financial self-assessment")
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
            "benchmark": "Buyers expect 3+ years clean financials",
            "margin_expectations": research_data.get("margin_expectations", "Stable or improving"),
            "impact": "Financial clarity critical for valuation confidence"
        }
    }

def score_operational_resilience(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score operational resilience and systematization"""
    # Initialize
    base_score = 0.0
    gaps = []
    strengths = []
    adjustments = []
    
    # Q8 - Documentation score (60% weight)
    q8_response = responses.get("q8", "").strip()
    if q8_response:
        try:
            documentation_score = float(q8_response)
            base_score = documentation_score * 0.6
            
            if documentation_score >= 8:
                strengths.append("Excellent process documentation")
                # Check for ISO mention in Q9
                q9_response = responses.get("q9", "")
                if q9_response and "iso" in q9_response.lower():
                    base_score += 0.5
                    adjustments.append("+0.5: ISO certification validates documentation")
                    strengths.append("ISO certification supports systematic operations")
            elif documentation_score >= 6:
                strengths.append("Good process documentation")
            elif documentation_score <= 3:
                gaps.append("Minimal process documentation")
                gaps.append("Knowledge transfer risk high")
        except:
            base_score = 3.0
    else:
        base_score = 3.0
        gaps.append("No documentation score provided")
    
    # Q7 - Key person dependencies (40% weight)
    q7_response = responses.get("q7", "").strip()
    if len(q7_response) > MIN_ANSWER_LENGTH:
        key_employee = q7_response.lower()
        
        # Analyze dependency depth
        critical_indicators = [
            (r"only\s+(?:person|one|employee)", "single person dependency", -1.0),
            (r"(\d+)\s+years?\s+(?:experience|knowledge)", "deep experience dependency", -0.5),
            (r"relationship", "relationship dependency", -0.7),
            (r"would\s+be\s+(?:impossible|very\s+difficult)", "critical dependency", -1.0),
            (r"certifi", "certification dependency", -0.6),
            (r"no\s+one\s+else", "no backup identified", -0.8)
        ]
        
        dependency_score = 0
        for pattern, description, impact in critical_indicators:
            if safe_pattern_match(key_employee, pattern):
                dependency_score += impact
                adjustments.append(f"{impact}: {description}")
                gaps.append(description.capitalize())
        
        # Positive indicators
        if safe_pattern_match(key_employee, r"team|backup|cross-train|document"):
            dependency_score += 0.5
            adjustments.append("+0.5: Mitigation efforts mentioned")
            strengths.append("Some redundancy or training mentioned")
        
        # Apply dependency score
        if dependency_score < -2:
            base_score += 0.5
            gaps.append("Multiple critical dependencies on key employee")
        elif dependency_score < -1:
            base_score += 2.0
            gaps.append("Significant key person risk")
        else:
            base_score += 3.5
            if dependency_score > 0:
                strengths.append("Limited key person dependencies")
    else:
        base_score += 2.0  # Neutral if no data
    
    # Business maturity indicators
    all_responses = " ".join(responses.values()).lower()
    maturity_score = 0
    
    positive_indicators = ["dashboard", "kpi", "metrics", "automated", "system", "process", "procedure"]
    negative_indicators = ["figure it out", "always done", "my way", "just know"]
    
    for indicator in positive_indicators:
        if indicator in all_responses:
            maturity_score += 0.2
    
    for indicator in negative_indicators:
        if indicator in all_responses:
            maturity_score -= 0.3
    
    if maturity_score > 0.5:
        base_score += 0.5
        adjustments.append("+0.5: Mature business language indicates systematization")
        strengths.append("Professional systems terminology used")
    elif maturity_score < -0.5:
        base_score -= 0.5
        adjustments.append("-0.5: Informal language suggests ad-hoc operations")
        gaps.append("Informal operational approach")
    
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
        "strengths": strengths if strengths else ["Unable to identify specific strengths"],
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
    q9_response = responses.get("q9", "").strip()
    if len(q9_response) > MIN_ANSWER_LENGTH:
        value_description = q9_response.lower()
        
        # High-value indicators with scoring
        value_indicators = {
            # Intellectual property and exclusivity
            "proprietary": (1.0, "Proprietary assets/methods"),
            "patent": (1.2, "Patent protection"),
            "exclusive": (0.8, "Exclusive arrangements"),
            "trademark": (0.6, "Trademark protection"),
            
            # Certifications and barriers
            "certification": (0.7, "Industry certifications"),
            "iso": (0.7, "ISO certification"),
            "license": (0.6, "Required licenses"),
            "accredit": (0.7, "Accreditation"),
            
            # Competitive advantages
            "only": (0.6, "Unique position"),
            "unique": (0.5, "Unique offering"),
            "competitive advantage": (1.0, "Clear competitive advantage"),
            "barrier": (0.8, "Entry barriers"),
            "moat": (1.0, "Competitive moat"),
            
            # Relationships and contracts
            "long-term": (0.6, "Long-term arrangements"),
            "contract": (0.5, "Contracted advantages"),
            "partnership": (0.6, "Strategic partnerships"),
            "preferred": (0.7, "Preferred status"),
            
            # Specialization
            "specialized": (0.7, "Specialized capability"),
            "rare": (0.8, "Rare expertise/equipment"),
            "custom": (0.5, "Customized solutions"),
            "niche": (0.6, "Niche market position")
        }
        
        value_score = 0
        identified_advantages = []
        
        for indicator, (points, description) in value_indicators.items():
            if safe_pattern_match(value_description, rf'\b{indicator}\b'):
                value_score += points
                identified_advantages.append(description)
                adjustments.append(f"+{points}: {description}")
        
        # Cap at 4.0 additional points but track if more
        uncapped_score = value_score
        value_score = min(value_score, 4.0)
        base_score += value_score
        
        if uncapped_score > 4.0:
            strengths.append(f"Multiple strong value drivers ({len(identified_advantages)} identified)")
        elif len(identified_advantages) > 0:
            strengths.extend(identified_advantages[:3])  # Top 3
        else:
            gaps.append("No clear competitive advantages articulated")
        
        # Quantification bonus
        numbers_found = re.findall(r'\$?\d+[KMkmm]?|\d+%|\d+\+?\s*year', value_description)
        if len(numbers_found) >= 2:
            base_score += 0.5
            adjustments.append("+0.5: Quantified value propositions")
            strengths.append("Value drivers are quantified")
        elif len(identified_advantages) > 0 and len(numbers_found) == 0:
            gaps.append("Value claims lack quantification")
        
        # Asset value analysis
        asset_matches = re.findall(r'\$(\d+(?:\.\d+)?)\s*([KMkmm])?', value_description)
        total_asset_value = 0
        for amount, multiplier in asset_matches:
            value = float(amount)
            if multiplier in ['M', 'm']:
                value *= 1000000
            elif multiplier in ['K', 'k']:
                value *= 1000
            total_asset_value += value
        
        if total_asset_value >= 1000000:
            base_score += 0.5
            adjustments.append(f"+0.5: Significant tangible assets (${total_asset_value:,.0f})")
            strengths.append(f"Valuable tangible assets: ${total_asset_value:,.0f}")
        
        # Geographic advantage
        if safe_pattern_match(value_description, r'only\s+(?:one|company|provider)\s+in\s+(?:the\s+)?(?:region|area|state|city)'):
            base_score += 0.8
            adjustments.append("+0.8: Geographic market advantage")
            strengths.append("Geographic monopoly/oligopoly position")
        
        # Competitive validation
        if "competitor" in value_description and any(word in value_description for word in ["can't", "cannot", "unable"]):
            base_score += 0.5
            adjustments.append("+0.5: Competitors cannot replicate")
            strengths.append("Difficult to replicate advantages")
    else:
        gaps.append("No value drivers provided for analysis")
    
    # Cross-reference with operational strength
    q8_score = responses.get("q8", "")
    if q8_score:
        try:
            if float(q8_score) >= 7 and base_score >= 6:
                base_score += 0.3
                adjustments.append("+0.3: Strong operations support growth potential")
        except:
            pass
    
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
        "strengths": strengths if strengths else ["Unable to identify specific value drivers"],
        "gaps": gaps if gaps else ["Limited information on unique value"],
        "industry_context": {
            "benchmark": "Buyers pay premiums for defensible competitive advantages",
            "impact": "Strong value drivers can add 20-40% to valuation multiples"
        }
    }

@tool("aggregate_final_scores")
def aggregate_final_scores(all_scores=None) -> str:
    """
    Calculate weighted overall score and readiness level
    """
    try:
        logger.info(f"=== AGGREGATE FINAL SCORES CALLED ===")
        logger.info(f"Input type: {type(all_scores)}")
        
        # Handle case where CrewAI doesn't pass any arguments
        if all_scores is None:
            logger.warning("No scores data provided - using defaults")
            return json.dumps({
                "error": "No scores data provided",
                "overall_score": 5.0,
                "readiness_level": "Unable to Calculate"
            })
        
        # Use safe JSON parsing
        data = safe_parse_json(all_scores, {}, "aggregate_final_scores")
        if not data:
            return json.dumps({
                "error": "No scores data provided",
                "overall_score": 5.0,
                "readiness_level": "Unable to Calculate"
            })
        
        category_scores = data.get('category_scores', {})
        
        # Calculate weighted average
        total_weight = 0
        weighted_sum = 0
        
        for category, score_data in category_scores.items():
            score = score_data.get('score', 5.0)
            weight = score_data.get('weight', 0.20)
            weighted_sum += score * weight
            total_weight += weight
        
        overall_score = weighted_sum / total_weight if total_weight > 0 else 5.0
        
        # Determine readiness level
        if overall_score >= 8.1:
            readiness_level = "Exit Ready"
            readiness_description = "Well-positioned for a successful exit"
        elif overall_score >= 6.6:
            readiness_level = "Approaching Ready"
            readiness_description = "Solid foundation with clear improvement areas"
        elif overall_score >= 4.1:
            readiness_level = "Needs Work"
            readiness_description = "Significant improvements needed before exit"
        else:
            readiness_level = "Not Ready"
            readiness_description = "Major transformation required"
        
        # Risk factor analysis
        risk_factors = {
            'high_owner_dependence': category_scores.get('owner_dependence', {}).get('score', 10) < 4,
            'revenue_concentration': any('concentration' in gap and '%' in gap 
                                       for gap in category_scores.get('revenue_quality', {}).get('gaps', [])),
            'poor_documentation': category_scores.get('operational_resilience', {}).get('score', 10) < 4,
            'declining_margins': any('decline' in gap.lower() 
                                   for gap in category_scores.get('financial_readiness', {}).get('gaps', [])),
            'no_value_drivers': category_scores.get('growth_value', {}).get('score', 10) < 4
        }
        
        active_risks = sum(1 for risk in risk_factors.values() if risk)
        
        # Compound risk adjustment
        if active_risks >= 4:
            overall_score *= 0.9
            risk_note = "Multiple risk factors compound buyer concerns"
        elif active_risks >= 3:
            overall_score *= 0.95
            risk_note = "Several risk factors present"
        elif active_risks == 0:
            overall_score *= 1.05
            risk_note = "Limited risk factors increase attractiveness"
        else:
            risk_note = ""
        
        return json.dumps({
            "overall_score": round(overall_score, 1),
            "readiness_level": readiness_level,
            "readiness_description": readiness_description,
            "active_risk_count": active_risks,
            "risk_factors": risk_factors,
            "risk_note": risk_note,
            "calculation_method": "weighted_average_with_risk_adjustment"
        })
        
    except Exception as e:
        logger.error(f"Error aggregating scores: {str(e)}")
        return json.dumps({
            "error": str(e),
            "overall_score": 5.0,
            "readiness_level": "Unable to Calculate"
        })

@tool("calculate_focus_areas")
def calculate_focus_areas(assessment_data=None) -> str:
    """
    Determine priority focus areas based on ROI calculation
    """
    try:
        logger.info(f"=== CALCULATE FOCUS AREAS CALLED ===")
        logger.info(f"Input type: {type(assessment_data)}")
        
        # Handle case where CrewAI doesn't pass any arguments
        if assessment_data is None:
            logger.warning("No assessment data provided - using defaults")
            return json.dumps({
                "error": "No assessment data provided",
                "primary_focus": None
            })
        
        # Use safe JSON parsing
        data = safe_parse_json(assessment_data, {}, "calculate_focus_areas")
        if not data:
            return json.dumps({
                "error": "No assessment data provided",
                "primary_focus": None
            })
        
        category_scores = data.get('category_scores', {})
        research_data = data.get('research_data', {})
        exit_timeline = data.get('exit_timeline', 'Unknown')
        responses = data.get('responses', {})
        
        focus_scores = []
        
        for category, score_data in category_scores.items():
            current_score = score_data.get('score', 5.0)
            potential_improvement = 10 - current_score
            
            # Get improvement data from research
            improvements = research_data.get('improvements', {})
            category_improvement = improvements.get(category, {})
            
            # Default values if not in research
            typical_timeline = category_improvement.get('timeline_months', 6)
            typical_impact = category_improvement.get('value_impact', 0.15)
            
            # Timeline urgency multiplier
            timeline_multiplier = 1.0
            if "Already in discussions" in exit_timeline:
                timeline_multiplier = 3.0 if typical_timeline <= 3 else 0.3
            elif "1-2 years" in exit_timeline:
                timeline_multiplier = 2.0 if typical_timeline <= 6 else 0.7
            elif "2-3 years" in exit_timeline:
                timeline_multiplier = 1.5
            else:
                timeline_multiplier = 1.0
            
            # Check for value killers
            is_value_killer = False
            killer_reason = ""
            
            if category == "owner_dependence" and current_score < 4:
                is_value_killer = True
                killer_reason = "Severe owner dependence will deter most buyers"
                typical_impact *= 2
            
            elif category == "revenue_quality":
                # Check for high concentration
                gaps = score_data.get('gaps', [])
                for gap in gaps:
                    if 'concentration' in gap and '%' in gap:
                        try:
                            concentration = int(re.search(r'(\d+)%', gap).group(1))
                            if concentration > 40:
                                is_value_killer = True
                                killer_reason = f"{concentration}% revenue concentration is a deal breaker"
                                typical_impact *= 1.5
                                break
                        except:
                            pass
            
            # Calculate ROI score
            effort_factor = 1.0 / (typical_timeline / 6)  # 6 months = baseline
            roi_score = potential_improvement * typical_impact * timeline_multiplier * effort_factor * 100
            
            if is_value_killer:
                roi_score *= 2  # Double priority for value killers
            
            # Determine quick win potential
            is_quick_win = typical_timeline <= 3 and typical_impact >= 0.1
            
            # Generate specific reasoning
            reasoning = generate_focus_reasoning(
                category, current_score, is_value_killer, killer_reason,
                is_quick_win, typical_timeline, typical_impact
            )
            
            focus_scores.append({
                'category': category,
                'roi_score': round(roi_score, 1),
                'current_score': current_score,
                'improvement_potential': round(potential_improvement, 1),
                'is_value_killer': is_value_killer,
                'is_quick_win': is_quick_win,
                'typical_timeline_months': typical_timeline,
                'expected_impact': f"{int(typical_impact * 100)}%",
                'reasoning': reasoning
            })
        
        # Sort by ROI score
        focus_scores.sort(key=lambda x: x['roi_score'], reverse=True)
        
        # Get specific action items for top priorities
        for i, focus in enumerate(focus_scores[:3]):
            focus['quick_actions'] = generate_quick_actions(
                focus['category'],
                category_scores[focus['category']],
                responses
            )
        
        return json.dumps({
            'primary_focus': focus_scores[0] if focus_scores else None,
            'secondary_focus': focus_scores[1] if len(focus_scores) > 1 else None,
            'tertiary_focus': focus_scores[2] if len(focus_scores) > 2 else None,
            'all_focus_areas': focus_scores
        })
        
    except Exception as e:
        logger.error(f"Error calculating focus areas: {str(e)}")
        return json.dumps({"error": str(e), "primary_focus": None})

def generate_focus_reasoning(category, score, is_value_killer, killer_reason, 
                           is_quick_win, timeline, impact):
    """Generate specific reasoning for focus area priority"""
    
    base_reasons = {
        'owner_dependence': "Owner involvement directly impacts valuation and sale feasibility",
        'revenue_quality': "Revenue predictability and concentration are key buyer concerns",
        'financial_readiness': "Clean financials are essential for due diligence",
        'operational_resilience': "Systematic operations reduce buyer risk",
        'growth_value': "Clear value drivers justify premium valuations"
    }
    
    reasoning = base_reasons.get(category, "Important for exit readiness")
    
    if is_value_killer:
        reasoning = f"CRITICAL: {killer_reason}. Must address before any serious buyer discussions."
    elif is_quick_win:
        reasoning += f". Quick win opportunity: {int(impact*100)}% impact achievable in {timeline} months."
    elif score < 4:
        reasoning += f". Currently scoring {score}/10 - significant improvement needed."
    
    return reasoning

def generate_quick_actions(category, score_data, responses):
    """Generate specific quick actions based on category and gaps"""
    
    actions = []
    gaps = score_data.get('gaps', [])
    
    if category == 'owner_dependence':
        if any('certification' in gap for gap in gaps):
            actions.append("Schedule certification training for senior team member")
        if any('approval' in gap for gap in gaps):
            actions.append("Create approval matrix delegating decisions under $50K")
        if any('client' in gap for gap in gaps):
            actions.append("Begin introducing senior team to key clients")
            
    elif category == 'revenue_quality':
        if any('concentration' in gap for gap in gaps):
            actions.append("Develop plan to acquire 3 new major clients")
        if any('month-to-month' in gap for gap in gaps):
            actions.append("Convert top 5 clients to annual contracts")
        if not any('contract' in str(responses.get('q3', '')).lower() for gap in gaps):
            actions.append("Implement formal service agreements")
            
    elif category == 'financial_readiness':
        if any('confidence' in gap for gap in gaps):
            actions.append("Engage CPA for financial cleanup project")
        if any('not tracked' in gap for gap in gaps):
            actions.append("Implement monthly P&L reviews")
            
    elif category == 'operational_resilience':
        if any('documentation' in gap for gap in gaps):
            actions.append("Document top 5 critical processes using templates")
        if any('key person' in gap for gap in gaps):
            actions.append("Create succession plan for key employee")
            
    elif category == 'growth_value':
        if any('quantification' in gap for gap in gaps):
            actions.append("Quantify and document all competitive advantages")
        if any('No clear' in gap for gap in gaps):
            actions.append("Conduct competitive analysis to identify unique value")
    
    # Default actions if none specific
    if not actions:
        actions = [
            f"Address top gap: {gaps[0]}" if gaps else f"Improve {category}",
            "Schedule consultation to develop improvement plan"
        ]
    
    return actions[:3]  # Return top 3 actions

def create_scoring_agent(llm, prompts: Dict[str, Any], scoring_rubric: Dict[str, Any]) -> Agent:
    """Create the enhanced scoring agent"""
    
    config = prompts.get('scoring_agent', {})
    
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