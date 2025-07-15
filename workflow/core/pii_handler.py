"""
PII detection and handling functions extracted from CrewAI agents.
Pure functions for privacy management.
"""

import re
from typing import Dict, Any, List, Tuple, Optional


class PIIDetector:
    """Pure PII detection and redaction logic"""
    
    def __init__(self):
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}')
        self.ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        self.credit_card_pattern = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
        
    def detect_and_redact(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Detect and redact PII from text.
        
        Returns:
            Tuple of (redacted_text, pii_mapping)
        """
        if not text:
            return text, {}
        
        redacted_text = text
        pii_mapping = {}
        counter = 0
        
        # Redact emails
        emails = self.email_pattern.findall(redacted_text)
        for email in emails:
            placeholder = f"[EMAIL_{counter}]"
            redacted_text = redacted_text.replace(email, placeholder)
            pii_mapping[placeholder] = email
            counter += 1
        
        # Redact phone numbers
        phones = self.phone_pattern.findall(redacted_text)
        for phone in phones:
            if len(phone) > 6:  # Avoid redacting short numbers
                placeholder = f"[PHONE_{counter}]"
                redacted_text = redacted_text.replace(phone, placeholder)
                pii_mapping[placeholder] = phone
                counter += 1
        
        # Redact SSNs
        ssns = self.ssn_pattern.findall(redacted_text)
        for ssn in ssns:
            placeholder = f"[SSN_{counter}]"
            redacted_text = redacted_text.replace(ssn, placeholder)
            pii_mapping[placeholder] = ssn
            counter += 1
        
        # Look for company names
        company_indicators = ['LLC', 'Inc', 'Corp', 'Company', 'Ltd', 'Partners']
        for indicator in company_indicators:
            pattern = re.compile(rf'\b[\w\s]+\s{indicator}\.?\b', re.IGNORECASE)
            companies = pattern.findall(redacted_text)
            for company in companies:
                placeholder = f"[COMPANY_{counter}]"
                redacted_text = redacted_text.replace(company, placeholder)
                pii_mapping[placeholder] = company
                counter += 1
        
        return redacted_text, pii_mapping


def extract_company_name(text: str) -> Optional[str]:
    """
    Extract potential company name from text.
    
    Returns:
        Company name if found, None otherwise
    """
    company_patterns = [
        r'(?:my company|our company|the company),?\s+([A-Z][A-Za-z\s&]+?)(?:\s+(?:Inc|LLC|Ltd|Corp))?',
        r'([A-Z][A-Za-z\s&]+?)\s+(?:Inc|LLC|Ltd|Corp|Company)',
        r'(?:called|named)\s+([A-Z][A-Za-z\s&]+)',
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None


def anonymize_form_data(form_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Anonymize complete form data and create PII mapping.
    
    Returns:
        Tuple of (anonymized_data, pii_mapping)
    """
    detector = PIIDetector()
    anonymized_data = form_data.copy()
    
    # Initialize standard PII mapping
    pii_mapping = {
        "[OWNER_NAME]": form_data.get('name', ''),
        "[EMAIL]": form_data.get('email', ''),
        "[LOCATION]": form_data.get('location', ''),
        "[UUID]": form_data.get('uuid', '')
    }
    
    # Redact basic fields
    anonymized_data['name'] = '[OWNER_NAME]'
    anonymized_data['email'] = '[EMAIL]'
    
    # Process all text responses
    anonymized_responses = {}
    all_responses_text = ""
    
    for q_id, response in form_data.get('responses', {}).items():
        if response and isinstance(response, str):
            all_responses_text += f" {response}"
            
            # Detect and redact PII in each response
            redacted_response, response_pii = detector.detect_and_redact(response)
            anonymized_responses[q_id] = redacted_response
            
            # Add to mapping
            pii_mapping.update(response_pii)
        else:
            anonymized_responses[q_id] = response
    
    anonymized_data['responses'] = anonymized_responses
    
    # Try to extract company name
    company_name = extract_company_name(all_responses_text)
    if company_name:
        pii_mapping["[COMPANY_NAME]"] = company_name
        
        # Redact company name from all responses
        for q_id in anonymized_responses:
            if company_name in anonymized_responses[q_id]:
                anonymized_responses[q_id] = anonymized_responses[q_id].replace(
                    company_name, "[COMPANY_NAME]"
                )
    
    return anonymized_data, pii_mapping


def reinsert_pii(content: str, pii_mapping: Dict[str, str]) -> str:
    """
    Reinsert PII into content using mapping.
    
    Returns:
        Personalized content with PII reinserted
    """
    if not pii_mapping:
        return content
    
    personalized_content = content
    
    # Sort by placeholder length (longest first) to avoid partial replacements
    sorted_mapping = sorted(pii_mapping.items(), key=lambda x: len(x[0]), reverse=True)
    
    for placeholder, actual_value in sorted_mapping:
        if placeholder in personalized_content and actual_value:
            personalized_content = personalized_content.replace(placeholder, actual_value)
    
    return personalized_content


def validate_pii_reinsertion(content: str) -> Dict[str, Any]:
    """
    Validate that PII reinsertion was successful.
    
    Returns:
        Dictionary with validation results
    """
    # Check for remaining placeholders
    placeholder_pattern = r'\[\w+_\d*\]'
    remaining_placeholders = re.findall(placeholder_pattern, content)
    
    # Check for standard placeholders
    standard_placeholders = ['[OWNER_NAME]', '[EMAIL]', '[COMPANY_NAME]', '[LOCATION]']
    remaining_standard = [p for p in standard_placeholders if p in content]
    
    return {
        'is_complete': len(remaining_placeholders) == 0 and len(remaining_standard) == 0,
        'remaining_placeholders': remaining_placeholders,
        'remaining_standard': remaining_standard,
        'total_remaining': len(remaining_placeholders) + len(remaining_standard)
    }


# Global PII mapping storage (in production, use secure storage)
_pii_mapping_store: Dict[str, Dict[str, str]] = {}


def store_pii_mapping(uuid: str, mapping: Dict[str, str]) -> None:
    """Store PII mapping for later retrieval"""
    _pii_mapping_store[uuid] = mapping


def retrieve_pii_mapping(uuid: str) -> Optional[Dict[str, str]]:
    """Retrieve PII mapping by UUID"""
    return _pii_mapping_store.get(uuid)


def clear_pii_mapping(uuid: str) -> None:
    """Clear PII mapping for a specific UUID"""
    if uuid in _pii_mapping_store:
        del _pii_mapping_store[uuid]