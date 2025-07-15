"""
Intake node for LangGraph workflow.
Handles form validation, PII detection/redaction, and data logging.
Uses pure functions from core modules.
"""

import logging
import json
from typing import Dict, Any
from datetime import datetime

from workflow.core.validators import validate_form_data, validate_email
from workflow.core.pii_handler import (
    anonymize_form_data, 
    store_pii_mapping,
    PIIDetector
)
from src.tools.google_sheets import GoogleSheetsLogger

logger = logging.getLogger(__name__)


def intake_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intake node that processes form submissions.
    
    This node:
    1. Validates form data
    2. Detects and redacts PII
    3. Stores PII mapping for later reinsertion
    4. Logs to CRM
    5. Logs anonymized responses
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with intake results
    """
    start_time = datetime.now()
    logger.info(f"=== INTAKE NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "intake"
        state["messages"].append(f"Intake started at {start_time.isoformat()}")
        
        # Get form data from state
        form_data = state["form_data"]
        
        # Step 1: Validate form data
        logger.info("Validating form data...")
        is_valid, missing_fields, validation_details = validate_form_data(form_data)
        
        if not is_valid:
            error_msg = f"Validation failed - Missing fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            state["error"] = error_msg
            state["current_stage"] = "intake_failed"
            return state
        
        logger.info(f"Validation passed - {validation_details['response_count']} responses found")
        
        # Step 2: Validate email format
        email = form_data.get('email', '')
        if not validate_email(email):
            logger.warning(f"Invalid email format: {email}")
        
        # Step 3: Anonymize form data and create PII mapping
        logger.info("Anonymizing form data...")
        anonymized_data, pii_mapping = anonymize_form_data(form_data)
        
        logger.info(f"Found {len(pii_mapping)} PII items to map")
        
        # Step 4: Store PII mapping (critical!)
        store_pii_mapping(state['uuid'], pii_mapping)
        logger.info(f"Stored PII mapping for UUID: {state['uuid']}")
        
        # Step 5: Log to CRM (with original data)
        logger.info("Logging to CRM...")
        sheets_logger = GoogleSheetsLogger()
        crm_result = sheets_logger.log_to_crm(form_data)
        crm_success = crm_result.get('status') == 'success'
        
        # Step 6: Log anonymized responses
        logger.info("Logging anonymized responses...")
        responses_result = sheets_logger.log_responses(
            state['uuid'], 
            anonymized_data.get('responses', {})
        )
        responses_success = responses_result.get('status') == 'success'
        
        # Prepare intake result
        intake_result = {
            "validation_status": "success",
            "validation_details": validation_details,
            "anonymized_data": anonymized_data,
            "pii_mapping_stored": True,
            "pii_entries": len(pii_mapping),
            "crm_logged": crm_success,
            "responses_logged": responses_success,
            "company_detected": "[COMPANY_NAME]" in pii_mapping
        }
        
        # Update state
        state["intake_result"] = intake_result
        state["anonymized_data"] = anonymized_data
        state["pii_mapping"] = pii_mapping
        
        # Add processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        state["processing_time"]["intake"] = processing_time
        
        # Add status message
        state["messages"].append(
            f"Intake completed in {processing_time:.2f}s - "
            f"PII: {len(pii_mapping)} items, "
            f"CRM: {'✓' if crm_success else '✗'}, "
            f"Responses: {'✓' if responses_success else '✗'}"
        )
        
        logger.info(f"=== INTAKE NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in intake node: {str(e)}", exc_info=True)
        state["error"] = f"Intake failed: {str(e)}"
        state["messages"].append(f"ERROR in intake: {str(e)}")
        state["current_stage"] = "intake_error"
        return state