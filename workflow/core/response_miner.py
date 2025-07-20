"""
Response mining intelligence for Exit Ready Snapshot.
Extracts specific business details, key personnel, competitive advantages,
and other valuable insights from assessment responses for personalization.

IMPORTANT: This module works with anonymized data that has already been 
processed by the intake node. Personal names will appear as [PERSON_NAME],
emails as [EMAIL], etc. The module extracts patterns and context around
these placeholders for later personalization when PII is reinserted.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


def mine_key_insights(anonymized_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract valuable details from anonymized responses for personalization.
    Works with data that has already been PII-redacted by the intake node.
    
    Args:
        anonymized_data: Dictionary containing anonymized form data with 'responses' sub-dict
        
    Returns:
        Dictionary containing extracted insights categorized by type
    """
    logger.info("Starting response mining for personalization insights")
    
    # Extract the responses sub-dictionary
    responses = anonymized_data.get('responses', {})
    
    insights = {
        "key_personnel": extract_personnel_mentions(responses),
        "time_indicators": extract_time_references(responses),
        "competitive_advantages": extract_competitive_advantages(responses),
        "technical_assets": extract_technical_terms(responses),
        "risk_indicators": extract_risk_language(responses),
        "specific_numbers": extract_numbers_with_context(responses),
        "industry_terms": extract_industry_terminology(responses),
        "certifications": extract_certifications_compliance(responses),
        "customer_details": extract_customer_information(responses),
        "operational_details": extract_operational_specifics(responses),
        "unique_phrases": extract_memorable_phrases(responses),
        "business_relationships": extract_relationships(responses),
        "owner_actions": extract_owner_specific_actions(responses)
    }
    
    # Add metadata from anonymized_data (already redacted)
    insights["business_metadata"] = {
        "industry": anonymized_data.get("industry", ""),
        "years_in_business": anonymized_data.get("years_in_business", ""),
        "revenue_range": anonymized_data.get("revenue_range", ""),
        "location": anonymized_data.get("location", ""),
        "exit_timeline": anonymized_data.get("exit_timeline", "")
    }
    
    # Add summary statistics
    insights["mining_summary"] = {
        "total_insights": sum(len(v) if isinstance(v, (list, dict)) else 1 for v in insights.values()),
        "categories_with_data": sum(1 for v in insights.values() if v),
        "most_valuable_category": max(
            [(k, len(v) if isinstance(v, (list, dict)) else 1) for k, v in insights.items()],
            key=lambda x: x[1]
        )[0] if insights else None
    }
    
    logger.info(f"Mined {insights['mining_summary']['total_insights']} insights across "
                f"{insights['mining_summary']['categories_with_data']} categories")
    
    return insights


def extract_personnel_mentions(responses: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Extract mentions of specific people and their roles.
    Note: Names may already be redacted as [PERSON_NAME] or similar by intake node.
    
    Returns:
        List of dicts with name/placeholder, role, context, and risk_level
    """
    personnel = []
    seen_names = set()
    
    # Patterns to identify people mentions (including redacted placeholders)
    patterns = [
        # Redacted name patterns from PII processing
        r'(\[PERSON_?\w*\])\s+(?:has|is|knows|handles|manages|leads|owns)',
        r'(\[NAME_?\w*\])\s+(?:has|is|knows|handles|manages|leads|owns)',
        # Names that might not have been caught by PII (single first names)
        r'\b([A-Z][a-z]+)\s+(?:has|is|knows|handles|manages|leads|owns)',
        r'(?:only |just |)\b([A-Z][a-z]+)\s+(?:can|knows|understands)',
        # Role-based patterns
        r'(?:our |the |my )?([A-Z][a-z]+|\[PERSON_?\w*\]),?\s+(?:who|our|the)\s+(\w+\s?\w*)',
        # Possessive patterns
        r"([A-Z][a-z]+|\[PERSON_?\w*\])'s\s+(\w+\s?\w*)",
        # Generic role mentions without names
        r'(?:our|the|my)\s+(CEO|CFO|CTO|COO|owner|founder|president|manager|director|supervisor)',
    ]
    
    for q_id, response in responses.items():
        if not isinstance(response, str) or not response.strip():
            continue
            
        # Special handling for Q7 (key dependencies)
        if q_id == "q7":
            # More aggressive extraction for dependency questions
            names = re.findall(r'\b([A-Z][a-z]+)\b', response)
            for name in names:
                if name not in seen_names and name not in ['I', 'We', 'The', 'Our']:
                    context = response[:100] + "..." if len(response) > 100 else response
                    personnel.append({
                        "name": name,
                        "role": "Key person (critical knowledge holder)",
                        "context": context,
                        "risk_level": "HIGH",
                        "question": q_id
                    })
                    seen_names.add(name)
        
        # Apply general patterns
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    name = match[0].split()[0] if match[0].split() else ""
                    role = match[1] if len(match) > 1 else "team member"
                else:
                    name = match.split()[0] if match.split() else ""
                    role = "team member"
                
                # Clean up name
                name = name.strip().title()
                
                # Filter out common false positives
                if (name and 
                    name not in seen_names and 
                    name not in ['I', 'We', 'The', 'Our', 'My', 'All', 'No', 'Yes', 'Only']):
                    
                    # Determine risk level based on context
                    risk_level = "MEDIUM"
                    if any(word in response.lower() for word in ['only', 'alone', 'personally', 'critical']):
                        risk_level = "HIGH"
                    elif any(word in response.lower() for word in ['team', 'several', 'backup']):
                        risk_level = "LOW"
                    
                    personnel.append({
                        "name": name,
                        "role": role.strip(),
                        "context": response[:150] + "..." if len(response) > 150 else response,
                        "risk_level": risk_level,
                        "question": q_id
                    })
                    seen_names.add(name)
    
    logger.info(f"Extracted {len(personnel)} personnel mentions")
    return personnel


def extract_time_references(responses: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Extract time-related information (experience, timelines, durations).
    
    Returns:
        List of time references with context and type
    """
    time_refs = []
    
    patterns = [
        # Years of experience/operation
        (r'(\d+)[\s-]?(?:\+\s)?year[s]?(?:\s+of)?\s+(\w+)', 'experience'),
        (r'(?:for |over |nearly |about |approximately )?(\d+)\s+year[s]?', 'duration'),
        (r'(?:established|founded|started|began)\s+(?:in\s+)?(\d{4})', 'founding'),
        # Months
        (r'(\d+)[\s-]?month[s]?', 'months'),
        # Time periods
        (r'(decade[s]?|century|centuries)', 'period'),
        # Relative time
        (r'(?:since|from)\s+(\d{4})', 'since'),
        # Business age
        (r'(\d+)[\s-]?year[\s-]?old', 'age'),
    ]
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        for pattern, time_type in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                time_value = match.group(1)
                context_start = max(0, match.start() - 30)
                context_end = min(len(response), match.end() + 30)
                context = response[context_start:context_end]
                
                # Get what the time refers to
                reference = match.group(2) if len(match.groups()) > 1 else ""
                
                time_refs.append({
                    "value": time_value,
                    "type": time_type,
                    "reference": reference,
                    "context": context,
                    "question": q_id,
                    "significance": _assess_time_significance(time_value, time_type)
                })
    
    logger.info(f"Extracted {len(time_refs)} time references")
    return time_refs


def extract_competitive_advantages(responses: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Identify unique strengths and competitive advantages.
    
    Returns:
        List of competitive advantages with strength level
    """
    advantages = []
    
    # Keywords that indicate advantages
    advantage_indicators = [
        'reputation', 'relationship', 'expertise', 'specialized', 'unique',
        'proprietary', 'exclusive', 'patent', 'certified', 'accredited',
        'leader', 'leading', 'only', 'first', 'best', 'superior',
        'award', 'recognized', 'trusted', 'preferred', 'unmatched',
        'quality', 'precision', 'standard', 'excellence'
    ]
    
    # Specific patterns
    patterns = [
        r'(?:our|we have|possess)\s+([^.]+(?:' + '|'.join(advantage_indicators) + ')[^.]+)',
        r'((?:' + '|'.join(advantage_indicators) + ')[^.]+)',
    ]
    
    # Focus on Q9 (unique value) but check all responses
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        # Higher weight for Q9 responses
        weight = 2.0 if q_id == "q9" else 1.0
        
        for pattern in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                advantage_text = match.group(1).strip()
                
                # Skip if too short or too long
                if len(advantage_text) < 10 or len(advantage_text) > 200:
                    continue
                
                # Assess strength
                strength = _assess_advantage_strength(advantage_text)
                
                advantages.append({
                    "advantage": advantage_text,
                    "strength": strength,
                    "weight": weight,
                    "question": q_id,
                    "keywords": [kw for kw in advantage_indicators if kw in advantage_text.lower()]
                })
    
    # Deduplicate similar advantages
    unique_advantages = []
    seen_concepts = set()
    
    for adv in advantages:
        # Create a simplified concept for deduplication
        concept = ' '.join(adv['keywords'])
        if concept not in seen_concepts or not concept:
            unique_advantages.append(adv)
            seen_concepts.add(concept)
    
    logger.info(f"Extracted {len(unique_advantages)} competitive advantages")
    return unique_advantages


def extract_technical_terms(responses: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Extract technical terminology, systems, and specialized equipment.
    Industry-agnostic approach that works across all business types.
    
    Returns:
        List of technical assets with category
    """
    technical_assets = []
    
    # Generic technical patterns that work across industries
    technical_patterns = {
        "equipment": [
            r'(\w+\s+(?:machine[s]?|equipment|device[s]?|tool[s]?|instrument[s]?))',
            r'(\w+\s+(?:unit[s]?|system[s]?|apparatus|machinery))',
            r'((?:automated|digital|electronic|mechanical)\s+\w+)'
        ],
        "certification": [
            r'([A-Z]{2,}(?:[-/]\d+)?(?:\s+\d+)?)',  # Generic certification pattern
            r'(\w+\s+(?:certified|accredited|licensed|approved|compliant))',
            r'((?:quality|safety|environmental|industry)\s+(?:standard[s]?|certification[s]?))'
        ],
        "software": [
            r'(\w+\s+(?:software|platform|system|application|program))',
            r'((?:ERP|CRM|CAD|CAM|MRP|SaaS|POS|EMR|EHR)\b)',  # Common business acronyms
            r'(\w+\s+(?:database|analytics|management\s+system))'
        ],
        "process": [
            r'(\w+\s+(?:process|methodology|protocol|procedure|workflow))',
            r'((?:proprietary|patented|unique|specialized)\s+\w+)',
            r'(\w+\s+(?:technique|method|approach|system))'
        ],
        "technology": [
            r'(\w+\s+(?:technology|tech|solution|innovation))',
            r'((?:AI|ML|IoT|blockchain|cloud|digital)\s+\w+)',
            r'(\w+\s+(?:automation|integration|optimization))'
        ]
    }
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        for category, patterns in technical_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, response, re.IGNORECASE)
                for match in matches:
                    term = match.group(1).strip()
                    
                    # Skip generic terms
                    if len(term) < 3 or term.lower() in ['the system', 'a machine', 'our process']:
                        continue
                    
                    context_start = max(0, match.start() - 40)
                    context_end = min(len(response), match.end() + 40)
                    
                    technical_assets.append({
                        "term": term,
                        "category": category,
                        "context": response[context_start:context_end],
                        "question": q_id,
                        "specificity": "high" if any(c.isdigit() for c in term) else "medium"
                    })
    
    logger.info(f"Extracted {len(technical_assets)} technical terms")
    return technical_assets


def extract_risk_language(responses: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Identify language indicating risks, dependencies, or concerns.
    
    Returns:
        List of risk indicators with severity
    """
    risks = []
    
    risk_patterns = {
        "high": [
            r'(only\s+(?:I|me|one person|[A-Z][a-z]+)\s+(?:can|know[s]?|understand[s]?)[^.]+)',
            r'(no\s+one\s+else[^.]+)',
            r'(completely\s+depend[s]?\s+on[^.]+)',
            r'(cannot\s+(?:operate|function|run)\s+without[^.]+)',
            r'(personally\s+(?:handle|manage|approve)[^.]+)',
            r'(all\s+(?:decisions|approvals|sign-offs)[^.]+)'
        ],
        "medium": [
            r'(limited\s+(?:to|by)[^.]+)',
            r'(struggle[s]?\s+(?:with|to)[^.]+)',
            r'(difficult\s+to[^.]+)',
            r'(concern[s]?\s+(?:about|with)[^.]+)',
            r'(challenge[s]?\s+(?:in|with)[^.]+)'
        ],
        "low": [
            r'(some\s+(?:dependency|reliance)\s+on[^.]+)',
            r'(occasionally\s+need[s]?[^.]+)',
            r'(minor\s+(?:issue|problem|concern)[^.]+)'
        ]
    }
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        for severity, patterns in risk_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, response, re.IGNORECASE)
                for match in matches:
                    risk_text = match.group(1).strip()
                    
                    risks.append({
                        "risk": risk_text,
                        "severity": severity,
                        "question": q_id,
                        "category": _categorize_risk(risk_text)
                    })
    
    logger.info(f"Extracted {len(risks)} risk indicators")
    return risks


def extract_numbers_with_context(responses: Dict[str, str]) -> Dict[str, List[Dict[str, str]]]:
    """
    Extract numerical data with surrounding context.
    
    Returns:
        Dictionary of numbers organized by type
    """
    numbers = defaultdict(list)
    
    patterns = [
        # Percentages
        (r'(\d+(?:\.\d+)?)\s*%', 'percentage'),
        # Currency
        (r'\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*([MKB])?', 'currency'),
        # Plain numbers with units
        (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s+(employee[s]?|customer[s]?|client[s]?|supplier[s]?|location[s]?)', 'count'),
        # Scores/ratings
        (r'(\d+)\s*(?:/|out of)\s*10', 'score'),
        # Time periods already covered in extract_time_references
    ]
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        for pattern, num_type in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                value = match.group(1)
                unit = match.group(2) if len(match.groups()) > 1 else ""
                
                context_start = max(0, match.start() - 30)
                context_end = min(len(response), match.end() + 30)
                
                numbers[num_type].append({
                    "value": value,
                    "unit": unit,
                    "context": response[context_start:context_end],
                    "question": q_id,
                    "full_text": match.group(0)
                })
    
    logger.info(f"Extracted {sum(len(v) for v in numbers.values())} numbers across {len(numbers)} types")
    return dict(numbers)


def extract_industry_terminology(responses: Dict[str, str]) -> List[str]:
    """
    Extract industry-specific terminology and jargon.
    
    Returns:
        List of unique industry terms
    """
    # Common business words to exclude
    common_words = {
        'business', 'company', 'customer', 'client', 'service', 'product',
        'process', 'system', 'management', 'operation', 'team', 'staff',
        'quality', 'standard', 'procedure', 'work', 'project', 'sale'
    }
    
    industry_terms = set()
    
    # Look for capitalized terms and specialized phrases
    patterns = [
        r'\b([A-Z]{2,}(?:\s+[A-Z]{2,})*)\b',  # Acronyms
        r'\b(\w+\s+(?:manufacturing|production|assembly|fabrication))\b',
        r'\b((?:precision|quality|safety|regulatory)\s+\w+)\b',
        r'\b(\w+\s+(?:certification|compliance|standard|specification))\b',
    ]
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        # Extract multi-word specialized terms
        words = response.split()
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}".lower()
            if (words[i][0].isupper() and words[i+1][0].isupper() and 
                bigram not in common_words and
                len(words[i]) > 2 and len(words[i+1]) > 2):
                industry_terms.add(bigram.title())
        
        # Apply patterns
        for pattern in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                term = match.group(1).strip()
                if term.lower() not in common_words and len(term) > 3:
                    industry_terms.add(term)
    
    logger.info(f"Extracted {len(industry_terms)} industry terms")
    return sorted(list(industry_terms))


def extract_certifications_compliance(responses: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Extract mentions of certifications, compliance requirements, and standards.
    
    Returns:
        List of certifications with type and importance
    """
    certifications = []
    
    cert_patterns = [
        # ISO standards
        r'(ISO\s*\d+(?::\d+)?)',
        # Industry certifications
        r'([A-Z]{2,}\s*\d+)',
        # Compliance mentions
        r'((?:FDA|OSHA|EPA|DOT|FAA|FCC|UL|CE|RoHS)\s*(?:compliant|certified|approved)?)',
        # General certification language
        r'((?:certified|accredited|licensed|approved)\s+(?:for|in|by)\s+\w+)',
        # Specific requirements
        r'((?:safety|quality|environmental)\s+(?:certification|approval|requirement))',
    ]
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        for pattern in cert_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                cert_text = match.group(1).strip()
                
                # Determine importance
                importance = "high"
                if any(word in response.lower() for word in ['require', 'must', 'mandatory', 'critical']):
                    importance = "critical"
                elif any(word in response.lower() for word in ['preferred', 'helpful', 'beneficial']):
                    importance = "medium"
                
                certifications.append({
                    "certification": cert_text,
                    "importance": importance,
                    "question": q_id,
                    "context": response[:100] + "..." if len(response) > 100 else response
                })
    
    logger.info(f"Extracted {len(certifications)} certifications/compliance mentions")
    return certifications


def extract_customer_information(responses: Dict[str, str]) -> Dict[str, Any]:
    """
    Extract customer/client details and relationships.
    Industry-agnostic approach for all business types.
    
    Returns:
        Dictionary with customer insights
    """
    customer_info = {
        "customer_types": [],
        "key_relationships": [],
        "contract_details": [],
        "concentration_risks": []
    }
    
    # Look for customer mentions across all industries
    customer_patterns = [
        # Industry mentions with customer/client
        r'(\w+(?:\s+\w+)?\s+(?:client[s]?|customer[s]?|buyer[s]?|account[s]?|patient[s]?|member[s]?|subscriber[s]?))',
        # Size/importance indicators
        r'((?:largest|biggest|major|key|primary|main|top)\s+(?:client[s]?|customer[s]?|account[s]?|buyer[s]?))',
        # Contract types
        r'((?:long-term|annual|multi-year|recurring|ongoing)\s+(?:contract[s]?|agreement[s]?|relationship[s]?|engagement[s]?))',
        # Customer segments
        r'((?:B2B|B2C|enterprise|retail|wholesale|commercial|residential|government|institutional)\s+(?:client[s]?|customer[s]?|business))',
        # Geographic customer base
        r'((?:local|regional|national|international|global)\s+(?:client[s]?|customer[s]?|market[s]?))'
    ]
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        for pattern in customer_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                customer_text = match.group(1).strip()
                
                # Categorize the information
                if 'largest' in customer_text.lower() or 'biggest' in customer_text.lower():
                    customer_info["concentration_risks"].append({
                        "text": customer_text,
                        "question": q_id,
                        "risk_level": "high"
                    })
                elif 'long-term' in customer_text.lower() or 'annual' in customer_text.lower():
                    customer_info["contract_details"].append({
                        "text": customer_text,
                        "question": q_id,
                        "stability": "good"
                    })
                else:
                    customer_info["customer_types"].append({
                        "text": customer_text,
                        "question": q_id
                    })
    
    return customer_info


def extract_operational_specifics(responses: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Extract specific operational details and processes.
    
    Returns:
        Dictionary of operational details by category
    """
    operations = defaultdict(list)
    
    operational_patterns = {
        "processes": [
            r'((?:quality|production|manufacturing|assembly)\s+(?:process|procedure|protocol))',
            r'((?:approval|sign-off|review|inspection)\s+(?:process|procedure))',
        ],
        "systems": [
            r'((?:ERP|CRM|CAD|CAM|MRP)\s+system)',
            r'(\w+\s+management\s+system)',
        ],
        "activities": [
            r'((?:daily|weekly|monthly)\s+\w+)',
            r'((?:handle|manage|oversee|control)\s+\w+)',
        ]
    }
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        for category, patterns in operational_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, response, re.IGNORECASE)
                for match in matches:
                    detail = match.group(1).strip()
                    if detail not in operations[category]:
                        operations[category].append(detail)
    
    return dict(operations)


def extract_memorable_phrases(responses: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Extract particularly memorable or quotable phrases.
    
    Returns:
        List of memorable phrases with impact scores
    """
    memorable = []
    
    # Patterns that often indicate memorable statements
    memorable_patterns = [
        r'"([^"]+)"',  # Quoted text
        r'(?:we\s+are|we\'re)\s+([^.]+\.)',  # Identity statements
        r'(?:our|my)\s+(\w+\s+(?:is|are)\s+[^.]+\.)',  # Pride statements
        r'((?:only|first|best|largest|oldest)\s+[^.]+\.)',  # Superlatives
    ]
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        # Special attention to Q9 (unique value)
        weight = 1.5 if q_id == "q9" else 1.0
        
        for pattern in memorable_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                phrase = match.group(1).strip()
                
                # Filter out very short or very long phrases
                if 10 < len(phrase) < 150:
                    memorable.append({
                        "phrase": phrase,
                        "question": q_id,
                        "impact": _assess_phrase_impact(phrase) * weight,
                        "type": _categorize_phrase(phrase)
                    })
    
    # Sort by impact and return top phrases
    memorable.sort(key=lambda x: x['impact'], reverse=True)
    logger.info(f"Extracted {len(memorable)} memorable phrases")
    return memorable[:10]  # Top 10 most impactful


def extract_relationships(responses: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Extract business relationships and partnerships.
    
    Returns:
        List of relationships with type and duration
    """
    relationships = []
    
    relationship_patterns = [
        r'((?:relationship|partnership|agreement)\s+with\s+[^.]+)',
        r'((?:work|working)\s+with\s+[^.]+\s+(?:for|since)\s+[^.]+)',
        r'((?:supplier|vendor|partner|customer)\s+[^.]+\s+(?:year|decade))',
    ]
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        for pattern in relationship_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                relationship_text = match.group(1).strip()
                
                # Extract duration if mentioned
                duration = None
                duration_match = re.search(r'(\d+)\s*(year|month|decade)', relationship_text)
                if duration_match:
                    duration = duration_match.group(0)
                
                relationships.append({
                    "relationship": relationship_text,
                    "duration": duration,
                    "question": q_id,
                    "strength": "strong" if duration and int(duration_match.group(1)) > 5 else "moderate"
                })
    
    logger.info(f"Extracted {len(relationships)} business relationships")
    return relationships


def extract_owner_specific_actions(responses: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Extract specific actions/tasks the owner personally handles.
    
    Returns:
        List of owner-specific actions with criticality
    """
    owner_actions = []
    
    # Focus on Q1 but check all responses
    owner_patterns = [
        r'I\s+(?:personally\s+)?(?:handle|manage|oversee|approve|sign|review|control)\s+([^.,]+)',
        r'(?:only\s+)?I\s+(?:can|am\s+able\s+to|know\s+how\s+to)\s+([^.,]+)',
        r'(?:require[s]?\s+)?my\s+(?:approval|signature|review|input)\s+(?:for\s+)?([^.,]+)',
    ]
    
    for q_id, response in responses.items():
        if not isinstance(response, str):
            continue
            
        # Higher weight for Q1
        is_primary_question = q_id == "q1"
        
        for pattern in owner_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                action = match.group(1).strip()
                
                # Skip very short actions
                if len(action) < 5:
                    continue
                
                # Assess criticality
                criticality = "high"
                if any(word in action.lower() for word in ['all', 'every', 'final', 'critical']):
                    criticality = "critical"
                elif any(word in action.lower() for word in ['some', 'occasional', 'review']):
                    criticality = "medium"
                
                owner_actions.append({
                    "action": action,
                    "criticality": criticality,
                    "question": q_id,
                    "is_primary": is_primary_question,
                    "delegation_difficulty": _assess_delegation_difficulty(action)
                })
    
    logger.info(f"Extracted {len(owner_actions)} owner-specific actions")
    return owner_actions


# Helper functions

def _assess_time_significance(value: str, time_type: str) -> str:
    """Assess the significance of a time reference."""
    try:
        if time_type in ['experience', 'duration', 'age']:
            years = int(re.findall(r'\d+', value)[0])
            if years >= 20:
                return "very_high"
            elif years >= 10:
                return "high"
            elif years >= 5:
                return "medium"
            else:
                return "low"
    except:
        pass
    return "medium"


def _assess_advantage_strength(text: str) -> str:
    """Assess the strength of a competitive advantage."""
    strong_indicators = ['only', 'exclusive', 'unmatched', 'leader', 'first', 'patent']
    medium_indicators = ['specialized', 'expertise', 'certified', 'trusted']
    
    text_lower = text.lower()
    
    if any(indicator in text_lower for indicator in strong_indicators):
        return "strong"
    elif any(indicator in text_lower for indicator in medium_indicators):
        return "medium"
    else:
        return "potential"


def _categorize_risk(risk_text: str) -> str:
    """Categorize the type of risk."""
    risk_lower = risk_text.lower()
    
    if any(word in risk_lower for word in ['only i', 'personally', 'me']):
        return "owner_dependence"
    elif any(word in risk_lower for word in ['know', 'understand', 'skill']):
        return "knowledge_concentration"
    elif any(word in risk_lower for word in ['customer', 'client', 'contract']):
        return "customer_concentration"
    elif any(word in risk_lower for word in ['system', 'process', 'equipment']):
        return "operational"
    else:
        return "general"


def _assess_phrase_impact(phrase: str) -> float:
    """Score the potential impact/memorability of a phrase."""
    impact = 1.0
    
    # Increase for superlatives
    if any(word in phrase.lower() for word in ['only', 'first', 'best', 'largest']):
        impact *= 1.5
    
    # Increase for numbers
    if re.search(r'\d+', phrase):
        impact *= 1.3
    
    # Increase for strong emotional words
    if any(word in phrase.lower() for word in ['proud', 'passion', 'commitment', 'excellence']):
        impact *= 1.2
    
    return impact


def _categorize_phrase(phrase: str) -> str:
    """Categorize the type of memorable phrase."""
    phrase_lower = phrase.lower()
    
    if any(word in phrase_lower for word in ['reputation', 'trusted', 'relationship']):
        return "reputation"
    elif any(word in phrase_lower for word in ['quality', 'precision', 'standard']):
        return "quality"
    elif any(word in phrase_lower for word in ['only', 'first', 'exclusive']):
        return "uniqueness"
    elif any(word in phrase_lower for word in ['year', 'decade', 'established']):
        return "heritage"
    else:
        return "general"


def _assess_delegation_difficulty(action: str) -> str:
    """Assess how difficult an action would be to delegate."""
    action_lower = action.lower()
    
    if any(word in action_lower for word in ['final', 'approval', 'sign', 'decision']):
        return "high"
    elif any(word in action_lower for word in ['review', 'oversee', 'manage']):
        return "medium"
    elif any(word in action_lower for word in ['routine', 'daily', 'standard']):
        return "low"
    else:
        return "medium"


# Aggregation function for easy access

def get_key_business_details(mined_insights: Dict[str, Any], anonymized_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the most important business details for report personalization.
    Combines mined insights with anonymized business metadata.
    
    Args:
        mined_insights: Full insights dictionary from mine_key_insights
        anonymized_data: Original anonymized data with business context
        
    Returns:
        Simplified dictionary with key details for easy use
    """
    details = {
        "primary_person_risk": None,
        "years_in_operation": None,
        "top_competitive_advantage": None,
        "key_certifications": [],
        "major_customer_type": None,
        "critical_owner_action": None,
        "memorable_statement": None,
        "industry": anonymized_data.get("industry", ""),
        "revenue_range": anonymized_data.get("revenue_range", ""),
        "exit_timeline": anonymized_data.get("exit_timeline", ""),
        "location": anonymized_data.get("location", "")
    }
    
    # Get primary person at risk
    personnel = mined_insights.get("key_personnel", [])
    high_risk_personnel = [p for p in personnel if p.get("risk_level") == "HIGH"]
    if high_risk_personnel:
        details["primary_person_risk"] = high_risk_personnel[0]
    
    # Get years in operation - check both mined data and metadata
    time_refs = mined_insights.get("time_indicators", [])
    for ref in time_refs:
        if ref.get("type") in ["experience", "duration"] and ref.get("reference"):
            details["years_in_operation"] = f"{ref['value']} years"
            break
    
    # If not found in responses, check metadata
    if not details["years_in_operation"] and anonymized_data.get("years_in_business"):
        details["years_in_operation"] = anonymized_data.get("years_in_business")
    
    # Get top competitive advantage
    advantages = mined_insights.get("competitive_advantages", [])
    if advantages:
        details["top_competitive_advantage"] = advantages[0]["advantage"]
    
    # Get key certifications
    certs = mined_insights.get("certifications", [])
    critical_certs = [c for c in certs if c.get("importance") == "critical"]
    details["key_certifications"] = critical_certs[:3]
    
    # Get major customer type
    customer_info = mined_insights.get("customer_details", {})
    if customer_info.get("customer_types"):
        details["major_customer_type"] = customer_info["customer_types"][0]["text"]
    
    # Get critical owner action
    owner_actions = mined_insights.get("owner_actions", [])
    critical_actions = [a for a in owner_actions if a.get("criticality") == "critical"]
    if critical_actions:
        details["critical_owner_action"] = critical_actions[0]["action"]
    
    # Get memorable statement
    phrases = mined_insights.get("unique_phrases", [])
    if phrases:
        details["memorable_statement"] = phrases[0]["phrase"]
    
    return details