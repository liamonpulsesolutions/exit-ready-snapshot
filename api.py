from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Import your CrewAI components
from src.crew import ExitReadySnapshotCrew
from src.utils.logging_config import setup_logging

# Load environment variables
load_dotenv()

# Debug: Check if environment variables are loaded
print(f"Current directory: {os.getcwd()}")
print(f".env exists: {os.path.exists('.env')}")
print(f"OpenAI API Key loaded: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
print(f"CREWAI_API_KEY from env: {os.getenv('CREWAI_API_KEY')}")

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
print(f"API expecting key: {API_KEY}")

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
    revenue_range: str  # Added missing field
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
    request_start_time = time.time()
    
    print("\n" + "="*80)
    print(f"🌐 NEW API REQUEST RECEIVED - {datetime.now().strftime('%H:%M:%S')}")
    print("="*80)
    print(f"📧 Request UUID: {request.uuid}")
    print(f"👤 Client: {request.name} ({request.email})")
    print(f"🏢 Industry: {request.industry}")
    print(f"📍 Location: {request.location}")
    print(f"⏰ Exit Timeline: {request.exit_timeline}")
    print(f"📊 Responses: {len(request.responses)} questions answered")
    print("="*80)
    
    try:
        logger.info(f"Processing assessment for UUID: {request.uuid}")
        logger.info(f"Request data: {json.dumps(request.model_dump(), indent=2)}")
        
        # Convert request to dict for CrewAI
        form_data = request.model_dump()
        print(f"📋 Form data prepared: {len(json.dumps(form_data))} chars")
        
        # Initialize crew with locale
        locale = determine_locale(request.location)
        print(f"🌍 Using locale: {locale}")
        logger.info(f"Using locale: {locale}")
        
        print("🤖 Initializing CrewAI...")
        crew_init_start = time.time()
        crew = ExitReadySnapshotCrew(locale=locale)
        crew_init_time = time.time() - crew_init_start
        print(f"✅ CrewAI initialized in {crew_init_time:.2f}s")
        
        # Process the assessment
        print("🚀 Starting CrewAI processing...")
        logger.info("Starting CrewAI processing...")
        
        crew_start_time = time.time()
        result = crew.kickoff(inputs=form_data)
        crew_execution_time = time.time() - crew_start_time
        
        print(f"✅ CrewAI completed in {crew_execution_time:.1f}s")
        logger.info(f"CrewAI result type: {type(result)}")
        logger.info(f"CrewAI result: {result}")
        
        # Handle the result based on what CrewAI returns
        if isinstance(result, dict) and result.get("status") == "error":
            # CrewAI returned an error
            print(f"❌ CrewAI error: {result.get('error')}")
            logger.error(f"CrewAI error: {result.get('error')}")
            raise HTTPException(status_code=500, detail=f"Assessment processing failed: {result.get('error')}")
        
        print("📊 Parsing crew output...")
        # Parse the crew output
        response_data = {
            "uuid": request.uuid,
            "status": result.get("status", "completed"),
            "owner_name": result.get("owner_name", request.name),
            "email": result.get("email", request.email),
            "company_name": result.get("company_name"),
            "industry": request.industry,
            "location": request.location,
            "scores": result.get("scores", {
                "overall": 5.0,
                "owner_dependence": 5.0,
                "revenue_quality": 5.0,
                "financial_readiness": 5.0,
                "operational_resilience": 5.0,
                "growth_value": 5.0
            }),
            "executive_summary": result.get("executive_summary", "Assessment completed successfully."),
            "category_summaries": result.get("category_summaries", {}),
            "recommendations": result.get("recommendations", {}),
            "next_steps": result.get("next_steps", "Schedule a consultation to discuss your personalized Exit Value Growth Plan.")
        }
        
        total_time = time.time() - request_start_time
        print(f"\n" + "="*80)
        print(f"✅ API REQUEST COMPLETED in {total_time:.1f}s")
        print(f"📈 Overall Score: {response_data['scores'].get('overall', 'N/A')}")
        print(f"📝 Summary Length: {len(response_data['executive_summary'])} chars")
        print("="*80)
        
        logger.info(f"Assessment completed for UUID: {request.uuid} in {total_time:.1f}s")
        return AssessmentResponse(**response_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        print(f"❌ HTTP Exception occurred")
        raise
    except Exception as e:
        total_time = time.time() - request_start_time
        print(f"\n❌ API REQUEST FAILED after {total_time:.1f}s")
        print(f"💥 Error: {str(e)}")
        print(f"🔍 Error type: {type(e).__name__}")
        print("="*80)
        
        logger.error(f"Error processing assessment: {str(e)}", exc_info=True)
        # Return a more informative error for debugging
        error_detail = {
            "error": str(e),
            "type": type(e).__name__,
            "detail": "Check server logs for full stack trace"
        }
        raise HTTPException(status_code=500, detail=json.dumps(error_detail))

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
        'Canada': 'us',  # Default to US for Canada
        'Other International': 'us'  # Default to US
    }
    return locale_mapping.get(location, 'us')

def extract_company_name(result: Dict[str, Any]) -> Optional[str]:
    """Extract company name from CrewAI result if available"""
    # This would come from the PII reinsertion agent
    return result.get("company_name")

# Error handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    print(f"\n💥 UNHANDLED EXCEPTION: {str(exc)}")
    print(f"🔍 Exception type: {type(exc).__name__}")
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Run the server
if __name__ == "__main__":
    # Final check for critical environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not found in environment!")
    if not os.getenv("CREWAI_API_KEY"):
        print("WARNING: CREWAI_API_KEY not found in environment!")
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    print(f"\nStarting API server on {host}:{port}")
    print(f"API Key authentication: {'Enabled' if API_KEY != 'your-secure-api-key-here' else 'DISABLED (using default)'}")
    print("-" * 50)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )