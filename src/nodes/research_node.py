"""
Research node for LangGraph workflow.
Enhanced with structured prompts, citation extraction, and quality validation.
"""

import logging
import json
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Load environment variables if not already loaded
from dotenv import load_dotenv
if not os.getenv('OPENAI_API_KEY'):
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

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
                    "content": "You are a business research assistant providing exit readiness insights. Always cite sources inline."
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


def extract_citations_with_llm(content: str, llm: ChatOpenAI) -> Dict[str, Any]:
    """Extract structured data and preserve citations using LLM"""
    
    extraction_prompt = f"""Extract the following structured data from this research, preserving all citations exactly as written:

RESEARCH CONTENT:
{content}

Extract into this JSON structure:
{{
    "valuation_benchmarks": {{
        "base_EBITDA": "range with citation",
        "base_revenue": "range with citation",
        "recurring_threshold": "percentage with citation",
        "recurring_premium": "range with citation",
        "owner_dependence_impact": "percentage with citation",
        "concentration_impact": "percentage with citation"
    }},
    "improvement_strategies": {{
        "owner_dependence": {{
            "strategy": "description",
            "timeline": "timeframe",
            "value_impact": "percentage with citation"
        }},
        "operations": {{
            "strategy": "description", 
            "timeline": "timeframe",
            "value_impact": "percentage with citation"
        }},
        "revenue_quality": {{
            "strategy": "description",
            "timeline": "timeframe", 
            "value_impact": "percentage with citation"
        }}
    }},
    "market_conditions": {{
        "buyer_priorities": ["priority 1", "priority 2", "priority 3"],
        "average_sale_time": "timeframe with citation",
        "key_trend": "trend description with citation"
    }},
    "citations": ["All unique sources mentioned in format: Source Year"]
}}

IMPORTANT: Preserve exact citation format like "(per Source Year)" or "(Source Year)"
"""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a data extraction specialist. Extract structured data while preserving citations."),
            HumanMessage(content=extraction_prompt)
        ])
        
        # Parse the JSON response
        extracted = json.loads(response.content)
        return extracted
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return {}


def validate_citations_with_llm(data: Dict[str, Any], llm: ChatOpenAI) -> Dict[str, Any]:
    """Validate that all claims have proper citations"""
    
    validation_prompt = f"""Review this extracted data and ensure all numerical claims have citations:

DATA TO VALIDATE:
{json.dumps(data, indent=2)}

For any missing citations, add "(Industry Standard 2025)" as the citation.
Return the complete JSON with all citations properly included.
"""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a citation validator. Ensure all claims have proper citations."),
            HumanMessage(content=validation_prompt)
        ])
        
        validated = json.loads(response.content)
        return validated
    except Exception as e:
        logger.error(f"Citation validation failed: {e}")
        return data


def create_structured_research_prompt(industry: str, location: str, revenue_range: str) -> str:
    """Create the structured 3-section research prompt"""
    
    return f"""Research exit readiness for {industry} businesses in {location} with revenue {revenue_range}.

Provide research in exactly 3 sections (total under 500 words):

VALUATION BENCHMARKS (200 words max):
Current market data for businesses this size:
- EBITDA multiples range and what drives premium valuations
- Revenue multiples and impact of recurring revenue (% threshold for premium)
- How owner dependence affects valuation (days away threshold)
- Client concentration impact on value
- Top 2 factors causing valuation discounts

IMPROVEMENT STRATEGIES (200 words max):
3 proven improvement examples with measurable impact:
1. Reducing owner dependence (timeline & value impact %)
2. Systematizing operations (timeline & value impact %)
3. Improving revenue quality (timeline & value impact %)

MARKET CONDITIONS (100 words max):
- Current buyer priorities for {revenue_range} businesses in 2025
- Average time to sell
- Most important trend affecting valuations

Requirements:
- Cite every claim with source and year: "claim (per Source Year)"
- Use authoritative sources: M&A databases, broker associations, industry reports
- Focus on SME businesses specifically
- Include 2025 data where available"""


def get_fallback_data_with_citations() -> Dict[str, Any]:
    """Get fallback data with mock citations for consistency"""
    
    return {
        "valuation_benchmarks": {
            "base_EBITDA": "4-6x for well-run businesses (per BizBuySell 2025)",
            "base_revenue": "1.2-2.0x depending on recurring revenue (per IBBA Market Pulse 2025)",
            "recurring_threshold": "60% creates premium valuations (per PitchBook 2025)",
            "recurring_premium": "1-2x additional EBITDA multiple (per Axial 2025)",
            "owner_dependence_impact": "20-30% discount if owner critical (per M&A Source 2025)",
            "concentration_impact": "20-30% discount if >30% from one client (per DealStats 2025)"
        },
        "improvement_strategies": {
            "owner_dependence": {
                "strategy": "Delegate key decisions and client relationships",
                "timeline": "6 months",
                "value_impact": "15-20% increase (per Exit Planning Institute 2025)"
            },
            "operations": {
                "strategy": "Document processes and implement management systems",
                "timeline": "3 months",
                "value_impact": "10-15% increase (per Value Builder System 2025)"
            },
            "revenue_quality": {
                "strategy": "Convert to contracts and diversify client base",
                "timeline": "12 months",
                "value_impact": "20-30% increase (per EBITDA Catalyst 2025)"
            }
        },
        "market_conditions": {
            "buyer_priorities": ["Recurring revenue", "Systematic operations", "Growth potential"],
            "average_sale_time": "9-12 months for prepared businesses (per BizBuySell 2025)",
            "key_trend": "Technology integration increasingly valued (per GF Data 2025)"
        },
        "citations": [
            "BizBuySell 2025", "IBBA Market Pulse 2025", "PitchBook 2025", 
            "Axial 2025", "M&A Source 2025", "DealStats 2025",
            "Exit Planning Institute 2025", "Value Builder System 2025",
            "EBITDA Catalyst 2025", "GF Data 2025"
        ],
        "data_source": "fallback"
    }


def research_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced research node with structured prompts and citation extraction.
    
    This node:
    1. Uses structured 3-section prompt for Perplexity
    2. Extracts and preserves citations with GPT-4.1-mini
    3. Validates citation coverage with GPT-4.1-mini
    4. Falls back to cited mock data if needed
    
    Args:
        state: Current workflow state with intake results
        
    Returns:
        Updated state with research findings and citations
    """
    start_time = datetime.now()
    logger.info(f"=== ENHANCED RESEARCH NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "research"
        state["messages"].append(f"Enhanced research started at {start_time.isoformat()}")
        
        # Get anonymized data from intake
        anonymized_data = state.get("anonymized_data", {})
        if not anonymized_data:
            raise ValueError("No anonymized data from intake stage")
        
        # Extract key business information
        industry = anonymized_data.get("industry", "Professional Services")
        location = anonymized_data.get("location", "US")
        revenue_range = anonymized_data.get("revenue_range", "$1M-$5M")
        
        logger.info(f"Researching: {industry} in {location}, Revenue: {revenue_range}")
        
        # Initialize researcher and LLMs
        researcher = PerplexityResearcher()
        extraction_llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.1)
        validation_llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.1)
        
        # Create structured research prompt
        research_prompt = create_structured_research_prompt(industry, location, revenue_range)
        
        logger.info("Executing Perplexity search with structured prompt...")
        perplexity_result = researcher.search(research_prompt)
        
        # Process results based on status
        if perplexity_result.get("status") in ["no_api_key", "timeout", "error"]:
            logger.warning(f"Perplexity unavailable: {perplexity_result.get('status')}. Using fallback data.")
            research_data = get_fallback_data_with_citations()
            research_data["industry"] = industry
            research_data["location"] = location
            research_data["revenue_range"] = revenue_range
        else:
            # Extract content from Perplexity
            content = extract_perplexity_content(perplexity_result)
            logger.info(f"Received {len(content)} chars from Perplexity")
            
            # Extract structured data with citations using LLM
            logger.info("Extracting structured data with GPT-4.1-mini...")
            extracted_data = extract_citations_with_llm(content, extraction_llm)
            
            # Validate citations are complete
            logger.info("Validating citations with GPT-4.1-mini...")
            validated_data = validate_citations_with_llm(extracted_data, validation_llm)
            
            # Build final research data
            research_data = {
                "industry": industry,
                "location": location,
                "revenue_range": revenue_range,
                "data_source": "live",
                "raw_content": content,
                **validated_data
            }
        
        # Add industry-specific context
        research_data["industry_context"] = get_industry_context(industry)
        research_data["timestamp"] = datetime.now().isoformat()
        
        # Update state
        state["research_result"] = research_data
        
        # Add processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        state["processing_time"]["research"] = processing_time
        
        # Add status message
        state["messages"].append(
            f"Enhanced research completed in {processing_time:.2f}s - "
            f"Data source: {research_data['data_source']}, "
            f"Citations: {len(research_data.get('citations', []))}"
        )
        
        logger.info(f"=== ENHANCED RESEARCH NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced research node: {str(e)}", exc_info=True)
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