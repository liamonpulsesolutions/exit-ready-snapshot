from crewai import Agent
from crewai.tools import tool
from typing import Dict, Any
import logging
from ..tools.google_sheets import GoogleSheetsLogger
from ..tools.pii_detector import PIIDetector

logger = logging.getLogger(__name__)

# Initialize tools globally so they can be decorated
sheets_logger = GoogleSheetsLogger()
pii_detector = PIIDetector()

@tool("validate_form_data")
def validate_form_data(form_data_str: str) -> str:
    """
    Validate that all required form fields are present and properly formatted.
    Input should be a JSON string representation of the form data.
    """
    import json
    
    try:
        # Parse the input string
        if isinstance(form_data_str, dict):
            form_data = form_data_str
        else:
            form_data = json.loads(form_data_str)
    except Exception as e:
        return json.dumps({
            "valid": False,
            "errors": f"Invalid input format: {str(e)}"
        })
    
    required_fields = [
        'uuid', 'name', 'email', 'industry', 'years_in_business',
        'age_range', 'exit_timeline', 'location', 'responses'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in form_data or not form_data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        return json.dumps({
            "valid": False,
            "errors": f"Missing required fields: {', '.join(missing_fields)}"
        })
    
    # Validate responses
    expected_questions = [f"q{i}" for i in range(1, 11)]
    missing_responses = []
    
    responses = form_data.get('responses', {})
    for q in expected_questions:
        if q not in responses or not responses[q]:
            missing_responses.append(q)
    
    if missing_responses:
        return json.dumps({
            "valid": False,
            "errors": f"Missing responses for: {', '.join(missing_responses)}"
        })
    
    return json.dumps({"valid": True, "data": form_data})

@tool("detect_and_redact_pii")
def detect_and_redact_pii_tool(text: str) -> str:
    """Detect and redact PII from text, returning anonymized text and mapping"""
    result = pii_detector.detect_and_redact(text)
    import json
    return json.dumps(result)

@tool("log_to_crm")
def log_to_crm_tool(user_data: str) -> str:
    """Log user data to Google Sheets CRM"""
    import json
    if isinstance(user_data, str):
        user_data = json.loads(user_data)
    result = sheets_logger.log_to_crm(user_data)
    return json.dumps(result)

@tool("log_responses")
def log_responses_tool(data: str) -> str:
    """Log anonymized responses to Google Sheets"""
    import json
    if isinstance(data, str):
        data = json.loads(data)
    uuid = data.get('uuid', '')
    responses = data.get('responses', {})
    result = sheets_logger.log_responses(uuid, responses)
    return json.dumps(result)

def create_intake_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the intake agent for processing form submissions"""
    
    # Get agent configuration from prompts
    config = prompts.get('intake_agent', {})
    
    # Create tools list
    tools = [
        validate_form_data,
        detect_and_redact_pii_tool,
        log_to_crm_tool,
        log_responses_tool
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