from crewai import Agent
from crewai.tools import tool
from typing import Dict, Any
import logging
import json
import os
import requests

logger = logging.getLogger(__name__)

class PerplexityResearcher:
    """Handle direct Perplexity API calls for focused research"""
    
    def __init__(self):
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        self.api_base = "https://api.perplexity.ai"
        
    def search(self, query: str) -> Dict[str, Any]:
        """Make a focused search query to Perplexity"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Structured query for consistent results
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a business research assistant. Provide concise, factual information with sources."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.2,  # Lower temp for more consistent results
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Perplexity API error: {str(e)}")
            return {"error": str(e)}

# Initialize researcher
perplexity = PerplexityResearcher()

@tool("research_industry_trends")
def research_industry_trends(query: str) -> str:
    """
    Research current trends and challenges for a specific industry and location.
    Returns raw research data from Perplexity.
    """
    # Parse the query to extract industry and location
    try:
        query_data = json.loads(query) if isinstance(query, str) else query
        industry = query_data.get('industry', 'business')
        location = query_data.get('location', 'US')
    except:
        industry = "business"
        location = "US"
    
    # Structured research query for Perplexity
    research_query = f"""
    For {industry} businesses in {location}, provide:
    1. Three current market trends (2024-2025)
    2. Three main challenges for business owners
    3. Three opportunities for growth or exit
    
    Be specific and include data points where available.
    Focus on factors affecting business valuation and sale readiness.
    """
    
    # Get raw research from Perplexity
    result = perplexity.search(research_query)
    
    if "error" in result:
        # Fallback to mock data if API fails
        logger.warning("Using mock data due to API error")
        return json.dumps({
            "source": "mock",
            "raw_content": "API unavailable - using cached data",
            "query": research_query
        })
    
    # Return raw Perplexity response
    return json.dumps({
        "source": "perplexity",
        "raw_content": result.get('choices', [{}])[0].get('message', {}).get('content', ''),
        "query": research_query
    })

@tool("find_exit_benchmarks")
def find_exit_benchmarks(industry: str) -> str:
    """
    Find typical valuation multiples and exit statistics for the industry.
    Returns raw benchmark data from Perplexity.
    """
    # Structured benchmark query
    benchmark_query = f"""
    For {industry} businesses:
    1. Typical revenue multiples for business sales
    2. Typical EBITDA multiples
    3. Average time to sell a business
    4. Success rate of business sales
    
    Provide specific ranges and cite sources where possible.
    Focus on small to medium businesses ($1M-$20M revenue).
    """
    
    # Get raw research from Perplexity
    result = perplexity.search(benchmark_query)
    
    if "error" in result:
        logger.warning("Using mock benchmarks due to API error")
        return json.dumps({
            "source": "mock",
            "raw_content": "API unavailable - using industry averages"
        })
    
    return json.dumps({
        "source": "perplexity",
        "raw_content": result.get('choices', [{}])[0].get('message', {}).get('content', ''),
        "industry": industry
    })

@tool("format_research_output")
def format_research_output(raw_research: str) -> str:
    """
    Takes raw Perplexity research and formats it into structured output.
    This tool uses the LLM to parse and structure the research data.
    """
    # This will be handled by the agent's LLM to format the raw data
    # into the expected structure
    return raw_research

def create_research_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the research agent for industry analysis"""
    
    # Get agent configuration from prompts
    config = prompts.get('research_agent', {})
    
    # Update the backstory to include formatting responsibility
    enhanced_backstory = config.get('backstory', '') + """
    
    You excel at taking raw research data and structuring it into actionable insights.
    When you receive raw research from Perplexity, you parse and format it into 
    clear categories: trends, challenges, opportunities, and benchmarks.
    """
    
    # Create tools list
    tools = [
        research_industry_trends,
        find_exit_benchmarks,
        format_research_output
    ]
    
    return Agent(
        role=config.get('role'),
        goal=config.get('goal') + " Format raw research into structured insights.",
        backstory=enhanced_backstory,
        tools=tools,
        llm=llm,  # This will use GPT-4.1 for formatting
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )