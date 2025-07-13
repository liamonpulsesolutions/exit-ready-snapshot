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
    
    Input: UUID string
    Returns: Status message with mapping details
    """
    args_schema: Type[BaseModel] = RetrievePIIMappingInput
    
    def _run(self, uuid: str = "", **kwargs) -> str:
        try:
            logger.info(f"=== RETRIEVE PII MAPPING CALLED ===")
            logger.info(f"UUID provided: '{uuid}'")
            
            if not uuid or uuid == "{}":
                return """PII MAPPING RETRIEVAL: Failed ❌

No UUID provided for PII mapping retrieval.

Required: Valid assessment UUID
Provided: None or empty

Action Required: Provide the assessment UUID from the intake agent."""
            
            # Actually retrieve the mapping from storage
            mapping = get_pii_mapping(uuid)
            
            if mapping:
                logger.info(f"Successfully retrieved PII mapping with {len(mapping)} entries")
                
                # Format mapping details for readable output
                mapping_details = '\n'.join(f"  - {k} → {v}" for k, v in mapping.items())
                
                return f"""PII MAPPING RETRIEVAL: Success ✓

UUID: {uuid}
Mapping Entries Found: {len(mapping)}

Mapping Details:
{mapping_details}

Status: Ready for personalization
All PII placeholders can be replaced with actual values."""
            else:
                logger.warning(f"No PII mapping found for UUID: {uuid}")
                return f"""PII MAPPING RETRIEVAL: Not Found ⚠️

UUID: {uuid}
Status: NO MAPPING FOUND

Possible Issues:
- Intake agent may not have completed successfully
- UUID mismatch between agents
- PII storage was skipped

Action Required: Verify intake agent execution and UUID consistency."""
                
        except Exception as e:
            logger.error(f"Error retrieving PII mapping: {str(e)}")
            return f"""PII MAPPING RETRIEVAL: Error ❌

UUID: {uuid}
Error: {str(e)}

System error occurred during retrieval.
Please check logs and retry."""

class ReinsertPersonalInfoTool(BaseTool):
    name: str = "reinsert_personal_info"
    description: str = """
    Replace all PII placeholders with actual personal information.
    Ensures natural language flow and proper formatting.
    
    Input should be JSON string containing:
    {"content": "Report for [OWNER_NAME] at [EMAIL]...", "mapping": {"[OWNER_NAME]": "John Doe", "[EMAIL]": "john@example.com"}}
    
    Returns personalization status message.
    """
    args_schema: Type[BaseModel] = ReinsertPersonalInfoInput
    
    def _run(self, content_with_mapping: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== REINSERT PERSONAL INFO CALLED ===")
            logger.info(f"Input type: {type(content_with_mapping)}")
            logger.info(f"Input preview: {str(content_with_mapping)[:200] if content_with_mapping else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not content_with_mapping or content_with_mapping == "{}":
                return """PERSONALIZATION: Failed ❌

No content provided for personalization.

Required:
- Content with PII placeholders
- Mapping of placeholders to actual values

Action Required: Provide both content and mapping."""
            
            # Handle CrewAI passing dict vs string vs raw content
            if isinstance(content_with_mapping, dict):
                # CrewAI passes the data as a dict
                data = content_with_mapping
                content = data.get('content', '') or data.get('content_with_mapping', '') or str(data)
                mapping = data.get('mapping', {})
            else:
                # Try to parse as JSON
                data = safe_parse_json(content_with_mapping, {}, "reinsert_personal_info")
                if data:
                    content = data.get('content', '')
                    mapping = data.get('mapping', {})
                else:
                    # Assume it's just content without mapping
                    content = content_with_mapping
                    mapping = {}
            
            # If no mapping provided, this tool can't work properly
            if not mapping:
                return """PERSONALIZATION: Failed ❌

No PII mapping provided.

Cannot personalize report without mapping data.
The mapping should contain:
- [OWNER_NAME] → Actual name
- [EMAIL] → Actual email
- [COMPANY_NAME] → Company name (if applicable)
- [LOCATION] → Location

Please retrieve the PII mapping first."""
            
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
            
            # Format result as readable text
            if replacements_made:
                replacements_text = '\n'.join(f"  • {r['placeholder']} → {r['value']} ({r['occurrences']} replacements)" 
                                            for r in replacements_made)
                
                if remaining_placeholders:
                    return f"""PERSONALIZATION: Partial Success ⚠️

Replacements Made: {len(replacements_made)}
{replacements_text}

⚠️ WARNING: Unreplaced placeholders remain:
{', '.join(remaining_placeholders)}

These placeholders were not in the mapping.
Report is partially personalized but needs review."""
                else:
                    return f"""PERSONALIZATION: Complete ✓

Successfully personalized report:
{replacements_text}

Total Replacements: {sum(r['occurrences'] for r in replacements_made)}
Remaining Placeholders: None

Report is fully personalized and ready for delivery."""
            else:
                return """PERSONALIZATION: No Changes

❌ No replacements made

Either:
- No placeholders found in content
- Mapping values are empty
- Placeholder/mapping mismatch

Report remains unpersonalized."""
            
        except Exception as e:
            logger.error(f"Error reinserting personal info: {str(e)}")
            return f"""PERSONALIZATION: Error ❌

Failed to reinsert personal information.
Error: {str(e)}

Please check the content format and retry."""

class PersonalizeRecommendationsTool(BaseTool):
    name: str = "personalize_recommendations"
    description: str = """
    Add personal touches to recommendations and key sections.
    Makes the report feel tailored to the specific owner.
    
    Input should be JSON string containing:
    {"content": "The owner should consider...", "owner_name": "John Doe"}
    
    Returns personalization status message.
    """
    args_schema: Type[BaseModel] = PersonalizeRecommendationsInput
    
    def _run(self, recommendation_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== PERSONALIZE RECOMMENDATIONS CALLED ===")
            logger.info(f"Input type: {type(recommendation_data)}")
            
            # Handle empty data
            if not recommendation_data or recommendation_data == "{}":
                return """RECOMMENDATION PERSONALIZATION: Failed ❌

No recommendation data provided.

Required:
- Content to personalize
- Owner name for personal touches

Action Required: Provide recommendation content and owner name."""
            
            # Parse input data
            if isinstance(recommendation_data, dict):
                data = recommendation_data
                content = data.get('content', '') or str(data)
                owner_name = data.get('owner_name', '')
            else:
                data = safe_parse_json(recommendation_data, {}, "personalize_recommendations")
                if data:
                    content = data.get('content', '')
                    owner_name = data.get('owner_name', '')
                else:
                    content = recommendation_data
                    owner_name = ''
            
            if not owner_name:
                return """RECOMMENDATION PERSONALIZATION: Limited ⚠️

No owner name provided for personalization.

Recommendations remain generic without personal touches.
To improve: Provide owner name for direct address."""
            
            # Add personal touches
            personalized_content = content
            personalizations_applied = 0
            
            # Direct address patterns
            replacements = [
                ("The owner", f"{owner_name}, you"),
                ("the owner", f"you"),
                ("The business owner", f"{owner_name}, you"),
                ("the business owner", f"you"),
                ("Your business", f"{owner_name}, your business"),
                ("Consider", f"{owner_name}, consider"),
                ("You should", f"{owner_name}, you should")
            ]
            
            for old_phrase, new_phrase in replacements:
                if old_phrase in personalized_content:
                    count = personalized_content.count(old_phrase)
                    personalized_content = personalized_content.replace(old_phrase, new_phrase, 1)  # Replace only first occurrence
                    personalizations_applied += 1
                    logger.info(f"Personalized '{old_phrase}' -> '{new_phrase}'")
            
            if personalizations_applied > 0:
                return f"""RECOMMENDATION PERSONALIZATION: Success ✓

Owner Name: {owner_name}
Personal Touches Added: {personalizations_applied}

Recommendations now address {owner_name} directly.
Report feels more personal and engaging.

Status: Personalization complete"""
            else:
                return f"""RECOMMENDATION PERSONALIZATION: No Changes ⚠️

Owner Name: {owner_name}
Personal Touches Added: 0

Content may already be personalized or lacks personalization opportunities.
Consider manual review for additional personal touches."""
                
        except Exception as e:
            logger.error(f"Error personalizing recommendations: {str(e)}")
            return f"""RECOMMENDATION PERSONALIZATION: Error ❌

Failed to personalize recommendations.
Error: {str(e)}

Please check the input format and retry."""

class ValidateFinalOutputTool(BaseTool):
    name: str = "validate_final_output"
    description: str = """
    Validate the final report has no remaining PII placeholders.
    Ensures professional quality and completeness.
    
    Input should be JSON string containing the final report content.
    
    Returns validation status message.
    """
    args_schema: Type[BaseModel] = ValidateFinalOutputInput
    
    def _run(self, final_report: str = "{}", **kwargs) -> str:
        try:
            logger.info("=== VALIDATE FINAL OUTPUT CALLED ===")
            
            # Handle empty input
            if not final_report or final_report == "{}":
                return """FINAL VALIDATION: Failed ❌

No report content provided for validation.

Cannot validate empty report.
Action Required: Provide the complete report for validation."""
            
            # Parse report content
            if isinstance(final_report, dict):
                if 'content' in final_report:
                    content = final_report['content']
                elif 'report' in final_report:
                    content = final_report['report']
                else:
                    content = str(final_report)
            else:
                # Try to parse as JSON
                data = safe_parse_json(final_report, {}, "validate_final_output")
                if data and isinstance(data, dict):
                    content = data.get('content', '') or data.get('report', '') or str(data)
                else:
                    content = final_report
            
            # Check for remaining placeholders
            placeholders = re.findall(r'\[[\w_]+\]', content)
            
            # Check content quality metrics
            word_count = len(content.split())
            has_sections = any(marker in content for marker in ['Executive Summary', 'Score', 'Analysis', 'Recommendations'])
            
            validation_issues = []
            
            if placeholders:
                validation_issues.append(f"Found {len(placeholders)} unreplaced placeholders: {', '.join(set(placeholders))}")
            
            if word_count < 500:
                validation_issues.append(f"Report too short ({word_count} words) - expected 1000+ words")
            
            if not has_sections:
                validation_issues.append("Missing standard report sections")
            
            # Check for professional language
            unprofessional_terms = ['gonna', 'wanna', 'stuff', 'things', 'etc.', '...']
            found_terms = [term for term in unprofessional_terms if term in content.lower()]
            if found_terms:
                validation_issues.append(f"Unprofessional language detected: {', '.join(found_terms)}")
            
            if validation_issues:
                issues_text = '\n'.join(f"  ❌ {issue}" for issue in validation_issues)
                return f"""FINAL VALIDATION: Failed ⚠️

Validation Issues Found:
{issues_text}

Report Quality Score: {max(0, 10 - len(validation_issues))}/10

Action Required: Address issues before delivery."""
            else:
                return f"""FINAL VALIDATION: Passed ✓

Report Quality Metrics:
  ✓ Word Count: {word_count} words
  ✓ No PII placeholders remaining
  ✓ All sections present
  ✓ Professional language used
  ✓ Ready for delivery

Quality Score: 10/10

Report is validated and ready for PDF generation."""
                
        except Exception as e:
            logger.error(f"Error validating final output: {str(e)}")
            return f"""FINAL VALIDATION: Error ❌

Validation process failed.
Error: {str(e)}

Please check the report format and retry."""

class StructureForPDFTool(BaseTool):
    name: str = "structure_for_pdf"
    description: str = """
    Structure the personalized content for PDF generation.
    Ensures proper formatting and metadata inclusion.
    
    Input should be JSON string containing content and metadata.
    
    Returns structured output status message.
    """
    args_schema: Type[BaseModel] = StructureForPDFInput
    
    def _run(self, final_content: str = "{}", **kwargs) -> str:
        try:
            logger.info("=== STRUCTURE FOR PDF CALLED ===")
            
            # Handle empty input
            if not final_content or final_content == "{}":
                return """PDF STRUCTURING: Failed ❌

No content provided for PDF structuring.

Required:
- Final report content
- Metadata (owner info, scores, etc.)

Action Required: Provide complete content for PDF generation."""
            
            # Parse input
            if isinstance(final_content, dict):
                data = final_content
                content = data.get('content', '') or str(data)
                metadata = data.get('metadata', {})
            else:
                data = safe_parse_json(final_content, {}, "structure_for_pdf")
                if data:
                    content = data.get('content', '')
                    metadata = data.get('metadata', {})
                else:
                    content = final_content
                    metadata = {}
            
            # Structure sections for PDF
            sections_found = []
            
            # Check for key sections
            if "Executive Summary" in content:
                sections_found.append("Executive Summary")
            if "Score" in content or "Readiness" in content:
                sections_found.append("Scoring Results")
            if "Analysis" in content or "Category" in content:
                sections_found.append("Detailed Analysis")
            if "Recommendation" in content or "Action" in content:
                sections_found.append("Recommendations")
            if "Market" in content or "Industry" in content:
                sections_found.append("Market Context")
            
            # Extract key metadata
            owner_name = metadata.get('owner_name', 'Business Owner')
            email = metadata.get('email', 'Not provided')
            overall_score = metadata.get('overall_score', 'Not calculated')
            
            if len(sections_found) >= 4:
                return f"""PDF STRUCTURING: Success ✓

Document Structure Prepared:
  ✓ Owner: {owner_name}
  ✓ Email: {email}
  ✓ Overall Score: {overall_score}

Sections Formatted ({len(sections_found)}):
{chr(10).join(f'  • {section}' for section in sections_found)}

Formatting Applied:
  ✓ Headers and subheaders
  ✓ Bullet points and lists
  ✓ Score visualizations
  ✓ Professional spacing

Status: Ready for PDF generation via Placid API"""
            else:
                return f"""PDF STRUCTURING: Incomplete ⚠️

Document structure issues detected.

Sections Found: {len(sections_found)}/5
{chr(10).join(f'  • {section}' for section in sections_found)}

Missing Sections:
  ❌ Some key sections appear to be missing

Owner Information:
  • Name: {owner_name}
  • Email: {email}

Action Required: Ensure all report sections are included."""
                
        except Exception as e:
            logger.error(f"Error structuring for PDF: {str(e)}")
            return f"""PDF STRUCTURING: Error ❌

Failed to structure content for PDF.
Error: {str(e)}

Please check the content format and retry."""

class ProcessCompleteReinsertionTool(BaseTool):
    name: str = "process_complete_reinsertion"
    description: str = """
    Complete PII reinsertion workflow: retrieve mapping, reinsert PII, validate.
    This is the main tool that orchestrates the entire reinsertion process.
    
    Input should be JSON string containing:
    {"uuid": "assessment-uuid", "content": "report content with placeholders"}
    
    Returns comprehensive status message of the complete process.
    """
    args_schema: Type[BaseModel] = ProcessCompleteReinsertionInput
    
    def _run(self, reinsertion_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== PROCESS COMPLETE REINSERTION CALLED ===")
            logger.info(f"Input type: {type(reinsertion_data)}")
            logger.info(f"Input length: {len(str(reinsertion_data))}")
            
            # Handle case where CrewAI doesn't pass any arguments
            if not reinsertion_data or reinsertion_data == "{}":
                return """COMPLETE REINSERTION PROCESS: Failed ❌

No data provided for reinsertion process.

Required:
- UUID from assessment
- Content with PII placeholders

Action Required: Provide both UUID and content for personalization."""
            
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
                    uuid_match = re.search(r'"uuid":\s*"([^"]+)"', content)
                    uuid = uuid_match.group(1) if uuid_match else 'unknown'
            
            if not content:
                content = reinsertion_data  # Use raw input as content
            
            logger.info(f"Extracted UUID: {uuid}")
            logger.info(f"Content length: {len(content)} chars")
            
            process_status = []
            
            # Step 1: Retrieve PII mapping
            process_status.append("STEP 1: Retrieving PII Mapping")
            mapping_result = retrieve_pii_mapping.run(uuid)
            
            # Parse the text response to check status
            if "Success" in mapping_result:
                # Extract mapping from the successful retrieval
                mapping = get_pii_mapping(uuid)
                if not mapping:
                    # Try to extract from result if tool returned it differently
                    mapping_lines = [line for line in mapping_result.split('\n') if '→' in line]
                    mapping = {}
                    for line in mapping_lines:
                        if '→' in line:
                            parts = line.strip().split('→')
                            if len(parts) == 2:
                                key = parts[0].strip().lstrip('- ')
                                value = parts[1].strip()
                                mapping[key] = value
                
                process_status.append(f"✓ Retrieved {len(mapping)} PII mappings")
                logger.info(f"Retrieved PII mapping with {len(mapping)} entries")
            else:
                logger.error(f"Cannot proceed without PII mapping for UUID: {uuid}")
                return f"""COMPLETE REINSERTION PROCESS: Failed ❌

{chr(10).join(process_status)}
✗ PII mapping not found for UUID: {uuid}

CRITICAL ERROR: The intake agent did not store PII mapping.
Cannot personalize report without owner information.

The report will contain placeholders like [OWNER_NAME] instead of actual names.

Action Required:
1. Check if intake agent completed successfully
2. Verify UUID matches between intake and reinsertion
3. Review PII storage system status"""
            
            # Step 2: Reinsert personal information
            process_status.append("\nSTEP 2: Reinserting Personal Information")
            reinsertion_input = {
                "content": content,
                "mapping": mapping
            }
            reinsertion_result = reinsert_personal_info.run(json.dumps(reinsertion_input))
            
            if "Complete ✓" in reinsertion_result:
                personalized_content = content
                # Apply replacements
                for placeholder, value in mapping.items():
                    if value:
                        personalized_content = personalized_content.replace(placeholder, value)
                
                process_status.append("✓ Successfully replaced all PII placeholders")
            elif "Partial Success" in reinsertion_result:
                personalized_content = content
                # Apply available replacements
                for placeholder, value in mapping.items():
                    if value:
                        personalized_content = personalized_content.replace(placeholder, value)
                
                process_status.append("⚠️ Partially replaced PII placeholders")
            else:
                process_status.append("✗ Failed to reinsert personal information")
                personalized_content = content
            
            # Step 3: Add personal touches to recommendations
            process_status.append("\nSTEP 3: Personalizing Recommendations")
            owner_name = mapping.get('[OWNER_NAME]', '')
            if owner_name:
                personalize_input = {
                    "content": personalized_content,
                    "owner_name": owner_name
                }
                personalize_result = personalize_recommendations.run(json.dumps(personalize_input))
                
                if "Success" in personalize_result:
                    # Apply basic personalizations
                    personalized_content = personalized_content.replace("The owner", f"{owner_name}, you", 1)
                    personalized_content = personalized_content.replace("the owner", "you")
                    process_status.append(f"✓ Added personal touches for {owner_name}")
                else:
                    process_status.append("⚠️ Limited personalization applied")
            else:
                process_status.append("⚠️ No owner name for personalization")
            
            # Step 4: Validate final output
            process_status.append("\nSTEP 4: Validating Final Report")
            validation_input = {"content": personalized_content}
            validation_result = validate_final_output.run(json.dumps(validation_input))
            
            if "Passed ✓" in validation_result:
                process_status.append("✓ Report validation passed")
            else:
                process_status.append("⚠️ Report has validation warnings")
            
            # Step 5: Structure for PDF
            process_status.append("\nSTEP 5: Structuring for PDF Generation")
            structure_input = {
                "content": personalized_content,
                "metadata": {
                    "owner_name": mapping.get('[OWNER_NAME]', 'Business Owner'),
                    "email": mapping.get('[EMAIL]', 'Not provided'),
                    "company_name": mapping.get('[COMPANY_NAME]', ''),
                    "overall_score": "Calculated in report"
                }
            }
            structure_result = structure_for_pdf.run(json.dumps(structure_input))
            
            if "Success" in structure_result:
                process_status.append("✓ Report structured for PDF generation")
            else:
                process_status.append("⚠️ PDF structuring completed with warnings")
            
            # Prepare final summary
            success_count = sum(1 for status in process_status if '✓' in status)
            warning_count = sum(1 for status in process_status if '⚠️' in status)
            error_count = sum(1 for status in process_status if '✗' in status)
            
            return f"""COMPLETE REINSERTION PROCESS: {'Complete ✓' if error_count == 0 else 'Completed with Issues ⚠️'}

PROCESS SUMMARY:
{chr(10).join(process_status)}

FINAL STATUS:
- Successful Steps: {success_count}
- Warnings: {warning_count}
- Errors: {error_count}

PERSONALIZATION APPLIED:
- Owner Name: {mapping.get('[OWNER_NAME]', 'Not found')}
- Email: {mapping.get('[EMAIL]', 'Not found')}
- Company: {mapping.get('[COMPANY_NAME]', 'N/A')}
- Location: {mapping.get('[LOCATION]', 'Not found')}

OUTPUT READY: {'Yes - Proceed to PDF generation' if error_count == 0 else 'Review required before delivery'}

{f'Note: Report is {"fully" if error_count == 0 else "partially"} personalized and {"ready" if error_count == 0 else "may need review"} for client delivery.'}"""
            
        except Exception as e:
            logger.error(f"Error in complete reinsertion process: {str(e)}")
            return f"""COMPLETE REINSERTION PROCESS: Failed ❌

Critical error in reinsertion process.
Error: {str(e)}

UUID: {uuid if 'uuid' in locals() else 'unknown'}

The report could not be personalized.
Manual intervention required."""

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