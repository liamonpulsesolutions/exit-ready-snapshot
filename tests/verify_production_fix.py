#!/usr/bin/env python3
"""
Verify production fixes are working correctly.
Tests the API endpoint and analyzes the response.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000/api/assessment"
API_KEY = "your-api-key-here"  # Replace with your actual API key

# Test data
TEST_DATA = {
    "uuid": f"test-prod-{int(time.time())}",
    "timestamp": datetime.now().isoformat() + "Z",
    "name": "John Smith",
    "email": "john@manufacturingco.com",
    "industry": "Manufacturing & Production",
    "years_in_business": "10-20 years",
    "revenue_range": "$10M-$25M",
    "location": "Northeast US",
    "exit_timeline": "1-2 years",
    "age_range": "55-64",
    "responses": {
        "q1": "I personally oversee all quality control for our largest automotive client. They require my certification on critical components.",
        "q2": "3-7 days",
        "q3": "Automotive parts manufacturing 60%, custom metal fabrication 30%, maintenance contracts 10%",
        "q4": "40-60%",
        "q5": "7",
        "q6": "Stayed flat",
        "q7": "CNC programming and setup - only our lead engineer Tom knows the legacy systems",
        "q8": "6",
        "q9": "ISO 9001 and AS9100 certifications, 30-year reputation with major OEMs",
        "q10": "7"
    }
}

def test_api():
    """Test the API and analyze response"""
    print("🧪 Testing Exit Ready Snapshot API\n")
    print(f"UUID: {TEST_DATA['uuid']}")
    print(f"Industry: {TEST_DATA['industry']}")
    print(f"Timeline: {TEST_DATA['exit_timeline']}\n")
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    print("📡 Sending request...")
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, json=TEST_DATA, headers=headers)
        elapsed = time.time() - start_time
        
        print(f"⏱️  Response time: {elapsed:.1f}s\n")
        
        if response.status_code == 200:
            data = response.json()
            analyze_response(data)
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def analyze_response(data):
    """Analyze the API response for completeness"""
    print("✅ API call successful!\n")
    
    # Check scores
    scores = data.get("scores", {})
    print("📊 SCORES:")
    print(f"   Overall: {scores.get('overall', 'N/A')}/10")
    for cat in ['owner_dependence', 'revenue_quality', 'financial_readiness', 
                'operational_resilience', 'growth_value']:
        score = scores.get(cat, 'N/A')
        print(f"   {cat}: {score}")
    
    # Check content generation
    print("\n📝 CONTENT GENERATION:")
    
    # Executive Summary
    exec_summary = data.get("executive_summary", "")
    word_count = len(exec_summary.split()) if exec_summary else 0
    is_fallback = "Thank you for completing the Exit Ready Snapshot" in exec_summary and word_count < 100
    print(f"   Executive Summary: {word_count} words {'❌ FALLBACK' if is_fallback else '✅'}")
    
    # Category Summaries
    cat_summaries = data.get("category_summaries", {})
    cat_count = len(cat_summaries)
    avg_words = sum(len(s.split()) for s in cat_summaries.values()) / cat_count if cat_count > 0 else 0
    print(f"   Category Summaries: {cat_count}/5 categories, avg {avg_words:.0f} words")
    
    # Recommendations
    recommendations = data.get("recommendations", {})
    if isinstance(recommendations, dict):
        rec_sections = len(recommendations)
        print(f"   Recommendations: {rec_sections} sections ✅")
    else:
        word_count = len(str(recommendations).split())
        print(f"   Recommendations: {word_count} words")
    
    # Next Steps
    next_steps = data.get("next_steps", "")
    word_count = len(next_steps.split()) if next_steps else 0
    print(f"   Next Steps: {word_count} words")
    
    # Processing metadata
    metadata = data.get("metadata", {})
    if metadata:
        print(f"\n⚙️  PROCESSING:")
        print(f"   Stages completed: {len(metadata.get('stages_completed', []))}")
        if 'stage_timings' in metadata:
            print("   Stage timings:")
            for stage, timing in metadata['stage_timings'].items():
                print(f"     - {stage}: {timing:.1f}s")
    
    # Quality checks
    print("\n🔍 QUALITY CHECKS:")
    
    # Check for fallback text indicators
    fallback_indicators = [
        "assessment is being processed",
        "fallback text",
        "Summary not available",
        "Analysis pending"
    ]
    
    full_text = json.dumps(data).lower()
    fallbacks_found = [ind for ind in fallback_indicators if ind in full_text]
    
    if fallbacks_found:
        print(f"   ⚠️  Possible fallback text found: {fallbacks_found}")
    else:
        print("   ✅ No obvious fallback text detected")
    
    # Outcome framing check
    outcome_words = ["typically", "often", "generally", "businesses like yours"]
    outcome_count = sum(1 for word in outcome_words if word in full_text)
    print(f"   ✅ Outcome framing words: {outcome_count} found")
    
    print("\n📋 SUMMARY:")
    if word_count > 150 and cat_count == 5 and not fallbacks_found:
        print("   ✅ Production fix appears successful!")
    else:
        print("   ⚠️  Some content may still be using fallbacks")

if __name__ == "__main__":
    test_api()