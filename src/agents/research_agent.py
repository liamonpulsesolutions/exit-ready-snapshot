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
        print(f"Perplexity API Key loaded: {'Yes' if self.api_key else 'No'}")  # Add this
        if self.api_key:
            print(f"Key starts with: {self.api_key[:10]}...")  # Add this
        
    def search(self, query: str) -> Dict[str, Any]:
        """Make a focused search query to Perplexity"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Structured query for consistent results
        payload = {
            "model": "sonar",
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
        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return {"error": str(e)}

# Initialize researcher
perplexity = PerplexityResearcher()

@tool("research_industry_trends")
def research_industry_trends(query: str) -> str:
    """
    Research current trends and challenges for a specific industry and location.
    Returns raw research data from Perplexity.
    """
    logger.info(f"=== RESEARCH TOOL CALLED ===")
    logger.info(f"Input type: {type(query)}")
    logger.info(f"Input value: {query}")
    
    # Parse the query to extract industry and location
    try:
        query_data = json.loads(query) if isinstance(query, str) else query
        industry = query_data.get('industry', 'business')
        location = query_data.get('location', 'US')
        logger.info(f"Parsed - Industry: {industry}, Location: {location}")
    except Exception as e:
        logger.error(f"Failed to parse query: {e}")
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
    
    logger.info(f"Calling Perplexity with query: {research_query[:100]}...")
    
    # Get raw research from Perplexity
    result = perplexity.search(research_query)
    logger.info(f"Perplexity result type: {type(result)}")
    logger.info(f"Perplexity result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
    
    if "error" in result:
        logger.error(f"Perplexity error: {result}")
        # Return mock data as fallback
        return json.dumps({
            "source": "mock",
            "raw_content": "API unavailable - using cached data",
            "query": research_query,
            "error": str(result.get('error'))
        })
    
    # Extract the content
    try:
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        logger.info(f"Extracted content length: {len(content)}")
    except Exception as e:
        logger.error(f"Failed to extract content: {e}")
        content = str(result)
    
    # Return raw Perplexity response
    output = {
        "source": "perplexity",
        "raw_content": content,
        "query": research_query
    }
    
    logger.info(f"=== RETURNING FROM RESEARCH TOOL ===")
    return json.dumps(output)

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

# Add this tool to src/agents/research_agent.py after the existing tools:

@tool("format_research_output")
def format_research_output(raw_research: str) -> str:
    """
    Format raw Perplexity research into structured data for other agents.
    """
    try:
        data = json.loads(raw_research)
        perplexity_content = data.get('raw_content', '')
        
        # This tool helps the agent structure the output
        # The actual parsing will be done by the agent's LLM
        
        output_structure = {
            "valuation_benchmarks": {
                "base_EBITDA": "",  # e.g., "4-6x"
                "base_revenue": "",  # e.g., "1.2-2.0x"
                "recurring_threshold": "",  # e.g., "60%"
                "recurring_premium": "",  # e.g., "1-2x EBITDA"
                "owner_dependence_threshold": "",  # e.g., "14 days"
                "owner_dependence_discount": "",  # e.g., "20-30%"
                "concentration_threshold": "",  # e.g., "30%"
                "concentration_discount": ""  # e.g., "20-30%"
            },
            "improvements": {
                "owner_dependence": {
                    "example": "",
                    "timeline_months": 0,
                    "value_impact": 0.0  # as decimal, e.g., 0.15 for 15%
                },
                "revenue_quality": {
                    "example": "",
                    "timeline_months": 0,
                    "value_impact": 0.0
                },
                "financial_readiness": {
                    "example": "",
                    "timeline_months": 0,
                    "value_impact": 0.0
                },
                "operational_resilience": {
                    "example": "",
                    "timeline_months": 0,
                    "value_impact": 0.0
                },
                "growth_value": {
                    "example": "",
                    "timeline_months": 0,
                    "value_impact": 0.0
                }
            },
            "market_conditions": {
                "buyer_priorities": [],  # List of top 3 priorities
                "average_sale_time": "",  # e.g., "9-12 months"
                "key_trend": "",  # Main trend affecting valuations
                "market_timing": ""  # e.g., "Seller's market" or "Buyer's market"
            },
            "sources": []  # List of sources cited
        }
        
        # Return template for agent to fill
        return json.dumps({
            "template": output_structure,
            "instructions": "Parse the Perplexity response and fill this structure with specific data",
            "perplexity_content": perplexity_content
        })
        
    except Exception as e:
        logger.error(f"Error formatting research output: {str(e)}")
        return json.dumps({"error": str(e)})

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
