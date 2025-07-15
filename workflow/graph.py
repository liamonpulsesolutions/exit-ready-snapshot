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
        form_data: Raw form data from Tally/n8n
        
    Returns:
        Complete assessment results ready for API response
    """
    logger.info(f"Starting workflow for UUID: {form_data.get('uuid')}")
    
    try:
        # Create the workflow
        app = create_workflow()
        
        # Prepare initial state
        initial_state = {
            "uuid": form_data.get("uuid", "unknown"),
            "form_data": form_data,
            "locale": determine_locale(form_data.get("location", "Other")),
            "current_stage": "starting",
            "processing_time": {},
            "messages": [f"Assessment started at {datetime.now().isoformat()}"],
            # Extract business context for easy access
            "industry": form_data.get("industry"),
            "location": form_data.get("location"),
            "revenue_range": form_data.get("revenue_range"),
            "exit_timeline": form_data.get("exit_timeline"),
            "years_in_business": form_data.get("years_in_business")
        }
        
        # Execute the workflow
        start_time = datetime.now()
        result = await app.ainvoke(initial_state)
        end_time = datetime.now()
        
        # Log execution time
        total_time = (end_time - start_time).total_seconds()
        logger.info(f"Assessment completed for UUID: {form_data.get('uuid')} in {total_time:.2f}s")
        
        # Extract and format the final output
        if result.get("error"):
            return {
                "uuid": form_data.get("uuid"),
                "status": "error",
                "error": result["error"],
                "locale": result.get("locale", "us")
            }
        
        # Return the formatted response matching existing API contract
        final_output = result.get("final_output", {})
        return {
            "uuid": form_data.get("uuid"),
            "status": "completed",
            "locale": result.get("locale", "us"),
            "owner_name": final_output.get("owner_name", form_data.get("name")),
            "email": final_output.get("email", form_data.get("email")),
            "company_name": final_output.get("company_name"),
            "industry": form_data.get("industry"),
            "location": form_data.get("location"),
            "scores": final_output.get("scores", {}),
            "executive_summary": final_output.get("executive_summary", ""),
            "category_summaries": final_output.get("category_summaries", {}),
            "recommendations": final_output.get("recommendations", {}),
            "next_steps": final_output.get("next_steps", ""),
            "content": final_output.get("content", ""),
            "processing_time": total_time,
            "metadata": {
                "stages_completed": list(result.get("processing_time", {}).keys()),
                "total_messages": len(result.get("messages", []))
            }
        }
        
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