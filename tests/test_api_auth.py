#!/usr/bin/env python3
"""
Test script for Exit Ready Snapshot API authentication
"""

import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API base URL
BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", "n_Tib0VaG6C9-cWcp570C-ZjvTdrGIoYCj3gsqwK_eA")

def test_health():
    """Test health endpoint (no auth required)"""
    print("\n1. Testing health endpoint (no auth):")
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        print(f"✅ Health check passed: {response.json()['status']}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

def test_debug_auth():
    """Test the debug auth endpoint"""
    print("\n2. Testing debug auth endpoint:")
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/test-auth", headers=headers)
        result = response.json()
        print("✅ Auth test response:")
        print(json.dumps(result, indent=2))
        
        if result.get('match'):
            print("✅ Authentication successful!")
        else:
            print("❌ Authentication failed - key mismatch")
            
    except Exception as e:
        print(f"❌ Auth test failed: {e}")

def test_header_variants():
    """Test different header name formats"""
    print("\n3. Testing different header formats:")
    
    variants = [
        ("X-API-Key", {"X-API-Key": API_KEY}),
        ("X-Api-Key", {"X-Api-Key": API_KEY}),
        ("x-api-key", {"x-api-key": API_KEY}),
        ("API-Key", {"API-Key": API_KEY}),
    ]
    
    for name, headers in variants:
        print(f"\nTrying header: {name}")
        headers["Content-Type"] = "application/json"
        
        try:
            response = requests.post(f"{BASE_URL}/test-auth", headers=headers)
            result = response.json()
            
            if result.get('match'):
                print(f"✅ SUCCESS with {name}")
                print(f"   Received value: {result.get('x_api_key_param')}")
            else:
                print(f"❌ Failed with {name} - no match")
                
        except Exception as e:
            print(f"❌ Error with {name}: {e}")

def test_full_assessment():
    """Test the full assessment endpoint"""
    print("\n4. Testing full assessment endpoint:")
    
    # Check if sample_request.json exists
    if not Path("sample_request.json").exists():
        print("⚠️  sample_request.json not found - creating it...")
        sample_data = {
            "uuid": "test-api-001",
            "timestamp": "2025-07-16T00:00:00.000Z",
            "name": "Test Owner",
            "email": "test@example.com",
            "industry": "Manufacturing & Production",
            "years_in_business": "5-10 years",
            "revenue_range": "$10M-$25M",
            "location": "Northeast US",
            "exit_timeline": "1-2 years",
            "age_range": "55-64",
            "responses": {
                "q1": "Quality control final sign-offs for our largest automotive client.",
                "q2": "3-7 days",
                "q3": "Custom metal fabrication for automotive suppliers - about 70% of revenue.",
                "q4": "60-80%",
                "q5": "6",
                "q6": "Stayed flat",
                "q7": "Programming and setup of our CNC machines - Tom has 15 years experience.",
                "q8": "8",
                "q9": "ISO 9001 and AS9100 aerospace certifications.",
                "q10": "4"
            },
            "_tallySubmissionId": "test-api-001",
            "_tallyFormId": "3100Y4"
        }
        
        with open("sample_request.json", "w") as f:
            json.dump(sample_data, f, indent=2)
        print("✅ Created sample_request.json")
    
    # Load the request data
    with open("sample_request.json", "r") as f:
        request_data = json.load(f)
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        print("Sending assessment request...")
        response = requests.post(
            f"{BASE_URL}/api/assessment", 
            headers=headers,
            json=request_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Assessment completed!")
            print(f"Overall Score: {result.get('scores', {}).get('overall_score', 'N/A')}/10")
            print(f"Status: {result.get('status')}")
            print(f"Executive Summary Length: {len(result.get('executive_summary', ''))}")
        else:
            print(f"❌ Assessment failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Assessment request failed: {e}")

def main():
    """Run all tests"""
    print("Testing Exit Ready Snapshot API Authentication")
    print("=" * 50)
    
    # Check if API is running
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except:
        print("❌ API is not running! Start it with: python api.py")
        return
    
    test_health()
    test_debug_auth()
    test_header_variants()
    test_full_assessment()
    
    print("\n" + "=" * 50)
    print("Check the API console for DEBUG output")

if __name__ == "__main__":
    main()