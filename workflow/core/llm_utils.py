"""
LLM utility functions for the Exit Ready workflow.
Provides standardized LLM access with fallback handling.
FIXED: JSON response handling using bind() method and added gpt-4.1 full model.
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, SystemMessage, HumanMessage

# Load environment if not already loaded
from dotenv import load_dotenv
if not os.getenv('OPENAI_API_KEY'):
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

logger = logging.getLogger(__name__)

# Model configurations with GPT-4.1 (April 2025)
MODEL_CONFIGS = {
    "gpt-4.1": {
        "model": "gpt-4.1",
        "max_tokens": 8000,
        "description": "Full GPT-4.1 - best reasoning and comprehension"
    },
    "gpt-4.1-mini": {
        "model": "gpt-4.1-mini",
        "max_tokens": 4000,
        "description": "Enhanced reasoning and coding, cost-effective"
    },
    "gpt-4.1-nano": {
        "model": "gpt-4.1-nano",
        "max_tokens": 2000,
        "description": "Fast, efficient for simple tasks"
    }
}

# Default model for fallback
DEFAULT_MODEL = "gpt-4.1-mini"


def get_llm_with_fallback(
    model_name: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    **kwargs
) -> ChatOpenAI:
    """
    Get an LLM instance with fallback to default model if specified model fails.
    FIXED: Store model name as custom attribute for reliable extraction.
    
    Args:
        model_name: Name of the model to use
        temperature: Temperature for sampling
        **kwargs: Additional arguments for ChatOpenAI
        
    Returns:
        ChatOpenAI instance
    """
    # Validate model name
    if model_name not in MODEL_CONFIGS:
        logger.warning(f"Unknown model '{model_name}', using default '{DEFAULT_MODEL}'")
        model_name = DEFAULT_MODEL
    
    config = MODEL_CONFIGS[model_name]
    
    try:
        # Create LLM instance
        llm = ChatOpenAI(
            model=config["model"],
            temperature=temperature,
            max_tokens=config.get("max_tokens", 4000),
            **kwargs
        )
        
        # FIXED: Store the model name as a custom attribute for reliable access
        llm._custom_model_name = config["model"]
        
        logger.debug(f"Created LLM: {model_name} (temp={temperature})")
        return llm
        
    except Exception as e:
        logger.error(f"Failed to create LLM '{model_name}': {e}")
        if model_name != DEFAULT_MODEL:
            logger.info(f"Falling back to default model '{DEFAULT_MODEL}'")
            return get_llm_with_fallback(DEFAULT_MODEL, temperature, **kwargs)
        else:
            raise


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extract JSON object from text that may contain non-JSON content.
    
    Args:
        text: Text potentially containing JSON
        
    Returns:
        Extracted JSON string or None
    """
    if not text:
        return None
    
    # Try to find JSON-like content
    patterns = [
        r'\{[^{}]*\}',  # Simple object
        r'\{(?:[^{}]|\{[^{}]*\})*\}',  # Nested object (one level)
        r'\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}'  # Nested object (two levels)
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in reversed(matches):  # Try from the end first
            try:
                # Validate it's proper JSON
                json.loads(match)
                return match
            except:
                continue
    
    return None


def parse_json_response(
    input_str: Union[str, Dict[str, Any]],
    default_value: Optional[Dict[str, Any]] = None,
    source_name: str = "Unknown",
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Safely parse JSON response with multiple fallback strategies.
    
    Args:
        input_str: String to parse or dict to return
        default_value: Default value if parsing fails
        source_name: Name of the calling function for logging
        max_retries: Maximum number of parse attempts
        
    Returns:
        Parsed dict or default_value
    """
    if default_value is None:
        default_value = {}
    
    # If already a dict, return it
    if isinstance(input_str, dict):
        return input_str
    
    # Handle None or empty input
    if not input_str or (isinstance(input_str, str) and input_str.strip() == ""):
        logger.warning(f"{source_name}: Received empty input")
        return default_value
    
    # Try to parse with retries
    for attempt in range(max_retries):
        try:
            if isinstance(input_str, str):
                # First attempt: direct parse
                if attempt == 0:
                    return json.loads(input_str)
                
                # Second attempt: extract JSON from mixed content
                elif attempt == 1:
                    extracted = extract_json_from_text(input_str)
                    if extracted:
                        return json.loads(extracted)
                    else:
                        logger.warning(f"{source_name}: Could not extract JSON from text")
                
                # Third attempt: try to fix common issues
                elif attempt == 2:
                    # Remove common prefixes/suffixes
                    cleaned = input_str.strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    if cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    cleaned = cleaned.strip()
                    
                    # Try to fix single quotes
                    cleaned = cleaned.replace("'", '"')
                    
                    return json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            logger.warning(f"{source_name}: JSON parse attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error(f"{source_name}: All parse attempts failed. Input preview: {str(input_str)[:200]}...")
        except Exception as e:
            logger.error(f"{source_name}: Unexpected error during parsing: {e}")
            break
    
    return default_value


# Alias for backward compatibility
safe_json_parse = parse_json_response


def ensure_json_response(
    llm: ChatOpenAI,
    messages: List[BaseMessage],
    function_name: str = "Unknown",
    retry_count: int = 3,
    require_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Wrapper for LLM calls that ensures JSON output with retry logic.
    FIXED: Use bind() method for JSON response format instead of creating new LLM.
    
    Args:
        llm: The LLM instance to use
        messages: List of messages to send
        function_name: Name of calling function for logging
        retry_count: Number of retries if JSON parsing fails
        require_keys: Optional list of keys that must be in the response
        
    Returns:
        Parsed JSON response as dict
    """
    last_error = None
    
    # Ensure the system message mentions JSON output
    if messages and isinstance(messages[0], SystemMessage):
        original_content = messages[0].content
        if "JSON" not in original_content.upper():
            messages[0].content = original_content + "\n\nIMPORTANT: You must respond with valid JSON only. No additional text or formatting."
    
    for attempt in range(retry_count):
        try:
            logger.debug(f"{function_name}: LLM call attempt {attempt + 1}/{retry_count}")
            
            # Get model name for logging
            model_name = getattr(llm, '_custom_model_name', 'unknown')
            logger.debug(f"{function_name}: Using model: {model_name}")
            
            # FIXED: Use bind() to add JSON response format
            json_llm = llm.bind(response_format={"type": "json_object"})
            
            # Make the call
            start_time = datetime.now()
            response = json_llm.invoke(messages)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            logger.debug(f"{function_name}: LLM call took {elapsed:.2f}s")
            
            # Check if response is too fast (likely initialization failure)
            if elapsed < 0.1:
                logger.warning(f"{function_name}: LLM call completed in {elapsed:.3f}s - likely initialization failure")
                # Try using the original LLM without JSON binding
                response = llm.invoke(messages)
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.debug(f"{function_name}: Retry without JSON binding took {elapsed:.2f}s")
            
            # Extract content
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            logger.debug(f"{function_name}: Raw response length: {len(content)}")
            
            # Parse JSON
            result = parse_json_response(
                content,
                source_name=function_name,
                default_value={}
            )
            
            # Validate required keys if specified
            if require_keys:
                missing_keys = [k for k in require_keys if k not in result]
                if missing_keys:
                    logger.warning(f"{function_name}: Response missing required keys: {missing_keys}")
                    if attempt < retry_count - 1:
                        # Add missing keys to prompt for retry
                        messages[-1].content += f"\n\nYour response is missing these required keys: {missing_keys}"
                        continue
            
            # Success!
            logger.info(f"{function_name}: Successfully parsed JSON response on attempt {attempt + 1}")
            return result
            
        except Exception as e:
            last_error = e
            logger.error(f"{function_name}: Attempt {attempt + 1} failed: {e}")
            
            # On failure, try without JSON binding as fallback
            if attempt == retry_count - 1:
                try:
                    logger.info(f"{function_name}: Final attempt without JSON binding")
                    response = llm.invoke(messages)
                    
                    if hasattr(response, 'content'):
                        content = response.content
                    else:
                        content = str(response)
                    
                    result = parse_json_response(
                        content,
                        source_name=function_name,
                        default_value={}
                    )
                    
                    if result:
                        logger.info(f"{function_name}: Successfully parsed response without JSON binding")
                        return result
                        
                except Exception as fallback_error:
                    logger.error(f"{function_name}: Fallback attempt failed: {fallback_error}")
    
    # All attempts failed
    logger.error(f"{function_name}: All {retry_count} attempts failed. Last error: {last_error}")
    
    # Return a default structure based on require_keys if available
    if require_keys:
        default_response = {key: None for key in require_keys}
        logger.info(f"{function_name}: Returning default response with required keys")
        return default_response
    
    return {}


def format_json_prompt(
    prompt: str,
    json_example: Dict[str, Any]
) -> str:
    """
    Format a prompt to include a JSON example.
    
    Args:
        prompt: The base prompt
        json_example: Example of expected JSON structure
        
    Returns:
        Formatted prompt with JSON example
    """
    formatted = f"""{prompt}

You must respond with valid JSON matching this structure.
No markdown, no extra text.

Expected JSON structure:
{json.dumps(json_example, indent=2)}

Your response must be parseable by json.loads() without any preprocessing."""
    
    return formatted


def validate_llm_response(
    response: Dict[str, Any],
    required_fields: List[str],
    field_types: Optional[Dict[str, type]] = None
) -> Tuple[bool, List[str]]:
    """
    Validate that an LLM response contains required fields and correct types.
    
    Args:
        response: The response dict to validate
        required_fields: List of required field names
        field_types: Optional dict mapping field names to expected types
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    for field in required_fields:
        if field not in response:
            errors.append(f"Missing required field: {field}")
    
    # Check field types if specified
    if field_types:
        for field, expected_type in field_types.items():
            if field in response:
                if not isinstance(response[field], expected_type):
                    actual_type = type(response[field]).__name__
                    expected_name = expected_type.__name__
                    errors.append(f"Field '{field}' has wrong type: expected {expected_name}, got {actual_type}")
    
    return len(errors) == 0, errors


# Convenience function for the most common use case
def call_llm_with_json(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    required_keys: Optional[List[str]] = None,
    example_response: Optional[Dict[str, Any]] = None,
    function_name: str = "call_llm_with_json"
) -> Dict[str, Any]:
    """
    Convenience function to make an LLM call that returns JSON.
    
    Args:
        model: Model name (e.g., "gpt-4.1-mini")
        system_prompt: System message content
        user_prompt: User message content
        temperature: Sampling temperature
        required_keys: Keys that must be in the response
        example_response: Example response structure
        function_name: Name for logging
        
    Returns:
        Parsed JSON response
    """
    # Create LLM
    llm = get_llm_with_fallback(model, temperature=temperature)
    
    # Format prompts
    if example_response:
        user_prompt = format_json_prompt(user_prompt, example_response)
    
    # Create messages
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Make call with JSON enforcement
    return ensure_json_response(
        llm=llm,
        messages=messages,
        function_name=function_name,
        require_keys=required_keys
    )


# Word count validation helper
def validate_word_count(
    text: str,
    target_words: int,
    tolerance: int = 10,
    llm: Optional[ChatOpenAI] = None,
    prompt: Optional[str] = None
) -> str:
    """
    Validate and optionally adjust text to meet word count requirements.
    
    Args:
        text: Text to validate
        target_words: Target word count
        tolerance: Acceptable deviation from target
        llm: Optional LLM to use for adjustment
        prompt: Original prompt if adjustment needed
        
    Returns:
        Validated/adjusted text
    """
    word_count = len(text.split())
    
    # Check if within tolerance
    if abs(word_count - target_words) <= tolerance:
        return text
    
    # Log the issue
    logger.warning(f"Text has {word_count} words, target is {target_words}")
    
    # If no LLM provided or no prompt, return as-is
    if not llm or not prompt:
        return text
    
    # Try to adjust
    try:
        adjustment_prompt = f"""The following text has {word_count} words but needs exactly {target_words} words (±{tolerance}).
Please adjust it to meet the word count while preserving all key information.

Current text:
{text}

Original instructions:
{prompt}

Provide only the adjusted text, no commentary."""
        
        messages = [
            SystemMessage(content="You are an expert editor who can precisely adjust text length."),
            HumanMessage(content=adjustment_prompt)
        ]
        
        response = llm.invoke(messages)
        adjusted_text = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Verify the adjustment
        new_count = len(adjusted_text.split())
        if abs(new_count - target_words) <= tolerance:
            logger.info(f"Successfully adjusted text from {word_count} to {new_count} words")
            return adjusted_text
        else:
            logger.warning(f"Adjustment failed: {new_count} words. Using original.")
            return text
            
    except Exception as e:
        logger.error(f"Failed to adjust word count: {e}")
        return text