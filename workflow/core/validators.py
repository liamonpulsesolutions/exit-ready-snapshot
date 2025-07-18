"""
Pure validation functions extracted from CrewAI agents.
No tool wrappers, just business logic.
"""

import re
from typing import Dict, Any, List, Tuple, Optional


def validate_form_data(form_data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate that all required form fields are present and properly formatted.
    
    Returns:
        Tuple of (is_valid, missing_fields, validation_details)
    """
    required_fields = [
        'uuid', 'name', 'email', 'industry', 'years_in_business',
        'age_range', 'exit_timeline', 'location', 'responses'
    ]
    
    optional_fields = ['revenue_range']
    
    missing_fields = []
    validation_details = {
        'total_fields': len(required_fields),
        'missing_required': [],
        'missing_optional': [],
        'response_count': 0,
        'missing_responses': []
    }
    
    # Check required fields
    for field in required_fields:
        if field not in form_data or not form_data[field]:
            missing_fields.append(field)
            validation_details['missing_required'].append(field)
    
    # Check optional fields
    for field in optional_fields:
        if field not in form_data or not form_data[field]:
            validation_details['missing_optional'].append(field)
    
    # Validate responses
    if 'responses' in form_data:
        responses = form_data.get('responses', {})
        validation_details['response_count'] = len(responses)
        
        # Check for all 10 questions
        expected_questions = [f"q{i}" for i in range(1, 11)]
        for q in expected_questions:
            if q not in responses or not responses[q]:
                validation_details['missing_responses'].append(q)
    
    is_valid = len(missing_fields) == 0 and len(validation_details['missing_responses']) == 0
    
    return is_valid, missing_fields, validation_details


def validate_email(email: str) -> bool:
    """Validate email format"""
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_pattern.match(email))


def validate_scoring_consistency(scores: Dict[str, Dict], responses: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate that scores align with their justifications and responses.
    
    Returns:
        Dictionary with consistency analysis
    """
    issues = []
    warnings = []
    
    # Extract category scores
    category_scores = {}
    for category, data in scores.items():
        if isinstance(data, dict) and 'score' in data:
            category_scores[category] = data['score']
    
    if not category_scores:
        return {
            'is_consistent': False,
            'issues': ['No scores found to validate'],
            'warnings': [],
            'analysis': {}
        }
    
    # Check overall score alignment
    if 'overall' in scores:
        overall = scores['overall']
        if isinstance(overall, (int, float)):
            # Calculate expected overall
            weighted_sum = 0
            total_weight = 0
            for cat, data in scores.items():
                if cat != 'overall' and isinstance(data, dict):
                    score = data.get('score', 0)
                    weight = data.get('weight', 0.2)
                    weighted_sum += score * weight
                    total_weight += weight
            
            expected_overall = weighted_sum / total_weight if total_weight > 0 else 0
            
            if abs(overall - expected_overall) > 1.5:
                issues.append(f"Overall score ({overall}) doesn't match weighted average ({expected_overall:.1f})")
    
    # Check for extreme variations
    score_values = [v for v in category_scores.values() if isinstance(v, (int, float))]
    if score_values and len(score_values) > 1:
        variance = max(score_values) - min(score_values)
        if variance > 5:
            warnings.append(f"Large score variance ({variance:.1f}) between categories")
    
    # Check for missing justifications on low scores
    for category, data in scores.items():
        if isinstance(data, dict):
            score = data.get('score', 10)
            gaps = data.get('gaps', [])
            if score < 4 and len(gaps) == 0:
                issues.append(f"Low score ({score}) in {category} lacks gap identification")
    
    return {
        'is_consistent': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'analysis': {
            'categories_validated': len(category_scores),
            'score_range': [min(score_values), max(score_values)] if score_values else [0, 0],
            'average_score': sum(score_values) / len(score_values) if score_values else 0
        }
    }


def validate_content_quality(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check content for completeness, clarity, and professional tone.
    
    Returns:
        Dictionary with quality assessment
    """
    issues = []
    warnings = []
    quality_score = 10.0
    
    # Check for placeholder text
    placeholder_patterns = [
        r'\[.*?\]',  # Brackets indicating placeholders
        r'TODO',
        r'PLACEHOLDER',
        r'INSERT.*HERE',
        r'X\.X',  # Placeholder numbers
    ]
    
    # Check executive summary
    exec_summary = content.get('executive_summary', '')
    if exec_summary:
        for pattern in placeholder_patterns:
            if re.search(pattern, exec_summary, re.IGNORECASE):
                issues.append(f"Placeholder text found in executive summary: {pattern}")
                quality_score -= 2.0
        
        if len(exec_summary.split()) < 150:
            warnings.append("Executive summary too brief (< 150 words)")
            quality_score -= 1.0
    else:
        issues.append("Missing executive summary")
        quality_score -= 3.0
    
    # Check recommendations
    recommendations = content.get('recommendations', {})
    if isinstance(recommendations, dict):
        if 'quick_wins' not in recommendations:
            issues.append("Missing quick wins section")
            quality_score -= 1.0
        if 'strategic_priorities' not in recommendations:
            issues.append("Missing strategic priorities")
            quality_score -= 1.0
    
    # Check category summaries
    category_summaries = content.get('category_summaries', {})
    if len(category_summaries) < 5:
        issues.append(f"Missing category summaries ({len(category_summaries)}/5)")
        quality_score -= 2.0
    
    # Check for minimum content length
    for category, summary in category_summaries.items():
        if isinstance(summary, str) and len(summary.split()) < 50:
            warnings.append(f"{category} summary too brief")
            quality_score -= 0.5
    
    # Check tone
    unprofessional_terms = ['gonna', 'wanna', 'stuff', 'things', 'etc.']
    all_content = str(content)
    for term in unprofessional_terms:
        if term in all_content.lower():
            warnings.append(f"Unprofessional language: '{term}'")
            quality_score -= 0.5
    
    quality_score = max(0, quality_score)
    
    return {
        'quality_score': quality_score,
        'passed': quality_score >= 7.0,
        'issues': issues,
        'warnings': warnings,
        'analysis': {
            'has_executive_summary': bool(exec_summary),
            'has_recommendations': bool(recommendations),
            'category_count': len(category_summaries),
            'total_word_count': len(all_content.split())
        }
    }


def scan_for_pii(content: Any) -> Dict[str, Any]:
    """
    Scan content for any remaining PII that wasn't properly anonymized.
    
    Returns:
        Dictionary with PII scan results
    """
    pii_patterns = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    }
    
    # Convert content to string for scanning
    if isinstance(content, dict):
        content_str = str(content)
    else:
        content_str = str(content)
    
    pii_found = []
    
    for pii_type, pattern in pii_patterns.items():
        matches = re.findall(pattern, content_str)
        if matches:
            # Filter out false positives
            filtered_matches = []
            for match in matches:
                # FIXED: Filter empty phone matches
                if pii_type == 'phone':
                    # Ensure the match has actual digits and isn't just formatting
                    if match and len(str(match).strip()) > 0:
                        # Extract just digits to check if it's a real phone number
                        digits_only = re.sub(r'\D', '', str(match))
                        if len(digits_only) >= 7:  # Minimum for a valid phone number
                            filtered_matches.append(match)
                elif pii_type == 'ip_address':
                    # Check if it's actually a score like "8.5.7.6"
                    parts = match.split('.')
                    try:
                        if all(0 <= int(part) <= 10 for part in parts):
                            continue  # Skip scores
                    except:
                        pass
                    filtered_matches.append(match)
                else:
                    # For other types, include if not empty
                    if match and str(match).strip():
                        filtered_matches.append(match)
            
            if filtered_matches:
                pii_found.append({
                    'type': pii_type,
                    'count': len(filtered_matches),
                    'samples': filtered_matches[:3]  # First 3 examples
                })
    
    # Check for potential names
    name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
    potential_names = re.findall(name_pattern, content_str)
    
    # FIXED: Extended business term whitelist
    safe_phrases = [
        # Original safe phrases
        'Exit Ready', 'Quick Wins', 'Strategic Priorities', 
        'Professional Services', 'Owner Dependence', 'Revenue Quality',
        'Financial Readiness', 'Operational Resilience', 'Growth Value',
        'On Pulse', 'Exit Value', 'United States', 'Pacific Western',
        # Additional business terms to whitelist
        'Overall Score', 'Readiness Level', 'Needs Work', 'Exit Ready',
        'Approaching Ready', 'Not Ready', 'Executive Summary', 'Your Score',
        'Critical Focus', 'Next Steps', 'Your Business', 'Business Owner',
        'Category Analysis', 'Industry Context', 'Market Context',
        'Value Enhancement', 'Due Diligence', 'Exit Timeline', 'Exit Process',
        'Business Assessment', 'Personalized Recommendations', 'Action Plan',
        'Implementation Support', 'Confidential Assessment', 'Report Date',
        'Proprietary Analysis', 'Market Conditions', 'Buyer Priorities',
        'Industry Benchmark', 'Best Practices', 'Key Findings', 'Value Proposition',
        'Competitive Position', 'Growth Potential', 'Unique Value',
        'Customer Concentration', 'Recurring Revenue', 'Profit Margins',
        'Management Team', 'Process Documentation', 'Knowledge Transfer',
        'Risk Mitigation', 'Value Creation', 'Exit Strategy', 'Business Value',
        'Sale Process', 'Transition Planning', 'Succession Planning',
        'Strategic Improvements', 'Operational Efficiency', 'Financial Performance',
        'Market Position', 'Competitive Advantage', 'Industry Standards',
        'Performance Metrics', 'Success Factors', 'Risk Factors',
        'Value Drivers', 'Growth Opportunities', 'Improvement Areas',
        'Action Items', 'Time Frame', 'Resource Requirements',
        'Expected Outcomes', 'Implementation Timeline', 'Priority Areas',
        'Focus Areas', 'Development Plan', 'Enhancement Opportunities',
        'Business Systems', 'Quality Standards', 'Client Relationships',
        'Team Development', 'Leadership Transition', 'Organizational Structure',
        'Business Processes', 'Standard Operating', 'Operating Procedures',
        'Financial Systems', 'Management Systems', 'Control Systems',
        'Performance Management', 'Quality Management', 'Risk Management',
        'Change Management', 'Project Management', 'Time Management',
        'Resource Management', 'Talent Management', 'Knowledge Management',
        'Customer Management', 'Vendor Management', 'Contract Management',
        'Data Management', 'Information Systems', 'Technology Systems',
        'Business Intelligence', 'Market Intelligence', 'Competitive Intelligence',
        'Strategic Planning', 'Business Planning', 'Financial Planning',
        'Capacity Planning', 'Resource Planning', 'Succession Planning',
        'Exit Planning', 'Transition Planning', 'Implementation Planning',
        'Risk Assessment', 'Value Assessment', 'Market Assessment',
        'Performance Assessment', 'Readiness Assessment', 'Financial Assessment',
        'Operational Assessment', 'Strategic Assessment', 'Comprehensive Assessment',
        'Industry Analysis', 'Market Analysis', 'Financial Analysis',
        'Competitive Analysis', 'Gap Analysis', 'SWOT Analysis',
        'Risk Analysis', 'Cost Analysis', 'Benefit Analysis',
        'Investment Analysis', 'Return Analysis', 'Valuation Analysis',
        'Due Diligence', 'Financial Audit', 'Operational Audit',
        'Compliance Audit', 'Quality Audit', 'Process Audit',
        'Internal Audit', 'External Audit', 'Third Party',
        'Service Provider', 'Solution Provider', 'Strategic Partner',
        'Business Partner', 'Joint Venture', 'Strategic Alliance',
        'Industry Leader', 'Market Leader', 'Best Practice',
        'Gold Standard', 'Industry Standard', 'Market Standard',
        'Performance Standard', 'Quality Standard', 'Service Standard',
        'Professional Standard', 'Ethical Standard', 'Compliance Standard',
        'Regulatory Compliance', 'Legal Compliance', 'Industry Compliance',
        'Quality Compliance', 'Safety Compliance', 'Environmental Compliance',
        'Data Protection', 'Information Security', 'Cyber Security',
        'Physical Security', 'Asset Protection', 'Intellectual Property',
        'Trade Secrets', 'Proprietary Information', 'Confidential Information',
        'Business Information', 'Market Information', 'Customer Information',
        'Financial Information', 'Operating Information', 'Strategic Information'
    ]
    
    real_names = [name for name in potential_names if name not in safe_phrases]
    
    if real_names:
        pii_found.append({
            'type': 'potential_names',
            'count': len(real_names),
            'samples': real_names[:3]
        })
    
    return {
        'has_pii': len(pii_found) > 0,
        'pii_found': pii_found,
        'total_items': sum(item['count'] for item in pii_found),
        'scan_complete': True
    }


def validate_report_structure(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure the report has all required sections and proper structure.
    
    Returns:
        Dictionary with structure validation results
    """
    required_sections = {
        'executive_summary': 'Executive Summary',
        'category_scores': 'Category Scores',
        'category_summaries': 'Category Summaries',
        'recommendations': 'Recommendations',
        'next_steps': 'Next Steps'
    }
    
    missing_sections = []
    incomplete_sections = []
    
    for key, name in required_sections.items():
        if key not in report or not report[key]:
            missing_sections.append(name)
        elif isinstance(report[key], (str, list)) and len(str(report[key])) < 10:
            incomplete_sections.append(name)
    
    # Check category completeness
    expected_categories = [
        'owner_dependence', 'revenue_quality', 'financial_readiness',
        'operational_resilience', 'growth_value'
    ]
    
    if 'category_scores' in report:
        missing_categories = []
        for cat in expected_categories:
            if cat not in report['category_scores']:
                missing_categories.append(cat)
        if missing_categories:
            incomplete_sections.append(f"Missing categories: {', '.join(missing_categories)}")
    
    structure_valid = len(missing_sections) == 0 and len(incomplete_sections) == 0
    completeness_score = (5 - len(missing_sections) - len(incomplete_sections) * 0.5) / 5 * 10
    
    return {
        'is_valid': structure_valid,
        'completeness_score': max(0, completeness_score),
        'missing_sections': missing_sections,
        'incomplete_sections': incomplete_sections,
        'has_all_categories': len(missing_categories) == 0 if 'missing_categories' in locals() else False,
        'section_count': sum(1 for key in required_sections if key in report and report[key])
    }