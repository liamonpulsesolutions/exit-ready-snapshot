"""
LLM utility functions for the Exit Ready workflow.
Provides standardized LLM access with fallback handling.
FIXED: JSON response handling using bind() method and added gpt-4.1 full model.
FIXED: Prevent duplicate 'model' keyword argument error.
ENHANCED: Word count validation now accepts partial improvements.
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
   FIXED: Prevent duplicate 'model' keyword argument by removing it from kwargs.
   
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
   
   # FIXED: Remove 'model' and 'max_tokens' from kwargs if present to prevent duplicate argument error
   kwargs_copy = kwargs.copy()
   kwargs_copy.pop('model', None)
   
   # Handle max_tokens separately to use config default
   max_tokens = kwargs_copy.pop('max_tokens', config.get("max_tokens", 4000))
   
   try:
       # Create LLM instance
       llm = ChatOpenAI(
           model=config["model"],
           temperature=temperature,
           max_tokens=max_tokens,
           **kwargs_copy
       )
       
       # Store the model name as a custom attribute for reliable access
       llm._custom_model_name = config["model"]
       
       logger.debug(f"Created LLM: {model_name} (temp={temperature})")
       return llm
       
   except Exception as e:
       logger.error(f"Failed to create LLM '{model_name}': {e}")
       if model_name != DEFAULT_MODEL:
           logger.info(f"Falling back to default model '{DEFAULT_MODEL}'")
           # Pass original kwargs to avoid accumulating modifications
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
       input_str: Input string or dict to parse
       default_value: Default value if parsing fails
       source_name: Name for logging purposes
       max_retries: Maximum number of parsing attempts
       
   Returns:
       Parsed dictionary
   """
   if default_value is None:
       default_value = {}
   
   # If already a dict, return it
   if isinstance(input_str, dict):
       return input_str
   
   # If not a string, convert and try
   if not isinstance(input_str, str):
       input_str = str(input_str)
   
   # Try direct JSON parsing
   try:
       return json.loads(input_str)
   except json.JSONDecodeError:
       pass
   
   # Try extracting JSON from text
   json_str = extract_json_from_text(input_str)
   if json_str:
       try:
           return json.loads(json_str)
       except:
           pass
   
   # Log failure and return default
   logger.warning(f"Failed to parse JSON from {source_name}: {input_str[:200]}...")
   return default_value


# Alias for backward compatibility - research node uses this name
safe_json_parse = parse_json_response


def ensure_json_response(
   llm: ChatOpenAI,
   messages: List[BaseMessage],
   function_name: str,
   retry_count: int = 2,
   require_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
   """
   Ensure LLM response is valid JSON with retries.
   FIXED: Use bind() method for JSON formatting.
   
   Args:
       llm: The LLM instance
       messages: Messages to send
       function_name: Name for logging
       retry_count: Number of retries
       require_keys: Keys that must be in response
       
   Returns:
       Parsed JSON response
   """
   last_error = None
   
   # Get model name for logging
   model_name = getattr(llm, '_custom_model_name', 'unknown')
   
   for attempt in range(retry_count + 1):
       try:
           # FIXED: Use bind() to enforce JSON response format
           llm_with_json = llm.bind(response_format={"type": "json_object"})
           
           # Make the call
           start_time = datetime.now()
           response = llm_with_json.invoke(messages)
           elapsed = (datetime.now() - start_time).total_seconds()
           
           # Extract content
           content = response.content if hasattr(response, 'content') else str(response)
           
           # Parse JSON
           try:
               result = json.loads(content)
           except json.JSONDecodeError as e:
               # Try to extract JSON from the content
               json_str = extract_json_from_text(content)
               if json_str:
                   result = json.loads(json_str)
               else:
                   raise e
           
           # Validate required keys
           if require_keys:
               missing_keys = [k for k in require_keys if k not in result]
               if missing_keys:
                   raise ValueError(f"Missing required keys: {missing_keys}")
           
           logger.info(f"{function_name}: Successfully parsed JSON response on attempt {attempt + 1}")
           return result
           
       except Exception as e:
           last_error = e
           logger.warning(f"{function_name} attempt {attempt + 1} failed: {e}")
           
           if attempt < retry_count:
               # Add more explicit JSON instruction for retry
               if attempt == 0:
                   messages.append(HumanMessage(
                       content="Please ensure your response is ONLY valid JSON with no additional text."
                   ))
               else:
                   messages.append(HumanMessage(
                       content=f"Your previous response was not valid JSON. Error: {str(e)}. "
                       "Please respond with ONLY a valid JSON object, no other text."
                   ))
   
   # All retries failed
   logger.error(f"{function_name}: All {retry_count + 1} attempts failed. Last error: {last_error}")
   return {"error": f"Failed to get valid JSON after {retry_count + 1} attempts", "last_error": str(last_error)}


def format_json_prompt(prompt: str, example_response: Dict[str, Any]) -> str:
   """
   Format a prompt to include JSON response example.
   
   Args:
       prompt: Original prompt
       example_response: Example of expected JSON structure
       
   Returns:
       Formatted prompt with JSON example
   """
   json_example = json.dumps(example_response, indent=2)
   return f"""{prompt}

Respond with a JSON object in this exact format:
{json_example}

Important: Return ONLY valid JSON, no additional text or explanation."""


def make_llm_json_call(
   model: str,
   system_prompt: str,
   user_prompt: str,
   temperature: float = 0.3,
   required_keys: Optional[List[str]] = None,
   example_response: Optional[Dict[str, Any]] = None,
   function_name: str = "llm_call"
) -> Dict[str, Any]:
   """
   Make a structured LLM call that returns JSON.
   
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


# Word count validation helper - ENHANCED VERSION
def validate_word_count(
   text: str,
   target_words: int,
   tolerance: int = 10,
   llm: Optional[ChatOpenAI] = None,
   prompt: Optional[str] = None
) -> str:
   """
   Validate and optionally adjust text to meet word count requirements.
   ENHANCED: Now accepts partial improvements and within 20% of target.
   
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
   
   # Check if within tolerance - PERFECT
   if abs(word_count - target_words) <= tolerance:
       return text
   
   # Log the issue
   logger.info(f"Text has {word_count} words, target is {target_words} (tolerance: ±{tolerance})")
   
   # If no LLM provided or no prompt, check if within 20% of target
   if not llm or not prompt:
       # ENHANCED: Accept if within 20% of target even without LLM adjustment
       if abs(word_count - target_words) / target_words <= 0.2:
           logger.info(f"Accepting {word_count} words as within 20% of target {target_words}")
           return text
       else:
           logger.warning(f"No LLM available and {word_count} words is >20% from target {target_words}")
           return text
   
   # Try to adjust with LLM
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
       
       # Calculate improvement metrics
       original_distance = abs(word_count - target_words)
       new_distance = abs(new_count - target_words)
       
       # Avoid division by zero
       if original_distance > 0:
           improvement_ratio = (original_distance - new_distance) / original_distance
       else:
           improvement_ratio = 1.0  # Already perfect
       
       # ENHANCED: Multi-tier acceptance criteria
       
       # 1. Perfect - within tolerance
       if abs(new_count - target_words) <= tolerance:
           logger.info(f"Successfully adjusted text from {word_count} to {new_count} words (target: {target_words})")
           return adjusted_text
       
       # 2. Significant improvement - 50%+ closer to target
       elif improvement_ratio >= 0.5:
           logger.info(f"Accepting partial improvement: {word_count} → {new_count} words "
                      f"({improvement_ratio:.0%} closer to target {target_words})")
           return adjusted_text
       
       # 3. Within 20% of target (even without significant improvement)
       elif abs(new_count - target_words) / target_words <= 0.2:
           logger.info(f"Accepting {new_count} words as within 20% of target {target_words}")
           return adjusted_text
       
       # 4. Check if original was actually better
       elif original_distance < new_distance:
           logger.warning(f"Adjustment made it worse: {word_count} → {new_count} words. Keeping original.")
           return text
       
       # 5. Otherwise, use the adjusted version if it's any improvement
       else:
           logger.info(f"Minor improvement: {word_count} → {new_count} words. Using adjusted version.")
           return adjusted_text
           
   except Exception as e:
       logger.error(f"Word count adjustment failed: {e}")
       # ENHANCED: Final check - if original is within 20% of target, accept it
       if abs(word_count - target_words) / target_words <= 0.2:
           logger.info(f"Adjustment failed but {word_count} words is within 20% of {target_words}. Accepting original.")
       return text


# Additional helper functions for formatting
def format_llm_prompt_with_structure(
   base_prompt: str,
   structure: Dict[str, Any],
   instructions: Optional[str] = None
) -> str:
   """
   Format a prompt with structured output requirements.
   
   Args:
       base_prompt: The main prompt text
       structure: Dictionary showing expected output structure
       instructions: Additional formatting instructions
       
   Returns:
       Formatted prompt with structure
   """
   formatted = base_prompt
   
   if instructions:
       formatted += f"\n\n{instructions}"
   
   formatted += f"\n\nProvide your response in the following structure:\n"
   formatted += json.dumps(structure, indent=2)
   formatted += "\n\nNo markdown, no extra text. Just the JSON object."
   
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
   
   This is a wrapper around make_llm_json_call for backward compatibility.
   """
   return make_llm_json_call(
       model=model,
       system_prompt=system_prompt,
       user_prompt=user_prompt,
       temperature=temperature,
       required_keys=required_keys,
       example_response=example_response,
       function_name=function_name
   )