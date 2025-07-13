"""
Enhanced input validation utilities for CrewAI tools
"""
import json
import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

def validate_and_extract_tool_input(
    input_data: Any, 
    expected_keys: list = None, 
    tool_name: str = "unknown",
    default_return: Dict = None
) -> Dict[str, Any]:
    """
    Robustly validate and extract tool input from various CrewAI formats
    
    Args:
        input_data: Raw input from CrewAI (could be dict, string, or complex nested structure)
        expected_keys: List of keys expected in the final dict
        tool_name: Name of the tool for logging
        default_return: Default dict to return if extraction fails
        
    Returns:
        Validated dictionary or default_return
    """
    if default_return is None:
        default_return = {}
        
    logger.debug(f"{tool_name}: Processing input type {type(input_data)}")
    
    # Handle None or empty input
    if input_data is None or input_data == "":
        logger.warning(f"{tool_name}: Received None or empty input")
        return default_return
    
    # Handle string input that might be JSON
    if isinstance(input_data, str):
        # Handle empty JSON
        if input_data.strip() in ["{}", "[]", ""]:
            logger.warning(f"{tool_name}: Received empty JSON string")
            return default_return
            
        # Try to parse as JSON
        try:
            parsed = json.loads(input_data)
            return validate_dict_structure(parsed, expected_keys, tool_name, default_return)
        except json.JSONDecodeError:
            logger.warning(f"{tool_name}: String input is not valid JSON, treating as raw text")
            return {"raw_input": input_data, **default_return}
    
    # Handle dict input (most common with new CrewAI)
    elif isinstance(input_data, dict):
        return validate_dict_structure(input_data, expected_keys, tool_name, default_return)
    
    # Handle list input (unexpected but possible)
    elif isinstance(input_data, list):
        if len(input_data) > 0:
            logger.warning(f"{tool_name}: Received list input, using first element")
            return validate_and_extract_tool_input(input_data[0], expected_keys, tool_name, default_return)
        else:
            logger.warning(f"{tool_name}: Received empty list")
            return default_return
    
    # Handle other types
    else:
        logger.warning(f"{tool_name}: Unexpected input type {type(input_data)}, converting to string")
        return {"raw_input": str(input_data), **default_return}

def validate_dict_structure(
    data: Dict[str, Any], 
    expected_keys: Optional[list] = None, 
    tool_name: str = "unknown",
    default_return: Dict = None
) -> Dict[str, Any]:
    """
    Validate dictionary structure and extract expected keys
    """
    if default_return is None:
        default_return = {}
        
    if not isinstance(data, dict):
        logger.error(f"{tool_name}: Expected dict but got {type(data)}")
        return default_return
    
    # Handle CrewAI security context wrapper
    if "security_context" in data and len(data) == 1:
        logger.info(f"{tool_name}: Detected security context wrapper, extracting content")
        # This might happen if CrewAI changes format again
        return default_return
    
    # Handle nested data structures that might contain the actual data
    if expected_keys:
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            # Try to find the data in nested structures
            for key, value in data.items():
                if isinstance(value, dict) and any(expected_key in value for expected_key in expected_keys):
                    logger.info(f"{tool_name}: Found expected keys in nested structure '{key}'")
                    return validate_dict_structure(value, expected_keys, tool_name, default_return)
            
            logger.warning(f"{tool_name}: Missing expected keys: {missing_keys}")
    
    return data

def extract_uuid_from_any_input(input_data: Any, default_uuid: str = "unknown") -> str:
    """
    Extract UUID from any input format
    """
    if isinstance(input_data, str):
        # Direct UUID string
        if len(input_data) < 100 and "-" in input_data:
            return input_data
        # JSON string containing UUID
        try:
            data = json.loads(input_data)
            return data.get("uuid", default_uuid)
        except:
            return default_uuid
    elif isinstance(input_data, dict):
        return input_data.get("uuid", default_uuid)
    else:
        return default_uuid

def safe_json_loads(input_str: str, default: Any = None, tool_name: str = "unknown") -> Any:
    """
    Safely parse JSON with detailed logging
    """
    if not input_str or input_str.strip() == "":
        logger.debug(f"{tool_name}: Empty input for JSON parsing")
        return default
    
    try:
        return json.loads(input_str)
    except json.JSONDecodeError as e:
        logger.error(f"{tool_name}: JSON decode error: {e}")
        logger.error(f"{tool_name}: Problematic input: {input_str[:200]}...")
        return default
    except Exception as e:
        logger.error(f"{tool_name}: Unexpected error parsing JSON: {e}")
        return default