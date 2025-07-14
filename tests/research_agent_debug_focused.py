#!/usr/bin/env python
"""
Focused research agent debug - isolate Perplexity API issues
"""

import os
import json
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

# Setup focused logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_perplexity_direct():
    """Test Perplexity API directly with detailed logging"""
    
    api_key = os.getenv('PERPLEXITY_API_KEY')
    print(f"=== PERPLEXITY API DEBUG ===")
    print(f"API Key Present: {'Yes' if api_key else 'No'}")
    
    if not api_key:
        print("❌ No PERPLEXITY_API_KEY found in environment")
        return False
    
    print(f"API Key starts with: {api_key[:15]}...")
    print(f"API Key length: {len(api_key)}")
    
    # Test the exact API call that research agent makes
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system", 
                "content": "You are a business research assistant. Provide concise, factual information with sources."
            },
            {
                "role": "user",
                "content": "For Professional Services businesses in US ($1M-$5M revenue): What are current EBITDA multiples and key success factors?"
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1000
    }
    
    print(f"\n📡 Making API call to: https://api.perplexity.ai/chat/completions")
    print(f"📄 Payload size: {len(json.dumps(payload))} bytes")
    
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"✅ Response received!")
        print(f"📊 Status Code: {response.status_code}")
        print(f"📏 Response size: {len(response.text)} bytes")
        print(f"⏱️ Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"✅ JSON parsed successfully")
                print(f"📝 Content length: {len(content)} chars")
                print(f"🔍 Content preview: {content[:200]}...")
                return True
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                print(f"📄 Raw response: {response.text[:500]}...")
                return False
        else:
            print(f"❌ API Error {response.status_code}")
            print(f"📄 Error response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ API Timeout after 30 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

def test_research_tool_direct():
    """Test the research tool directly as CrewAI would call it"""
    
    print(f"\n=== RESEARCH TOOL DIRECT TEST ===")
    
    try:
        from src.agents.research_agent import research_industry_trends
        
        # Test with simple string input (as CrewAI might pass)
        test_inputs = [
            "Professional Services",
            '{"industry": "Professional Services", "location": "US", "revenue_range": "$1M-$5M"}',
            "",  # Empty input
            "{}",  # Empty JSON
        ]
        
        for i, test_input in enumerate(test_inputs, 1):
            print(f"\n--- Test {i}: {repr(test_input)} ---")
            try:
                result = research_industry_trends.run(test_input)
                print(f"✅ Tool succeeded")
                print(f"📊 Result type: {type(result)}")
                print(f"📏 Result length: {len(str(result))}")
                
                # Try to parse result
                try:
                    parsed = json.loads(result)
                    print(f"✅ Result is valid JSON")
                    print(f"🔑 Keys: {list(parsed.keys())}")
                    if 'error' in parsed:
                        print(f"⚠️ Error in result: {parsed['error']}")
                    if 'raw_content' in parsed:
                        content_len = len(parsed['raw_content'])
                        print(f"📝 Content length: {content_len}")
                        if content_len > 0:
                            print(f"🔍 Content preview: {parsed['raw_content'][:100]}...")
                except json.JSONDecodeError:
                    print(f"❌ Result is not valid JSON")
                    print(f"📄 Raw result: {str(result)[:200]}...")
                    
            except Exception as e:
                print(f"❌ Tool failed: {e}")
                import traceback
                traceback.print_exc()
    
    except ImportError as e:
        print(f"❌ Cannot import research tool: {e}")
        return False

def test_environment_variables():
    """Check all required environment variables"""
    
    print(f"\n=== ENVIRONMENT VARIABLES ===")
    
    required_vars = [
        'OPENAI_API_KEY',
        'PERPLEXITY_API_KEY', 
        'CREWAI_API_KEY'
    ]
    
    all_present = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Present ({len(value)} chars)")
        else:
            print(f"❌ {var}: Missing")
            all_present = False
    
    return all_present

def main():
    """Run comprehensive research agent debugging"""
    
    print("🔍 RESEARCH AGENT COMPREHENSIVE DEBUG")
    print("=" * 50)
    
    # Test 1: Environment variables
    env_ok = test_environment_variables()
    
    # Test 2: Direct Perplexity API
    if env_ok:
        api_ok = test_perplexity_direct()
    else:
        print("⏭️ Skipping API test due to missing environment variables")
        api_ok = False
    
    # Test 3: Research tool direct
    test_research_tool_direct()
    
    print(f"\n" + "=" * 50)
    print(f"🏁 DEBUG SUMMARY")
    print(f"Environment: {'✅ OK' if env_ok else '❌ Issues'}")
    print(f"Perplexity API: {'✅ OK' if api_ok else '❌ Issues'}")
    print("=" * 50)
    
    if not api_ok:
        print("\n🔧 NEXT STEPS:")
        print("1. Verify PERPLEXITY_API_KEY is correct")
        print("2. Check Perplexity API status/rate limits")
        print("3. Test with curl manually")
        print("4. Consider network/firewall issues")

if __name__ == "__main__":
    main()