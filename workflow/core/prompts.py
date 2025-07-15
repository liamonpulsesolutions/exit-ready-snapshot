"""
All LLM prompts consolidated from YAML files and CrewAI agents.
Pure prompt templates for use in workflow nodes.
"""

# Research prompts
RESEARCH_PROMPTS = {
    "industry_trends": """
For small to medium {industry} businesses in {location} (revenue {revenue_range}) planning to exit in 2025:

VALUATION BENCHMARKS (150 words max):
1. Current revenue and EBITDA multiples for businesses this size
2. Multiple variations for:
   - Recurring revenue threshold that creates premium (e.g., 60%+) and premium amount
   - High owner dependence vs distributed leadership - quantify discount/premium
   - Client concentration threshold affecting valuation (e.g., 30%+) and impact
3. Top 2 factors causing valuation discounts

IMPROVEMENT STRATEGIES (200 words max):
3 proven improvement examples:
1. Reducing owner dependence (with timeline)
2. Systematizing operations (with timeline)  
3. Improving revenue quality (with timeline)
Include measurable impact on valuation where available.

MARKET CONDITIONS (100 words max):
1. Current buyer priorities for businesses this size in 2025
2. Average time to sell
3. Most important trend affecting valuations

Requirements:
- Total response under 500 words
- Focus on SME businesses in the {revenue_range} range specifically
- Cite source name and year inline (e.g., "per IBISWorld 2025")
- Prioritize data from: M&A databases, broker associations, industry reports
""",
    
    "exit_benchmarks": """
For {industry} businesses:
1. Typical revenue multiples for business sales
2. Typical EBITDA multiples
3. Average time to sell a business
4. Success rate of business sales

Provide specific ranges and cite sources where possible.
Focus on small to medium businesses ($1M-$20M revenue).
"""
}

# Summary generation prompts
SUMMARY_PROMPTS = {
    "executive_summary": """
Create a compelling executive summary for a business exit readiness assessment.

Business Details:
- Industry: {industry}
- Location: {location}
- Years in Business: {years_in_business}
- Exit Timeline: {exit_timeline}

Assessment Results:
- Overall Score: {overall_score}/10
- Readiness Level: {readiness_level}
- Strongest Area: {strongest_area} ({strongest_score}/10)
- Weakest Area: {weakest_area} ({weakest_score}/10)

Requirements:
1. Open with personalized acknowledgment of their specific situation
2. State overall readiness and what it means
3. Highlight 2-3 most important findings
4. Include value proposition (current vs potential)
5. End with encouraging but realistic assessment
6. Keep between 200-250 words
7. Use "you/your" throughout (not "the owner")
8. Balance honesty with encouragement

Tone: Professional yet approachable, empathetic but direct
""",
    
    "category_analysis": """
Analyze the {category} assessment results and provide actionable insights.

Score: {score}/10
Strengths: {strengths}
Gaps: {gaps}
Industry Context: {industry_context}

Create a 150-200 word analysis that includes:
1. Score Interpretation (40-50 words): What this score means in their industry
2. Strengths Identified (40-50 words): 2-3 specific strengths and why they matter
3. Critical Gaps (40-50 words): 1-2 most important gaps and their impact
4. Action Plan (60-70 words): 30-day, 90-day, and 6-month actions with expected outcomes

Make it specific, actionable, and tied to real value creation.
Use second person ("you/your") throughout.
""",
    
    "recommendations": """
Generate comprehensive recommendations based on assessment results.

Focus Areas:
- Primary: {primary_focus} (score: {primary_score}/10)
- Secondary: {secondary_focus} (score: {secondary_score}/10)
- Exit Timeline: {exit_timeline}

Create recommendations with:
1. Quick Wins (30 Days): 3 specific actions with exact steps
2. Strategic Priorities (3-6 Months): 3 initiatives with implementation roadmaps
3. Critical Focus Area: THE ONE area that matters most with specific weekly actions

For each recommendation include:
- Specific action steps
- Expected outcome/impact
- Success metrics
- Resource requirements

Total length: 250-300 words
Tone: Action-oriented, specific, encouraging
"""
}

# QA validation prompts
QA_PROMPTS = {
    "consistency_check": """
Review the scoring data for logical consistency.

Scores: {scores}
Responses: {responses}

Check for:
1. Overall score alignment with category averages
2. Justifications matching score levels
3. Response patterns supporting scores
4. Any contradictions or anomalies

Return: Clear pass/fail with specific issues if found
""",
    
    "quality_check": """
Review content quality for professional standards.

Content: {content}

Check for:
1. Placeholder text or incomplete sections
2. Professional tone and language
3. Specific vs generic recommendations
4. Appropriate length and detail

Return: Quality score (0-10) with specific issues
""",
    
    "pii_scan": """
Scan for any remaining personally identifiable information.

Content: {content}

Look for:
1. Email addresses
2. Phone numbers
3. Names (not properly anonymized)
4. Company names (outside of placeholders)
5. Any other PII

Return: Pass/fail with any PII found
"""
}

# Industry-specific context additions
INDUSTRY_CONTEXTS = {
    "professional_services": {
        "key_factors": "Client relationships, recurring contracts, knowledge transfer, certifications",
        "typical_multiples": "4-6x EBITDA for established firms, higher for specialized practices",
        "buyer_concerns": "Client concentration, key person dependency, contract transferability"
    },
    "manufacturing": {
        "key_factors": "Equipment condition, supply contracts, customer diversification, IP/patents",
        "typical_multiples": "3-5x EBITDA, varies by specialization and automation level",
        "buyer_concerns": "Equipment age, customer concentration, supplier dependencies"
    },
    "retail": {
        "key_factors": "Location value, inventory management, online presence, brand strength",
        "typical_multiples": "2-4x EBITDA, higher for e-commerce enabled",
        "buyer_concerns": "Lease terms, inventory turnover, online competition"
    },
    "healthcare": {
        "key_factors": "Regulatory compliance, patient retention, provider contracts, equipment",
        "typical_multiples": "5-7x EBITDA for practices, varies by specialty",
        "buyer_concerns": "Compliance history, payer mix, provider stability"
    },
    "technology": {
        "key_factors": "Recurring revenue, IP ownership, technical debt, team retention",
        "typical_multiples": "3-8x revenue for SaaS, 5-10x EBITDA for services",
        "buyer_concerns": "Code quality, customer churn, key developer retention"
    }
}

# Locale-specific terminology
LOCALE_TERMS = {
    "us": {
        "currency": "USD",
        "currency_symbol": "$",
        "revenue": "revenue",
        "solicitor": "attorney",
        "accountant": "CPA",
        "date_format": "MM/DD/YYYY"
    },
    "uk": {
        "currency": "GBP", 
        "currency_symbol": "£",
        "revenue": "turnover",
        "solicitor": "solicitor",
        "accountant": "chartered accountant",
        "date_format": "DD/MM/YYYY"
    },
    "au": {
        "currency": "AUD",
        "currency_symbol": "$",
        "revenue": "revenue",
        "solicitor": "solicitor",
        "accountant": "accountant",
        "date_format": "DD/MM/YYYY"
    }
}

# Report templates
REPORT_TEMPLATES = {
    "section_header": """
{title}
{underline}

""",
    
    "score_display": """
SCORE: {score}/10 - {interpretation}
""",
    
    "action_item": """
□ {action}
  Timeline: {timeline}
  Impact: {impact}
""",
    
    "footer": """
CONFIDENTIAL BUSINESS ASSESSMENT
Prepared by: On Pulse Solutions
Report Date: {date}
Valid for: 90 days

This report contains proprietary analysis and recommendations specific to your business. 
The insights and strategies outlined are based on your assessment responses and current market conditions.

© On Pulse Solutions - Exit Ready Snapshot Assessment
"""
}

# Scoring interpretation templates
SCORING_INTERPRETATIONS = {
    "score_ranges": {
        "excellent": (8.0, 10.0, "exceptional and well above buyer expectations"),
        "good": (6.5, 7.9, "solid with some room for improvement"),
        "fair": (4.5, 6.4, "below average and needs focused attention"),
        "poor": (0.0, 4.4, "concerning and requires immediate action")
    },
    
    "readiness_levels": {
        "exit_ready": (8.1, 10.0, "Exit Ready", "Your business is exceptionally well-prepared for a premium exit"),
        "approaching_ready": (6.6, 8.0, "Approaching Ready", "Your business is well-positioned with specific improvements needed"),
        "needs_work": (4.1, 6.5, "Needs Work", "Your business requires focused improvements before exit"),
        "not_ready": (0.0, 4.0, "Not Ready", "Your business needs substantial preparation for exit")
    }
}

# Email templates (for future use)
EMAIL_TEMPLATES = {
    "report_delivery": """
Subject: Your Exit Ready Snapshot Assessment Results - {company_name}

Dear {owner_name},

Thank you for completing the Exit Ready Snapshot assessment. Your personalized report is attached.

Key Findings:
- Overall Exit Readiness: {overall_score}/10
- Readiness Level: {readiness_level}
- Primary Focus Area: {primary_focus}

Your report includes:
✓ Detailed analysis of 5 critical exit readiness factors
✓ Personalized recommendations and action plans
✓ Industry benchmarks and market context
✓ Clear next steps for value enhancement

Next Steps:
1. Review your report with your leadership team
2. Focus on the Quick Wins identified for immediate impact
3. Consider our Exit Value Growth Plan for deeper analysis

I'm available to discuss your results and answer any questions.

Best regards,
{advisor_name}
On Pulse Solutions

P.S. Business owners who implement our recommendations typically see 15-30% value increases within 12 months.
""",
    
    "follow_up": """
Subject: Ready to Implement Your Exit Value Improvements?

{owner_name},

It's been a week since you received your Exit Ready Snapshot assessment. I wanted to check in and see if you have any questions about your results.

Your assessment identified {primary_focus} as your biggest opportunity for value enhancement, with potential for {value_increase} increase in sale value.

Many business owners find it helpful to discuss their results with an expert who can:
- Clarify the recommendations
- Help prioritize improvements
- Create a detailed implementation roadmap
- Connect you with specialized resources

Would you like to schedule a brief call to discuss your next steps?

Best regards,
{advisor_name}
"""
}

def get_prompt(category: str, subcategory: str, **kwargs) -> str:
    """
    Get a formatted prompt with variables replaced.
    
    Args:
        category: Main prompt category (e.g., 'research', 'summary')
        subcategory: Specific prompt within category
        **kwargs: Variables to format into the prompt
        
    Returns:
        Formatted prompt string
    """
    prompt_categories = {
        'research': RESEARCH_PROMPTS,
        'summary': SUMMARY_PROMPTS,
        'qa': QA_PROMPTS,
        'report': REPORT_TEMPLATES,
        'email': EMAIL_TEMPLATES
    }
    
    if category not in prompt_categories:
        raise ValueError(f"Unknown prompt category: {category}")
    
    prompts = prompt_categories[category]
    
    if subcategory not in prompts:
        raise ValueError(f"Unknown prompt subcategory: {subcategory} in {category}")
    
    prompt_template = prompts[subcategory]
    
    try:
        return prompt_template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing required variable for prompt: {e}")


def get_industry_context(industry: str) -> Dict[str, str]:
    """Get industry-specific context"""
    # Normalize industry name
    industry_key = industry.lower().replace(' ', '_').replace('&', 'and')
    
    # Return specific context or empty dict
    return INDUSTRY_CONTEXTS.get(industry_key, {})


def get_locale_terms(locale: str) -> Dict[str, str]:
    """Get locale-specific terminology"""
    return LOCALE_TERMS.get(locale, LOCALE_TERMS['us'])


def get_score_interpretation(score: float) -> str:
    """Get interpretation for a specific score"""
    for range_name, (min_score, max_score, interpretation) in SCORING_INTERPRETATIONS['score_ranges'].items():
        if min_score <= score <= max_score:
            return interpretation
    return "score out of expected range"


def get_readiness_level(score: float) -> Tuple[str, str]:
    """Get readiness level and description for overall score"""
    for level_name, (min_score, max_score, level, description) in SCORING_INTERPRETATIONS['readiness_levels'].items():
        if min_score <= score <= max_score:
            return level, description
    return "Unknown", "Score out of expected range"