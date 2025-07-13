#!/usr/bin/env python
"""Simple crew test with minimal data"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Reduce logging noise - only show our messages and errors
logging.basicConfig(
    level=logging.ERROR,  # Only errors
    format='%(name)s - %(levelname)s - %(message)s'
)

# But enable our logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)

def test_crew_execution():
    """Test crew with minimal data"""
    logger.info("Starting simple crew test...")
    
    # Minimal test data
    test_data = {
        "uuid": "simple-test-123",
        "timestamp": datetime.now().isoformat(),
        "name": "John Doe",
        "email": "john@test.com",
        "industry": "Professional Services", 
        "years_in_business": "10-20 years",
        "age_range": "55-64",
        "exit_timeline": "1-2 years",
        "location": "Pacific/Western US",
        "revenue_range": "$1M-$5M",
        "responses": {
            "q1": "I handle client meetings",
            "q2": "Less than 3 days",
            "q3": "Consulting services",
            "q4": "40-60%",
            "q5": "6",
            "q6": "Stable",
            "q7": "Senior consultant",
            "q8": "5",
            "q9": "Industry expertise",
            "q10": "7"
        }
    }
    
    try:
        from src.crew import ExitReadySnapshotCrew
        
        logger.info("Creating crew...")
        crew = ExitReadySnapshotCrew(locale='us')
        
        logger.info("Starting crew execution...")
        result = crew.kickoff(inputs=test_data)
        
        logger.info("Crew execution completed!")
        logger.info(f"Result type: {type(result)}")
        
        if isinstance(result, dict):
            status = result.get('status', 'unknown')
            logger.info(f"Status: {status}")
            
            if status == 'error':
                logger.error(f"Crew error: {result.get('error', 'Unknown error')}")
            else:
                logger.info(f"Success! UUID: {result.get('uuid')}")
                logger.info(f"Owner: {result.get('owner_name')}")
                
                # Check scores
                scores = result.get('scores', {})
                if scores:
                    overall = scores.get('overall', 'N/A')
                    logger.info(f"Overall score: {overall}")
                
        print("\n" + "="*50)
        print("FINAL RESULT:")
        print("="*50)
        
        if isinstance(result, dict):
            # Print a clean summary
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"UUID: {result.get('uuid', 'N/A')}")
            
            if 'error' in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Owner: {result.get('owner_name', 'N/A')}")
                scores = result.get('scores', {})
                if scores:
                    print(f"Overall Score: {scores.get('overall', 'N/A')}")
                    
                # Show if we got actual content
                content = result.get('content', '')
                if content:
                    print(f"Content Length: {len(content)} chars")
                    print(f"Content Preview: {content[:100]}...")
        else:
            print(str(result))
            
        return result
        
    except Exception as e:
        logger.error(f"Crew execution failed: {str(e)}")
        
        # Show more detail for debugging
        import traceback
        print("\nFULL ERROR TRACEBACK:")
        traceback.print_exc()
        
        return {"error": str(e)}

if __name__ == "__main__":
    print("SIMPLE CREW TEST")
    print("="*50)
    result = test_crew_execution()