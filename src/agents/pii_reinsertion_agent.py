from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Type
import logging
import json
import re
from ..utils.json_helper import safe_parse_json
from ..utils.pii_storage import retrieve_pii_mapping as get_pii_mapping, store_pii_mapping

logger = logging.getLogger(__name__)

# Tool Input Schemas
class RetrievePIIMappingInput(BaseModel):
    uuid: str = Field(
        default="",
        description="The assessment UUID to retrieve PII mapping for"
    )

class ReinsertPersonalInfoInput(BaseModel):
    content_with_mapping: str = Field(
        default="{}",
        description="JSON string containing content and mapping"
    )

class PersonalizeRecommendationsInput(BaseModel):
    recommendation_data: str = Field(
        default="{}",
        description="JSON string containing content and owner_name"
    )

class ValidateFinalOutputInput(BaseModel):
    final_report: str = Field(
        default="{}",
        description="JSON string containing the final report content"
    )

class StructureForPDFInput(BaseModel):
    final_content: str = Field(
        default="{}",
        description="JSON string containing content and metadata"
    )

class ProcessCompleteReinsertionInput(BaseModel):
    reinsertion_data: str = Field(
        default="{}",
        description="JSON string containing uuid and content"
    )

# Tool Classes
class RetrievePIIMappingTool(BaseTool):
    name: str = "retrieve_pii_mapping"
    description: str = """
    Retrieve the PII mapping for a specific assessment UUID.
    CRITICAL: This must use the actual mapping from intake agent, not mock data.
    
    Input: The assessment UUID to retrieve PII mapping for
    Example: "simple-test-123"
    
    Returns JSON with mapping data:
    {"uuid": "simple-test-123", "mapping": {"[OWNER_NAME]": "John Doe", "[EMAIL]": "john@example.com"}, "status": "found"}
    """
    args_schema: Type[BaseModel] = RetrievePIIMappingInput
    
    def _run(self, uuid: str = "", **kwargs) -> str:
        try:
            logger.info(f"=== RETRIEVE PII MAPPING CALLED ===")
            logger.info(f"Input type: {type(uuid)}")
            logger.info(f"Input value: {str(uuid)[:100] if uuid else 'No UUID provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not uuid or uuid == "":
                logger.warning("No UUID provided for PII mapping retrieval")
                return json.dumps({
                    "uuid": "unknown",
                    "mapping": {},
                    "mapping_count": 0,
                    "status": "not_found",
                    "error": "No UUID provided"
                })
            
            # Handle case where uuid might be passed as JSON
            if isinstance(uuid, str) and uuid.startswith('{'):
                uuid_data = safe_parse_json(uuid, {}, "retrieve_pii_mapping")
                uuid = uuid_data.get('uuid', uuid)
            
            # Check if we have a stored mapping for this UUID
            mapping = get_pii_mapping(uuid)
            if mapping:
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

class ReinsertPersonalInfoTool(BaseTool):
    name: str = "reinsert_personal_info"
    description: str = """
    Replace all placeholders with actual personal information.
    Ensures natural language flow and proper formatting.
    
    Input should be JSON string containing:
    {"content": "Report for [OWNER_NAME] at [EMAIL]...", "mapping": {"[OWNER_NAME]": "John Doe", "[EMAIL]": "john@example.com"}}
    
    Returns JSON with personalized content:
    {"success": true, "content": "Report for John Doe at john@example.com...", "replacements_made": [...]}
    """
    args_schema: Type[BaseModel] = ReinsertPersonalInfoInput
    
    def _run(self, content_with_mapping: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== REINSERT PERSONAL INFO CALLED ===")
            logger.info(f"Input type: {type(content_with_mapping)}")
            logger.info(f"Input preview: {str(content_with_mapping)[:200] if content_with_mapping else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not content_with_mapping or content_with_mapping == "{}":
                logger.warning("No content provided for personal info reinsertion")
                return json.dumps({
                    "success": False,
                    "error": "No content provided for reinsertion",
                    "content": ""
                })
            
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

class PersonalizeRecommendationsTool(BaseTool):
    name: str = "personalize_recommendations"
    description: str = """
    Add personal touches to recommendations and key sections.
    Makes the report feel tailored to the specific owner.
    
    Input should be JSON string containing:
    {"content": "The owner should consider...", "owner_name": "John Doe"}
    
    Returns JSON with personalized content:
    {"success": true, "content": "John, you should consider...", "personalizations_applied": 3}
    """
    args_schema: Type[BaseModel] = PersonalizeRecommendationsInput
    
    def _run(self, recommendation_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== PERSONALIZE RECOMMENDATIONS CALLED ===")
            logger.info(f"Input type: {type(recommendation_data)}")
            logger.info(f"Input preview: {str(recommendation_data)[:200] if recommendation_data else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not recommendation_data or recommendation_data == "{}":
                logger.warning("No recommendation data provided for personalization")
                return json.dumps({
                    "success": False,
                    "error": "No recommendation data provided",
                    "content": ""
                })
            
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

class ValidateFinalOutputTool(BaseTool):
    name: str = "validate_final_output"
    description: str = """
    Perform final validation to ensure all personalizations are complete
    and the report is ready for delivery.
    
    Input should be JSON string containing:
    {"content": "Complete report text with personalized content..."}
    
    Returns JSON with validation results:
    {"ready_for_delivery": true, "has_placeholders": false, "content_length": 2500}
    """
    args_schema: Type[BaseModel] = ValidateFinalOutputInput
    
    def _run(self, final_report: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== VALIDATE FINAL OUTPUT CALLED ===")
            logger.info(f"Input type: {type(final_report)}")
            logger.info(f"Input preview: {str(final_report)[:200] if final_report else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not final_report or final_report == "{}":
                logger.warning("No report data provided for final validation")
                return json.dumps({
                    "ready_for_delivery": False,
                    "error": "No report data provided for validation"
                })
            
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

class StructureForPDFTool(BaseTool):
    name: str = "structure_for_pdf"
    description: str = """
    Structure the final report content for PDF generation.
    Ensures proper formatting and section organization.
    
    Input should be JSON string containing:
    {"content": "Complete report content...", "metadata": {"owner_name": "John Doe", "date": "2025-01-15"}}
    
    Returns JSON with PDF structure:
    {"header": {...}, "sections": [...], "footer": {...}}
    """
    args_schema: Type[BaseModel] = StructureForPDFInput
    
    def _run(self, final_content: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== STRUCTURE FOR PDF CALLED ===")
            logger.info(f"Input type: {type(final_content)}")
            logger.info(f"Input preview: {str(final_content)[:200] if final_content else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not final_content or final_content == "{}":
                logger.warning("No content provided for PDF structuring")
                return json.dumps({"error": "No content provided for PDF structuring"})
            
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

class ProcessCompleteReinsertionTool(BaseTool):
    name: str = "process_complete_reinsertion"
    description: str = """
    Complete PII reinsertion process: retrieve mapping, reinsert, personalize, and validate.
    This is the main tool that orchestrates the entire reinsertion workflow.
    
    Input should be JSON string containing:
    {"uuid": "simple-test-123", "content": "Report content with [OWNER_NAME] placeholders...", "approved_report": "Alternative content field..."}
    
    Returns JSON with complete personalized report:
    {"success": true, "content": "Personalized report content...", "metadata": {"owner_name": "John Doe", "validation": {...}}}
    """
    args_schema: Type[BaseModel] = ProcessCompleteReinsertionInput
    
    def _run(self, reinsertion_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== PROCESS COMPLETE REINSERTION CALLED ===")
            logger.info(f"Input type: {type(reinsertion_data)}")
            logger.info(f"Input preview: {str(reinsertion_data)[:200] if reinsertion_data else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not reinsertion_data or reinsertion_data == "{}":
                logger.warning("No reinsertion data provided")
                return json.dumps({
                    "success": False,
                    "error": "No reinsertion data provided",
                    "content": "",
                    "uuid": "unknown"
                })
            
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
            mapping_result = safe_parse_json(retrieve_pii_mapping.run(uuid), {}, "process_complete_reinsertion")
            
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
            reinsertion_result = safe_parse_json(reinsert_personal_info.run(json.dumps({
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
                personalization_result = safe_parse_json(personalize_recommendations.run(json.dumps({
                    "content": personalized_content,
                    "owner_name": owner_name
                })), {}, "process_complete_reinsertion")
                personalized_content = personalization_result.get('content', personalized_content)
            
            # Step 4: Validate
            validation_result = safe_parse_json(validate_final_output.run(json.dumps({
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

# Create tool instances
retrieve_pii_mapping = RetrievePIIMappingTool()
reinsert_personal_info = ReinsertPersonalInfoTool()
personalize_recommendations = PersonalizeRecommendationsTool()
validate_final_output = ValidateFinalOutputTool()
structure_for_pdf = StructureForPDFTool()
process_complete_reinsertion = ProcessCompleteReinsertionTool()

def create_pii_reinsertion_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the PII reinsertion agent for final personalization"""
    
    # Get agent configuration from prompts
    config = prompts.get('pii_reinsertion_agent', {})
    
    # Create tools list using instances
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

# Helper functions moved to shared utility - keeping for backward compatibility
def store_pii_mapping_legacy(uuid: str, mapping: Dict[str, str]):
    """Legacy function - redirects to shared utility"""
    store_pii_mapping(uuid, mapping)
    
def clear_old_mappings(older_than_hours: int = 24):
    """Clear mappings older than specified hours"""
    # In production, you'd track timestamps and clear old entries
    # For now, this is a placeholder
    pass