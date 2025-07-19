"""
LLM utility functions for the Exit Ready Snapshot workflow.
Provides centralized functions for JSON parsing, word counting, and LLM management.
Fixes the core issues with JSON response formatting across all nodes.
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, SystemMessage, HumanMessage
import time

logger = logging.getLogger(__name__)


def get_llm_with_fallback(
    model: str = "gpt-4.1-mini",
    temperature: float = 0.1,
    max_tokens: int = 4000,
    **kwargs
) -> ChatOpenAI:
    """
    Create an LLM instance with proper model names and JSON response format support.
    
    Args:
        model: Model name (will be corrected if using old names)
        temperature: Temperature for sampling
        max_tokens: Maximum tokens in response
        **kwargs: Additional parameters for ChatOpenAI
        
    Returns:
        Configured ChatOpenAI instance
    """
    # Model name mapping (fix incorrect references)
    model_mapping = {
        "gpt-4o-mini": "gpt-4.1-mini",
        "gpt-4o": "gpt-4.1",
        "gpt-4.5": "gpt-4.1",
        "gpt-4-turbo": "gpt-4.1",
        "gpt-3.5-turbo": "gpt-4.1-nano"
    }
    
    # Correct the model name if needed
    corrected_model = model_mapping.get(model, model)
    if corrected_model != model:
        logger.info(f"Corrected model name from {model} to {corrected_model}")
    
    # Create LLM WITHOUT response format - let individual calls decide
    llm_kwargs = {
        "model": corrected_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        **kwargs
    }
    
    # REMOVED: automatic JSON response format
    # This was causing issues for non-JSON requests
    
    try:
        llm = ChatOpenAI(**llm_kwargs)
        logger.debug(f"Created LLM: {corrected_model} (temp={temperature})")
        return llm
    except Exception as e:
        logger.error(f"Failed to create LLM with model {corrected_model}: {e}")
        # Fallback to a known good model
        logger.info("Falling back to gpt-4.1-mini")
        return ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=temperature,
            max_tokens=max_tokens
        )


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extract JSON from text that might have other content around it.
    
    Args:
        text: Text that might contain JSON
        
    Returns:
        Extracted JSON string or None
    """
    # Try to find JSON-like content
    # Look for content between { and } or [ and ]
    json_patterns = [
        r'\{[^{}]*\{[^{}]*\}[^{}]*\}',  # Nested objects
        r'\{[^{}]+\}',  # Simple objects
        r'\[[^\[\]]*\[[^\[\]]*\][^\[\]]*\]',  # Nested arrays
        r'\[[^\[\]]+\]'  # Simple arrays
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                # Validate it's actual JSON
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
    
    # Try to find content after common prefixes
    prefixes = [
        "```json",
        "Here is the JSON:",
        "JSON output:",
        "Response:"
    ]
    
    for prefix in prefixes:
        if prefix in text:
            start = text.find(prefix) + len(prefix)
            # Find the end of JSON (could be ```, end of text, or double newline)
            end_markers = ["```", "\n\n", "\n---"]
            end = len(text)
            for marker in end_markers:
                marker_pos = text.find(marker, start)
                if marker_pos != -1:
                    end = min(end, marker_pos)
            
            potential_json = text[start:end].strip()
            try:
                json.loads(potential_json)
                return potential_json
            except json.JSONDecodeError:
                continue
    
    return None


def safe_json_parse(
    input_str: Union[str, Dict, Any],
    default_value: Optional[Dict] = None,
    source_name: str = "Unknown",
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Safely parse JSON with retry logic and detailed error logging.
    
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


def ensure_json_response(
    llm: ChatOpenAI,
    messages: List[BaseMessage],
    function_name: str = "Unknown",
    retry_count: int = 3,
    require_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Wrapper for LLM calls that ensures JSON output with retry logic.
    FIXED: Only use JSON response format when actually requesting JSON.
    
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
            
            # Create a new LLM instance with JSON response format for this specific call
            json_llm = ChatOpenAI(
                model=llm.model_name,
                temperature=llm.temperature,
                max_tokens=llm.max_tokens,
                model_kwargs={"response_format": {"type": "json_object"}}
            )
            
            # Make the LLM call
            response = json_llm.invoke(messages)
            
            # Extract content
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            logger.debug(f"{function_name}: Raw response length: {len(content)}")
            
            # Parse the response
            result = safe_json_parse(content, source_name=function_name)
            
            # Validate required keys if specified
            if require_keys:
                missing_keys = [key for key in require_keys if key not in result]
                if missing_keys:
                    logger.warning(f"{function_name}: Response missing required keys: {missing_keys}")
                    if attempt < retry_count - 1:
                        # Add a message to request the missing keys
                        messages.append(HumanMessage(
                            content=f"Your response is missing these required keys: {missing_keys}. "
                                   f"Please provide a complete JSON response with all required fields."
                        ))
                        continue
                    else:
                        # On last attempt, add default values for missing keys
                        for key in missing_keys:
                            result[key] = None
            
            logger.info(f"{function_name}: Successfully parsed JSON response on attempt {attempt + 1}")
            return result
            
        except Exception as e:
            last_error = e
            logger.error(f"{function_name}: Attempt {attempt + 1} failed: {e}")
            
            if attempt < retry_count - 1:
                # Add a message to help the model understand what went wrong
                error_msg = (
                    f"Your previous response could not be parsed as JSON. Error: {str(e)}. "
                    f"Please respond with valid JSON only, no markdown formatting or extra text."
                )
                messages.append(HumanMessage(content=error_msg))
                # Small delay before retry
                time.sleep(1)
    
    # All retries failed
    logger.error(f"{function_name}: All {retry_count} attempts failed. Last error: {last_error}")
    return {} if require_keys is None else {key: None for key in require_keys}


def count_words(text: str) -> int:
    """
    Accurately count words in text.
    
    Args:
        text: Text to count words in
        
    Returns:
        Number of words
    """
    # Remove extra whitespace and split
    words = text.strip().split()
    # Filter out empty strings
    words = [w for w in words if w]
    return len(words)


def validate_word_count(
    text: str,
    target_words: int,
    tolerance: int = 10,
    llm: Optional[ChatOpenAI] = None,
    prompt: Optional[str] = None,
    max_retries: int = 3
) -> str:
    """
    Validate word count and retry with LLM if outside tolerance.
    
    Args:
        text: Text to validate
        target_words: Target word count
        tolerance: Acceptable deviation from target
        llm: LLM instance for regeneration (optional)
        prompt: Original prompt for regeneration (optional)
        max_retries: Maximum regeneration attempts
        
    Returns:
        Text that meets word count requirements (or best attempt)
    """
    word_count = count_words(text)
    min_words = target_words - tolerance
    max_words = target_words + tolerance
    
    # If within tolerance, return as is
    if min_words <= word_count <= max_words:
        logger.debug(f"Word count {word_count} is within target {target_words} ± {tolerance}")
        return text
    
    logger.warning(f"Word count {word_count} outside target range {min_words}-{max_words}")
    
    # If no LLM provided, return original text
    if not llm or not prompt:
        logger.warning("No LLM provided for word count correction, returning original text")
        return text
    
    # Try to regenerate with specific word count instruction
    best_text = text
    best_diff = abs(word_count - target_words)
    
    for attempt in range(max_retries):
        try:
            # Modify prompt to emphasize word count
            if word_count > max_words:
                instruction = f"\n\nYour response was {word_count} words, which is too long. Please shorten it to EXACTLY {target_words} words."
            else:
                instruction = f"\n\nYour response was {word_count} words, which is too short. Please expand it to EXACTLY {target_words} words."
            
            messages = [
                SystemMessage(content=f"You must respond with EXACTLY {target_words} words. Count carefully."),
                HumanMessage(content=prompt + instruction)
            ]
            
            response = llm.invoke(messages)
            new_text = response.content if hasattr(response, 'content') else str(response)
            new_count = count_words(new_text)
            
            logger.info(f"Regeneration attempt {attempt + 1}: {new_count} words")
            
            # Check if this is better
            new_diff = abs(new_count - target_words)
            if new_diff < best_diff:
                best_text = new_text
                best_diff = new_diff
            
            # If within tolerance, we're done
            if min_words <= new_count <= max_words:
                logger.info(f"Successfully adjusted word count to {new_count}")
                return new_text
                
        except Exception as e:
            logger.error(f"Error during word count adjustment attempt {attempt + 1}: {e}")
    
    logger.warning(f"Could not achieve exact word count after {max_retries} attempts. Best attempt: {count_words(best_text)} words")
    return best_text


def format_json_prompt(prompt: str, example_structure: Dict[str, Any]) -> str:
    """
    Format a prompt to ensure JSON response with example structure.
    
    Args:
        prompt: Original prompt
        example_structure: Example of expected JSON structure
        
    Returns:
        Formatted prompt that emphasizes JSON response
    """
    json_example = json.dumps(example_structure, indent=2)
    
    formatted = f"""{prompt}

IMPORTANT: Respond with valid JSON only. No markdown, no extra text.

Expected JSON structure:
{json_example}

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