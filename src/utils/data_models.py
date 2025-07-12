from pydantic import BaseModel, EmailStr, Field
from typing import Dict, List, Optional
from datetime import datetime
import uuid

class FormSubmission(BaseModel):
    """Raw form submission from Tally via n8n"""
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Collection fields
    name: str
    email: EmailStr
    industry: str
    years_in_business: str
    age_range: str
    exit_timeline: str
    location: str
    
    # Assessment responses
    responses: Dict[str, str] = Field(
        description="Question responses keyed by question ID (q1-q10)"
    )

class PIIMapping(BaseModel):
    """Secure storage of PII mappings"""
    uuid: str
    original_values: Dict[str, str]
    placeholders: Dict[str, str]

class AssessmentResult(BaseModel):
    """Final assessment output"""
    uuid: str
    timestamp: datetime
    status: str
    locale: str
    
    # Scores
    overall_score: float
    scores: Dict[str, float]
    
    # Summary
    summary: str
    recommendations: List[str]