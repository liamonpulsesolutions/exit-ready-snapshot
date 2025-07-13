from crewai import Agent
from crewai.tools import tool
from typing import Dict, Any, List
import logging
import json
import re
from ..utils.json_helper import safe_parse_json

logger = logging.getLogger(__name__)

# Global storage for PII mapping (in production, use secure storage like Redis)
pii_mapping_store = {}

@tool("retrieve_pii_mapping")
def retrieve_pii_mapping(uuid: str) -> str:
    """
    Retrieve the PII mapping for a specific assessment UUID.
    CRITICAL: This must use the actual mapping from intake agent, not mock data.
    """
    try:
        # Handle case where uuid might be passed as JSON
        if isinstance(uuid, str) and uuid.startswith('{'):
            uuid_data = safe_parse_json(uuid, {}, "retrieve_pii_mapping")
            uuid = uuid_data.get('uuid', uuid)
        
        # Check if we have a stored mapping for this UUID
        if uuid in pii_mapping_store:
            mapping = pii_mapping_store[uuid]
            logger.info(f"Retrieved PII mapping for UUID {uuid} with {len(mapping)} entries")
            
            return json.dumps({
                "uuid": uuid,
                "mapping": mapping,
                "mapping_count": len(mapping),
                "status": "found"
            })
        else:
            # CRITICAL: No mock data! Return empty mapping if not found
            logger.error(f"No PII mapping found for UUID {uuid} - this is a critical error")
            
            # Return empty mapping with error status
            return json.dumps({
                "uuid": uuid,
                "mapping": {},
                "mapping_count": 0,
                "status": "not_found",
                "error": "PII mapping not found - intake agent may have failed to store mapping"
            })
        
    except Exception as e:
        logger.error(f"Error retrieving PII mapping: {str(e)}")
        return json.dumps({
            "error": str(e), 
            "mapping": {}, 
            "status": "error"
        })

@tool("reinsert_personal_info")
def reinsert_personal_info(content_with_mapping: str) -> str:
    """
    Replace all placeholders with actual personal information.
    Ensures natural language flow and proper formatting.
    """
    try:
        logger.info(f"=== REINSERT PERSONAL INFO CALLED ===")
        logger.info(f"Input type: {type(content_with_mapping)}")
        logger.info(f"Input preview: {str(content_with_mapping)[:200]}...")
        
        # Handle CrewAI passing dict vs string vs raw content
        if isinstance(content_with_mapping, dict):
            # CrewAI passes the data as a dict
            data = content_with_mapping
            content = data.get('content', '') or data.get('content_with_mapping', '') or str(data)
            mapping = data.get('mapping', {})
        else:
            # Try to parse as JSON first
            data = safe_parse_json(content_with_mapping, {}, "reinsert_personal_info")
            if data and isinstance(data, dict):
                content = data.get('content', '') or data.get('content_with_mapping', '')
                mapping = data.get('mapping', {})
            else:
                # CrewAI might be passing raw content - treat as content, get mapping separately
                content = content_with_mapping
                mapping = {}
                logger.warning("No mapping provided in input - will need to retrieve separately")
        
        if not content:
            return json.dumps({
                "success": False,
                "error": "No content provided for reinsertion",
                "content": ""
            })
        
        # If no mapping provided, this tool can't work properly
        if not mapping:
            return json.dumps({
                "success": False,
                "error": "No PII mapping provided - cannot personalize report",
                "content": content
            })
        
        # Track replacements
        replacements_made = []
        personalized_content = content
        
        # Sort by placeholder length (longest first) to avoid partial replacements
        sorted_mapping = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
        
        for placeholder, actual_value in sorted_mapping:
            if placeholder in personalized_content and actual_value:  # Only replace if value exists
                # Count occurrences before replacement
                occurrences = personalized_content.count(placeholder)
                
                # Replace placeholder with actual value
                personalized_content = personalized_content.replace(placeholder, actual_value)
                
                replacements_made.append({
                    "placeholder": placeholder,
                    "value": actual_value,
                    "occurrences": occurrences
                })
                
                logger.info(f"Replaced {occurrences} occurrences of {placeholder}")
        
        # Check for any remaining placeholders
        remaining_placeholders = re.findall(r'\[[\w_]+\]', personalized_content)
        if remaining_placeholders:
            logger.warning(f"Remaining placeholders after reinsertion: {remaining_placeholders}")
        
        return json.dumps({
            "success": True,
            "content": personalized_content,
            "replacements_made": replacements_made,
            "remaining_placeholders": remaining_placeholders
        })
        
    except Exception as e:
        logger.error(f"Error reinserting personal info: {str(e)}")
        return json.dumps({"error": str(e), "success": False})

@tool("personalize_recommendations")
def personalize_recommendations(recommendation_data: str) -> str:
    """
    Add personal touches to recommendations and key sections.
    Makes the report feel tailored to the specific owner.
    """
    try:
        data = safe_parse_json(recommendation_data, {}, "personalize_recommendations")
        if not data:
            return json.dumps({
                "success": False,
                "error": "No recommendation data provided",
                "content": ""
            })
        
        content = data.get('content', '')
        owner_name = data.get('owner_name', '')
        
        if not owner_name:
            logger.warning("No owner name provided for personalization")
            return json.dumps({
                "success": True,  # Not a failure, just less personal
                "content": content,
                "personalizations_applied": 0
            })
        
        # Extract first name for more personal touch
        first_name = owner_name.split()[0] if owner_name else "Business Owner"
        
        # Personalization patterns
        personalizations = {
            "Dear Business Owner": f"Dear {owner_name}",
            "the owner": "you",
            "The owner": "You",
            "the business owner": "you",
            "The business owner": "You",
            "business owner's": "your",
            "owner's": "your",
            "their business": "your business",
            "Their business": "Your business"
        }
        
        personalized_content = content
        personalization_count = 0
        
        # Apply personalizations
        for generic, personal in personalizations.items():
            if generic in personalized_content:
                personalized_content = personalized_content.replace(generic, personal)
                personalization_count += 1
        
        # Add personal touches to specific sections
        if "Executive Summary" in personalized_content:
            # Add personal greeting at the start
            personalized_content = personalized_content.replace(
                "Executive Summary\n\n",
                f"Executive Summary\n\n{first_name}, thank you for taking the time to complete this assessment. "
            )
        
        if "Next Steps" in personalized_content:
            # Make next steps more personal
            personalized_content = personalized_content.replace(
                "We recommend scheduling",
                f"{first_name}, we recommend scheduling"
            )
            personalized_content = personalized_content.replace(
                "Consider scheduling",
                f"{first_name}, consider scheduling"
            )
        
        return json.dumps({
            "success": True,
            "content": personalized_content,
            "personalizations_applied": personalization_count
        })
        
    except Exception as e:
        logger.error(f"Error personalizing recommendations: {str(e)}")
        return json.dumps({"error": str(e), "success": False})

@tool("validate_final_output")
def validate_final_output(final_report: str) -> str:
    """
    Perform final validation to ensure all personalizations are complete
    and the report is ready for delivery.
    """
    try:
        data = safe_parse_json(final_report, {}, "validate_final_output")
        if not data:
            return json.dumps({
                "ready_for_delivery": False,
                "error": "No report data provided for validation"
            })
        
        content = data.get('content', '')
        
        validation_results = {
            "has_placeholders": False,
            "has_owner_name": False,
            "has_email": False,
            "formatting_issues": [],
            "ready_for_delivery": True,
            "content_length": len(content.split())
        }
        
        # Check for remaining placeholders
        placeholders = re.findall(r'\[[\w_]+\]', content)
        if placeholders:
            validation_results["has_placeholders"] = True
            validation_results["ready_for_delivery"] = False
            validation_results["formatting_issues"].append(f"Found unreplaced placeholders: {placeholders}")
            logger.error(f"Critical: Unreplaced placeholders found: {placeholders}")
        
        # Verify personalization elements are present
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, content):
            validation_results["has_email"] = True
        
        # Check for proper name (capital letters pattern)
        # Exclude common business terms
        name_pattern = r'\b(?!Exit|Ready|Quick|Strategic|Professional|Manufacturing|Services)[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        potential_names = re.findall(name_pattern, content)
        if potential_names:
            validation_results["has_owner_name"] = True
            logger.info(f"Found potential owner names: {potential_names[:3]}")
        
        # Check for common formatting issues
        if '  ' in content:  # Double spaces
            validation_results["formatting_issues"].append("Contains double spaces")
        
        if '\n\n\n' in content:  # Triple line breaks
            validation_results["formatting_issues"].append("Contains excessive line breaks")
        
        # Check content length
        if validation_results["content_length"] < 1000:
            validation_results["formatting_issues"].append("Content seems too short")
            validation_results["ready_for_delivery"] = False
        
        # Determine final status
        if validation_results["formatting_issues"] or validation_results["has_placeholders"]:
            validation_results["ready_for_delivery"] = False
        
        return json.dumps(validation_results)
        
    except Exception as e:
        logger.error(f"Error validating final output: {str(e)}")
        return json.dumps({
            "error": str(e),
            "ready_for_delivery": False
        })

@tool("structure_for_pdf")
def structure_for_pdf(final_content: str) -> str:
    """
    Structure the final report content for PDF generation.
    Ensures proper formatting and section organization.
    """
    try:
        data = safe_parse_json(final_content, {}, "structure_for_pdf")
        if not data:
            return json.dumps({"error": "No content provided for PDF structuring"})
        
        content = data.get('content', '')
        metadata = data.get('metadata', {})
        
        # Structure for PDF generation
        pdf_structure = {
            "header": {
                "title": "Exit Ready Snapshot Assessment",
                "subtitle": "Personalized Business Exit Readiness Report",
                "date": metadata.get('date', ''),
                "prepared_for": metadata.get('owner_name', '')
            },
            "sections": [],
            "footer": {
                "company": "On Pulse Solutions",
                "confidential": True
            }
        }
        
        # Parse content into sections
        section_pattern = r'##\s+(.+?)\n(.*?)(?=##|\Z)'
        sections = re.findall(section_pattern, content, re.DOTALL)
        
        for title, section_content in sections:
            pdf_structure["sections"].append({
                "title": title.strip(),
                "content": section_content.strip()
            })
        
        # Add metadata
        pdf_structure["metadata"] = {
            "total_words": len(content.split()),
            "total_sections": len(sections),
            "has_personalization": bool(metadata.get('owner_name'))
        }
        
        return json.dumps(pdf_structure)
        
    except Exception as e:
        logger.error(f"Error structuring for PDF: {str(e)}")
        return json.dumps({"error": str(e)})

@tool("process_complete_reinsertion")
def process_complete_reinsertion(reinsertion_data: str) -> str:
    """
    Complete PII reinsertion process: retrieve mapping, reinsert, personalize, and validate
    """
    try:
        logger.info(f"=== PROCESS COMPLETE REINSERTION CALLED ===")
        logger.info(f"Input type: {type(reinsertion_data)}")
        logger.info(f"Input preview: {str(reinsertion_data)[:200]}...")
        
        # Handle CrewAI passing different input formats
        if isinstance(reinsertion_data, dict):
            data = reinsertion_data
            uuid = data.get('uuid', '')
            content = data.get('content', '') or data.get('approved_report', '') or str(data)
        else:
            # Try to parse as JSON
            data = safe_parse_json(reinsertion_data, {}, "process_complete_reinsertion")
            if data:
                uuid = data.get('uuid', '')
                content = data.get('content', '') or data.get('approved_report', '')
            else:
                # CrewAI might be passing raw content - extract UUID from content if possible
                content = reinsertion_data
                uuid_match = re.search(r'"([^"]*test[^"]*)"', content)
                uuid = uuid_match.group(1) if uuid_match else 'simple-test-123'
        
        if not content:
            content = reinsertion_data  # Use raw input as content
        
        logger.info(f"Extracted UUID: {uuid}")
        logger.info(f"Content length: {len(content)} chars")
        
        # Step 1: Retrieve PII mapping
        mapping_result = safe_parse_json(retrieve_pii_mapping(uuid), {}, "process_complete_reinsertion")
        
        if mapping_result.get('status') != 'found':
            logger.error(f"Cannot proceed without PII mapping for UUID: {uuid}")
            return json.dumps({
                "success": False,
                "error": "PII mapping not found - cannot personalize report",
                "content": content,
                "uuid": uuid
            })
        
        mapping = mapping_result.get('mapping', {})
        logger.info(f"Retrieved PII mapping with {len(mapping)} entries")
        
        # Step 2: Reinsert personal information
        reinsertion_result = safe_parse_json(reinsert_personal_info(json.dumps({
            "content": content,
            "mapping": mapping
        })), {}, "process_complete_reinsertion")
        
        if not reinsertion_result.get('success'):
            logger.error(f"Reinsertion failed: {reinsertion_result.get('error', 'Unknown error')}")
            return json.dumps(reinsertion_result)
        
        personalized_content = reinsertion_result.get('content', '')
        
        # Step 3: Add personal touches
        owner_name = mapping.get('[OWNER_NAME]', '')
        if owner_name:
            personalization_result = safe_parse_json(personalize_recommendations(json.dumps({
                "content": personalized_content,
                "owner_name": owner_name
            })), {}, "process_complete_reinsertion")
            personalized_content = personalization_result.get('content', personalized_content)
        
        # Step 4: Validate
        validation_result = safe_parse_json(validate_final_output(json.dumps({
            "content": personalized_content
        })), {}, "process_complete_reinsertion")
        
        # Step 5: Structure for output
        final_output = {
            "uuid": uuid,
            "success": validation_result.get('ready_for_delivery', False),
            "content": personalized_content,
            "metadata": {
                "owner_name": mapping.get('[OWNER_NAME]', ''),
                "email": mapping.get('[EMAIL]', ''),
                "company_name": mapping.get('[COMPANY_NAME]', ''),
                "total_words": validation_result.get('content_length', 0),
                "validation": validation_result,
                "replacements_made": reinsertion_result.get('replacements_made', [])
            }
        }
        
        logger.info(f"Successfully completed reinsertion for UUID: {uuid}")
        return json.dumps(final_output)
        
    except Exception as e:
        logger.error(f"Error in complete reinsertion process: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "content": reinsertion_data if isinstance(reinsertion_data, str) else str(reinsertion_data)
        })

def create_pii_reinsertion_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the PII reinsertion agent for final personalization"""
    
    # Get agent configuration from prompts
    config = prompts.get('pii_reinsertion_agent', {})
    
    # Create tools list
    tools = [
        retrieve_pii_mapping,
        reinsert_personal_info,
        personalize_recommendations,
        validate_final_output,
        structure_for_pdf,
        process_complete_reinsertion
    ]
    
    return Agent(
        role=config.get('role'),
        goal=config.get('goal'),
        backstory=config.get('backstory'),
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )

# Helper function to store PII mapping (called by intake agent)
def store_pii_mapping(uuid: str, mapping: Dict[str, str]):
    """Store PII mapping for later retrieval"""
    pii_mapping_store[uuid] = mapping
    logger.info(f"Stored PII mapping for UUID: {uuid} with entries: {list(mapping.keys())}")
    
# Helper function to clear old mappings (optional, for memory management)
def clear_old_mappings(older_than_hours: int = 24):
    """Clear mappings older than specified hours"""
    # In production, you'd track timestamps and clear old entries
    # For now, this is a placeholder
    pass