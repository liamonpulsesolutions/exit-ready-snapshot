"""
LangGraph workflow orchestration for Exit Ready Snapshot.
Defines the node execution order and state flow.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END

from workflow.state import WorkflowState
from workflow.nodes.intake import intake_node
from workflow.nodes.research import research_node
from workflow.nodes.scoring import scoring_node
from workflow.nodes.summary import summary_node
from workflow.nodes.qa import qa_node
from workflow.nodes.pii_reinsertion import pii_reinsertion_node

logger = logging.getLogger(__name__)


def create_workflow() -> StateGraph:
    """
    Creates the LangGraph workflow for Exit Ready Snapshot assessment.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Initialize workflow with our state schema
    workflow = StateGraph(WorkflowState)
    
    # Add all nodes to the graph
    workflow.add_node("intake", intake_node)
    workflow.add_node("research", research_node)
    workflow.add_node("scoring", scoring_node)
    workflow.add_node("summary", summary_node)
    workflow.add_node("qa", qa_node)
    workflow.add_node("pii_reinsertion", pii_reinsertion_node)
    
    # Define the execution flow (sequential pipeline)
    workflow.set_entry_point("intake")
    workflow.add_edge("intake", "research")
    workflow.add_edge("research", "scoring")
    workflow.add_edge("scoring", "summary")
    workflow.add_edge("summary", "qa")
    workflow.add_edge("qa", "pii_reinsertion")
    workflow.add_edge("pii_reinsertion", END)
    
    # Compile the workflow
    return workflow.compile()


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


async def process_assessment_async(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async entry point for processing assessments.
    
    Args:
        form_data: Dictionary containing the assessment form data
        
    Returns:
        Dictionary formatted according to the API contract
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting LangGraph workflow for UUID: {form_data.get('uuid')}")
        
        # Create the workflow
        app = create_workflow()
        
        # Prepare initial state
        initial_state = {
            "uuid": form_data.get("uuid"),
            "form_data": form_data,
            "locale": determine_locale(form_data.get("location", "Other")),
            "current_stage": "intake",
            "error": None,
            "processing_time": {},
            "messages": []
        }
        
        # Execute the workflow
        result = await app.ainvoke(initial_state)
        
        # Calculate total processing time
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Check if there was an error
        if result.get("error"):
            logger.error(f"Workflow error: {result.get('error')}")
            return {
                "uuid": form_data.get("uuid"),
                "status": "error",
                "error": result.get("error"),
                "locale": result.get("locale", "us")
            }
        
        # Extract the final output from the workflow state
        final_output = result.get("final_output", {})
        
        # Format the response according to the API contract
        formatted_response = {
            "uuid": form_data.get("uuid"),
            "status": "completed",
            "owner_name": final_output.get("owner_name", form_data.get("name", "")),
            "email": final_output.get("email", form_data.get("email", "")),
            "company_name": final_output.get("company_name", ""),
            "industry": form_data.get("industry", ""),
            "location": form_data.get("location", ""),
            "locale": result.get("locale", "us"),
            "scores": final_output.get("scores", {}),
            "executive_summary": final_output.get("executive_summary", ""),
            "category_summaries": final_output.get("category_summaries", {}),
            "recommendations": final_output.get("recommendations", {}),
            "next_steps": final_output.get("next_steps", "Schedule a consultation to discuss your personalized Exit Value Growth Plan."),
            "content": final_output.get("content", ""),
            "processing_time": total_time,
            "metadata": {
                "stages_completed": list(result.get("processing_time", {}).keys()),
                "total_messages": len(result.get("messages", [])),
                "stage_timings": result.get("processing_time", {})
            }
        }
        
        logger.info(f"Workflow completed successfully for UUID: {form_data.get('uuid')} in {total_time:.1f}s")
        
        return formatted_response
        
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}", exc_info=True)
        return {
            "uuid": form_data.get("uuid"),
            "status": "error",
            "error": str(e),
            "locale": determine_locale(form_data.get("location", "Other"))
        }


def process_assessment_sync(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper for process_assessment_async.
    Used for backwards compatibility with existing code.
    """
    import asyncio
    
    # Get or create event loop
    try:
        loop = asyncio.get_running_loop()
        # If we're already in an async context, we can't use run()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, process_assessment_async(form_data))
            return future.result()
    except RuntimeError:
        # No running loop, we can use asyncio.run()
        return asyncio.run(process_assessment_async(form_data))