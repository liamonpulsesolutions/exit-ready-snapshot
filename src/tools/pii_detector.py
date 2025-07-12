import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class PIIDetector:
    """Detect and redact PII from text"""
    
    def __init__(self):
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}')
        self.redaction_counter = 0
        self.pii_mapping = {}
    
    def detect_and_redact(self, text: str) -> Dict[str, Any]:
        """Detect and redact PII from text"""
        if not text:
            return {"redacted_text": text, "pii_found": False, "mapping": {}}
        
        redacted_text = text
        self.pii_mapping = {}
        pii_found = False
        
        # Redact emails
        emails = self.email_pattern.findall(redacted_text)
        for email in emails:
            placeholder = f"[EMAIL_{self.redaction_counter}]"
            redacted_text = redacted_text.replace(email, placeholder)
            self.pii_mapping[placeholder] = email
            self.redaction_counter += 1
            pii_found = True
        
        # Redact phone numbers
        phones = self.phone_pattern.findall(redacted_text)
        for phone in phones:
            if len(phone) > 6:  # Avoid redacting short numbers
                placeholder = f"[PHONE_{self.redaction_counter}]"
                redacted_text = redacted_text.replace(phone, placeholder)
                self.pii_mapping[placeholder] = phone
                self.redaction_counter += 1
                pii_found = True
        
        # Look for company names (basic approach - will improve)
        # This is a simplified version - in production, use NER
        company_indicators = ['LLC', 'Inc', 'Corp', 'Company', 'Ltd', 'Partners']
        for indicator in company_indicators:
            pattern = re.compile(rf'\b[\w\s]+\s{indicator}\.?\b', re.IGNORECASE)
            companies = pattern.findall(redacted_text)
            for company in companies:
                placeholder = f"[COMPANY_{self.redaction_counter}]"
                redacted_text = redacted_text.replace(company, placeholder)
                self.pii_mapping[placeholder] = company
                self.redaction_counter += 1
                pii_found = True
        
        return {
            "redacted_text": redacted_text,
            "pii_found": pii_found,
            "mapping": self.pii_mapping
        }