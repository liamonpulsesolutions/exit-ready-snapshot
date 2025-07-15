"""
LangGraph state definition for Exit Ready Snapshot assessment pipeline.
Single source of truth for all data flowing through the workflow.
"""

from typing import TypedDict, Dict, Any, Optional, List, Annotated
from datetime import datetime
from langgraph.graph.message import add_messages


class WorkflowState(TypedDict):
    """
    Complete state definition for the Exit Ready Snapshot workflow.
    All data flows through this state as it passes between nodes.
    """
    # Input data
    uuid: str
    form_data: Dict[str, Any]
    locale: str
    
    # Node outputs
    intake_result: Optional[Dict[str, Any]]
    research_result: Optional[Dict[str, Any]]
    scoring_result: Optional[Dict[str, Any]]
    summary_result: Optional[Dict[str, Any]]
    qa_result: Optional[Dict[str, Any]]
    final_output: Optional[Dict[str, Any]]
    
    # Shared data
    pii_mapping: Optional[Dict[str, str]]
    anonymized_data: Optional[Dict[str, Any]]
    
    # Execution metadata
    current_stage: str
    error: Optional[str]
    processing_time: Dict[str, float]
    messages: Annotated[List[str], add_messages]
    
    # Business context (extracted for easy access)
    industry: Optional[str]
    location: Optional[str]
    revenue_range: Optional[str]
    exit_timeline: Optional[str]
    years_in_business: Optional[str]