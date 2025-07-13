from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Type
import logging
import json
import os
from datetime import datetime
from ..utils.json_helper import safe_parse_json

# ========== DEBUG SETUP ==========
DEBUG_MODE = os.getenv('CREWAI_DEBUG', 'false').lower() == 'true'

class DebugFileLogger:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = "debug_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create debug file
        self.debug_file = os.path.join(
            self.log_dir, 
            f"{agent_name}_{self.session_id}_debug.log"
        )
        
        # Create structured output file
        self.output_file = os.path.join(
            self.log_dir,
            f"{agent_name}_{self.session_id}_output.json"
        )
        
        self.outputs = []
        
        # Write header
        with open(self.debug_file, 'w') as f:
            f.write(f"=== {agent_name.upper()} DEBUG LOG ===\n")
            f.write(f"Session: {self.session_id}\n")
            f.write(f"Started: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
    
    def log(self, category: str, message: str, data: Any = None):
        timestamp = datetime.now().isoformat()
        with open(self.debug_file, 'a') as f:
            f.write(f"[{timestamp}] {category}: {message}\n")
            if data:
                f.write(f"  Data Type: {type(data)}\n")
                f.write(f"  Data Content: {repr(data)[:500]}...\n")
                if isinstance(data, str):
                    try:
                        parsed = json.loads(data)
                        f.write(f"  Parsed JSON: {json.dumps(parsed, indent=2)[:500]}...\n")
                    except:
                        f.write("  Not valid JSON\n")
            f.write("-" * 30 + "\n")
    
    def save_output(self, tool_name: str, input_data: Any, output_data: Any):
        output_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "input": {
                "type": str(type(input_data)),
                "content": str(input_data)[:1000]
            },
            "output": {
                "type": str(type(output_data)),
                "content": str(output_data)[:1000]
            }
        }
        self.outputs.append(output_entry)
        
        # Save to file
        with open(self.output_file, 'w') as f:
            json.dump({
                "agent": self.agent_name,
                "session": self.session_id,
                "outputs": self.outputs
            }, f, indent=2)
    
    def log_context_received(self, context_data: Any):
        """Special logging for context received from other agents"""
        timestamp = datetime.now().isoformat()
        with open(self.debug_file, 'a') as f:
            f.write(f"[{timestamp}] CONTEXT_RECEIVED: Data from previous agents\n")
            f.write(f"  Context Type: {type(context_data)}\n")
            
            if isinstance(context_data, list):
                f.write(f"  Number of context items: {len(context_data)}\n")
                for i, item in enumerate(context_data):
                    f.write(f"  Context Item {i}: {type(item)}\n")
                    f.write(f"    Preview: {str(item)[:300]}...\n")
            else:
                f.write(f"  Context Preview: {str(context_data)[:500]}...\n")
            f.write("=" * 50 + "\n")

# Global logger instance
debug_logger = DebugFileLogger("scoring_agent") if DEBUG_MODE else None

# Regular logger
logger = logging.getLogger(__name__)

# Tool Input Schemas
class CalculateCategoryScoreInput(BaseModel):
    score_data: str = Field(
        default="{}",
        description="JSON string containing category name and assessment responses"
    )

class AggregateFinalScoresInput(BaseModel):
    all_scores: str = Field(
        default="{}",
        description="JSON string containing all category scores"
    )

class CalculateFocusAreasInput(BaseModel):
    score_results: str = Field(
        default="{}",
        description="JSON string containing scores and business context"
    )

# Helper functions remain the same
def score_owner_dependence(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score owner dependence category"""
    base_score = 5.0
    gaps = []
    strengths = []
    
    # Q1 - Owner involvement
    q1_response = responses.get("q1", "").lower()
    if "all" in q1_response or "everything" in q1_response or "personally" in q1_response:
        base_score -= 2.0
        gaps.append("Owner handles all critical functions")
    elif "some" in q1_response or "major" in q1_response:
        base_score -= 0.5
        gaps.append("Owner involved in too many key decisions")
    else:
        base_score += 1.0
        strengths.append("Good delegation of responsibilities")
    
    # Q2 - Time away
    q2_response = responses.get("q2", "")
    if "Less than 3 days" in q2_response:
        base_score -= 1.5
        gaps.append("Business cannot operate without owner for even a week")
    elif "3-7 days" in q2_response:
        base_score -= 0.5
        gaps.append("Limited operational independence")
    elif "1-2 weeks" in q2_response:
        base_score += 0.5
        strengths.append("Moderate operational independence")
    else:
        base_score += 2.0
        strengths.append("Strong operational independence")
    
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.25,
        "strengths": strengths if strengths else ["Some delegation in place"],
        "gaps": gaps if gaps else ["No critical gaps identified"],
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": [f"Owner involvement: {-2.0 if 'all' in q1_response else 0}"],
            "final_score": round(final_score, 1)
        }
    }

def score_revenue_quality(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score revenue quality and predictability"""
    base_score = 5.0
    gaps = []
    strengths = []
    
    # Q3 - Revenue mix
    q3_response = responses.get("q3", "").lower()
    if "recurring" in q3_response or "subscription" in q3_response or "retainer" in q3_response:
        base_score += 1.5
        strengths.append("Recurring revenue model")
    elif "project" in q3_response or "one-time" in q3_response:
        base_score -= 1.0
        gaps.append("Project-based revenue less predictable")
    
    # Q4 - Recurring percentage
    q4_response = responses.get("q4", "")
    if "60-80%" in q4_response or "Over 80%" in q4_response:
        base_score += 2.0
        strengths.append("High recurring revenue percentage")
    elif "40-60%" in q4_response:
        base_score += 0.5
        strengths.append("Moderate recurring revenue")
    elif "20-40%" in q4_response:
        base_score -= 0.5
        gaps.append("Low recurring revenue percentage")
    else:
        base_score -= 1.5
        gaps.append("Minimal recurring revenue")
    
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.25,
        "strengths": strengths if strengths else ["Revenue model established"],
        "gaps": gaps if gaps else ["Revenue quality acceptable"],
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": [],
            "final_score": round(final_score, 1)
        }
    }

# Simplified versions of other scoring functions
def score_financial_readiness(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score financial readiness"""
    q5_score = float(responses.get("q5", "5"))
    q6_response = responses.get("q6", "Stayed flat")
    
    base_score = q5_score * 0.7  # 70% weight on financial confidence
    
    if "Improved" in q6_response:
        base_score += 2.0
    elif "Declined" in q6_response:
        base_score -= 1.0
    
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.20,
        "strengths": ["Financial records maintained"] if q5_score >= 7 else [],
        "gaps": ["Financial confidence low"] if q5_score < 5 else [],
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": [],
            "final_score": round(final_score, 1)
        }
    }

def score_operational_resilience(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score operational resilience"""
    q7_response = responses.get("q7", "").lower()
    q8_score = float(responses.get("q8", "5"))
    
    base_score = 5.0
    
    if "critical" in q7_response or "only person" in q7_response:
        base_score -= 2.0
    elif "some" in q7_response or "most" in q7_response:
        base_score += 1.0
    
    base_score += (q8_score - 5) * 0.5  # Documentation impact
    
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.15,
        "strengths": ["Documentation exists"] if q8_score >= 6 else [],
        "gaps": ["Key person dependencies"] if "critical" in q7_response else [],
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": [],
            "final_score": round(final_score, 1)
        }
    }

def score_growth_value(responses: Dict[str, str], research_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score growth potential and unique value"""
    q9_response = responses.get("q9", "").lower()
    q10_score = float(responses.get("q10", "5"))
    
    base_score = 3.0 + (q10_score * 0.5)
    
    if "proprietary" in q9_response or "unique" in q9_response or "exclusive" in q9_response:
        base_score += 2.0
    elif "relationships" in q9_response:
        base_score += 0.5
    
    final_score = max(1.0, min(10.0, base_score))
    
    return {
        "score": round(final_score, 1),
        "weight": 0.15,
        "strengths": ["Unique value drivers"] if "proprietary" in q9_response else [],
        "gaps": ["Limited differentiation"] if base_score < 5 else [],
        "scoring_breakdown": {
            "base_score": 5.0,
            "adjustments": [],
            "final_score": round(final_score, 1)
        }
    }

# Tool Classes
class CalculateCategoryScoreTool(BaseTool):
    name: str = "calculate_category_score"
    description: str = """
    Calculate score for a specific assessment category.
    
    Input should be JSON string containing:
    {"category": "owner_dependence", "responses": {...}, "research_data": {...}}
    
    Returns scoring results as formatted text.
    """
    args_schema: Type[BaseModel] = CalculateCategoryScoreInput
    
    def _run(self, score_data: str = "{}", **kwargs) -> str:
        if debug_logger:
            debug_logger.log("TOOL_INPUT", f"{self.name} called", score_data)
            
        try:
            logger.info(f"=== CALCULATE CATEGORY SCORE CALLED ===")
            
            # Parse input
            if isinstance(score_data, dict):
                data = score_data
            else:
                data = safe_parse_json(score_data, {}, "calculate_category_score")
            
            if not data:
                result = """SCORING ERROR: No data provided

Required:
- category: Category name to score
- responses: Assessment responses
- research_data: Industry research findings

Cannot calculate score without this data."""
                
                if debug_logger:
                    debug_logger.save_output(self.name, score_data, result)
                return result
            
            category = data.get('category', '').lower()
            responses = data.get('responses', {})
            research_data = data.get('research_data', {})
            
            if debug_logger:
                debug_logger.log("PARSED_DATA", f"Category: {category}, Responses: {len(responses)}, Research: {bool(research_data)}")
            
            # Map categories to scoring functions
            scoring_functions = {
                'owner_dependence': score_owner_dependence,
                'revenue_quality': score_revenue_quality,
                'financial_readiness': score_financial_readiness,
                'operational_resilience': score_operational_resilience,
                'growth_value': score_growth_value
            }
            
            if category not in scoring_functions:
                result = f"""SCORING ERROR: Invalid category '{category}'

Valid categories:
- owner_dependence
- revenue_quality
- financial_readiness
- operational_resilience
- growth_value"""
                
                if debug_logger:
                    debug_logger.save_output(self.name, score_data, result)
                return result
            
            # Calculate score
            scoring_result = scoring_functions[category](responses, research_data)
            score = scoring_result['score']
            weight = scoring_result['weight']
            
            # Format as text
            result = f"""CATEGORY SCORING COMPLETE: {category.replace('_', ' ').title()}

SCORE: {score}/10 (Weight: {int(weight*100)}%)

SCORING BREAKDOWN:
- Base score: 5.0
- Final score: {score}
- Weighted contribution: {score * weight:.1f} points

STRENGTHS IDENTIFIED:
{chr(10).join(f'✓ {s}' for s in scoring_result['strengths']) if scoring_result['strengths'] else '✓ No specific strengths noted'}

GAPS TO ADDRESS:
{chr(10).join(f'⚠️ {g}' for g in scoring_result['gaps']) if scoring_result['gaps'] else '⚠️ No critical gaps identified'}

Status: Scoring successful
Category: {category}
Score: {score}/10"""
            
            if debug_logger:
                debug_logger.save_output(self.name, score_data, result)
                debug_logger.log("SCORE_CALCULATED", f"{category}: {score}/10")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating category score: {str(e)}")
            error_result = f"""SCORING ERROR: Calculation failed

Category: {data.get('category', 'Unknown') if 'data' in locals() else 'Unknown'}
Error: {str(e)}

Please check the input format and try again."""
            
            if debug_logger:
                debug_logger.save_output(self.name, score_data, error_result)
            return error_result

class AggregateFinalScoresTool(BaseTool):
    name: str = "aggregate_final_scores"
    description: str = """
    Aggregate all category scores into final assessment results.
    
    Input should be JSON string containing all category scores.
    
    Returns aggregated results as formatted text.
    """
    args_schema: Type[BaseModel] = AggregateFinalScoresInput
    
    def _run(self, all_scores: str = "{}", **kwargs) -> str:
        if debug_logger:
            debug_logger.log("TOOL_INPUT", f"{self.name} called", all_scores)
            
        try:
            # Parse input
            if isinstance(all_scores, dict):
                scores = all_scores
            else:
                scores = safe_parse_json(all_scores, {}, "aggregate_final_scores")
            
            if not scores:
                result = """AGGREGATION ERROR: No scores provided

Cannot calculate final score without category scores.

Required: Scores for all 5 categories"""
                
                if debug_logger:
                    debug_logger.save_output(self.name, all_scores, result)
                return result
            
            # Calculate overall score
            total_weighted = 0.0
            total_weight = 0.0
            category_summaries = []
            
            for category, score_data in scores.items():
                if isinstance(score_data, dict) and 'score' in score_data:
                    score = score_data['score']
                    weight = score_data.get('weight', 0.2)
                    total_weighted += score * weight
                    total_weight += weight
                    category_summaries.append(f"• {category.replace('_', ' ').title()}: {score}/10 (weight {int(weight*100)}%)")
            
            overall_score = round(total_weighted / total_weight, 1) if total_weight > 0 else 0
            
            # Determine readiness level
            if overall_score >= 8.0:
                readiness_level = "Exit Ready"
            elif overall_score >= 6.5:
                readiness_level = "Approaching Ready"
            elif overall_score >= 4.5:
                readiness_level = "Needs Work"
            else:
                readiness_level = "Not Ready"
            
            result = f"""FINAL SCORE AGGREGATION COMPLETE

OVERALL EXIT READINESS SCORE: {overall_score}/10
READINESS LEVEL: {readiness_level}

CATEGORY BREAKDOWN:
{chr(10).join(category_summaries)}

SCORE ANALYSIS:
- Total weighted score: {total_weighted:.1f}
- Total weight: {total_weight:.1f}
- Categories scored: {len(scores)}

Status: Aggregation successful
Overall Score: {overall_score}/10
Readiness: {readiness_level}"""
            
            if debug_logger:
                debug_logger.save_output(self.name, all_scores, result)
                debug_logger.log("OVERALL_SCORE", f"{overall_score}/10 - {readiness_level}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error aggregating scores: {str(e)}")
            error_result = f"""AGGREGATION ERROR: Failed to calculate

Error: {str(e)}

Please ensure all category scores are provided."""
            
            if debug_logger:
                debug_logger.save_output(self.name, all_scores, error_result)
            return error_result

class CalculateFocusAreasTool(BaseTool):
    name: str = "calculate_focus_areas"
    description: str = """
    Identify top 3 focus areas based on scores and gaps.
    
    Input should be JSON string containing scores and business context.
    
    Returns prioritized focus areas as formatted text.
    """
    args_schema: Type[BaseModel] = CalculateFocusAreasInput
    
    def _run(self, score_results: str = "{}", **kwargs) -> str:
        if debug_logger:
            debug_logger.log("TOOL_INPUT", f"{self.name} called", score_results)
            
        try:
            # Parse input
            if isinstance(score_results, dict):
                data = score_results
            else:
                data = safe_parse_json(score_results, {}, "calculate_focus_areas")
            
            if not data:
                result = """FOCUS AREAS ERROR: No data provided

Cannot identify focus areas without:
- Category scores
- Identified gaps
- Business context"""
                
                if debug_logger:
                    debug_logger.save_output(self.name, score_results, result)
                return result
            
            scores = data.get('scores', {})
            timeline = data.get('timeline', '1-2 years')
            
            # Find lowest scoring categories
            category_scores = []
            for category, score_data in scores.items():
                if isinstance(score_data, dict):
                    category_scores.append({
                        'category': category,
                        'score': score_data.get('score', 5),
                        'gaps': score_data.get('gaps', [])
                    })
            
            # Sort by score (lowest first)
            category_scores.sort(key=lambda x: x['score'])
            
            # Generate focus areas
            focus_areas = []
            for i, cat_data in enumerate(category_scores[:3]):
                focus_areas.append(f"""
PRIORITY {i+1}: {cat_data['category'].replace('_', ' ').title()}
Current Score: {cat_data['score']}/10
Key Gaps: {', '.join(cat_data['gaps'][:2]) if cat_data['gaps'] else 'General improvement needed'}
Action Required: Focus on addressing identified gaps
Timeline: {"Immediate" if cat_data['score'] < 4 else "Next 3-6 months"}""")
            
            result = f"""FOCUS AREAS IDENTIFIED

EXIT TIMELINE: {timeline}

TOP 3 PRIORITIES:
{chr(10).join(focus_areas)}

RECOMMENDATION:
Start with Priority 1 as it has the most impact on your exit readiness.

Status: Focus areas calculated successfully"""
            
            if debug_logger:
                debug_logger.save_output(self.name, score_results, result)
                debug_logger.log("FOCUS_AREAS", f"Top priority: {category_scores[0]['category'] if category_scores else 'None'}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating focus areas: {str(e)}")
            error_result = f"""FOCUS AREAS ERROR: Calculation failed

Error: {str(e)}

Please check the scoring results format."""
            
            if debug_logger:
                debug_logger.save_output(self.name, score_results, error_result)
            return error_result

# Create tool instances
calculate_category_score = CalculateCategoryScoreTool()
aggregate_final_scores = AggregateFinalScoresTool()
calculate_focus_areas = CalculateFocusAreasTool()

def create_scoring_agent(llm, prompts: Dict[str, Any], scoring_rubric: Dict[str, Any]) -> Agent:
    """Create the scoring agent"""
    
    config = prompts.get('scoring_agent', {})
    
    # Create tools list
    tools = [
        calculate_category_score,
        aggregate_final_scores,
        calculate_focus_areas
    ]
    
    if debug_logger:
        debug_logger.log("AGENT_CREATION", f"Creating scoring agent with {len(tools)} tools")
        # Log what context we expect to receive
        debug_logger.log("EXPECTED_CONTEXT", "Expecting context from: intake_agent (anonymized data) and research_agent (industry findings)")
    
    return Agent(
        role=config.get('role'),
        goal=config.get('goal'),
        backstory=config.get('backstory'),
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )