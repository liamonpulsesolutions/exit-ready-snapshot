from crewai import Agent
from crewai.tools import tool
from typing import Dict, Any
import logging
import json
import os
import requests
from ..utils.json_helper import safe_parse_json

logger = logging.getLogger(__name__)

class PerplexityResearcher:
    """Handle direct Perplexity API calls for focused research"""
    
    def __init__(self):
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        self.api_base = "https://api.perplexity.ai"
        logger.info(f"Perplexity API Key loaded: {'Yes' if self.api_key else 'No'}")
        if self.api_key:
            logger.info(f"Key starts with: {self.api_key[:10]}...")
        
    def search(self, query: str) -> Dict[str, Any]:
        """Make a focused search query to Perplexity"""
        if not self.api_key:
            logger.warning("No Perplexity API key - returning mock data")
            return {"error": "No API key configured"}
            
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
                json=payload,
                timeout=30
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
def research_industry_trends(query) -> str:
    """
    Research current trends and challenges for a specific industry and location.
    Returns raw research data from Perplexity.
    """
    logger.info(f"=== RESEARCH TOOL CALLED ===")
    logger.info(f"Input type: {type(query)}")
    logger.info(f"Input value preview: {str(query)[:200]}...")
    
    # Handle any input format from CrewAI
    if isinstance(query, dict):
        # CrewAI passes a complex nested dict
        if 'description' in query:
            actual_query = query['description']
        elif 'query' in query:
            actual_query = query['query']
        else:
            # Extract from nested structure
            actual_query = json.dumps(query)
        logger.info(f"Extracted from dict: {actual_query[:100]}...")
    elif isinstance(query, str):
        actual_query = query
    else:
        actual_query = str(query)
    
    # Parse industry info from the query text - use defaults if not found
    industry = "Professional Services"  # Default
    location = "US"  # Default
    revenue_range = "$1M-$5M"  # Default
    
    # Try to extract from the actual query text
    if actual_query and isinstance(actual_query, str):
        if "professional services" in actual_query.lower():
            industry = "Professional Services"
        elif "manufacturing" in actual_query.lower():
            industry = "Manufacturing"
        elif "retail" in actual_query.lower():
            industry = "Retail"
        
        # Extract location if mentioned
        if "pacific" in actual_query.lower() or "western us" in actual_query.lower():
            location = "Pacific/Western US"
        elif "uk" in actual_query.lower() or "united kingdom" in actual_query.lower():
            location = "UK"
    
    logger.info(f"Using industry: {industry}, location: {location}, revenue: {revenue_range}")
    
    # Create structured research query for Perplexity
    research_query = f"""
    For small to medium {industry} businesses in {location} (revenue {revenue_range}) planning to exit in 2025:

    VALUATION BENCHMARKS (150 words max):
    1. Current revenue and EBITDA multiples for businesses this size
    2. Multiple variations for:
       - Recurring revenue threshold that creates premium (e.g., 60%+) and premium amount
       - High owner dependence vs distributed leadership - quantify discount/premium
       - Client concentration threshold affecting valuation (e.g., 30%+) and impact
    3. Top 2 factors causing valuation discounts

    IMPROVEMENT STRATEGIES (200 words max):
    3 proven improvement examples:
    1. Reducing owner dependence (with timeline)
    2. Systematizing operations (with timeline)  
    3. Improving revenue quality (with timeline)
    Include measurable impact on valuation where available.

    MARKET CONDITIONS (100 words max):
    1. Current buyer priorities for businesses this size in 2025
    2. Average time to sell
    3. Most important trend affecting valuations

    Requirements:
    - Total response under 500 words
    - Focus on SME businesses in the {revenue_range} range specifically
    - Cite source name and year inline (e.g., "per IBISWorld 2025")
    - Prioritize data from: M&A databases, broker associations, industry reports
    """
    
    logger.info(f"Calling Perplexity with structured query...")
    
    # Get research from Perplexity
    result = perplexity.search(research_query)
    logger.info(f"Perplexity result type: {type(result)}")
    
    if "error" in result:
        logger.error(f"Perplexity error: {result}")
        # Return mock data as fallback
        return json.dumps({
            "source": "mock",
            "raw_content": f"Mock research data for {industry} in {location}. EBITDA multiples: 4-6x. Revenue multiples: 1.2-2.0x. Recurring revenue threshold: 60% creates 1-2x premium. Owner dependence over 30 days acceptable. Client concentration over 30% reduces value by 20-30%. Key improvements: delegate operations (6 months, 15% value increase), document processes (3 months, 10% increase), diversify revenue (12 months, 20% increase). Buyers prioritize: recurring revenue, systematic operations, growth potential. Average sale time: 9-12 months. Trend: Buyers increasingly value technology integration and remote capabilities.",
            "query": research_query,
            "industry": industry,
            "location": location,
            "revenue_range": revenue_range,
            "error": str(result.get('error'))
        })
    
    # Extract content from Perplexity response
    try:
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        logger.info(f"Extracted content length: {len(content)}")
    except Exception as e:
        logger.error(f"Failed to extract content: {e}")
        content = str(result)
    
    # Return structured response
    output = {
        "source": "perplexity",
        "raw_content": content,
        "query": research_query,
        "industry": industry,
        "location": location,
        "revenue_range": revenue_range
    }
    
    logger.info(f"=== RETURNING FROM RESEARCH TOOL ===")
    return json.dumps(output)

@tool("find_exit_benchmarks")
def find_exit_benchmarks(industry: str) -> str:
    """
    Find typical valuation multiples and exit statistics for the industry.
    Returns raw benchmark data from Perplexity.
    """
    # Use safe parsing in case industry comes as JSON
    if isinstance(industry, str) and industry.startswith('{'):
        industry_data = safe_parse_json(industry, {"industry": "Professional Services"}, "find_exit_benchmarks")
        industry = industry_data.get('industry', 'Professional Services')
    
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
            "raw_content": f"Mock benchmark data for {industry}: Revenue multiples 1.2-2.0x, EBITDA multiples 4-6x, average sale time 9-12 months, success rate 60-70%",
            "industry": industry
        })
    
    try:
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
    except:
        content = str(result)
    
    return json.dumps({
        "source": "perplexity",
        "raw_content": content,
        "industry": industry
    })

@tool("format_research_output")
def format_research_output(raw_research: str) -> str:
    """
    Format raw Perplexity research into structured data for other agents.
    """
    try:
        data = safe_parse_json(raw_research, {}, "format_research_output")
        if not data:
            return json.dumps({"error": "No research data to format"})
            
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
            "perplexity_content": perplexity_content,
            "industry": data.get('industry', ''),
            "location": data.get('location', '')
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
    You always use the format_research_output tool to structure your findings.
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