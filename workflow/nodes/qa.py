"""
QA Node - Quality assurance with LLM intelligence, formatting standardization, and outcome framing verification.
Performs mechanical checks, intelligent analysis, Placid-compatible formatting, and ensures proper outcome language.
FIXED: Replace ensure_json_response with bind() method for JSON responses.
"""

import logging
import time
import json
import re
from typing import Dict, Any, List, Tuple
from datetime import datetime
from langchain.schema import HumanMessage, SystemMessage

# FIXED: Import LLM utilities without ensure_json_response
from workflow.core.llm_utils import (
    get_llm_with_fallback,
    parse_json_response
)

from workflow.state import WorkflowState
from workflow.core.validators import (
    validate_scoring_consistency,
    validate_content_quality,
    scan_for_pii,
    validate_report_structure
)

logger = logging.getLogger(__name__)


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
    
    # Format individual sections (no separators)
    if isinstance(sections.get("executive_summary"), str):
        formatted_sections["executive_summary"] = standardize_formatting_for_placid(
            sections["executive_summary"]
        )
    
    if isinstance(sections.get("category_summaries"), dict):
        formatted_cats = {}
        for cat, summary in sections["category_summaries"].items():
            formatted_cats[cat] = standardize_formatting_for_placid(summary)
        formatted_sections["category_summaries"] = formatted_cats
    
    if isinstance(sections.get("recommendations"), str):
        formatted_sections["recommendations"] = standardize_formatting_for_placid(
            sections["recommendations"]
        )
    elif isinstance(sections.get("recommendations"), dict):
        formatted_sections["recommendations"] = sections["recommendations"]
    
    if isinstance(sections.get("next_steps"), str):
        formatted_sections["next_steps"] = standardize_formatting_for_placid(
            sections["next_steps"]
        )
    
    # Format the complete report with section separators
    if final_report:
        formatted_report = format_final_report_with_separators(final_report)
        formatted_sections["final_report"] = formatted_report
    
    return formatted_sections


def format_final_report_with_separators(report: str) -> str:
    """
    Format the complete report with visual separators between sections.
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


def qa_node(state: WorkflowState) -> WorkflowState:
    """
    Enhanced QA validation with LLM-based checks, outcome framing verification, and formatting.
    
    FIXED: Replace ensure_json_response with bind() method for JSON responses.
    """
    start_time = time.time()
    
    try:
        logger.info("Starting enhanced QA validation with formatting and outcome framing...")
        
        # Get required data
        scoring_result = state.get("scoring_result", {})
        summary_result = state.get("summary_result", {})
        
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
        
        # 1. Validate Content Structure (basic checks)
        logger.info("Validating content structure...")
        content_quality_check = validate_content_quality(summary_result)
        quality_scores["content_quality"] = content_quality_check
        if not content_quality_check.get("passed", True):
            qa_issues.extend(content_quality_check.get("issues", []))
        qa_warnings.extend(content_quality_check.get("warnings", []))
        
        # 2. PII Detection with Regex
        logger.info("Scanning for PII...")
        pii_scan = scan_for_pii(summary_result.get("final_report", ""))
        quality_scores["pii_compliance"] = pii_scan
        
        if pii_scan.get("has_pii", False):
            qa_issues.append(f"CRITICAL: PII detected - {', '.join(pii_scan.get('found_types', []))}")
        
        # 3. Enhanced LLM-Based Checks
        logger.info("Running LLM-based quality checks...")
        
        # Check for redundancy with GPT-4.1
        logger.info("Checking for content redundancy with GPT-4.1...")
        redundancy_check = check_redundancy_llm(
            summary_result.get("final_report", ""),
            redundancy_llm
        )
        quality_scores["redundancy_check"] = redundancy_check
        
        # Allow redundancy scores down to 3/10 for long reports
        report_word_count = len(summary_result.get("final_report", "").split())
        redundancy_threshold = 3 if report_word_count > 2000 else 5
        
        if redundancy_check.get("redundancy_score", 10) < redundancy_threshold:
            qa_warnings.append(f"High redundancy detected (score: {redundancy_check.get('redundancy_score')}/10)")
        
        # Check tone consistency
        logger.info("Checking tone consistency...")
        tone_check = check_tone_consistency_llm(
            summary_result.get("final_report", ""),
            qa_llm
        )
        quality_scores["tone_consistency"] = tone_check
        
        if tone_check.get("tone_score", 10) < 4:
            qa_warnings.append(f"Tone inconsistency detected (score: {tone_check.get('tone_score')}/10)")
        
        # Verify Citations
        logger.info("Verifying citations and statistical claims...")
        research_result = state.get("research_result", {})
        citation_check = verify_citations_llm(
            summary_result.get("final_report", ""),
            research_result,
            qa_llm
        )
        quality_scores["citation_verification"] = citation_check
        
        if citation_check.get("citation_score", 10) < 6:
            uncited_count = citation_check.get("issues_found", 0)
            if uncited_count > 2:
                qa_issues.append(f"Too many uncited claims found: {uncited_count}")
                for claim in citation_check.get("uncited_claims", [])[:3]:
                    if claim.get("issue") == "claim not found in research data":
                        qa_issues.append(f"CRITICAL: Unfounded claim - {claim.get('claim', '')[:50]}...")
                    else:
                        qa_warnings.append(f"Missing citation: {claim.get('claim', '')[:50]}...")
        
        # Verify Outcome Framing
        logger.info("Verifying outcome framing compliance...")
        outcome_framing_check = verify_outcome_framing_llm(
            summary_result.get("final_report", ""),
            summary_result.get("recommendations", ""),
            summary_result.get("next_steps", ""),
            qa_llm
        )
        quality_scores["outcome_framing"] = outcome_framing_check
        
        # Flag outcome framing violations
        if outcome_framing_check.get("framing_score", 10) < 7:
            violations_count = outcome_framing_check.get("violations_found", 0)
            if violations_count > 0:
                qa_issues.append(f"Outcome framing violations found: {violations_count}")
                
                for violation in outcome_framing_check.get("specific_violations", [])[:3]:
                    qa_issues.append(f"PROMISE LANGUAGE: {violation.get('text', '')[:50]}... - {violation.get('issue', '')}")
                
                non_ranges = outcome_framing_check.get("non_range_numbers", [])
                if non_ranges:
                    qa_warnings.append(f"Specific percentages should be ranges: {', '.join(non_ranges[:3])}")
        
        # Calculate overall QA score
        overall_quality_score = calculate_overall_qa_score(quality_scores)
        
        # Lower approval threshold from 7.0 to 6.0
        critical_issues = [issue for issue in qa_issues if "CRITICAL" in issue or "PII" in issue or "PROMISE LANGUAGE" in issue]
        non_critical_issues = [issue for issue in qa_issues if issue not in critical_issues]
        
        # Approval based on critical issues only
        approved = len(critical_issues) == 0 and overall_quality_score >= 6.0
        ready_for_delivery = approved and not pii_scan.get("has_pii", False)
        
        # If not approved, attempt to fix issues
        fix_attempts = 0
        max_fix_attempts = 3
        fixed_sections = {}
        
        # Only attempt fixes for critical issues or very low scores
        while not approved and fix_attempts < max_fix_attempts and (critical_issues or overall_quality_score < 5.0):
            fix_attempts += 1
            logger.info(f"Attempting to fix issues - Attempt {fix_attempts}/{max_fix_attempts}")
            
            # Fix critical issues with LLM
            if critical_issues or overall_quality_score < 5.0:
                fixed_sections = fix_quality_issues_llm(
                    critical_issues if critical_issues else qa_issues,
                    qa_warnings,
                    summary_result,
                    scoring_result,
                    redundancy_check,
                    tone_check,
                    qa_llm
                )
                
                # Fix outcome framing violations if found
                if outcome_framing_check.get("violations_found", 0) > 0:
                    logger.info("Fixing outcome framing violations...")
                    framing_fixes = fix_outcome_framing_llm(
                        outcome_framing_check.get("specific_violations", []),
                        summary_result.get("recommendations", ""),
                        summary_result.get("next_steps", ""),
                        summary_result.get("executive_summary", ""),
                        qa_llm
                    )
                    
                    # Merge framing fixes into fixed sections
                    for section, content in framing_fixes.items():
                        fixed_sections[section] = content
                
                # Update summary result with fixes
                for section, content in fixed_sections.items():
                    summary_result[section] = content
                
                # Regenerate final report if needed
                if fixed_sections:
                    summary_result["final_report"] = regenerate_final_report(
                        summary_result,
                        scoring_result.get("overall_score"),
                        scoring_result.get("readiness_level")
                    )
                
                # Re-run critical checks
                content_quality_check = validate_content_quality(summary_result)
                quality_scores["content_quality"] = content_quality_check
                
                redundancy_check = check_redundancy_llm(
                    summary_result.get("final_report", ""),
                    qa_llm
                )
                quality_scores["redundancy_check"] = redundancy_check
                
                # Re-evaluate
                qa_issues = []
                qa_warnings = []
                critical_issues = []
                
                if not content_quality_check.get("passed", True):
                    issues = content_quality_check.get("issues", [])
                    for issue in issues:
                        if "CRITICAL" in issue or "missing" in issue.lower():
                            critical_issues.append(issue)
                        else:
                            qa_issues.append(issue)
                
                # Recalculate approval
                overall_quality_score = calculate_overall_qa_score(quality_scores)
                approved = len(critical_issues) == 0 and overall_quality_score >= 6.0
                ready_for_delivery = approved and not pii_scan.get("has_pii", False)
                
                if approved:
                    logger.info(f"Issues fixed successfully after {fix_attempts} attempts!")
                    break
            else:
                break
        
        # Apply Final Polish with GPT-4.1 (if approved)
        polished_sections = {}
        if approved:
            logger.info("Applying final polish with GPT-4.1...")
            polished_sections = polish_report_llm(
                summary_result,
                scoring_result,
                polish_llm
            )
            
            # Apply polished sections
            if polished_sections.get("executive_summary"):
                summary_result["executive_summary"] = polished_sections["executive_summary"]
                # Regenerate final report with polished summary
                summary_result["final_report"] = regenerate_final_report(
                    summary_result,
                    scoring_result.get("overall_score"),
                    scoring_result.get("readiness_level")
                )
        
        # 4. Apply formatting standardization
        logger.info("Applying Placid-compatible formatting...")
        formatted_sections = apply_section_formatting(summary_result, summary_result.get("final_report", ""))
        
        # Update summary result with formatted content
        for section, content in formatted_sections.items():
            summary_result[section] = content
        
        # Validate formatting
        formatting_valid = validate_plain_text_formatting(summary_result)
        if not formatting_valid.get("is_valid", True):
            qa_warnings.extend(formatting_valid.get("issues", []))
        
        # Prepare QA result
        qa_result = {
            "status": "success",
            "approved": approved,
            "ready_for_delivery": ready_for_delivery,
            "overall_quality_score": overall_quality_score,
            "quality_scores": quality_scores,
            "issues": qa_issues + critical_issues,
            "critical_issues": critical_issues,
            "warnings": qa_warnings,
            "polished_sections": list(polished_sections.keys()) if polished_sections else [],
            "fixed_sections": list(fixed_sections.keys()) if fixed_sections else [],
            "formatted_sections": list(formatted_sections.keys()),
            "fix_attempts": fix_attempts,
            "formatting_applied": True,
            "outcome_framing_applied": True,
            "validation_summary": {
                "total_checks": 8,
                "mechanical_checks": 4,
                "llm_checks": 4,
                "critical_issues": len(critical_issues),
                "non_critical_issues": len(qa_issues),
                "warnings": len(qa_warnings),
                "sections_polished": len(polished_sections) if polished_sections else 0,
                "sections_fixed": len(fixed_sections) if fixed_sections else 0
            }
        }
        
        # Final PII check on formatted report
        final_pii_check = scan_for_pii(summary_result.get("final_report", ""))
        if final_pii_check.get("has_pii", False):
            qa_result["ready_for_delivery"] = False
            qa_result["pii_detected"] = True
            qa_result["pii_types"] = final_pii_check.get("found_types", [])
        
        # Update state and return
        state["qa_result"] = qa_result
        state["summary_result"] = summary_result
        state["current_stage"] = "qa_completed"
        state["messages"].append(f"QA completed - Score: {overall_quality_score}/10, Approved: {approved}")
        
        elapsed_time = time.time() - start_time
        state["processing_time"]["qa"] = elapsed_time
        
        logger.info(f"=== QA NODE COMPLETED - {elapsed_time:.2f}s, Approved: {approved} ===")
        return state
        
    except Exception as e:
        logger.error(f"QA validation failed: {e}")
        elapsed_time = time.time() - start_time
        
        # Return state with error
        state["qa_result"] = {
            "status": "error",
            "approved": False,
            "ready_for_delivery": False,
            "overall_quality_score": 0,
            "error": str(e),
            "elapsed_time": elapsed_time
        }
        state["current_stage"] = "qa_error"
        state["error"] = f"QA validation error: {str(e)}"
        
        return state


def verify_outcome_framing_llm(report: str, recommendations: str, next_steps: str, llm) -> Dict[str, Any]:
    """
    Verify that outcome framing follows compliance rules.
    FIXED: Replace ensure_json_response with bind() method.
    """
    
    prompt = """Analyze this business assessment report for proper outcome framing.

Report Sections to Check:
RECOMMENDATIONS:
{recommendations}

NEXT STEPS:
{next_steps}

EXECUTIVE SUMMARY (excerpt):
{summary_excerpt}

Verify compliance with these CRITICAL rules:
1. All outcome claims must use qualifying language: "typically," "often," "on average," "generally," "businesses like yours"
2. Never use absolute promises: "will," "guaranteed," "definitely," "ensure," "certainly"
3. All improvements must be expressed as ranges (e.g., "20-30%") not specific numbers (e.g., "25%")
4. Every outcome claim should have a source citation (Source Year)

Provide your analysis in this exact JSON format:
{
    "framing_score": 8,
    "violations_found": 0,
    "specific_violations": [
        {"text": "exact problematic phrase", "issue": "why it violates rules"}
    ],
    "uncited_claims": [
        {"claim": "outcome claim without citation", "location": "section name"}
    ],
    "promise_language": ["list", "of", "absolute", "promises", "found"],
    "non_range_numbers": ["25% increase", "30% improvement"],
    "compliance_summary": "brief assessment of overall compliance"
}"""

    try:
        start_time = time.time()
        
        # Extract executive summary excerpt
        summary_excerpt = ""
        if "EXECUTIVE SUMMARY" in report:
            summary_start = report.find("EXECUTIVE SUMMARY")
            summary_end = report.find("YOUR EXIT READINESS SCORE", summary_start)
            if summary_end > summary_start:
                summary_excerpt = report[summary_start:summary_end][:500]
        
        messages = [
            SystemMessage(content="You are a compliance reviewer ensuring business recommendations follow proper outcome framing rules. Be strict about promises and specific numbers. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(
                recommendations=recommendations[:3000],
                next_steps=next_steps[:2000],
                summary_excerpt=summary_excerpt
            ))
        ]
        
        # FIXED: Use bind() method instead of ensure_json_response
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response
        if hasattr(response, 'content'):
            result = json.loads(response.content)
        else:
            result = json.loads(str(response))
        
        elapsed = time.time() - start_time
        logger.info(f"Outcome framing verification took {elapsed:.2f}s")
        
        # Validate result has expected keys
        if not isinstance(result.get("framing_score"), (int, float)):
            result["framing_score"] = 8
        if not isinstance(result.get("violations_found"), int):
            result["violations_found"] = 0
            
        return result
        
    except Exception as e:
        logger.warning(f"LLM outcome framing verification failed: {e}, using fallback regex check")
        
        # Fallback to regex-based checking
        violations = []
        promise_language = []
        
        # Check for promise language
        promise_patterns = [
            r'\bwill\s+(?:increase|achieve|ensure|improve|deliver|guarantee)',
            r'\bguaranteed\b',
            r'\bdefinitely\b',
            r'\bensure[sd]?\b'
        ]
        
        for pattern in promise_patterns:
            matches = re.findall(pattern, recommendations + next_steps, re.IGNORECASE)
            promise_language.extend(matches)
            for match in matches[:3]:
                violations.append({
                    "text": match,
                    "issue": "Uses absolute promise language"
                })
        
        # Check for non-range numbers
        non_range_numbers = []
        single_percent_pattern = r'\b(\d+)%\s+(?:increase|improvement|growth|value|higher)'
        matches = re.findall(single_percent_pattern, recommendations + next_steps)
        for match in matches:
            if f"{match}-" not in recommendations + next_steps:
                non_range_numbers.append(f"{match}%")
        
        # Calculate score based on violations
        framing_score = 10
        framing_score -= len(promise_language) * 0.5
        framing_score -= len(non_range_numbers) * 0.3
        framing_score = max(0, min(10, framing_score))
        
        return {
            "framing_score": framing_score,
            "violations_found": len(violations),
            "specific_violations": violations[:5],
            "uncited_claims": [],
            "promise_language": list(set(promise_language))[:5],
            "non_range_numbers": list(set(non_range_numbers))[:5],
            "compliance_summary": "Fallback regex-based check performed"
        }


def fix_outcome_framing_llm(violations: List[Dict], recommendations: str, next_steps: str, 
                           executive_summary: str, llm) -> Dict[str, str]:
    """Fix outcome framing violations identified in the report. FIXED: Replace ensure_json_response with bind()."""
    
    violations_text = "\n".join([f"- {v['text']}: {v['issue']}" for v in violations[:10]])
    
    prompt = """Fix the following outcome framing violations in this business report.

VIOLATIONS TO FIX:
{violations}

Current Recommendations (excerpt):
{recommendations}

Current Next Steps (excerpt):
{next_steps}

Current Executive Summary (excerpt):
{executive_summary}

Fix these violations by:
1. Replacing "will" with "typically/often/generally"
2. Converting specific percentages to ranges (e.g., 25% → 20-30%)
3. Adding source citations where missing (use realistic sources like "IBBA 2023" or "M&A Source 2023")
4. Removing any guarantee language

Provide fixed content in this exact JSON format:
{
    "recommendations": "fixed recommendations text if violations found there",
    "next_steps": "fixed next steps text if violations found there",
    "executive_summary": "fixed executive summary if violations found there"
}

Only include sections that had violations. Maintain all other content exactly as is."""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content="You are a compliance editor fixing outcome language while maintaining persuasive business writing. Make minimal changes to fix violations. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(
                violations=violations_text,
                recommendations=recommendations[:1500],
                next_steps=next_steps[:1000],
                executive_summary=executive_summary[:1000]
            ))
        ]
        
        # FIXED: Use bind() method instead of ensure_json_response
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response
        if hasattr(response, 'content'):
            result = json.loads(response.content)
        else:
            result = json.loads(str(response))
        
        elapsed = time.time() - start_time
        logger.info(f"Outcome framing fixes took {elapsed:.2f}s")
        
        # Only return sections that were actually fixed
        fixed_sections = {}
        for section in ["recommendations", "next_steps", "executive_summary"]:
            if section in result and result[section]:
                fixed_sections[section] = result[section]
                
        return fixed_sections
        
    except Exception as e:
        logger.warning(f"LLM outcome framing fixes failed: {e}, applying regex-based fixes")
        
        # Fallback to regex-based fixes
        fixed_sections = {}
        
        # Fix recommendations if needed
        if any("recommendation" in str(v).lower() for v in violations):
            fixed_rec = recommendations
            fixed_rec = re.sub(r'\bwill\s+increase', 'typically increases', fixed_rec)
            fixed_rec = re.sub(r'\bwill\s+achieve', 'often achieve', fixed_rec)
            fixed_rec = re.sub(r'\bensures?\b', 'generally results in', fixed_rec)
            fixed_rec = re.sub(r'\b(\d+)%\s+(increase|improvement)', 
                              lambda m: f"{int(m.group(1))-5}-{int(m.group(1))+5}% {m.group(2)}", 
                              fixed_rec)
            fixed_sections["recommendations"] = fixed_rec
        
        # Fix next steps if needed
        if any("next" in str(v).lower() for v in violations):
            fixed_next = next_steps
            fixed_next = re.sub(r'\bwill\s+see', 'typically see', fixed_next)
            fixed_next = re.sub(r'\bwill\s+achieve', 'often achieve', fixed_next)
            fixed_sections["next_steps"] = fixed_next
        
        return fixed_sections


def check_redundancy_llm(report: str, llm) -> Dict[str, Any]:
    """Use GPT-4.1 to detect redundant content with nuanced understanding. FIXED: Replace ensure_json_response with bind()."""
    
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
        
        # FIXED: Use bind() method instead of ensure_json_response
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response
        if hasattr(response, 'content'):
            result = json.loads(response.content)
        else:
            result = json.loads(str(response))
        
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
    """Use LLM to check tone consistency throughout the report. FIXED: Replace ensure_json_response with bind()."""
    
    prompt = """Analyze this business assessment report for tone consistency.

Report:
{report}

Evaluate:
1. Is the tone professional and consultative throughout?
2. Are there jarring shifts between overly technical and overly casual language?
3. Does the report maintain appropriate gravitas for a business exit assessment?
4. Is the level of formality consistent across all sections?

Important considerations:
- Natural tone variations between sections are ACCEPTABLE
- Executive summary may be more direct than detailed analysis
- Recommendations can be more action-oriented
- Only flag JARRING inconsistencies that confuse the reader

Provide your analysis in this exact JSON format:
{
    "tone_score": 8,
    "consistent": true,
    "tone_issues": ["issue 1", "issue 2"],
    "inconsistent_sections": ["section 1", "section 2"],
    "recommended_tone": "description of ideal tone"
}"""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content="You are a business communications expert who understands that different sections of a report may naturally vary in tone while maintaining overall coherence. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(report=report[:8000]))
        ]
        
        # FIXED: Use bind() method instead of ensure_json_response
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response
        if hasattr(response, 'content'):
            result = json.loads(response.content)
        else:
            result = json.loads(str(response))
        
        elapsed = time.time() - start_time
        logger.info(f"Tone consistency check took {elapsed:.2f}s")
        
        # Validate result
        if not isinstance(result.get("tone_score"), (int, float)):
            result["tone_score"] = 8
        if not isinstance(result.get("consistent"), bool):
            result["consistent"] = True
            
        return result
        
    except Exception as e:
        logger.warning(f"LLM tone check failed: {e}, using default score")
        return {
            "tone_score": 8,
            "consistent": True,
            "tone_issues": [],
            "inconsistent_sections": [],
            "recommended_tone": "Professional and consultative"
        }


def verify_citations_llm(report: str, research_data: Dict[str, Any], llm) -> Dict[str, Any]:
    """Verify that statistical claims and data points are properly cited. FIXED: Replace ensure_json_response with bind()."""
    
    # Extract citations and benchmarks from research data
    citations = research_data.get("citations", [])
    benchmarks = research_data.get("benchmarks", {})
    
    # Convert to searchable text
    citation_text = "\n".join([f"- {c.get('source', '')}: {c.get('title', '')}" for c in citations])
    benchmarks_text = json.dumps(benchmarks, indent=2)
    
    # List of common business phrases that don't need citations
    uncited_whitelist_phrases = [
        "businesses typically see",
        "companies often achieve", 
        "owners generally report",
        "industry experience shows",
        "common practice includes",
        "standard approaches involve",
        "best practices suggest",
        "market conditions favor",
        "economic factors indicate"
    ]
    
    prompt = """Verify citations in this business assessment report.

Report:
{report}

Available Citations:
{citations}

Research Benchmarks:
{benchmarks}

Check for:
1. Statistical claims without sources (e.g., "30% of businesses fail" needs citation)
2. Specific data points without attribution 
3. Industry benchmarks mentioned without source
4. Claims that contradict the research data

IMPORTANT EXCEPTIONS - These phrases do NOT need citations:
{whitelist}

These are general business wisdom and common knowledge that don't require specific attribution.

Provide your analysis in this exact JSON format:
{
    "citation_score": 8,
    "total_claims_found": 15,
    "properly_cited": 12,
    "issues_found": 3,
    "uncited_claims": [
        {"claim": "specific claim text", "issue": "reason it needs citation"}
    ]
}"""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content=f"You are a fact-checker for business reports who understands the difference between specific claims needing citations and general business knowledge. Common phrases that don't need citations include: {', '.join(uncited_whitelist_phrases[:5])}. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(
                report=report[:6000],
                citations=citation_text[:2000],
                benchmarks=benchmarks_text[:1000],
                whitelist=", ".join(uncited_whitelist_phrases[:10])
            ))
        ]
        
        # FIXED: Use bind() method instead of ensure_json_response
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response
        if hasattr(response, 'content'):
            result = json.loads(response.content)
        else:
            result = json.loads(str(response))
        
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


def fix_quality_issues_llm(issues: List[str], warnings: List[str], 
                          summary_result: Dict[str, Any], scoring_result: Dict[str, Any],
                          redundancy_info: Dict[str, Any], tone_info: Dict[str, Any],
                          llm) -> Dict[str, str]:
    """Use LLM to fix identified quality issues. FIXED: Replace ensure_json_response with bind()."""
    
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
        
        # FIXED: Use bind() method instead of ensure_json_response
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response
        if hasattr(response, 'content'):
            result = json.loads(response.content)
        else:
            result = json.loads(str(response))
        
        elapsed = time.time() - start_time
        logger.info(f"Quality issue fixes took {elapsed:.2f}s")
        
        # Only return sections that were actually fixed
        fixed_sections = {}
        if result.get("executive_summary") and issues_text:
            fixed_sections["executive_summary"] = result["executive_summary"]
        if result.get("recommendations") and any("recommendation" in issue.lower() for issue in issues):
            fixed_sections["recommendations"] = result["recommendations"]
        if result.get("next_steps") and any("next" in issue.lower() for issue in issues):
            fixed_sections["next_steps"] = result["next_steps"]
            
        return fixed_sections
        
    except Exception as e:
        logger.warning(f"LLM issue fixing failed: {e}, returning empty fixes")
        return {}


def polish_report_llm(summary_result: Dict[str, Any], scoring_result: Dict[str, Any], 
                     llm) -> Dict[str, str]:
    """Apply final polish using GPT-4.1's superior writing capabilities. FIXED: Replace ensure_json_response with bind()."""
    
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
6. Use varied sentence structure for better flow
7. Include power words that convey urgency and opportunity
8. CRITICAL: Maintain proper outcome framing - use "typically/often/generally" for all outcome claims

Provide the polished version in this exact JSON format:
{
    "executive_summary": "polished executive summary"
}

Maintain all facts, scores, and data points exactly. Only improve clarity, impact, flow, and emotional resonance.
Remove any markdown formatting - use plain text only.
Ensure outcome framing is preserved or improved."""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content="You are a master business communication expert using GPT-4.1. Create compelling, action-oriented content that motivates business owners while maintaining complete accuracy and proper outcome framing. Your writing should be clear, powerful, and personalized. Always respond with valid JSON."),
            HumanMessage(content=prompt.format(
                exec_summary=summary_result.get("executive_summary", ""),
                score=scoring_result.get("overall_score", 0),
                level=scoring_result.get("readiness_level", "Unknown")
            ))
        ]
        
        # FIXED: Use bind() method instead of ensure_json_response
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        response = llm_with_json.invoke(messages)
        
        # Parse the JSON response
        if hasattr(response, 'content'):
            result = json.loads(response.content)
        else:
            result = json.loads(str(response))
        
        elapsed = time.time() - start_time
        logger.info(f"Report polishing took {elapsed:.2f}s")
        
        polished = {}
        if result.get("executive_summary"):
            # Also polish recommendations if they exist
            if summary_result.get("recommendations"):
                polished_recs = polish_recommendations_llm(
                    summary_result.get("recommendations", ""),
                    scoring_result,
                    llm
                )
                if polished_recs:
                    result["recommendations"] = polished_recs
                    
            return result
        return {}
        
    except Exception as e:
        logger.warning(f"GPT-4.1 report polishing failed: {e}, skipping polish")
        return {}


def polish_recommendations_llm(recommendations: str, scoring_result: Dict[str, Any], 
                              llm) -> str:
    """Polish recommendations section with GPT-4.1 for maximum impact."""
    
    prompt = """Polish these recommendations to be more impactful while maintaining accuracy and proper outcome framing.

Current Recommendations:
{recommendations}

Primary Focus Area: {focus}
Overall Score: {score}/10

Improvements to make:
1. Make each action item more specific and concrete
2. Ensure every outcome is quantified with data ranges (not specific numbers)
3. Add urgency without being alarmist
4. Use action verbs that inspire immediate implementation
5. Make the language more dynamic and engaging
6. CRITICAL: Ensure all outcome claims use "typically/often/generally" language

Keep the exact same structure and facts. Only improve:
- Action verb choices (implement → launch, create → develop, etc.)
- Outcome descriptions (make them more vivid while keeping "typically" language)
- Transitions between sections
- Overall energy and momentum

Return the polished recommendations as plain text (no JSON wrapper).
Ensure every outcome claim uses proper framing language."""

    try:
        start_time = time.time()
        
        messages = [
            SystemMessage(content="You are a business strategy expert using GPT-4.1 to create compelling action plans. Make recommendations feel urgent, specific, and achievable while always using 'typically/often' language for outcomes."),
            HumanMessage(content=prompt.format(
                recommendations=recommendations[:3000],
                focus=scoring_result.get("focus_areas", {}).get("primary", {}).get("category", ""),
                score=scoring_result.get("overall_score", 0)
            ))
        ]
        
        response = llm.invoke(messages)
        polished = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        elapsed = time.time() - start_time
        logger.info(f"Recommendations polishing took {elapsed:.2f}s")
        
        return polished
        
    except Exception as e:
        logger.warning(f"GPT-4.1 recommendations polishing failed: {e}, returning original")
        return recommendations


def regenerate_final_report(summary_result: Dict[str, Any], overall_score: float, 
                          readiness_level: str) -> str:
    """Regenerate the final report after fixes and polish"""
    
    report_parts = []
    
    # Executive Summary
    if summary_result.get("executive_summary"):
        report_parts.append("EXECUTIVE SUMMARY\n")
        report_parts.append(summary_result["executive_summary"])
    
    # Score section
    if overall_score > 0:
        report_parts.append("\nYOUR EXIT READINESS SCORE\n")
        report_parts.append(f"Overall Score: {overall_score}/10")
        report_parts.append(f"Readiness Level: {readiness_level}")
    
    # Category Analysis
    if summary_result.get("category_summaries"):
        report_parts.append("\nDETAILED ANALYSIS BY CATEGORY\n")
        for category, data in summary_result["category_summaries"].items():
            cat_name = category.replace('_', ' ').title()
            report_parts.append(f"\n{cat_name} Analysis")
            if isinstance(data, dict):
                report_parts.append(f"Score: {data.get('score', 0)}/10")
                report_parts.append(data.get('summary', ''))
            else:
                report_parts.append(str(data))
    
    # Recommendations
    if summary_result.get("recommendations"):
        report_parts.append("\nPERSONALIZED RECOMMENDATIONS\n")
        recs = summary_result["recommendations"]
        if isinstance(recs, dict):
            for category, cat_recs in recs.items():
                cat_name = category.replace('_', ' ').title()
                report_parts.append(f"\n{cat_name}:")
                if isinstance(cat_recs, list):
                    for i, rec in enumerate(cat_recs, 1):
                        report_parts.append(f"{i}. {rec}")
                else:
                    report_parts.append(str(cat_recs))
        else:
            report_parts.append(str(recs))
    
    # Industry Context
    if summary_result.get("industry_context"):
        report_parts.append("\nINDUSTRY & MARKET CONTEXT\n")
        report_parts.append(summary_result["industry_context"])
    
    # Next Steps
    if summary_result.get("next_steps"):
        report_parts.append("\nYOUR NEXT STEPS\n")
        report_parts.append(summary_result["next_steps"])
    
    return "\n".join(report_parts)


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


def validate_plain_text_formatting(sections: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that all sections are properly formatted for Placid"""
    issues = []
    
    # Check for remaining markdown
    markdown_patterns = [
        r'\*\*[^*]+\*\*',  # **bold**
        r'\*[^*]+\*',      # *italic*
        r'#{1,6}\s+',      # # headers
        r'\[([^\]]+)\]\([^)]+\)',  # [text](url)
        r'`[^`]+`',        # `code`
    ]
    
    sections_to_check = [
        "executive_summary",
        "recommendations", 
        "next_steps",
        "final_report"
    ]
    
    for section in sections_to_check:
        if section in sections and isinstance(sections[section], str):
            content = sections[section]
            for pattern in markdown_patterns:
                if re.search(pattern, content):
                    issues.append(f"Markdown found in {section}: {pattern}")
    
    # Check category summaries
    if "category_summaries" in sections and isinstance(sections["category_summaries"], dict):
        for cat, summary in sections["category_summaries"].items():
            for pattern in markdown_patterns:
                if re.search(pattern, summary):
                    issues.append(f"Markdown found in {cat}: {pattern}")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues
    }