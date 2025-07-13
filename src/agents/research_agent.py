from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, Type
import logging
import json
import os
import requests
from ..utils.json_helper import safe_parse_json
from ..utils.tool_input_validator import validate_and_extract_tool_input

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
                timeout=45  # Increased timeout for reliability
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Perplexity API timeout - using fallback data")
            return {"error": "API timeout - using fallback research data"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return {"error": str(e)}

# Initialize researcher
perplexity = PerplexityResearcher()

# Tool Input Schemas
class ResearchIndustryTrendsInput(BaseModel):
    query: str = Field(
        default="{}",
        description="JSON string containing industry, location, and revenue_range, or simple string industry name"
    )

class FindExitBenchmarksInput(BaseModel):
    industry: str = Field(
        default="Professional Services",
        description="Industry name or JSON string containing industry info"
    )

class FormatResearchOutputInput(BaseModel):
    raw_research: str = Field(
        default="{}",
        description="JSON string containing raw research data from Perplexity"
    )

# Tool Classes
class ResearchIndustryTrendsTool(BaseTool):
    name: str = "research_industry_trends"
    description: str = """
    Research current trends and challenges for a specific industry and location.
    Returns formatted research findings that agents can understand and use.
    
    Input should be JSON string containing industry, location, and revenue_range:
    {"industry": "Professional Services", "location": "US", "revenue_range": "$1M-$5M"}
    
    Or simple string input: "Professional Services"
    
    Returns formatted text with research findings organized by section.
    """
    args_schema: Type[BaseModel] = ResearchIndustryTrendsInput
    
    def _run(self, query: str = "{}", **kwargs) -> str:
        logger.info(f"=== RESEARCH TOOL CALLED ===")
        logger.info(f"Input type: {type(query)}")
        
        # Enhanced input validation
        try:
            # Use the new validator for robust input handling
            validated_input = validate_and_extract_tool_input(
                query, 
                expected_keys=['industry', 'location', 'revenue_range'],
                tool_name="research_industry_trends",
                default_return={'industry': 'Professional Services', 'location': 'US', 'revenue_range': '$1M-$5M'}
            )
            
            industry = validated_input.get('industry', 'Professional Services')
            location = validated_input.get('location', 'US')
            revenue_range = validated_input.get('revenue_range', '$1M-$5M')
            
        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            # Fallback to defaults
            industry = "Professional Services"
            location = "US"
            revenue_range = "$1M-$5M"
        
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
            # Return formatted fallback text that agent can understand
            return f"""Industry Research for {industry} in {location} ({revenue_range}):

VALUATION BENCHMARKS:
- EBITDA multiples: 4-6x for well-run businesses
- Revenue multiples: 1.2-2.0x depending on recurring revenue
- Recurring revenue threshold: 60%+ creates 1-2x EBITDA premium
- Owner dependence: Over 30 days away reduces value by 20-30%
- Client concentration: Over 30% from one client reduces value by 20-30%
- Top discount factors: Owner dependence and customer concentration

IMPROVEMENT STRATEGIES:
1. Reducing owner dependence: Delegate key decisions and client relationships over 6 months. Impact: 15-20% value increase
2. Systematizing operations: Document all processes and implement management systems over 3 months. Impact: 10-15% value increase
3. Improving revenue quality: Convert to contracts and diversify client base over 12 months. Impact: 20-30% value increase

MARKET CONDITIONS:
- Buyers prioritize: Recurring revenue, systematic operations, growth potential
- Average sale time: 9-12 months for prepared businesses
- Key trend: Technology integration and remote capabilities increasingly valued

Note: Research data unavailable - using industry standard benchmarks."""
        
        # Extract content from Perplexity response
        try:
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            logger.info(f"Extracted content length: {len(content)}")
        except Exception as e:
            logger.error(f"Failed to extract content: {e}")
            content = "Research extraction failed"
        
        # CRITICAL: Return formatted TEXT that agent can parse naturally
        return f"""Industry Research for {industry} in {location} ({revenue_range}):

{content}

Research Details:
- Industry: {industry}
- Location: {location}
- Revenue Range: {revenue_range}
- Source: Perplexity AI Research

Instructions for analysis: Extract specific benchmarks, improvement strategies, and market conditions from the research above."""

class FindExitBenchmarksTool(BaseTool):
    name: str = "find_exit_benchmarks"
    description: str = """
    Find typical valuation multiples and exit statistics for the industry.
    Returns formatted benchmark data that agents can understand.
    
    Input: Industry name or JSON string containing industry info
    Example: "Professional Services" or {"industry": "Professional Services"}
    
    Returns formatted text with benchmark findings.
    """
    args_schema: Type[BaseModel] = FindExitBenchmarksInput
    
    def _run(self, industry: str = "Professional Services", **kwargs) -> str:
        logger.info(f"=== FIND EXIT BENCHMARKS CALLED ===")
        logger.info(f"Input type: {type(industry)}")
        logger.info(f"Input value: {str(industry)[:100]}...")
        
        # Handle case where no industry is provided or empty data
        if not industry or industry == "{}" or industry == "":
            industry = "Professional Services"
        
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
            return f"""Exit Benchmarks for {industry}:

VALUATION MULTIPLES:
- Revenue multiples: 1.2-2.0x (varies by recurring revenue percentage)
- EBITDA multiples: 4-6x for average businesses, 6-8x for top performers
- SDE multiples: 2.5-4x for smaller businesses under $2M revenue

SALE STATISTICS:
- Average time to sell: 9-12 months from listing to close
- Success rate: 60-70% of listed businesses sell
- Preparation time: 6-12 months recommended before listing

KEY VALUE DRIVERS:
- Recurring revenue over 60%: Adds 1-2x to EBITDA multiple
- Owner working less than 20 hours/week: Adds 15-25% to value
- Diversified customer base: Critical for achieving higher multiples

Note: Using industry standard benchmarks as research unavailable."""
        
        try:
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        except:
            content = "Benchmark data extraction failed"
        
        # Return formatted text
        return f"""Exit Benchmarks for {industry}:

{content}

Benchmark Summary:
- Industry analyzed: {industry}
- Focus: Small to medium businesses ($1M-$20M revenue)
- Data relevance: Current market conditions (2025)"""

class FormatResearchOutputTool(BaseTool):
    name: str = "format_research_output"
    description: str = """
    Format raw Perplexity research into structured insights for analysis.
    Helps agents organize research findings into actionable categories.
    
    Input: Text containing raw research findings
    
    Returns structured text with clear sections and instructions for data extraction.
    """
    args_schema: Type[BaseModel] = FormatResearchOutputInput
    
    def _run(self, raw_research: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== FORMAT RESEARCH OUTPUT CALLED ===")
            logger.info(f"Input type: {type(raw_research)}")
            logger.info(f"Input preview: {str(raw_research)[:200] if raw_research else 'No data provided'}...")
            
            # Handle empty input
            if not raw_research or raw_research == "{}" or raw_research == "":
                return """No research data provided to format.

Please provide research findings to structure into:
- VALUATION BENCHMARKS
- IMPROVEMENT STRATEGIES  
- MARKET CONDITIONS"""
            
            # If input is already formatted text, help structure it
            if isinstance(raw_research, str) and not raw_research.startswith('{'):
                research_text = raw_research
            else:
                # Try to parse JSON input
                data = safe_parse_json(raw_research, {}, "format_research_output")
                research_text = data.get('raw_content', '') or data.get('content', '') or str(data)
            
            # Return structured guidance for the agent
            return f"""Research Analysis Framework:

ORIGINAL RESEARCH:
{research_text}

EXTRACTION INSTRUCTIONS:

1. VALUATION BENCHMARKS (Extract these specific data points):
   - Base EBITDA multiple range (e.g., "4-6x")
   - Base revenue multiple range (e.g., "1.2-2.0x")
   - Recurring revenue threshold for premium (e.g., "60%")
   - Size of recurring revenue premium (e.g., "1-2x additional")
   - Owner dependence threshold (e.g., "14 days")
   - Owner dependence discount (e.g., "20-30%")
   - Client concentration threshold (e.g., "30%")
   - Client concentration discount (e.g., "20-30%")

2. IMPROVEMENT STRATEGIES (Extract for each category):
   Owner Dependence Improvements:
   - Specific action and timeline
   - Expected value impact percentage
   
   Revenue Quality Improvements:
   - Specific action and timeline
   - Expected value impact percentage
   
   Operational Improvements:
   - Specific action and timeline
   - Expected value impact percentage

3. MARKET CONDITIONS (Extract these elements):
   - Top 3 buyer priorities in order
   - Average sale timeline in months
   - Current market trend and its impact

Analyze the research above and extract specific numbers, percentages, and timelines for each category."""
            
        except Exception as e:
            logger.error(f"Error formatting research output: {str(e)}")
            return f"""Error formatting research: {str(e)}

Please manually extract:
- Valuation benchmarks
- Improvement strategies
- Market conditions"""

# Create tool instances
research_industry_trends = ResearchIndustryTrendsTool()
find_exit_benchmarks = FindExitBenchmarksTool()
format_research_output = FormatResearchOutputTool()

def create_research_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the research agent for industry analysis"""
    
    # Get agent configuration from prompts
    config = prompts.get('research_agent', {})
    
    # Update the backstory to include formatting responsibility
    enhanced_backstory = config.get('backstory', '') + """
    
    You excel at taking raw research data and structuring it into actionable insights.
    When you receive research findings, you parse and extract specific data points,
    organizing them into clear categories: benchmarks, strategies, and conditions.
    You always focus on extracting concrete numbers, percentages, and timelines.
    """
    
    # Create tools list using instances
    tools = [
        research_industry_trends,
        find_exit_benchmarks,
        format_research_output
    ]
    
    return Agent(
        role=config.get('role'),
        goal=config.get('goal') + " Extract specific data points from research.",
        backstory=enhanced_backstory,
        tools=tools,
        llm=llm,  # This will use GPT-4.1 mini for formatting
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )