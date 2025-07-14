"""
LangGraph workflow definition for Exit Ready Snapshot assessment pipeline.
Replaces CrewAI orchestration with explicit state management.
"""

from typing import TypedDict, Dict, Any, Optional, List, Annotated
from datetime import datetime
import logging
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)

class AssessmentState(TypedDict):
    """
    State definition for the Exit Ready Snapshot assessment workflow.
    All data flows through this state as it passes between nodes.
    """
    # Input data
    uuid: str
    form_data: Dict[str, Any]
    locale: str
    
    # Agent outputs - each node adds its results here
    intake_result: Optional[Dict[str, Any]]
    research_result: Optional[Dict[str, Any]]
    scoring_result: Optional[Dict[str, Any]]
    summary_result: Optional[Dict[str, Any]]
    qa_result: Optional[Dict[str, Any]]
    final_output: Optional[Dict[str, Any]]
    
    # Shared data across agents
    pii_mapping: Optional[Dict[str, str]]
    anonymized_data: Optional[Dict[str, Any]]
    
    # Execution metadata
    current_stage: str
    error: Optional[str]
    processing_time: Optional[Dict[str, float]]
    messages: Annotated[List[str], add_messages]  # For debugging
    
    # Business context (extracted for easy access)
    industry: Optional[str]
    location: Optional[str]
    revenue_range: Optional[str]
    exit_timeline: Optional[str]
    years_in_business: Optional[str]


def create_assessment_workflow() -> StateGraph:
    """
    Creates the LangGraph workflow for Exit Ready Snapshot assessment.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Import all node functions (we'll create these next)
    from src.nodes.intake_node import intake_node
    from src.nodes.research_node import research_node
    from src.nodes.scoring_node import scoring_node
    from src.nodes.summary_node import summary_node
    from src.nodes.qa_node import qa_node
    from src.nodes.pii_reinsertion_node import pii_reinsertion_node
    
    # Initialize workflow with our state schema
    workflow = StateGraph(AssessmentState)
    
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
    """Determine locale based on location - reused from crew.py"""
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


async def process_assessment_async(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async entry point for processing assessments.
    Supports concurrent execution without data mixing.
    
    Args:
        form_data: Raw form data from Tally/n8n
        
    Returns:
        Complete assessment results ready for API response
    """
    logger.info(f"Starting LangGraph assessment for UUID: {form_data.get('uuid')}")
    
    try:
        # Create the workflow
        app = create_assessment_workflow()
        
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
        
        # Return the formatted response matching CrewAI output structure
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
        logger.error(f"Error in LangGraph assessment: {str(e)}", exc_info=True)
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


# For debugging - visualize the workflow
def visualize_workflow():
    """Generate a visual representation of the workflow graph"""
    app = create_assessment_workflow()
    try:
        # This will print the mermaid graph definition
        print(app.get_graph().draw_mermaid())
    except Exception as e:
        logger.warning(f"Could not generate visualization: {e}")
        # Fallback to simple text representation
        print("Workflow: intake → research → scoring → summary → qa → pii_reinsertion → END")