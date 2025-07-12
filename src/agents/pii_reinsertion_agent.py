from crewai import Agent
from crewai.tools import tool
from typing import Dict, Any, List
import logging
import json
import re

logger = logging.getLogger(__name__)

# Global storage for PII mapping (in production, use secure storage like Redis)
pii_mapping_store = {}

@tool("retrieve_pii_mapping")
def retrieve_pii_mapping(uuid: str) -> str:
    """
    Retrieve the PII mapping for a specific assessment UUID.
    In production, this would fetch from secure storage.
    """
    try:
        # For now, we'll simulate retrieval
        # In production, this would connect to Redis or secure database
        
        # Mock PII mapping for testing
        mock_mapping = {
            "[OWNER_NAME]": "John Smith",
            "[EMAIL]": "john@example.com",
            "[COMPANY_NAME]": "Smith Enterprises",
            "[LOCATION]": "Pacific/Western US"
        }
        
        # Check if we have a stored mapping (from intake agent)
        if uuid in pii_mapping_store:
            mapping = pii_mapping_store[uuid]
        else:
            # Use mock data for testing
            mapping = mock_mapping
            logger.warning(f"No PII mapping found for UUID {uuid}, using mock data")
        
        return json.dumps({
            "uuid": uuid,
            "mapping": mapping,
            "mapping_count": len(mapping)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving PII mapping: {str(e)}")
        return json.dumps({"error": str(e), "mapping": {}})

@tool("reinsert_personal_info")
def reinsert_personal_info(content_with_mapping: str) -> str:
    """
    Replace all placeholders with actual personal information.
    Ensures natural language flow and proper formatting.
    """
    try:
        data = json.loads(content_with_mapping)
        content = data.get('content', '')
        mapping = data.get('mapping', {})
        
        if not mapping:
            return json.dumps({
                "success": False,
                "error": "No PII mapping provided",
                "content": content
            })
        
        # Track replacements
        replacements_made = []
        personalized_content = content
        
        # Sort by placeholder length (longest first) to avoid partial replacements
        sorted_mapping = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
        
        for placeholder, actual_value in sorted_mapping:
            if placeholder in personalized_content:
                # Count occurrences before replacement
                occurrences = personalized_content.count(placeholder)
                
                # Replace placeholder with actual value
                personalized_content = personalized_content.replace(placeholder, actual_value)
                
                replacements_made.append({
                    "placeholder": placeholder,
                    "value": actual_value,
                    "occurrences": occurrences
                })
        
        # Check for any remaining placeholders
        remaining_placeholders = re.findall(r'\[[\w_]+\]', personalized_content)
        
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
        data = json.loads(recommendation_data)
        content = data.get('content', '')
        owner_name = data.get('owner_name', '')
        
        if not owner_name:
            return json.dumps({
                "success": False,
                "error": "Owner name not provided",
                "content": content
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
            "owner's": "your"
        }
        
        personalized_content = content
        
        # Apply personalizations
        for generic, personal in personalizations.items():
            personalized_content = personalized_content.replace(generic, personal)
        
        # Add personal touches to specific sections
        if "Executive Summary" in personalized_content:
            # Add personal greeting at the start
            personalized_content = personalized_content.replace(
                "Executive Summary",
                f"Executive Summary\n\n{first_name}, thank you for completing the Exit Ready Snapshot assessment."
            )
        
        if "Next Steps" in personalized_content:
            # Make next steps more personal
            personalized_content = personalized_content.replace(
                "consider scheduling",
                f"{first_name}, I recommend scheduling"
            )
        
        return json.dumps({
            "success": True,
            "content": personalized_content,
            "personalizations_applied": len(personalizations)
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
        data = json.loads(final_report)
        content = data.get('content', '')
        
        validation_results = {
            "has_placeholders": False,
            "has_owner_name": False,
            "has_email": False,
            "formatting_issues": [],
            "ready_for_delivery": True
        }
        
        # Check for remaining placeholders
        placeholders = re.findall(r'\[[\w_]+\]', content)
        if placeholders:
            validation_results["has_placeholders"] = True
            validation_results["ready_for_delivery"] = False
            validation_results["formatting_issues"].append(f"Found placeholders: {placeholders}")
        
        # Verify personalization elements are present
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, content):
            validation_results["has_email"] = True
        
        # Check for proper name (capital letters pattern)
        name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        if re.search(name_pattern, content):
            validation_results["has_owner_name"] = True
        
        # Check for common formatting issues
        if '  ' in content:  # Double spaces
            validation_results["formatting_issues"].append("Contains double spaces")
        
        if '\n\n\n' in content:  # Triple line breaks
            validation_results["formatting_issues"].append("Contains excessive line breaks")
        
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
        data = json.loads(final_content)
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
        
        for title, content in sections:
            pdf_structure["sections"].append({
                "title": title.strip(),
                "content": content.strip()
            })
        
        return json.dumps(pdf_structure)
        
    except Exception as e:
        logger.error(f"Error structuring for PDF: {str(e)}")
        return json.dumps({"error": str(e)})

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
        structure_for_pdf
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
    logger.info(f"Stored PII mapping for UUID: {uuid}")