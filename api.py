from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Import your CrewAI components
from src.crew import ExitReadySnapshotCrew
from src.utils.logging_config import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="Exit Ready Snapshot API",
    description="API endpoint for processing Exit Ready Snapshot assessments",
    version="1.0.0"
)

# API Key for authentication
API_KEY = os.getenv("CREWAI_API_KEY", "your-secure-api-key-here")

# Request/Response models
class AssessmentRequest(BaseModel):
    uuid: str
    timestamp: str
    name: str
    email: str
    industry: str
    years_in_business: str
    age_range: str
    exit_timeline: str
    location: str
    responses: Dict[str, str]
    _tallySubmissionId: Optional[str] = None
    _tallyFormId: Optional[str] = None

class AssessmentResponse(BaseModel):
    uuid: str
    status: str
    owner_name: str
    email: str
    company_name: Optional[str]
    industry: str
    location: str
    scores: Dict[str, float]
    executive_summary: str
    category_summaries: Dict[str, str]
    recommendations: Dict[str, Any]
    next_steps: str

# Authentication dependency
async def verify_api_key(x_api_key: str = Header()):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Exit Ready Snapshot API"}

# Main assessment endpoint
@app.post("/api/assessment", response_model=AssessmentResponse)
async def process_assessment(
    request: AssessmentRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Process an Exit Ready Snapshot assessment
    """
    try:
        logger.info(f"Processing assessment for UUID: {request.uuid}")
        
        # Convert request to dict for CrewAI
        form_data = request.dict()
        
        # Initialize crew with locale
        locale = determine_locale(request.location)
        crew = ExitReadySnapshotCrew(locale=locale)
        
        # Process the assessment
        result = crew.kickoff(inputs=form_data)
        
        # Parse the crew output
        # Note: This assumes your crew returns properly formatted data
        # You may need to adjust based on actual CrewAI output format
        
        response_data = {
            "uuid": request.uuid,
            "status": "completed",
            "owner_name": request.name,
            "email": request.email,
            "company_name": extract_company_name(result),
            "industry": request.industry,
            "location": request.location,
            "scores": result.get("scores", {}),
            "executive_summary": result.get("executive_summary", ""),
            "category_summaries": result.get("category_summaries", {}),
            "recommendations": result.get("recommendations", {}),
            "next_steps": result.get("next_steps", "")
        }
        
        logger.info(f"Assessment completed for UUID: {request.uuid}")
        return AssessmentResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Error processing assessment: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Utility functions
def determine_locale(location: str) -> str:
    """Determine locale based on location"""
    locale_mapping = {
        'Pacific/Western US': 'us',
        'Mountain/Central US': 'us',
        'Midwest US': 'us',
        'Southern US': 'us',
        'Northeast US': 'us',
        'United Kingdom': 'uk',
        'Australia/New Zealand': 'au',
        'Canada': 'us',
        'Other International': 'us'
    }
    return locale_mapping.get(location, 'us')

def extract_company_name(result: Dict[str, Any]) -> Optional[str]:
    """Extract company name from CrewAI result if available"""
    # This would come from the PII reinsertion agent
    return result.get("company_name")

# Error handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Run the server
if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )