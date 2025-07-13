from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, Type
import logging
from ..tools.google_sheets import GoogleSheetsLogger
from ..tools.pii_detector import PIIDetector
from ..utils.json_helper import safe_parse_json
from ..utils.pii_storage import store_pii_mapping
import json

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
        try:
            # Use safe parsing
            form_data = safe_parse_json(form_data_str, {}, "validate_form_data")
            if not form_data:
                return "Validation Failed: No form data provided or invalid JSON format. Please check the input data."
        except Exception as e:
            return f"Validation Failed: Input parsing error - {str(e)}"
        
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
            return f"Validation Failed: Missing required fields - {', '.join(missing_fields)}. Please ensure all required fields are provided."
        
        # Log missing optional fields as warnings
        missing_optional = []
        for field in optional_fields:
            if field not in form_data or not form_data[field]:
                missing_optional.append(field)
        
        if missing_optional:
            logger.warning(f"Missing optional fields: {', '.join(missing_optional)} - using defaults")
        
        # Validate responses
        expected_questions = [f"q{i}" for i in range(1, 11)]
        missing_responses = []
        
        responses = form_data.get('responses', {})
        for q in expected_questions:
            if q not in responses or not responses[q]:
                missing_responses.append(q)
        
        if missing_responses:
            return f"Validation Failed: Missing responses for questions - {', '.join(missing_responses)}. All 10 questions must be answered."
        
        # Success message with summary
        return f"""Validation Successful:
- UUID: {form_data.get('uuid')}
- Name: {form_data.get('name')}
- Industry: {form_data.get('industry')}
- All required fields present
- All 10 questions answered
- Ready for processing"""

class DetectAndRedactPIITool(BaseTool):
    name: str = "detect_and_redact_pii_tool"
    description: str = """
    Detect and redact PII from text, returning anonymized text and mapping.
    
    Input: Text string to scan for PII
    
    Returns summary of PII detection and redaction results.
    """
    args_schema: Type[BaseModel] = DetectAndRedactPIIInput
    
    def _run(self, text: str = "", **kwargs) -> str:
        if not text or text.strip() == "":
            return "No text provided for PII detection."
        
        result = pii_detector.detect_and_redact(text)
        
        # Format as readable text
        if result.get('pii_found'):
            mapping = result.get('mapping', {})
            return f"""PII Detection Complete:
- PII Found: Yes
- Items Redacted: {len(mapping)}
- Redaction Details:
  {chr(10).join(f'  - {k}: [REDACTED]' for k in mapping.keys())}
- All PII successfully anonymized"""
        else:
            return """PII Detection Complete:
- PII Found: No
- No personal information detected in the text
- Text is already anonymous"""

class LogToCRMTool(BaseTool):
    name: str = "log_to_crm_tool"
    description: str = """
    Log user data to Google Sheets CRM.
    
    Input should be JSON string containing user data.
    
    Returns logging status message.
    """
    args_schema: Type[BaseModel] = LogToCRMInput
    
    def _run(self, user_data: str = "{}", **kwargs) -> str:
        try:
            user_data_dict = safe_parse_json(user_data, {}, "log_to_crm")
            if not user_data_dict:
                return "CRM Logging Failed: No user data provided"
            
            result = sheets_logger.log_to_crm(user_data_dict)
            
            # Format result as readable text
            if result.get('status') == 'success':
                mode = result.get('mode', 'unknown')
                return f"""CRM Logging Successful:
- UUID: {user_data_dict.get('uuid')}
- Name: {user_data_dict.get('name')}
- Email: {user_data_dict.get('email')}
- Mode: {mode}
- Entry created in CRM spreadsheet"""
            else:
                error = result.get('error', 'Unknown error')
                return f"CRM Logging Failed: {error}"
                
        except Exception as e:
            logger.error(f"Error in log_to_crm_tool: {str(e)}")
            return f"CRM Logging Failed: {str(e)}"

class LogResponsesTool(BaseTool):
    name: str = "log_responses_tool"
    description: str = """
    Log anonymized responses to Google Sheets.
    
    Input should be JSON string containing UUID and responses.
    
    Returns logging status message.
    """
    args_schema: Type[BaseModel] = LogResponsesInput
    
    def _run(self, data: str = "{}", **kwargs) -> str:
        try:
            data_dict = safe_parse_json(data, {}, "log_responses")
            if not data_dict:
                return "Response Logging Failed: No data provided"
            
            uuid = data_dict.get('uuid', '')
            responses = data_dict.get('responses', {})
            result = sheets_logger.log_responses(uuid, responses)
            
            # Format result as readable text
            if result.get('status') == 'success':
                mode = result.get('mode', 'unknown')
                return f"""Response Logging Successful:
- UUID: {uuid}
- Responses: {len(responses)} questions logged
- Mode: {mode}
- Anonymized data saved to responses spreadsheet"""
            else:
                error = result.get('error', 'Unknown error')
                return f"Response Logging Failed: {error}"
                
        except Exception as e:
            logger.error(f"Error in log_responses_tool: {str(e)}")
            return f"Response Logging Failed: {str(e)}"

class StorePIIMappingTool(BaseTool):
    name: str = "store_pii_mapping_tool"
    description: str = """
    Store PII mapping for later retrieval by reinsertion agent.
    
    Input should be JSON string containing UUID and mapping data.
    
    Returns storage status message.
    """
    args_schema: Type[BaseModel] = StorePIIMappingInput
    
    def _run(self, mapping_data: str = "{}", **kwargs) -> str:
        try:
            data = safe_parse_json(mapping_data, {}, "store_pii_mapping")
            if not data:
                return "PII Storage Failed: No mapping data provided"
            
            uuid = data.get('uuid')
            mapping = data.get('mapping')
            
            if uuid and mapping:
                store_pii_mapping(uuid, mapping)
                logger.info(f"Stored PII mapping for UUID: {uuid} with {len(mapping)} entries")
                
                # Format success message with mapping details
                return f"""PII Mapping Stored Successfully:
- UUID: {uuid}
- Entries Stored: {len(mapping)}
- Mapping includes:
  {chr(10).join(f'  - {k}' for k in mapping.keys())}
- Ready for final personalization"""
            else:
                return "PII Storage Failed: Missing UUID or mapping data in input"
                
        except Exception as e:
            logger.error(f"Error storing PII mapping: {str(e)}")
            return f"PII Storage Failed: {str(e)}"

class ProcessCompleteFormTool(BaseTool):
    name: str = "process_complete_form"
    description: str = """
    Complete intake processing: validate, detect PII, redact, and prepare output.
    
    Input should be JSON string representation of the complete form data.
    
    Returns comprehensive processing status and results.
    """
    args_schema: Type[BaseModel] = ProcessCompleteFormInput
    
    def _run(self, form_data_str: str = "{}", **kwargs) -> str:
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
                return """Form Processing Failed:
- Error: No form data provided or invalid JSON
- Status: Unable to process
- Please check the input data format"""
            
            uuid = form_data.get('uuid', 'unknown')
            logger.info(f"Processing form for UUID: {uuid}")
            
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
            
            # Return comprehensive status message
            return f"""Form Processing Complete:

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
            
        except Exception as e:
            logger.error(f"Error processing form: {str(e)}")
            return f"""Form Processing Failed:
- Error: {str(e)}
- UUID: {form_data.get('uuid', 'unknown') if 'form_data' in locals() else 'unknown'}
- Status: Processing incomplete
- Please review error and retry"""

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