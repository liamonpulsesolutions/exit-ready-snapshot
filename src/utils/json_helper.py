import json
import logging

logger = logging.getLogger(__name__)

def safe_parse_json(input_str, default_value=None, tool_name="Unknown"):
    """Safely parse JSON with detailed error logging"""
    if not input_str or input_str.strip() == "":
        logger.warning(f"{tool_name}: Received empty input")
        return default_value or {}
    
    try:
        if isinstance(input_str, dict):
            return input_str
        
        # Log first 100 chars of input for debugging
        logger.info(f"{tool_name}: Parsing input: {input_str[:100]}...")
        
        return json.loads(input_str)
    except json.JSONDecodeError as e:
        logger.error(f"{tool_name}: JSON parse error: {e}")
        logger.error(f"{tool_name}: Invalid input was: '{input_str}'")
        return default_value or {}