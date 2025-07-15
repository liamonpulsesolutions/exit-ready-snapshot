"""
Research node for LangGraph workflow.
Handles industry research using Perplexity API.
Uses pure functions and prompts from core modules.
"""

import logging
import json
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional

from workflow.core.prompts import get_prompt, get_industry_context

logger = logging.getLogger(__name__)


class PerplexityResearcher:
    """Handle direct Perplexity API calls for focused research"""
    
    def __init__(self):
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        self.api_base = "https://api.perplexity.ai"
        self.has_key = bool(self.api_key)
        
    def search(self, query: str) -> Dict[str, Any]:
        """Make a focused search query to Perplexity"""
        if not self.api_key:
            logger.warning("No Perplexity API key - using fallback data")
            return {"status": "no_api_key"}
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
                    "content": query
                }
            ],
            "temperature": 0.2,
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
        except requests.exceptions.Timeout:
            logger.error("Perplexity API timeout")
            return {"status": "timeout"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API error: {str(e)}")
            return {"status": "error", "error": str(e)}


def research_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Research node that gathers industry-specific insights.
    
    This node:
    1. Uses anonymized data from intake
    2. Researches industry trends and benchmarks
    3. Finds exit strategies and valuations
    4. Falls back to default data if API fails
    
    Args:
        state: Current workflow state with intake results
        
    Returns:
        Updated state with research findings
    """
    start_time = datetime.now()
    logger.info(f"=== RESEARCH NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "research"
        state["messages"].append(f"Research started at {start_time.isoformat()}")
        
        # Get business info
        anonymized_data = state.get("anonymized_data", {})
        industry = state.get("industry") or anonymized_data.get("industry", "Professional Services")
        location = state.get("location") or anonymized_data.get("location", "US")
        revenue_range = state.get("revenue_range") or anonymized_data.get("revenue_range", "$1M-$5M")
        
        logger.info(f"Researching: {industry} in {location}, Revenue: {revenue_range}")
        
        # Initialize researcher
        researcher = PerplexityResearcher()
        
        # Get research prompts
        trends_prompt = get_prompt(
            "research", 
            "industry_trends",
            industry=industry,
            location=location,
            revenue_range=revenue_range
        )
        
        benchmarks_prompt = get_prompt(
            "research",
            "exit_benchmarks", 
            industry=industry
        )
        
        # Research industry trends
        logger.info("Researching industry trends...")
        trends_result = researcher.search(trends_prompt)
        
        # Research exit benchmarks
        logger.info("Researching exit benchmarks...")
        benchmarks_result = researcher.search(benchmarks_prompt)
        
        # Process results
        research_data = {
            "industry": industry,
            "location": location,
            "revenue_range": revenue_range,
            "timestamp": datetime.now().isoformat()
        }
        
        # Check if we got real data or need fallback
        if trends_result.get("status") in ["no_api_key", "timeout", "error"]:
            logger.warning("Using fallback research data")
            research_data["data_source"] = "fallback"
            research_data["valuation_benchmarks"] = get_fallback_benchmarks(industry)
            research_data["improvement_strategies"] = get_fallback_strategies()
            research_data["market_conditions"] = get_fallback_conditions()
        else:
            # Extract content from Perplexity response
            research_data["data_source"] = "live"
            content = extract_perplexity_content(trends_result)
            research_data["raw_trends"] = content
            
            # Parse structured data from content
            parsed_data = parse_research_content(content)
            research_data.update(parsed_data)
        
        # Add industry-specific context from prompts module
        research_data["industry_context"] = get_industry_context(industry)
        
        # Update state
        state["research_result"] = research_data
        
        # Add processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        state["processing_time"]["research"] = processing_time
        
        # Add status message
        state["messages"].append(
            f"Research completed in {processing_time:.2f}s - "
            f"Data source: {research_data['data_source']}"
        )
        
        logger.info(f"=== RESEARCH NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in research node: {str(e)}", exc_info=True)
        state["error"] = f"Research failed: {str(e)}"
        state["messages"].append(f"ERROR in research: {str(e)}")
        state["current_stage"] = "research_error"
        return state


def extract_perplexity_content(response: Dict[str, Any]) -> str:
    """Extract content from Perplexity API response"""
    try:
        return response.get('choices', [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        logger.error(f"Failed to extract Perplexity content: {e}")
        return ""


def parse_research_content(content: str) -> Dict[str, Any]:
    """Parse structured data from research content"""
    parsed = {
        "valuation_benchmarks": {},
        "improvement_strategies": {},
        "market_conditions": {}
    }
    
    # Parse valuation benchmarks
    if "EBITDA multiples:" in content:
        ebitda_text = content.split("EBITDA multiples:")[1].split("\n")[0].strip()
        parsed["valuation_benchmarks"]["base_EBITDA"] = ebitda_text
    
    if "Revenue multiples:" in content:
        revenue_text = content.split("Revenue multiples:")[1].split("\n")[0].strip()
        parsed["valuation_benchmarks"]["base_revenue"] = revenue_text
    
    # Parse market conditions
    if "Average sale time:" in content:
        sale_time = content.split("Average sale time:")[1].split("\n")[0].strip()
        parsed["market_conditions"]["average_sale_time"] = sale_time
    
    return parsed


def get_fallback_benchmarks(industry: str) -> Dict[str, Any]:
    """Get fallback benchmark data"""
    return {
        "base_EBITDA": "4-6x",
        "base_revenue": "1.2-2.0x",
        "recurring_threshold": "60%",
        "recurring_premium": "1-2x additional",
        "owner_dependence_impact": "20-30% discount if high",
        "concentration_threshold": "30%",
        "concentration_impact": "20-30% discount"
    }


def get_fallback_strategies() -> Dict[str, Any]:
    """Get fallback improvement strategies"""
    return {
        "owner_dependence": {
            "strategy": "Delegate key decisions and client relationships",
            "timeline": "6 months",
            "value_impact": "15-20%"
        },
        "operations": {
            "strategy": "Document processes and implement systems",
            "timeline": "3 months",
            "value_impact": "10-15%"
        },
        "revenue_quality": {
            "strategy": "Convert to contracts and diversify",
            "timeline": "12 months",
            "value_impact": "20-30%"
        }
    }


def get_fallback_conditions() -> Dict[str, Any]:
    """Get fallback market conditions"""
    return {
        "buyer_priorities": ["Recurring revenue", "Systematic operations", "Growth potential"],
        "average_sale_time": "9-12 months",
        "key_trend": "Technology integration increasingly valued"
    }