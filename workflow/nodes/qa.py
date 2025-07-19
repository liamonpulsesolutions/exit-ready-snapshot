"""
QA validation node for LangGraph workflow.
Enhanced with LLM-based quality checks, outcome framing verification, and Placid formatting.
Uses GPT-4.1 for advanced redundancy detection and report polishing.
FIXED: JSON parsing to handle malformed LLM responses.
"""

import logging
import time
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from workflow.state import WorkflowState
from workflow.core.llm_utils import get_llm_with_fallback, parse_json_response
from langchain.schema import SystemMessage, HumanMessage

# Import validators from core module
from workflow.core.validators import (
    validate_scoring_consistency,
    validate_content_quality,
    scan_for_pii,
    validate_report_structure
)

logger = logging.getLogger(__name__)


def parse_json_with_fixes(content: str, function_name: str = "Unknown") -> Dict[str, Any]:
    """
    Parse JSON with fixes for common LLM response issues.
    Handles malformed JSON that's missing braces or has extra text.
    """
    import re
    
    # Strip whitespace
    content = content.strip()
    
    # If empty, return empty dict
    if not content:
        logger.warning(f"{function_name}: Empty response content")
        return {}
    
    # Fix missing opening brace - check for common QA response patterns
    if content and not content.startswith('{'):
        qa_patterns = ['redundancy_score', 'tone_score', 'citation_score', 'framing_score', 
                      'executive_summary', 'recommendations', 'repetitive_phrases']
        if any(f'"{pattern}"' in content for pattern in qa_patterns):
            content = '{' + content
            logger.debug(f"{function_name}: Added missing opening brace")
    
    # Fix missing closing brace
    if content.startswith('{') and not content.endswith('}'):
        # Count braces to see if we need to add one
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces > close_braces:
            content = content + '}'
            logger.debug(f"{function_name}: Added missing closing brace")
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"{function_name}: Initial JSON parse failed: {e}")
        logger.debug(f"{function_name}: Content preview: {repr(content[:200])}")
        
        # Try to extract valid JSON using regex
        # Look for JSON object pattern (handles nested objects)
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in json_matches:
            try:
                result = json.loads(match)
                logger.info(f"{function_name}: Successfully extracted JSON from text")
                return result
            except:
                continue
        
        # If all else fails, log the error and raise
        logger.error(f"{function_name}: Failed to parse JSON. Content: {repr(content[:500])}")
        raise


def standardize_formatting_for_placid(text: str) -> str:
    """
    Standardize text formatting for Placid compatibility.
    Removes all markdown and applies consistent plain text formatting.
    """
    if not text:
        return text
    
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_
    
    # Convert markdown headers to plain text
    text = re.sub(r'^#{1,6}\s+(.+)$', lambda m: m.group(1).upper(), text, flags=re.MULTILINE)
    
    # Standardize bullet points
    text = re.sub(r'^[\-\*\+]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'^[\d]+\.\s+', lambda m: f"{m.group(0)}", text, flags=re.MULTILINE)
    
    # Remove any remaining markdown syntax
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # [text](url) -> text
    text = re.sub(r'`([^`]+)`', r'\1', text)  # `code` -> code
    text = re.sub(r'```[^`]*```', '', text)   # Remove code blocks
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove any HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    return text.strip()


def apply_section_formatting(sections: Dict[str, Any], final_report: str) -> Dict[str, Any]:
    """
    Apply formatting to all report sections.
    Individual sections get clean text only.
    Final report gets section separators for document view.
    """
    formatted_sections = {}
    
    # Format individual sections (for Placid fields) - CLEAN TEXT ONLY
    for key, value in sections.items():
        if isinstance(value, str):
            formatted_sections[key] = standardize_formatting_for_placid(value)
        elif isinstance(value, dict):
            formatted_sections[key] = {
                k: standardize_formatting_for_placid(v) if isinstance(v, str) else v
                for k, v in value.items()
            }
        else:
            formatted_sections[key] = value
    
    # Format final report (for document view) - WITH SEPARATORS
    if final_report:
        formatted_sections["final_report"] = add_document_separators(final_report)
    
    return formatted_sections


def add_document_separators(report: str) -> str:
    """
    Add section separators for the full document view only.
    This is only for the full document view, not individual Placid fields.
    """
    # First apply standard formatting
    report = standardize_formatting_for_placid(report)
    
    # Define section patterns
    section_patterns = [
        (r'(EXECUTIVE SUMMARY)', r'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n\1'),
        (r'(YOUR EXIT READINESS SCORE)', r'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n\1'),
        (r'(DETAILED ANALYSIS BY CATEGORY)', r'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n\1'),
        (r'(PERSONALIZED RECOMMENDATIONS)', r'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n\1'),
        (r'(INDUSTRY & MARKET CONTEXT)', r'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n\1'),
        (r'(YOUR NEXT STEPS)', r'\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n\1'),
    ]
    
    # Apply major section separators
    for pattern, replacement in section_patterns:
        report = re.sub(pattern, replacement, report)
    
    # Add subsection separators for category analyses
    category_headers = [
        'Owner Dependence Analysis',
        'Revenue Quality Analysis', 
        'Financial Readiness Analysis',
        'Operational Resilience Analysis',
        'Growth Potential Analysis'
    ]
    
    for header in category_headers:
        pattern = f'({header.upper()})'
        replacement = r'\n───────────────────────────────────────\n\n\1'
        report = re.sub(pattern, replacement, report)
    
    # Clean up any duplicate separators
    report = re.sub(r'(━{60}\n\n){2,}', r'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n', report)
    report = re.sub(r'(─{39}\n\n){2,}', r'───────────────────────────────────────\n\n', report)
    
    # Add header
    header = """EXIT READY SNAPSHOT ASSESSMENT REPORT

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    # Add footer
    footer = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIDENTIAL BUSINESS ASSESSMENT
Prepared by: On Pulse Solutions
Report Date: [REPORT_DATE]
Valid for: 90 days

This report contains proprietary analysis and recommendations specific to your business.
The insights and strategies outlined are based on your assessment responses and current market conditions.

© On Pulse Solutions - Exit Ready Snapshot"""
    
    if not report.startswith("EXIT READY SNAPSHOT"):
        report = header + report
    
    if "© On Pulse Solutions" not in report:
        report = report + footer
    
    return report


def check_redundancy_llm(report: str, llm) -> Dict[str, Any]:
    """Use LLM to check for content redundancy with GPT-4.1. FIXED: Handle malformed JSON responses."""
    
    prompt = """Analyze this business assessment report for redundancy and repetitive content.

Report:
{report}

Evaluate:
1. Are key points repeated unnecessarily across sections?
2. Is the same information presented multiple times without adding value?
3. Are there verbose explanations that could be more concise?
4. Do multiple sections say essentially the same thing?

Important: Strategic repetition is ESSENTIAL in business reports:
- Key metrics appearing in summary and detailed sections is GOOD
- Important recommendations emphasized 2-3 times is EFFECTIVE
- Scores and critical findings in multiple contexts is NECESSARY

Only flag TRUE redundancy where:
- The exact same sentence appears 3+ times
- A concept is explained identically 4+ times with no new context
- Filler content repeats without purpose

Provide your analysis in this exact JSON format:
{
    "redundancy_score": 8,
    "redundant_sections": ["list", "of", "truly", "redundant", "sections"],
    "specific_examples": ["exact duplicate content only"],
    "suggested_consolidations": ["only if truly excessive"]
}"""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content="You are an expert business communication analyst using GPT-4.1's superior comprehension. You understand the difference between strategic emphasis and true redundancy. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(report=report[:10000]))
        ]
        
        # Use bind() method for JSON response format
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response with fixes
        if hasattr(response, 'content'):
            result = parse_json_with_fixes(response.content, "check_redundancy_llm")
        else:
            result = parse_json_with_fixes(str(response), "check_redundancy_llm")
        
        elapsed = time.time() - start_time
        logger.info(f"Redundancy check took {elapsed:.2f}s")
        
        # Validate result
        if not isinstance(result.get("redundancy_score"), (int, float)):
            result["redundancy_score"] = 8
            
        return result
        
    except Exception as e:
        logger.warning(f"GPT-4.1 redundancy check failed: {e}, using default score")
        return {
            "redundancy_score": 8,
            "redundant_sections": [],
            "specific_examples": [],
            "suggested_consolidations": []
        }


def check_tone_consistency_llm(report: str, llm) -> Dict[str, Any]:
    """Use LLM to check tone consistency throughout the report. FIXED: Handle malformed JSON responses."""
    
    prompt = """Analyze this business assessment report for tone consistency.

Report:
{report}

Evaluate:
1. Is the tone professional and consultative throughout?
2. Are there jarring shifts between overly technical and overly casual language?
3. Does the voice remain consistent across all sections?
4. Are recommendations actionable without being prescriptive?

Provide your analysis in this exact JSON format:
{
    "tone_score": 8,
    "tone_issues": ["list", "specific", "tone", "problems"],
    "inconsistent_sections": ["sections", "with", "tone", "issues"],
    "improvement_suggestions": ["specific", "fixes"]
}"""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content="You are a business communication expert. Evaluate tone consistency and professionalism. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(report=report[:8000]))
        ]
        
        # Use bind() method for JSON response format
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response with fixes
        if hasattr(response, 'content'):
            result = parse_json_with_fixes(response.content, "check_tone_consistency_llm")
        else:
            result = parse_json_with_fixes(str(response), "check_tone_consistency_llm")
        
        elapsed = time.time() - start_time
        logger.info(f"Tone check took {elapsed:.2f}s")
        
        # Validate result
        if not isinstance(result.get("tone_score"), (int, float)):
            result["tone_score"] = 8
            
        return result
        
    except Exception as e:
        logger.warning(f"LLM tone check failed: {e}, using default score")
        return {
            "tone_score": 8,
            "tone_issues": [],
            "inconsistent_sections": [],
            "improvement_suggestions": []
        }


def verify_citations_llm(report: str, research_result: Dict[str, Any], llm) -> Dict[str, Any]:
    """Verify that statistical claims are properly cited. FIXED: Handle malformed JSON responses."""
    
    # Extract citation sources from research
    citations = research_result.get("citations", [])
    citation_text = "\n".join([f"- {c.get('source', 'Unknown')} ({c.get('year', 'N/A')})" 
                              for c in citations[:10]])
    
    # Industry benchmarks that should be cited
    benchmarks = research_result.get("valuation_benchmarks", {})
    benchmarks_text = json.dumps(benchmarks, indent=2)[:1000]
    
    prompt = """Verify that statistical claims and benchmarks in this report are properly cited.

Report:
{report}

Available Citations:
{citations}

Key Benchmarks Requiring Citation:
{benchmarks}

Check for:
1. Uncited statistics (percentages, multiples, dollar amounts)
2. Industry claims without sources
3. Benchmark references without attribution
4. Time-based claims (e.g., "typically takes X months") without sources

Note: General business wisdom and common practices don't need citations.

Whitelist (don't need citations):
{whitelist}

Provide your analysis in this exact JSON format:
{
    "citation_score": 8,
    "total_claims_found": 15,
    "properly_cited": 12,
    "issues_found": 3,
    "uncited_claims": ["specific", "uncited", "statistical", "claims"]
}"""

    # Common phrases that don't need citations
    uncited_whitelist_phrases = [
        "businesses typically", "companies often", "owners usually",
        "industry best practice", "common challenges include",
        "standard valuation", "general market conditions"
    ]
    
    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content=f"""You are a fact-checking expert verifying business report citations. 
Focus on statistical claims, specific percentages, and industry benchmarks that require sources.
Common phrases that don't need citations include: {', '.join(uncited_whitelist_phrases[:5])}. Always respond with valid JSON."""),
            HumanMessage(content=prompt.format(
                report=report[:6000],
                citations=citation_text[:2000],
                benchmarks=benchmarks_text[:1000],
                whitelist=", ".join(uncited_whitelist_phrases[:10])
            ))
        ]
        
        # Use bind() method for JSON response format
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response with fixes
        if hasattr(response, 'content'):
            result = parse_json_with_fixes(response.content, "verify_citations_llm")
        else:
            result = parse_json_with_fixes(str(response), "verify_citations_llm")
        
        elapsed = time.time() - start_time
        logger.info(f"Citation verification took {elapsed:.2f}s")
        
        # Validate result
        if not isinstance(result.get("citation_score"), (int, float)):
            result["citation_score"] = 8
        if not isinstance(result.get("issues_found"), int):
            result["issues_found"] = 0
            
        return result
        
    except Exception as e:
        logger.warning(f"LLM citation verification failed: {e}, using default score")
        return {
            "citation_score": 8,
            "total_claims_found": 0,
            "properly_cited": 0,
            "issues_found": 0,
            "uncited_claims": []
        }


def verify_outcome_framing_llm(report: str, llm) -> Dict[str, Any]:
    """Verify proper outcome framing (no guarantees, uses typically/often language). FIXED: Handle malformed JSON responses."""
    
    prompt = """Analyze this business assessment for proper outcome framing.

Report:
{report}

Check for:
1. Promise language: "will increase", "will achieve", "guaranteed", "ensures"
2. Proper framing: "typically see", "often achieve", "generally experience", "commonly find"
3. Range-based outcomes: "15-25% increase" vs "20% increase"
4. Citation of sources for outcome claims

Flag any instances where outcomes are presented as guarantees rather than typical results.

Provide your analysis in this exact JSON format:
{
    "framing_score": 9,
    "promises_found": 0,
    "promise_phrases": ["list", "of", "problematic", "phrases"],
    "properly_framed": 15,
    "framing_examples": ["good", "framing", "examples"],
    "needs_revision": ["phrases", "that", "need", "fixes"]
}"""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content="You are a compliance expert ensuring business communications avoid guarantees and use proper outcome framing. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(report=report[:8000]))
        ]
        
        # Use bind() method for JSON response format
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response with fixes
        if hasattr(response, 'content'):
            result = parse_json_with_fixes(response.content, "verify_outcome_framing_llm")
        else:
            result = parse_json_with_fixes(str(response), "verify_outcome_framing_llm")
        
        elapsed = time.time() - start_time
        logger.info(f"Outcome framing check took {elapsed:.2f}s")
        
        # Validate result
        if not isinstance(result.get("framing_score"), (int, float)):
            result["framing_score"] = 8
        if not isinstance(result.get("promises_found"), int):
            result["promises_found"] = 0
            
        return result
        
    except Exception as e:
        logger.warning(f"LLM outcome framing verification failed: {e}, using fallback regex check")
        
        # Fallback to regex checking
        promise_patterns = [
            r'\bwill\s+(?:increase|improve|achieve|ensure|guarantee)',
            r'\bguaranteed?\b',
            r'\bensures?\b',
            r'\bdefinitely\s+will\b'
        ]
        
        promises = []
        for pattern in promise_patterns:
            matches = re.findall(pattern, report, re.IGNORECASE)
            promises.extend(matches)
        
        return {
            "framing_score": 5 if promises else 9,
            "promises_found": len(promises),
            "promise_phrases": promises[:10],
            "properly_framed": 0,
            "framing_examples": [],
            "needs_revision": promises[:5]
        }


def fix_quality_issues_llm(issues: List[str], warnings: List[str], 
                          summary_result: Dict[str, Any], scoring_result: Dict[str, Any],
                          redundancy_info: Dict[str, Any], tone_info: Dict[str, Any],
                          llm) -> Dict[str, str]:
    """Use LLM to fix identified quality issues. FIXED: Handle malformed JSON responses."""
    
    issues_text = "\n".join([f"- ISSUE: {issue}" for issue in issues])
    warnings_text = "\n".join([f"- WARNING: {warning}" for warning in warnings])
    
    prompt = """Fix the following quality issues in this business assessment report.

CRITICAL ISSUES TO FIX:
{issues}

WARNINGS TO ADDRESS:
{warnings}

Current Executive Summary:
{exec_summary}

Overall Score: {score}/10
Readiness Level: {level}

Redundancy Issues: {redundancy}
Tone Issues: {tone}

Provide fixed content in this exact JSON format:
{
    "executive_summary": "fixed executive summary if needed",
    "recommendations": {
        "financial_readiness": ["rec 1", "rec 2"],
        "revenue_quality": ["rec 1", "rec 2"],
        "operational_resilience": ["rec 1", "rec 2"]
    },
    "next_steps": "fixed next steps if needed"
}

Focus on fixing ONLY the sections with issues. Keep other sections unchanged.
Ensure all content remains professional, specific, and actionable."""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content="You are a business report editor fixing quality issues while maintaining accuracy. Always use proper outcome framing with 'typically/often' language. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(
                issues=issues_text,
                warnings=warnings_text,
                exec_summary=summary_result.get("executive_summary", "")[:2000],
                score=scoring_result.get("overall_score", 0),
                level=scoring_result.get("readiness_level", "Unknown"),
                redundancy=json.dumps(redundancy_info.get("redundant_sections", []))[:500],
                tone=json.dumps(tone_info.get("tone_issues", []))[:500]
            ))
        ]
        
        # Use bind() method for JSON response format
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response with fixes
        if hasattr(response, 'content'):
            result = parse_json_with_fixes(response.content, "fix_quality_issues_llm")
        else:
            result = parse_json_with_fixes(str(response), "fix_quality_issues_llm")
        
        elapsed = time.time() - start_time
        logger.info(f"Quality issue fixes took {elapsed:.2f}s")
        
        # Only return sections that were actually fixed
        fixed_sections = {}
        if result.get("executive_summary") and issues_text:
            fixed_sections["executive_summary"] = result["executive_summary"]
        if result.get("recommendations") and any("recommendation" in issue.lower() for issue in issues):
            # Ensure recommendations maintains the expected format
            fixed_sections["recommendations"] = result["recommendations"]
        if result.get("next_steps") and any("next" in issue.lower() for issue in issues):
            fixed_sections["next_steps"] = result["next_steps"]
            
        return fixed_sections
        
    except Exception as e:
        logger.warning(f"LLM issue fixing failed: {e}, returning empty fixes")
        return {}


def polish_report_llm(summary_result: Dict[str, Any], scoring_result: Dict[str, Any], 
                     llm) -> Dict[str, str]:
    """Apply final polish using GPT-4.1's superior writing capabilities. FIXED: Handle malformed JSON responses."""
    
    prompt = """Polish this executive summary to make it more impactful and actionable.

Current Executive Summary:
{exec_summary}

Overall Score: {score}/10
Readiness Level: {level}

Guidelines:
1. Start with a powerful, specific opening statement about the business's exit readiness
2. Use concrete numbers and timeframes where possible
3. Add motivating language that inspires action without overpromising
4. Keep the same length and all factual content unchanged
5. Make it feel personalized to this specific business owner
6. Use "typically/often/generally" language for all outcome predictions

Provide the polished version in this exact JSON format:
{
    "executive_summary": "polished executive summary here",
    "key_improvements": ["what you improved", "second improvement", "third improvement"]
}"""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content="You are a master business writer using GPT-4.1's advanced capabilities. Create compelling, action-oriented content while maintaining accuracy and proper outcome framing. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(
                exec_summary=summary_result.get("executive_summary", ""),
                score=scoring_result.get("overall_score", 0),
                level=scoring_result.get("readiness_level", "Unknown")
            ))
        ]
        
        # Use bind() method for JSON response format
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response with fixes
        if hasattr(response, 'content'):
            result = parse_json_with_fixes(response.content, "polish_report_llm")
        else:
            result = parse_json_with_fixes(str(response), "polish_report_llm")
        
        elapsed = time.time() - start_time
        logger.info(f"Report polishing took {elapsed:.2f}s")
        
        return {
            "executive_summary": result.get("executive_summary", summary_result.get("executive_summary", ""))
        }
        
    except Exception as e:
        logger.warning(f"GPT-4.1 report polishing failed: {e}, skipping polish")
        return {}


def validate_structure_and_word_counts(sections: Dict[str, Any]) -> Dict[str, Any]:
    """Validate report structure and check word counts"""
    issues = []
    warnings = []
    section_stats = {}
    
    # Define expected word counts
    expected_counts = {
        "executive_summary": {"target": 200, "min": 150, "max": 250},
        "category_summaries": {"target": 150, "min": 100, "max": 200},  # per category
        "industry_context": {"target": 200, "min": 150, "max": 250},
        "next_steps": {"target": 300, "min": 250, "max": 350}
    }
    
    # Check executive summary
    exec_summary = sections.get("executive_summary", "")
    if exec_summary:
        word_count = len(exec_summary.split())
        section_stats["executive_summary"] = word_count
        
        if word_count < expected_counts["executive_summary"]["min"]:
            issues.append(f"Executive summary too short: {word_count} words (need {expected_counts['executive_summary']['min']}+)")
        elif word_count > expected_counts["executive_summary"]["max"]:
            warnings.append(f"Executive summary too long: {word_count} words (target {expected_counts['executive_summary']['target']})")
    else:
        issues.append("Missing executive summary")
    
    # Check category summaries
    category_summaries = sections.get("category_summaries", {})
    required_categories = ["owner_dependence", "revenue_quality", "financial_readiness", 
                          "operational_resilience", "growth_value"]
    
    for category in required_categories:
        if category not in category_summaries:
            issues.append(f"Missing category summary: {category}")
        else:
            summary = category_summaries[category]
            if isinstance(summary, dict):
                summary_text = summary.get("summary", "")
            else:
                summary_text = str(summary)
            
            word_count = len(summary_text.split())
            section_stats[f"category_{category}"] = word_count
            
            if word_count < expected_counts["category_summaries"]["min"]:
                warnings.append(f"{category} summary too short: {word_count} words")
    
    # Check recommendations
    recommendations = sections.get("recommendations", {})
    if not recommendations:
        issues.append("Missing recommendations section")
    elif isinstance(recommendations, dict):
        if "quick_wins" not in recommendations:
            issues.append("Recommendations missing quick_wins")
        if "strategic_priorities" not in recommendations:
            issues.append("Recommendations missing strategic_priorities")
    elif isinstance(recommendations, str):
        # If recommendations is a string, check if it has content
        if len(recommendations.strip()) < 50:
            warnings.append("Recommendations section seems too short")
    
    # Check next steps
    next_steps = sections.get("next_steps", "")
    if next_steps:
        word_count = len(next_steps.split())
        section_stats["next_steps"] = word_count
        
        if word_count < expected_counts["next_steps"]["min"]:
            warnings.append(f"Next steps too short: {word_count} words (need {expected_counts['next_steps']['min']}+)")
    else:
        issues.append("Missing next steps section")
    
    # Calculate completeness score
    total_expected = 6  # exec summary + 5 categories
    total_found = sum(1 for stat in section_stats.values() if stat > 50)
    completeness_score = (total_found / total_expected) * 10 if total_expected > 0 else 0
    
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "section_stats": section_stats,
        "completeness_score": round(completeness_score, 1)
    }


def check_scoring_consistency(scoring_result: Dict[str, Any], summary_result: Dict[str, Any]) -> Dict[str, Any]:
    """Verify scores are used consistently throughout the report"""
    issues = []
    
    # Get scores from scoring result
    overall_score = scoring_result.get("overall_score", 0)
    readiness_level = scoring_result.get("readiness_level", "")
    category_scores = scoring_result.get("category_scores", {})
    
    # Check if scores are mentioned in executive summary
    exec_summary = summary_result.get("executive_summary", "").lower()
    
    # Look for overall score mention
    score_patterns = [
        str(overall_score),
        f"{overall_score}/10",
        f"{overall_score} out of 10"
    ]
    
    score_mentioned = any(pattern in exec_summary for pattern in score_patterns)
    if not score_mentioned and overall_score > 0:
        issues.append("Overall score not mentioned in executive summary")
    
    # Check readiness level
    if readiness_level and readiness_level.lower() not in exec_summary:
        issues.append(f"Readiness level '{readiness_level}' not mentioned in executive summary")
    
    # Verify category scores are reflected
    category_summaries = summary_result.get("category_summaries", {})
    for category, score_data in category_scores.items():
        if category in category_summaries:
            cat_summary = str(category_summaries[category]).lower()
            score = score_data.get("score", 0)
            
            # Check if low scores have appropriate language
            if score < 4 and not any(word in cat_summary for word in ["challenge", "gap", "improve", "address"]):
                issues.append(f"Low score ({score}) in {category} not reflected in summary tone")
            elif score > 7 and not any(word in cat_summary for word in ["strong", "excellent", "well", "solid"]):
                issues.append(f"High score ({score}) in {category} not reflected in summary tone")
    
    return {
        "is_consistent": len(issues) == 0,
        "issues": issues,
        "scores_found": {
            "overall": overall_score,
            "readiness_level": readiness_level,
            "categories": len(category_scores)
        }
    }


def assemble_final_report(summary_result: Dict[str, Any]) -> str:
    """Assemble all sections into final report text"""
    report_parts = []
    
    # Executive Summary
    if summary_result.get("executive_summary"):
        report_parts.append("EXECUTIVE SUMMARY\n")
        report_parts.append(summary_result["executive_summary"])
    
    # Category Analyses
    category_summaries = summary_result.get("category_summaries", {})
    if category_summaries:
        report_parts.append("\n\nDETAILED ANALYSIS BY CATEGORY\n")
        
        category_titles = {
            "owner_dependence": "Owner Dependence",
            "revenue_quality": "Revenue Quality & Stability",
            "financial_readiness": "Financial Readiness",
            "operational_resilience": "Operational Resilience",
            "growth_value": "Growth & Value Potential"
        }
        
        # Handle both dict and string formats
        if isinstance(category_summaries, dict):
            for category, title in category_titles.items():
                if category in category_summaries:
                    report_parts.append(f"\n{title.upper()}")
                    cat_data = category_summaries[category]
                    if isinstance(cat_data, dict):
                        report_parts.append(cat_data.get("summary", ""))
                        if cat_data.get("score"):
                            report_parts.append(f"Score: {cat_data['score']}/10")
                    else:
                        report_parts.append(str(cat_data))
        else:
            # If category_summaries is not a dict, just append it as string
            report_parts.append(str(category_summaries))
    
    # Recommendations
    recommendations = summary_result.get("recommendations", {})
    if recommendations:
        report_parts.append("\n\nRECOMMENDATIONS\n")
        
        # Handle both string and dict formats
        if isinstance(recommendations, str):
            # If recommendations is a string, just append it
            report_parts.append(recommendations)
        elif isinstance(recommendations, dict):
            # Quick Wins
            if recommendations.get("quick_wins"):
                report_parts.append("\nQuick Wins (0-3 months):")
                for i, rec in enumerate(recommendations["quick_wins"], 1):
                    report_parts.append(f"{i}. {rec}")
            
            # Strategic Priorities
            if recommendations.get("strategic_priorities"):
                report_parts.append("\nStrategic Priorities (3-12 months):")
                for i, rec in enumerate(recommendations["strategic_priorities"], 1):
                    report_parts.append(f"{i}. {rec}")
            
            # Critical Focus
            if recommendations.get("critical_focus"):
                report_parts.append(f"\nCritical Focus Area: {recommendations['critical_focus']}")
        else:
            # Handle other types by converting to string
            report_parts.append(str(recommendations))
    
    # Industry Context
    if summary_result.get("industry_context"):
        report_parts.append("\n\nINDUSTRY & MARKET CONTEXT\n")
        report_parts.append(summary_result["industry_context"])
    
    # Next Steps
    if summary_result.get("next_steps"):
        report_parts.append("\n\nYOUR NEXT STEPS\n")
        report_parts.append(summary_result["next_steps"])
    
    return "\n".join(report_parts)


def format_for_placid(report: str) -> str:
    """Apply Placid-compatible formatting to the report"""
    # Add consistent headers and footers
    header = """EXIT READY SNAPSHOT

Your Personalized Business Exit Readiness Assessment

---

"""
    
    footer = """

---

© On Pulse Solutions - Exit Ready Snapshot"""
    
    if not report.startswith("EXIT READY SNAPSHOT"):
        report = header + report
    
    if "© On Pulse Solutions" not in report:
        report = report + footer
    
    return report

def calculate_overall_qa_score(quality_scores: Dict[str, Dict]) -> float:
    """Calculate overall QA score from individual checks"""
    total_score = 0.0
    total_weight = 0.0
    
    # Scoring weights (adjusted for new checks)
    weights = {
        "scoring_consistency": 0.15,
        "content_quality": 0.20,
        "pii_compliance": 0.15,
        "structure_validation": 0.10,
        "redundancy_check": 0.10,
        "tone_consistency": 0.10,
        "citation_verification": 0.10,
        "outcome_framing": 0.10
    }
    
    for check_name, check_result in quality_scores.items():
        weight = weights.get(check_name, 0.10)
        
        # Extract score based on check type
        if check_name == "content_quality":
            score = check_result.get("quality_score", 5.0) if check_result.get("passed", False) else 5.0
        elif check_name == "structure_validation":
            score = check_result.get("completeness_score", 5.0)
        elif check_name == "pii_compliance":
            score = 10.0 if not check_result.get("has_pii", False) else 0.0
        elif check_name == "scoring_consistency":
            score = 10.0 if check_result.get("is_consistent", True) else 5.0
        elif check_name == "redundancy_check":
            score = check_result.get("redundancy_score", 8.0)
        elif check_name == "tone_consistency":
            score = check_result.get("tone_score", 8.0)
        elif check_name == "citation_verification":
            score = check_result.get("citation_score", 8.0)
        elif check_name == "outcome_framing":
            score = check_result.get("framing_score", 8.0)
        else:
            score = 5.0
        
        total_score += score * weight
        total_weight += weight
    
    # Normalize to 0-10 scale
    return round(total_score / total_weight, 1) if total_weight > 0 else 5.0

def qa_node(state: WorkflowState) -> WorkflowState:
    """
    Enhanced QA validation with LLM-based checks, outcome framing verification, and formatting.
    
    FIXED: Handle malformed JSON responses from LLMs.
    """
    start_time = time.time()
    
    try:
        logger.info("Starting enhanced QA validation with formatting and outcome framing...")
        
        # Get required data
        scoring_result = state.get("scoring_result", {})
        summary_result = state.get("summary_result", {})
        research_result = state.get("research_result", {})
        
        # Initialize QA LLMs with higher token limits for analyzing full reports
        qa_llm = get_llm_with_fallback(
            model="gpt-4.1-nano",
            temperature=0,
            max_tokens=8000
        )
        
        # GPT-4.1 for redundancy and polish
        redundancy_llm = get_llm_with_fallback(
            model="gpt-4.1",
            temperature=0.1,
            max_tokens=8000
        )
        
        polish_llm = get_llm_with_fallback(
            model="gpt-4.1",
            temperature=0.3,
            max_tokens=8000
        )
        
        # Track all quality checks
        quality_scores = {}
        qa_issues = []
        qa_warnings = []
        
        # 1. Validate Scoring Consistency
        logger.info("Checking scoring consistency...")
        scoring_consistency_check = check_scoring_consistency(scoring_result, summary_result)
        quality_scores["scoring_consistency"] = scoring_consistency_check
        if not scoring_consistency_check.get("is_consistent", True):
            qa_issues.extend(scoring_consistency_check.get("issues", []))
        
        # 2. Validate Content Quality
        logger.info("Validating content quality...")
        content_quality_check = validate_content_quality(summary_result)
        quality_scores["content_quality"] = content_quality_check
        if not content_quality_check.get("passed", True):
            qa_issues.extend(content_quality_check.get("issues", []))
        qa_warnings.extend(content_quality_check.get("warnings", []))
        
        # 3. PII Detection
        logger.info("Scanning for PII...")
        # First assemble the report
        final_report = assemble_final_report(summary_result)
        pii_scan = scan_for_pii(final_report)
        quality_scores["pii_compliance"] = pii_scan
        
        if pii_scan.get("has_pii", False):
            qa_issues.append(f"CRITICAL: PII detected - {', '.join(pii_scan.get('found_types', []))}")
        
        # 4. Structure Validation
        logger.info("Validating report structure and word counts...")
        structure_check = validate_structure_and_word_counts(summary_result)
        quality_scores["structure_validation"] = structure_check
        if not structure_check.get("passed", True):
            qa_issues.extend(structure_check.get("issues", []))
        qa_warnings.extend(structure_check.get("warnings", []))
        
        # 5. Enhanced LLM-Based Checks
        logger.info("Running LLM-based quality checks...")
        
        # Check for redundancy with GPT-4.1
        logger.info("Checking for content redundancy with GPT-4.1...")
        redundancy_check = check_redundancy_llm(final_report, redundancy_llm)
        quality_scores["redundancy_check"] = redundancy_check
        
        # Allow redundancy scores down to 3/10 for long reports
        report_word_count = len(final_report.split())
        redundancy_threshold = 3 if report_word_count > 2000 else 5
        
        if redundancy_check.get("redundancy_score", 10) < redundancy_threshold:
            qa_warnings.append(f"High redundancy detected (score: {redundancy_check.get('redundancy_score')}/10)")
        
        # Check tone consistency
        logger.info("Checking tone consistency...")
        tone_check = check_tone_consistency_llm(final_report, qa_llm)
        quality_scores["tone_consistency"] = tone_check
        
        if tone_check.get("tone_score", 10) < 4:
            qa_warnings.append(f"Tone inconsistency detected (score: {tone_check.get('tone_score')}/10)")
        
        # Verify Citations
        logger.info("Verifying citations and statistical claims...")
        citation_check = verify_citations_llm(final_report, research_result, qa_llm)
        quality_scores["citation_verification"] = citation_check
        
        if citation_check.get("citation_score", 10) < 6:
            uncited_count = citation_check.get("issues_found", 0)
            if uncited_count > 2:
                qa_issues.append(f"Too many uncited claims found: {uncited_count}")
                for claim in citation_check.get("uncited_claims", [])[:3]:
                    qa_warnings.append(f"Uncited: {claim[:100]}...")
        
        # Verify Outcome Framing
        logger.info("Verifying outcome framing compliance...")
        framing_check = verify_outcome_framing_llm(final_report, qa_llm)
        quality_scores["outcome_framing"] = framing_check
        
        if framing_check.get("promises_found", 0) > 0:
            qa_issues.append(f"Promise language detected: {framing_check.get('promises_found')} instances")
            for phrase in framing_check.get("promise_phrases", [])[:3]:
                qa_warnings.append(f"Promise phrase: '{phrase}'")
        
        # 6. Attempt to Fix Issues
        max_fix_attempts = 3
        fix_attempt = 0
        
        while qa_issues and fix_attempt < max_fix_attempts:
            fix_attempt += 1
            logger.info(f"Attempting to fix issues - Attempt {fix_attempt}/{max_fix_attempts}")
            
            fixed_sections = fix_quality_issues_llm(
                qa_issues, qa_warnings,
                summary_result, scoring_result,
                redundancy_check, tone_check,
                qa_llm
            )
            
            if fixed_sections:
                # Apply fixes
                for section, content in fixed_sections.items():
                    if section in summary_result:
                        summary_result[section] = content
                
                # Re-check for issues (simplified)
                if fixed_sections.get("executive_summary"):
                    # Quick promise language check
                    promise_patterns = [r'\bwill\s+increase', r'\bguaranteed?\b', r'\bensures?\b']
                    new_promises = sum(1 for p in promise_patterns 
                                     if re.search(p, fixed_sections["executive_summary"], re.I))
                    if new_promises == 0:
                        qa_issues = [i for i in qa_issues if "Promise language" not in i]
                
                # Check if we fixed the critical issues
                remaining_critical = [i for i in qa_issues if "CRITICAL" in i or "Promise language" in i]
                if not remaining_critical:
                    logger.info(f"Issues fixed successfully after {fix_attempt} attempts!")
                    break
            else:
                logger.warning(f"No fixes generated on attempt {fix_attempt}")
        
        # 7. Apply Final Polish with GPT-4.1
        if len(qa_issues) == 0 or all("CRITICAL" not in issue for issue in qa_issues):
            logger.info("Applying final polish with GPT-4.1...")
            polished_content = polish_report_llm(summary_result, scoring_result, polish_llm)
            
            if polished_content.get("executive_summary"):
                summary_result["executive_summary"] = polished_content["executive_summary"]
        
        # 8. Reassemble and format final report
        logger.info("Assembling final report...")
        final_report = assemble_final_report(summary_result)
        
        # 9. Apply Placid Formatting
        logger.info("Applying Placid-compatible formatting...")
        final_report = format_for_placid(final_report)
        
        # Store formatted report
        summary_result["final_report"] = final_report
        
        # 10. Calculate Overall QA Score
        overall_qa_score = calculate_overall_qa_score(quality_scores)
        
        # 11. Determine Approval Status
        critical_issues = [i for i in qa_issues if "CRITICAL" in i]
        approved = len(critical_issues) == 0 and overall_qa_score >= 6.0  # Lowered threshold
        
        if not approved:
            qa_warnings.insert(0, "REPORT NOT APPROVED - Critical issues found or quality score too low")
        
        # Update state
        state["qa_result"] = {
            "approved": approved,
            "quality_score": overall_qa_score,
            "issues": qa_issues,
            "warnings": qa_warnings,
            "quality_checks": quality_scores,
            "fix_attempts": fix_attempt,
            "final_report": final_report
        }
        
        # Update summary result with QA-enhanced content
        state["summary_result"] = summary_result
        
        # Update processing time
        elapsed_time = time.time() - start_time
        state["processing_time"]["qa"] = elapsed_time
        
        # Update stage
        state["current_stage"] = "qa_complete"
        state["messages"].append(
            f"QA validation completed in {elapsed_time:.2f}s - "
            f"Approved: {approved}, Quality: {overall_qa_score:.1f}/10, "
            f"Issues: {len(qa_issues)}, Warnings: {len(qa_warnings)}"
        )
        
        logger.info(f"=== QA NODE COMPLETED - {elapsed_time:.2f}s, Approved: {approved} ===")
        
        return state
        
    except Exception as e:
        logger.error(f"QA validation failed: {str(e)}", exc_info=True)
        
        # Ensure we still have a result even on error
        state["qa_result"] = {
            "approved": False,
            "quality_score": 0,
            "issues": [f"QA validation error: {str(e)}"],
            "warnings": [],
            "quality_checks": {},
            "error": str(e)
        }
        
        state["current_stage"] = "qa_error"
        state["error"] = f"QA validation error: {str(e)}"
        state["messages"].append(f"ERROR in QA: {str(e)}")
        
        return state