import os
import json
from datetime import datetime
from dotenv import load_dotenv
from src.crew import ExitReadySnapshotCrew
from src.utils.logging_config import setup_logging

load_dotenv()
logger = setup_logging()

def process_assessment(form_data: dict) -> dict:
    """
    Main entry point for processing Exit Ready Snapshot assessments
    """
    logger.info(f"Processing assessment for UUID: {form_data.get('uuid')}")
    
    try:
        # Initialize the crew with locale
        locale = determine_locale(form_data.get('location', 'Other'))
        crew = ExitReadySnapshotCrew(locale=locale)
        
        # Execute the assessment pipeline
        result = crew.kickoff(inputs=form_data)
        
        logger.info(f"Assessment completed for UUID: {form_data.get('uuid')}")
        return result
        
    except Exception as e:
        logger.error(f"Assessment failed: {str(e)}")
        raise

def determine_locale(location: str) -> str:
    """Determine locale based on location"""
    locale_mapping = {
        'Pacific/Western US': 'us',
        'Mountain/Central US': 'us',
        'Midwest US': 'us',
        'Southern US': 'us',
        'Northeast US': 'us',
        'United Kingdom': 'uk',
        'Australia/New Zealand': 'au',
        'Canada': 'us',  # Default to US for Canada
        'Other International': 'us'  # Default to US
    }
    return locale_mapping.get(location, 'us')

if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        "uuid": "test-123",
        "timestamp": datetime.now().isoformat(),
        "name": "John Smith",
        "email": "john@example.com",
        "industry": "Professional Services",
        "years_in_business": "10-20 years",
        "age_range": "55-64",
        "exit_timeline": "1-2 years",
        "location": "Pacific/Western US",
        "responses": {
            "q1": "I handle all client meetings and final approvals on projects",
            "q2": "Less than 3 days",
            "q3": "Consulting services 60%, Training workshops 40%",
            "q4": "20-40%",
            "q5": "7",
            "q6": "Improved slightly",
            "q7": "Client relationships and technical knowledge of our main service",
            "q8": "4",
            "q9": "Long-term client relationships and specialized expertise in our niche",
            "q10": "8"
        }
    }
    
    print("Starting test assessment...")
    result = process_assessment(sample_data)
    print("\nResult:")
    print(json.dumps(result, indent=2))