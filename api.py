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
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import LangGraph workflow instead of CrewAI
from workflow.graph import process_assessment_async
from src.utils.logging_config import setup_logging

# Load environment variables
load_dotenv()

# Debug: Check if environment variables are loaded
print(f"Current directory: {os.getcwd()}")
print(f".env exists: {os.path.exists('.env')}")
print(f"OpenAI API Key loaded: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
print(f"API_KEY from env: {os.getenv('API_KEY')}")

# Setup logging
logger = setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="Exit Ready Snapshot API",
    description="API endpoint for processing Exit Ready Snapshot assessments using LangGraph",
    version="2.0.0"
)

# API Key for authentication (renamed from CREWAI_API_KEY)
API_KEY = os.getenv("API_KEY", "your-secure-api-key-here")
print(f"API expecting key: {API_KEY}")

# Thread pool for running async code in sync context
executor = ThreadPoolExecutor(max_workers=3)

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
    revenue_range: str
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
    locale: Optional[str] = "us"

# Authentication dependency
async def verify_api_key(x_api_key: str = Header()):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "Exit Ready Snapshot API",
        "version": "2.0.0",
        "workflow": "LangGraph"
    }

# Debug endpoint for workflow visualization
@app.get("/api/workflow-graph")
async def get_workflow_graph():
    """Get a visual representation of the LangGraph workflow"""
    try:
        from workflow.graph import create_workflow
        app = create_workflow()
        
        # Get the mermaid diagram
        graph_def = app.get_graph().draw_mermaid()
        
        return {
            "graph": graph_def,
            "nodes": ["intake", "research", "scoring", "summary", "qa", "pii_reinsertion"],
            "description": "LangGraph workflow for Exit Ready Snapshot assessment"
        }
    except Exception as e:
        return {
            "error": str(e),
            "description": "Could not generate workflow visualization"
        }

# Main assessment endpoint
@app.post("/api/assessment", response_model=AssessmentResponse)
async def process_assessment(
    request: AssessmentRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Process an Exit Ready Snapshot assessment using LangGraph
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
        
        # Convert request to dict for LangGraph
        form_data = request.model_dump()
        
        # Add company name if available from responses
        if not form_data.get("company_name"):
            # Try to extract from responses if available
            form_data["company_name"] = form_data.get("responses", {}).get("company_name", "")
        
        print(f"📋 Form data prepared: {len(json.dumps(form_data))} chars")
        print("🤖 Initializing LangGraph workflow...")
        
        workflow_start = time.time()
        
        # Run the async workflow
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, use run_in_executor
                future = loop.run_in_executor(
                    executor,
                    asyncio.run,
                    process_assessment_async(form_data)
                )
                result = await future
            else:
                # No running loop, we can use asyncio.run directly
                result = await process_assessment_async(form_data)
        except RuntimeError:
            # Fallback: create new event loop in thread
            future = executor.submit(asyncio.run, process_assessment_async(form_data))
            result = await asyncio.get_event_loop().run_in_executor(None, future.result)
        
        workflow_time = time.time() - workflow_start
        print(f"✅ LangGraph workflow completed in {workflow_time:.1f}s")
        
        # Check for errors
        if result.get("status") == "error":
            logger.error(f"Workflow error: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Assessment processing failed: {result.get('error')}"
            )
        
        # Format response to match existing API contract
        response_data = {
            "uuid": request.uuid,
            "status": "completed",
            "owner_name": result.get("owner_name", request.name),
            "email": result.get("email", request.email),
            "company_name": result.get("company_name"),
            "industry": request.industry,
            "location": request.location,
            "locale": result.get("locale", "us"),
            "scores": result.get("scores", {}),
            "executive_summary": result.get("executive_summary", ""),
            "category_summaries": result.get("category_summaries", {}),
            "recommendations": result.get("recommendations", {}),
            "next_steps": result.get("next_steps", "Schedule a consultation to discuss your personalized Exit Value Growth Plan.")
        }
        
        total_time = time.time() - request_start_time
        print(f"\n" + "="*80)
        print(f"✅ API REQUEST COMPLETED in {total_time:.1f}s")
        print(f"📈 Overall Score: {response_data['scores'].get('overall_score', 'N/A')}/10")
        print(f"📝 Summary Length: {len(response_data['executive_summary'])} chars")
        print(f"🔄 Workflow Version: LangGraph Enhanced")
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
        print("⚠️  WARNING: OPENAI_API_KEY not found in environment!")
    if not os.getenv("API_KEY"):
        print("⚠️  WARNING: API_KEY not found in environment!")
    if os.getenv("PERPLEXITY_API_KEY"):
        print("✅ Perplexity API key found - will use real research")
    else:
        print("ℹ️  No Perplexity key - will use fallback research data")
        
    print(f"\n🚀 Starting Exit Ready Snapshot API Server...")
    print(f"📡 Listening on http://0.0.0.0:8000")
    print(f"📝 API Docs: http://0.0.0.0:8000/docs")
    print(f"🔄 Workflow: LangGraph Enhanced Pipeline\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)