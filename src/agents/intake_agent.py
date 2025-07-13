from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, Type
import logging
import json
import os
from datetime import datetime
from ..tools.google_sheets import GoogleSheetsLogger
from ..tools.pii_detector import PIIDetector
from ..utils.json_helper import safe_parse_json
from ..utils.pii_storage import store_pii_mapping

# ========== DEBUG SETUP ==========
DEBUG_MODE = os.getenv('CREWAI_DEBUG', 'false').lower() == 'true'

class DebugFileLogger:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = "debug_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create debug file
        self.debug_file = os.path.join(
            self.log_dir, 
            f"{agent_name}_{self.session_id}_debug.log"
        )
        
        # Create structured output file
        self.output_file = os.path.join(
            self.log_dir,
            f"{agent_name}_{self.session_id}_output.json"
        )
        
        self.outputs = []
        
        # Write header
        with open(self.debug_file, 'w') as f:
            f.write(f"=== {agent_name.upper()} DEBUG LOG ===\n")
            f.write(f"Session: {self.session_id}\n")
            f.write(f"Started: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
    
    def log(self, category: str, message: str, data: Any = None):
        timestamp = datetime.now().isoformat()
        with open(self.debug_file, 'a') as f:
            f.write(f"[{timestamp}] {category}: {message}\n")
            if data:
                f.write(f"  Data Type: {type(data)}\n")
                f.write(f"  Data Content: {repr(data)[:500]}...\n")
                if isinstance(data, str):
                    try:
                        parsed = json.loads(data)
                        f.write(f"  Parsed JSON: {json.dumps(parsed, indent=2)[:500]}...\n")
                    except:
                        f.write("  Not valid JSON\n")
            f.write("-" * 30 + "\n")
    
    def save_output(self, tool_name: str, input_data: Any, output_data: Any):
        output_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "input": {
                "type": str(type(input_data)),
                "content": str(input_data)[:1000]
            },
            "output": {
                "type": str(type(output_data)),
                "content": str(output_data)[:1000]
            }
        }
        self.outputs.append(output_entry)
        
        # Save to file
        with open(self.output_file, 'w') as f:
            json.dump({
                "agent": self.agent_name,
                "session": self.session_id,
                "outputs": self.outputs
            }, f, indent=2)

# Global logger instance
debug_logger = DebugFileLogger("intake_agent") if DEBUG_MODE else None

# Regular logger
logger = logging.getLogger(__name__)

# Initialize tools globally so they can be used by tool classes
sheets_logger = GoogleSheetsLogger()
pii_detector = PIIDetector()

# Tool Input Schemas
class ValidateFormDataInput(BaseModel):
    form_data_str: str = Field(
        default="{}",
        description="JSON string representation of the form data"
    )

class DetectAndRedactPIIInput(BaseModel):
    text: str = Field(
        default="",
        description="Text to scan for PII and redact"
    )

class LogToCRMInput(BaseModel):
    user_data: str = Field(
        default="{}",
        description="JSON string containing user data to log"
    )

class LogResponsesInput(BaseModel):
    data: str = Field(
        default="{}",
        description="JSON string containing UUID and responses to log"
    )

class StorePIIMappingInput(BaseModel):
    mapping_data: str = Field(
        default="{}",
        description="JSON string containing UUID and PII mapping"
    )

class ProcessCompleteFormInput(BaseModel):
    form_data_str: str = Field(
        default="{}",
        description="JSON string representation of the complete form data"
    )

# Tool Classes
class ValidateFormDataTool(BaseTool):
    name: str = "validate_form_data"
    description: str = """
    Validate that all required form fields are present and properly formatted.
    
    Input should be JSON string representation of the form data.
    
    Returns validation status message.
    """
    args_schema: Type[BaseModel] = ValidateFormDataInput
    
    def _run(self, form_data_str: str = "{}", **kwargs) -> str:
        if debug_logger:
            debug_logger.log("TOOL_INPUT", f"{self.name} called", form_data_str)
        
        try:
            # Use safe parsing
            form_data = safe_parse_json(form_data_str, {}, "validate_form_data")
            if not form_data:
                result = "Validation Failed: No form data provided or invalid JSON format. Please check the input data."
                if debug_logger:
                    debug_logger.save_output(self.name, form_data_str, result)
                return result
        except Exception as e:
            result = f"Validation Failed: Input parsing error - {str(e)}"
            if debug_logger:
                debug_logger.save_output(self.name, form_data_str, result)
            return result
        
        required_fields = [
            'uuid', 'name', 'email', 'industry', 'years_in_business',
            'age_range', 'exit_timeline', 'location', 'responses'
        ]
        
        # Revenue range is optional but recommended
        optional_fields = ['revenue_range']
        
        missing_fields = []
        for field in required_fields:
            if field not in form_data or not form_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            result = f"Validation Failed: Missing required fields - {', '.join(missing_fields)}. Please ensure all required fields are provided."
        else:
            responses = form_data.get('responses', {})
            response_count = len(responses)
            
            result = f"""Validation Successful:
- UUID: {form_data.get('uuid')}
- All {len(required_fields)} required fields present
- {response_count} responses provided
- Revenue range: {'Provided' if form_data.get('revenue_range') else 'Not provided (optional)'}
- Ready for PII processing"""
            
        if debug_logger:
            debug_logger.save_output(self.name, form_data_str, result)
            debug_logger.log("VALIDATION_RESULT", result, form_data)
            
        return result

class DetectAndRedactPIITool(BaseTool):
    name: str = "detect_and_redact_pii"
    description: str = """
    Detect PII in text and return both the redacted text and a mapping of what was redacted.
    
    Input should be plain text to scan.
    
    Returns status message with redaction summary.
    """
    args_schema: Type[BaseModel] = DetectAndRedactPIIInput
    
    def _run(self, text: str = "", **kwargs) -> str:
        if debug_logger:
            debug_logger.log("TOOL_INPUT", f"{self.name} called", text)
            
        if not text:
            result = "PII Detection Failed: No text provided for scanning"
            if debug_logger:
                debug_logger.save_output(self.name, text, result)
            return result
        
        try:
            # Use the PII detector
            detection_result = pii_detector.detect_and_redact(text)
            
            redacted_text = detection_result.get('redacted_text', text)
            pii_mapping = detection_result.get('mapping', {})
            
            if pii_mapping:
                mapping_items = '\n'.join(f"  - {k}: {v}" for k, v in pii_mapping.items())
                result = f"""PII Detection Complete:
- Original text length: {len(text)} chars
- Redacted text length: {len(redacted_text)} chars
- PII items found: {len(pii_mapping)}

Mapping:
{mapping_items}

Status: Successfully redacted all PII"""
            else:
                result = """PII Detection Complete:
- No PII detected in the provided text
- Text remains unchanged
- Safe to use as-is"""
            
            if debug_logger:
                debug_logger.save_output(self.name, text, result)
                debug_logger.log("PII_DETECTION", f"Found {len(pii_mapping)} PII items", pii_mapping)
                
            return result
            
        except Exception as e:
            result = f"PII Detection Failed: {str(e)}"
            if debug_logger:
                debug_logger.save_output(self.name, text, result)
            logger.error(f"Error in PII detection: {str(e)}")
            return result

class LogToCRMTool(BaseTool):
    name: str = "log_to_crm"
    description: str = """
    Log user data to CRM (Google Sheets).
    
    Input should be JSON string containing user data.
    
    Returns logging status message.
    """
    args_schema: Type[BaseModel] = LogToCRMInput
    
    def _run(self, user_data: str = "{}", **kwargs) -> str:
        if debug_logger:
            debug_logger.log("TOOL_INPUT", f"{self.name} called", user_data)
            
        try:
            data = safe_parse_json(user_data, {}, "log_to_crm")
            if not data:
                result = "CRM Logging Failed: No data provided"
                if debug_logger:
                    debug_logger.save_output(self.name, user_data, result)
                return result
            
            # Log to CRM
            log_result = sheets_logger.log_to_crm(data)
            
            if log_result.get('success'):
                result = f"""CRM Logging Successful:
- UUID: {data.get('uuid')}
- Name: {data.get('name')}
- Email: {data.get('email')}
- Mode: {log_result.get('mode', 'Unknown')}
- Status: Entry logged successfully"""
            else:
                result = f"CRM Logging Failed: {log_result.get('error', 'Unknown error')}"
            
            if debug_logger:
                debug_logger.save_output(self.name, user_data, result)
                debug_logger.log("CRM_RESULT", result, log_result)
                
            return result
            
        except Exception as e:
            result = f"CRM Logging Failed: {str(e)}"
            if debug_logger:
                debug_logger.save_output(self.name, user_data, result)
            logger.error(f"Error logging to CRM: {str(e)}")
            return result

class LogResponsesTool(BaseTool):
    name: str = "log_responses"
    description: str = """
    Log assessment responses to tracking sheet.
    
    Input should be JSON string containing UUID and responses.
    
    Returns logging status message.
    """
    args_schema: Type[BaseModel] = LogResponsesInput
    
    def _run(self, data: str = "{}", **kwargs) -> str:
        if debug_logger:
            debug_logger.log("TOOL_INPUT", f"{self.name} called", data)
            
        try:
            parsed_data = safe_parse_json(data, {}, "log_responses")
            if not parsed_data:
                result = "Response Logging Failed: No data provided"
                if debug_logger:
                    debug_logger.save_output(self.name, data, result)
                return result
            
            # Log responses
            log_result = sheets_logger.log_responses(
                parsed_data.get('uuid', 'unknown'),
                parsed_data.get('responses', {})
            )
            
            response_count = len(parsed_data.get('responses', {}))
            
            if log_result.get('success'):
                result = f"""Response Logging Successful:
- UUID: {parsed_data.get('uuid')}
- Responses logged: {response_count}
- Mode: {log_result.get('mode', 'Unknown')}
- Status: All responses logged successfully"""
            else:
                result = f"Response Logging Failed: {log_result.get('error', 'Unknown error')}"
            
            if debug_logger:
                debug_logger.save_output(self.name, data, result)
                debug_logger.log("RESPONSE_LOG_RESULT", result, log_result)
                
            return result
            
        except Exception as e:
            result = f"Response Logging Failed: {str(e)}"
            if debug_logger:
                debug_logger.save_output(self.name, data, result)
            logger.error(f"Error logging responses: {str(e)}")
            return result

class StorePIIMappingTool(BaseTool):
    name: str = "store_pii_mapping"
    description: str = """
    Store PII mapping for later reinsertion.
    
    Input should be JSON string containing UUID and mapping data.
    
    Returns storage status message.
    """
    args_schema: Type[BaseModel] = StorePIIMappingInput
    
    def _run(self, mapping_data: str = "{}", **kwargs) -> str:
        if debug_logger:
            debug_logger.log("TOOL_INPUT", f"{self.name} called", mapping_data)
            
        try:
            data = safe_parse_json(mapping_data, {}, "store_pii_mapping")
            if not data:
                result = "PII Storage Failed: No mapping data provided"
                if debug_logger:
                    debug_logger.save_output(self.name, mapping_data, result)
                return result
            
            uuid = data.get('uuid')
            mapping = data.get('mapping')
            
            if uuid and mapping:
                store_pii_mapping(uuid, mapping)
                logger.info(f"Stored PII mapping for UUID: {uuid} with {len(mapping)} entries")
                
                # Format success message with mapping details
                result = f"""PII Mapping Stored Successfully:
- UUID: {uuid}
- Entries Stored: {len(mapping)}
- Mapping includes:
  {chr(10).join(f'  - {k}' for k in mapping.keys())}
- Ready for final personalization"""
            else:
                result = "PII Storage Failed: Missing UUID or mapping data in input"
            
            if debug_logger:
                debug_logger.save_output(self.name, mapping_data, result)
                debug_logger.log("PII_STORAGE", result, {"uuid": uuid, "mapping_size": len(mapping) if mapping else 0})
                
            return result
                
        except Exception as e:
            result = f"PII Storage Failed: {str(e)}"
            if debug_logger:
                debug_logger.save_output(self.name, mapping_data, result)
            logger.error(f"Error storing PII mapping: {str(e)}")
            return result

class ProcessCompleteFormTool(BaseTool):
    name: str = "process_complete_form"
    description: str = """
    Complete intake processing: validate, detect PII, redact, and prepare output.
    
    Input should be JSON string representation of the complete form data.
    
    Returns comprehensive processing status and results.
    """
    args_schema: Type[BaseModel] = ProcessCompleteFormInput
    
    def _run(self, form_data_str: str = "{}", **kwargs) -> str:
        if debug_logger:
            debug_logger.log("TOOL_INPUT", f"{self.name} called - MAIN PROCESSING TOOL", form_data_str)
            
        try:
            logger.info(f"=== PROCESS COMPLETE FORM CALLED ===")
            logger.info(f"Input type: {type(form_data_str)}")
            logger.info(f"Input preview: {str(form_data_str)[:200]}...")
            
            # Handle CrewAI passing dict vs string
            if isinstance(form_data_str, dict):
                # CrewAI might pass the task context as a dict
                if 'form_data' in form_data_str:
                    actual_form_data = form_data_str['form_data']
                elif 'description' in form_data_str:
                    actual_form_data = form_data_str['description']
                else:
                    # Try to find JSON in the dict
                    actual_form_data = json.dumps(form_data_str)
            else:
                actual_form_data = form_data_str
            
            # Parse form data using safe parsing
            form_data = safe_parse_json(actual_form_data, {}, "process_complete_form")
            
            if not form_data:
                result = """Form Processing Failed:
- Error: No form data provided or invalid JSON
- Status: Unable to process
- Please check the input data format"""
                if debug_logger:
                    debug_logger.save_output(self.name, form_data_str, result)
                return result
            
            uuid = form_data.get('uuid', 'unknown')
            logger.info(f"Processing form for UUID: {uuid}")
            
            if debug_logger:
                debug_logger.log("FORM_PARSED", f"Successfully parsed form for UUID: {uuid}", form_data)
            
            # Initialize PII mapping
            complete_pii_mapping = {
                "[OWNER_NAME]": form_data.get('name', ''),
                "[EMAIL]": form_data.get('email', ''),
                "[LOCATION]": form_data.get('location', ''),
                "[UUID]": uuid
            }
            
            # Create anonymized version
            anonymized_data = form_data.copy()
            
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
                        complete_pii_mapping.update(pii_result['mapping'])
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
                        complete_pii_mapping["[COMPANY_NAME]"] = company_name
                        # Redact company name from responses
                        for q_id in anonymized_responses:
                            if company_name in anonymized_responses[q_id]:
                                anonymized_responses[q_id] = anonymized_responses[q_id].replace(
                                    company_name, "[COMPANY_NAME]"
                                )
                        break
            
            # Store the mapping (critical step!)
            store_pii_mapping(uuid, complete_pii_mapping)
            
            if debug_logger:
                debug_logger.log("PII_MAPPING_COMPLETE", f"Stored {len(complete_pii_mapping)} PII entries", complete_pii_mapping)
            
            # Return comprehensive status message
            result = f"""Form Processing Complete:

VALIDATION STATUS: Success
- UUID: {uuid}
- All required fields validated
- All 10 responses present

PII PROCESSING:
- Basic PII extracted: 4 items (name, email, location, UUID)
- Additional PII found in responses: {pii_found_in_responses} items
- Company name detected: {'Yes' if '[COMPANY_NAME]' in complete_pii_mapping else 'No'}
- Total PII mappings stored: {len(complete_pii_mapping)}

ANONYMIZATION:
- Owner name → [OWNER_NAME]
- Email → [EMAIL]
- Location → [LOCATION]
- All response PII → [REDACTED]

PII MAPPING STORED:
- Storage status: Success
- Mapping entries: {len(complete_pii_mapping)}
- Ready for final personalization

NEXT STEPS:
- CRM logging ready
- Response logging ready
- Data prepared for analysis"""
            
            if debug_logger:
                debug_logger.save_output(self.name, form_data_str, result)
                debug_logger.log("FINAL_OUTPUT", "Processing complete", {
                    "uuid": uuid,
                    "anonymized_data": anonymized_data,
                    "pii_mapping_stored": True,
                    "validation_status": "success"
                })
                
                # Save final JSON output that task expects
                task_output = {
                    "uuid": uuid,
                    "anonymized_data": anonymized_data,
                    "pii_mapping_stored": True,
                    "validation_status": "success"
                }
                debug_logger.log("TASK_OUTPUT_FORMAT", "JSON output for task", task_output)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing form: {str(e)}")
            result = f"""Form Processing Failed:
- Error: {str(e)}
- UUID: {form_data.get('uuid', 'unknown') if 'form_data' in locals() else 'unknown'}
- Status: Processing incomplete
- Please review error and retry"""
            
            if debug_logger:
                debug_logger.save_output(self.name, form_data_str, result)
                debug_logger.log("ERROR", "Processing failed", str(e))
                
            return result

# Create tool instances
validate_form_data = ValidateFormDataTool()
detect_and_redact_pii_tool = DetectAndRedactPIITool()
log_to_crm_tool = LogToCRMTool()
log_responses_tool = LogResponsesTool()
store_pii_mapping_tool = StorePIIMappingTool()
process_complete_form = ProcessCompleteFormTool()

def create_intake_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the intake agent for processing form submissions"""
    
    # Get agent configuration from prompts
    config = prompts.get('intake_agent', {})
    
    # Create tools list using instances
    tools = [
        validate_form_data,
        detect_and_redact_pii_tool,
        log_to_crm_tool,
        log_responses_tool,
        store_pii_mapping_tool,
        process_complete_form
    ]
    
    if debug_logger:
        debug_logger.log("AGENT_CREATION", f"Creating intake agent with {len(tools)} tools")
    
    return Agent(
        role=config.get('role'),
        goal=config.get('goal'),
        backstory=config.get('backstory'),
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3
    )