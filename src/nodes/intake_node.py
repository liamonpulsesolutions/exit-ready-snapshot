"""
Intake node for LangGraph workflow.
Handles form validation, PII detection/redaction, and data logging.
Reuses all existing tools from the CrewAI intake agent.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any

# Import the state type
from src.workflow import AssessmentState

# Import ALL existing tools from the CrewAI intake agent
from src.agents.intake_agent import (
    validate_form_data,
    detect_and_redact_pii_tool,
    log_to_crm_tool,
    log_responses_tool,
    store_pii_mapping_tool,
    process_complete_form
)

# Import utilities
from src.tools.google_sheets import GoogleSheetsLogger
from src.tools.pii_detector import PIIDetector
from src.utils.pii_storage import store_pii_mapping as store_pii_mapping_direct
from src.utils.json_helper import safe_parse_json

logger = logging.getLogger(__name__)


def intake_node(state: AssessmentState) -> AssessmentState:
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
        
        # Step 1: Process complete form (this does validation, PII detection, and storage)
        logger.info("Processing complete form with PII detection...")
        
        # Convert form data to JSON string for the tool
        form_data_json = json.dumps(form_data)
        
        # Call the main processing tool
        process_result = process_complete_form._run(form_data_json)
        
        # The tool returns a formatted text result, but we need the actual data
        # So we'll also call the underlying functions directly for structured data
        
        # Direct PII detection and redaction
        pii_detector = PIIDetector()
        anonymized_data = form_data.copy()
        
        # Initialize PII mapping
        pii_mapping = {
            "[OWNER_NAME]": form_data.get('name', ''),
            "[EMAIL]": form_data.get('email', ''),
            "[LOCATION]": form_data.get('location', ''),
            "[UUID]": state['uuid']
        }
        
        # Redact basic fields
        anonymized_data['name'] = '[OWNER_NAME]'
        anonymized_data['email'] = '[EMAIL]'
        
        # Process all text responses for additional PII
        anonymized_responses = {}
        pii_found_in_responses = 0
        
        for q_id, response in form_data.get('responses', {}).items():
            if response and isinstance(response, str) and len(response) > 20:
                # Detect and redact PII in responses
                pii_result = pii_detector.detect_and_redact(response)
                anonymized_responses[q_id] = pii_result['redacted_text']
                
                # Add any found PII to mapping
                if pii_result.get('mapping'):
                    pii_mapping.update(pii_result['mapping'])
                    pii_found_in_responses += len(pii_result['mapping'])
            else:
                anonymized_responses[q_id] = response
        
        anonymized_data['responses'] = anonymized_responses
        
        # Look for company names in responses
        all_responses_text = ' '.join(str(v) for v in form_data.get('responses', {}).values())
        if 'company' in all_responses_text.lower() or 'business' in all_responses_text.lower():
            # Simple company name extraction
            import re
            company_patterns = [
                r'(?:my company|our company|the company),?\s+([A-Z][A-Za-z\s&]+?)(?:\s+(?:Inc|LLC|Ltd|Corp))?',
                r'([A-Z][A-Za-z\s&]+?)\s+(?:Inc|LLC|Ltd|Corp|Company)',
            ]
            
            for pattern in company_patterns:
                match = re.search(pattern, all_responses_text)
                if match:
                    company_name = match.group(1).strip()
                    pii_mapping["[COMPANY_NAME]"] = company_name
                    # Redact company name from responses
                    for q_id in anonymized_responses:
                        if company_name in anonymized_responses[q_id]:
                            anonymized_responses[q_id] = anonymized_responses[q_id].replace(
                                company_name, "[COMPANY_NAME]"
                            )
                    break
        
        # Store the PII mapping (critical!)
        store_pii_mapping_direct(state['uuid'], pii_mapping)
        logger.info(f"Stored PII mapping with {len(pii_mapping)} entries")
        
        # Step 2: Log to CRM (with original data)
        logger.info("Logging to CRM...")
        crm_result = log_to_crm_tool._run(json.dumps(form_data))
        
        # Step 3: Log anonymized responses
        logger.info("Logging anonymized responses...")
        response_log_data = {
            "uuid": state['uuid'],
            "responses": anonymized_responses
        }
        responses_result = log_responses_tool._run(json.dumps(response_log_data))
        
        # Prepare intake result
        intake_result = {
            "validation_status": "success",
            "anonymized_data": anonymized_data,
            "pii_mapping_stored": True,
            "pii_entries": len(pii_mapping),
            "crm_logged": "success" in crm_result.lower(),
            "responses_logged": "success" in responses_result.lower(),
            "pii_found_in_responses": pii_found_in_responses,
            "company_detected": "[COMPANY_NAME]" in pii_mapping,
            "processing_summary": process_result
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
            f"CRM: {'✓' if intake_result['crm_logged'] else '✗'}, "
            f"Responses: {'✓' if intake_result['responses_logged'] else '✗'}"
        )
        
        logger.info(f"=== INTAKE NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in intake node: {str(e)}", exc_info=True)
        state["error"] = f"Intake failed: {str(e)}"
        state["messages"].append(f"ERROR in intake: {str(e)}")
        raise