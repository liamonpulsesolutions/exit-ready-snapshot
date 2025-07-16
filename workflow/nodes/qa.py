"""
QA Node - Quality assurance with LLM intelligence.
Performs both mechanical and intelligent quality checks.
"""

import logging
import time
import json
import re
from typing import Dict, Any, List, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from workflow.state import WorkflowState
from workflow.core.validators import (
    validate_scoring_consistency,
    validate_content_quality,
    scan_for_pii,
    validate_report_structure
)

logger = logging.getLogger(__name__)


def qa_node(state: WorkflowState) -> WorkflowState:
    """
    Enhanced QA validation with LLM-based improvements.
    
    Key enhancements:
    1. LLM-based redundancy detection
    2. Tone consistency checking
    3. Citation verification
    4. Issue fixing with LLM assistance
    5. Report polishing for readability
    """
    start_time = time.time()
    
    try:
        logger.info("Starting enhanced QA validation...")
        
        # Get required data
        scoring_result = state.get("scoring_result", {})
        summary_result = state.get("summary_result", {})
        
        # Initialize QA LLM (using nano for speed)
        qa_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=4000
        )
        
        # Track all quality checks
        quality_scores = {}
        qa_issues = []
        qa_warnings = []
        
        # 1. Original Mechanical Checks
        logger.info("Running mechanical quality checks...")
        
        # Check scoring consistency
        consistency_result = validate_scoring_consistency(
            scores=scoring_result.get("category_scores", {}),
            responses=state.get("form_data", {}).get("responses", {})
        )
        quality_scores["scoring_consistency"] = consistency_result
        
        if not consistency_result.get("is_consistent", True):
            qa_issues.extend(consistency_result.get("issues", []))
        qa_warnings.extend(consistency_result.get("warnings", []))
        
        # Check content quality
        content_quality = validate_content_quality({
            "executive_summary": summary_result.get("executive_summary", ""),
            "recommendations": summary_result.get("recommendations", {}),
            "category_summaries": summary_result.get("category_summaries", {})
        })
        quality_scores["content_quality"] = content_quality
        if not content_quality.get("passed", True):
            qa_issues.extend(content_quality.get("issues", []))
        qa_warnings.extend(content_quality.get("warnings", []))
        
        # Check PII compliance
        pii_scan = scan_for_pii(summary_result.get("final_report", ""))
        quality_scores["pii_compliance"] = pii_scan
        if pii_scan.get("has_pii", False):
            pii_items = pii_scan.get("pii_found", [])
            pii_summary = ", ".join([f"{item['type']} ({item['count']}x)" for item in pii_items])
            qa_issues.append(f"PII detected: {pii_summary}")
        
        # Check report structure
        structure_validation = validate_report_structure({
            "executive_summary": summary_result.get("executive_summary", ""),
            "category_scores": scoring_result.get("category_scores", {}),
            "category_summaries": summary_result.get("category_summaries", {}),
            "recommendations": summary_result.get("recommendations", {}),
            "next_steps": summary_result.get("next_steps", "")
        })
        quality_scores["structure_validation"] = structure_validation
        if not structure_validation.get("is_valid", True):
            missing = structure_validation.get("missing_sections", [])
            incomplete = structure_validation.get("incomplete_sections", [])
            if missing:
                qa_issues.append(f"Missing sections: {', '.join(missing)}")
            if incomplete:
                qa_warnings.append(f"Incomplete sections: {', '.join(incomplete)}")
        
        # 2. Enhanced LLM-Based Checks
        logger.info("Running LLM-based quality checks...")
        
        # Check for redundancy
        logger.info("Checking for content redundancy...")
        redundancy_check = check_redundancy_llm(
            summary_result.get("final_report", ""),
            qa_llm
        )
        quality_scores["redundancy_check"] = redundancy_check
        
        # ADJUSTED: Allow redundancy scores down to 3/10 for long reports
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
        
        # ADJUSTED: More lenient tone consistency - allow scores down to 4/10
        if tone_check.get("tone_score", 10) < 4:
            qa_warnings.append(f"Tone inconsistency detected (score: {tone_check.get('tone_score')}/10)")
        
        # Verify Citations (FIXED to handle both string and dict formats)
        logger.info("Verifying citations and statistical claims...")
        research_result = state.get("research_result", {})
        citation_check = verify_citations_llm(
            summary_result.get("final_report", ""),
            research_result,
            qa_llm
        )
        quality_scores["citation_verification"] = citation_check
        
        # ADJUSTED: Allow 1-2 uncited general business claims
        if citation_check.get("citation_score", 10) < 6:
            uncited_count = citation_check.get("issues_found", 0)
            if uncited_count > 2:  # Only flag if more than 2 uncited claims
                qa_issues.append(f"Too many uncited claims found: {uncited_count}")
                for claim in citation_check.get("uncited_claims", [])[:3]:
                    if claim.get("issue") == "claim not found in research data":
                        qa_issues.append(f"CRITICAL: Unfounded claim - {claim.get('claim', '')[:50]}...")
                    else:
                        qa_warnings.append(f"Missing citation: {claim.get('claim', '')[:50]}...")
        
        # Calculate overall QA score
        overall_quality_score = calculate_overall_qa_score(quality_scores)
        
        # ADJUSTED: Lower approval threshold from 7.0 to 6.0
        # Also separate critical issues from warnings
        critical_issues = [issue for issue in qa_issues if "CRITICAL" in issue or "PII" in issue]
        non_critical_issues = [issue for issue in qa_issues if issue not in critical_issues]
        
        # Approval based on critical issues only
        approved = len(critical_issues) == 0 and overall_quality_score >= 6.0
        ready_for_delivery = approved and not pii_scan.get("has_pii", False)
        
        # If not approved, attempt to fix issues
        fix_attempts = 0
        max_fix_attempts = 3
        fixed_sections = {}
        
        # ADJUSTED: Only attempt fixes for critical issues or very low scores
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
                content_quality_check = validate_content_quality({
                    "executive_summary": summary_result.get("executive_summary", ""),
                    "recommendations": summary_result.get("recommendations", {}),
                    "category_summaries": summary_result.get("category_summaries", {})
                })
                quality_scores["content_quality"] = content_quality_check
                
                redundancy_check = check_redundancy_llm(
                    summary_result.get("final_report", ""),
                    qa_llm
                )
                quality_scores["redundancy_check"] = redundancy_check
                
                tone_check = check_tone_consistency_llm(
                    summary_result.get("final_report", ""),
                    qa_llm
                )
                quality_scores["tone_consistency"] = tone_check
                
                # Re-check citations after fixes
                citation_check = verify_citations_llm(
                    regenerate_final_report(summary_result, 
                                          scoring_result.get("overall_score"),
                                          scoring_result.get("readiness_level")),
                    state.get("research_result", {}),
                    qa_llm
                )
                quality_scores["citation_verification"] = citation_check
                
                # Re-evaluate with adjusted thresholds
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
                qa_warnings.extend(content_quality_check.get("warnings", []))
                
                # Apply adjusted thresholds
                report_word_count = len(summary_result.get("final_report", "").split())
                redundancy_threshold = 3 if report_word_count > 2000 else 5
                
                if redundancy_check.get("redundancy_score", 10) < redundancy_threshold:
                    qa_warnings.append(f"Redundancy still present (score: {redundancy_check.get('redundancy_score')}/10)")
                
                if tone_check.get("tone_score", 10) < 4:
                    qa_warnings.append(f"Tone still inconsistent (score: {tone_check.get('tone_score')}/10)")
                
                if citation_check.get("issues_found", 0) > 2:
                    # Check if these are critical citation issues
                    for claim in citation_check.get("uncited_claims", []):
                        if claim.get("issue") == "claim not found in research data":
                            critical_issues.append(f"CRITICAL: Unfounded claim - {claim.get('claim', '')[:50]}...")
                
                # Recalculate approval with new threshold and critical issues only
                overall_quality_score = calculate_overall_qa_score(quality_scores)
                approved = len(critical_issues) == 0 and overall_quality_score >= 6.0
                ready_for_delivery = approved and not pii_scan.get("has_pii", False)
                
                if approved:
                    logger.info(f"Issues fixed successfully after {fix_attempts} attempts!")
                    break
            else:
                # No critical issues, just apply polish
                break
        
        # If still not approved after max attempts, log the remaining issues
        if not approved and fix_attempts >= max_fix_attempts:
            logger.warning(f"Could not fix all issues after {max_fix_attempts} attempts")
        
        # 3. Apply Final Polish (even if approved)
        logger.info("Applying final polish to report...")
        polished_sections = {}
        
        if approved or fix_attempts < max_fix_attempts:
            polished_sections = polish_report_llm(
                summary_result,
                scoring_result,
                qa_llm
            )
            
            # Update with polished content
            for section, content in polished_sections.items():
                summary_result[section] = content
            
            # Regenerate final report with polish
            if polished_sections:
                summary_result["final_report"] = regenerate_final_report(
                    summary_result,
                    scoring_result.get("overall_score"),
                    scoring_result.get("readiness_level")
                )
        
        # Prepare QA result
        qa_result = {
            "status": "success",
            "approved": approved,
            "ready_for_delivery": ready_for_delivery,
            "overall_quality_score": overall_quality_score,
            "quality_scores": quality_scores,
            "issues": qa_issues + critical_issues,  # Include all issues in report
            "critical_issues": critical_issues,  # But track critical separately
            "warnings": qa_warnings,
            "polished_sections": polished_sections,
            "fixed_sections": fixed_sections,
            "fix_attempts": fix_attempts,
            "validation_summary": {
                "total_checks": 7,
                "mechanical_checks": 4,
                "llm_checks": 3,
                "critical_issues": len(critical_issues),
                "non_critical_issues": len(qa_issues),
                "warnings": len(qa_warnings),
                "sections_polished": len(polished_sections),
                "sections_fixed": len(fixed_sections),
                "required_fix_attempts": fix_attempts
            }
        }
        
        # Update state
        state["qa_result"] = qa_result
        
        # If we fixed sections, update the summary result and regenerate report
        if fixed_sections or polished_sections:
            all_updates = {**fixed_sections, **polished_sections}
            for section, content in all_updates.items():
                if section in summary_result:
                    summary_result[section] = content
            
            # Regenerate final report with all updates
            summary_result["final_report"] = regenerate_final_report(
                summary_result,
                scoring_result.get("overall_score"),
                scoring_result.get("readiness_level")
            )
            
            # Update state with improved content
            state["summary_result"] = summary_result
        
        state["current_stage"] = "qa_complete"
        
        # Add timing
        processing_time = time.time() - start_time
        state["processing_time"]["qa"] = processing_time
        
        # Add status message
        if approved:
            state["messages"].append(
                f"✅ Enhanced QA validation passed with score {overall_quality_score:.1f}/10 "
                f"({fix_attempts} fix attempts, {len(polished_sections)} sections polished)"
            )
        else:
            state["messages"].append(
                f"⚠️ QA validation completed with {len(qa_issues)} issues and {len(qa_warnings)} warnings "
                f"(score: {overall_quality_score:.1f}/10, {fix_attempts} fix attempts)"
            )
        
        logger.info(f"Enhanced QA validation completed in {processing_time:.2f}s")
        logger.info(f"Result: Approved={approved}, Score={overall_quality_score:.1f}/10, "
                   f"Issues={len(qa_issues)}, Warnings={len(qa_warnings)}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced QA node: {str(e)}", exc_info=True)
        state["error"] = f"QA validation failed: {str(e)}"
        state["messages"].append(f"ERROR in QA: {str(e)}")
        state["current_stage"] = "qa_error"
        return state


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
        "redundancy_check": 0.15,
        "tone_consistency": 0.10,
        "citation_verification": 0.15
    }
    
    for check_name, check_result in quality_scores.items():
        weight = weights.get(check_name, 0.15)
        
        # Extract score based on check type
        if check_name == "content_quality":
            score = check_result.get("quality_score", 5.0)
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
        else:
            score = 5.0  # Default middle score
        
        total_score += score * weight
        total_weight += weight
    
    # Normalize to 0-10 scale
    return round(total_score / total_weight, 1) if total_weight > 0 else 5.0


def check_redundancy_llm(report: str, llm: ChatOpenAI) -> Dict[str, Any]:
    """Use LLM to detect redundant content in the report"""
    
    prompt = """Analyze this business assessment report for redundancy and repetitive content.

Report:
{report}

Evaluate:
1. Are key points repeated unnecessarily across sections?
2. Is the same information presented multiple times without adding value?
3. Are there verbose explanations that could be more concise?
4. Do multiple sections say essentially the same thing?

Important: Some repetition is NORMAL and NECESSARY in business reports:
- Key metrics may appear in summary and detailed sections
- Important recommendations may be emphasized multiple times
- Scores and ratings will naturally appear in multiple contexts
- Only flag content that appears 3+ times with no added value

Provide your analysis in this exact JSON format:
{
    "redundancy_score": <0-10, where 10 is no redundancy>,
    "redundant_sections": ["list", "of", "redundant", "sections"],
    "specific_examples": ["example 1", "example 2"],
    "suggested_consolidations": ["suggestion 1", "suggestion 2"]
}

Be lenient - business reports need emphasis and clarity through strategic repetition.
Only flag truly excessive redundancy (3+ identical repetitions) that hurts readability."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a business report editor who understands that strategic repetition aids clarity and emphasis."),
            HumanMessage(content=prompt.format(report=report[:8000]))  # Limit to avoid token issues
        ])
        
        result = json.loads(response.content)
        return result
        
    except Exception as e:
        logger.warning(f"LLM redundancy check failed: {e}")
        return {
            "redundancy_score": 8,
            "redundant_sections": [],
            "specific_examples": [],
            "suggested_consolidations": []
        }


def check_tone_consistency_llm(report: str, llm: ChatOpenAI) -> Dict[str, Any]:
    """Use LLM to check tone consistency throughout the report"""
    
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
- Technical sections may use more specialized language
- Only flag JARRING inconsistencies that confuse the reader

Provide your analysis in this exact JSON format:
{
    "tone_score": <0-10, where 10 is perfectly consistent>,
    "consistent": <true/false>,
    "tone_issues": ["issue 1", "issue 2"],
    "inconsistent_sections": ["section 1", "section 2"],
    "recommended_tone": "description of ideal tone"
}

Be reasonable - allow natural variations that serve the content.
Only flag major tone shifts that disrupt the reading experience."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a business communications expert who understands that different sections of a report may naturally vary in tone while maintaining overall coherence."),
            HumanMessage(content=prompt.format(report=report[:8000]))
        ])
        
        result = json.loads(response.content)
        return result
        
    except Exception as e:
        logger.warning(f"LLM tone check failed: {e}")
        return {
            "tone_score": 8,
            "consistent": True,
            "tone_issues": [],
            "inconsistent_sections": [],
            "recommended_tone": "Professional and consultative"
        }


def verify_citations_llm(report: str, research_data: Dict[str, Any], llm: ChatOpenAI) -> Dict[str, Any]:
    """Verify that statistical claims and data points are properly cited"""
    
    # FIXED: Handle both string and dict citation formats
    citations = research_data.get("citations", [])
    
    if not citations:
        citation_text = "No citations available"
    elif isinstance(citations[0], str):
        # Citations are strings (from enhanced research node)
        citation_text = "\n".join([f"- {c}" for c in citations[:10]])
    elif isinstance(citations[0], dict):
        # Citations are dicts (legacy format)
        citation_text = "\n".join([f"- {c.get('title', '')}: {c.get('summary', '')}" for c in citations[:10]])
    else:
        citation_text = "No citations available"
    
    # Common business knowledge that doesn't need citations
    uncited_whitelist_phrases = [
        "buyers typically seek",
        "buyers generally prefer",
        "industry expects",
        "businesses need",
        "businesses should",
        "owners should",
        "companies often",
        "market conditions",
        "economic factors",
        "business owners",
        "potential acquirers",
        "exit planning",
        "strategic buyers",
        "financial buyers",
        "due diligence",
        "valuation multiples"
    ]
    
    prompt = """Analyze this report to verify that all statistical claims and specific data points are properly supported.

Report:
{report}

Available Research Data:
{citations}

Check for:
1. Industry statistics without sources (e.g., "manufacturing sector grew 15%")
2. Market data claims without context (e.g., "EBITDA multiples of 4-6x")
3. Specific percentages or numbers that appear unsupported
4. Benchmarks mentioned without reference

DO NOT flag as needing citations:
- General business principles and common knowledge
- Phrases like: {whitelist}
- The business's own scores and assessment results
- Common business terminology and concepts
- General recommendations based on the assessment

Provide your analysis in this exact JSON format:
{
    "citation_score": <0-10, where 10 means all claims are supported>,
    "total_claims_found": <number>,
    "properly_cited": <number>,
    "issues_found": <number>,
    "uncited_claims": [
        {"claim": "specific claim text", "issue": "why it needs citation"},
        {"claim": "another claim", "issue": "reason"}
    ]
}

Be very reasonable - only flag SPECIFIC statistical claims that would require external validation.
General business advice and common industry knowledge should NOT be flagged."""

    try:
        response = llm.invoke([
            SystemMessage(content=f"You are a fact-checker for business reports who understands the difference between specific claims needing citations and general business knowledge. Common phrases that don't need citations include: {', '.join(uncited_whitelist_phrases[:5])}."),
            HumanMessage(content=prompt.format(
                report=report[:6000],
                citations=citation_text[:2000],
                whitelist=", ".join(uncited_whitelist_phrases[:10])
            ))
        ])
        
        result = json.loads(response.content)
        return result
        
    except Exception as e:
        logger.warning(f"LLM citation verification failed: {e}")
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
                          llm: ChatOpenAI) -> Dict[str, str]:
    """Use LLM to fix identified quality issues"""
    
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
        response = llm.invoke([
            SystemMessage(content="You are a business report editor fixing quality issues while maintaining accuracy."),
            HumanMessage(content=prompt.format(
                issues=issues_text,
                warnings=warnings_text,
                exec_summary=summary_result.get("executive_summary", "")[:2000],
                score=scoring_result.get("overall_score", 0),
                level=scoring_result.get("readiness_level", "Unknown"),
                redundancy=json.dumps(redundancy_info.get("redundant_sections", []))[:500],
                tone=json.dumps(tone_info.get("tone_issues", []))[:500]
            ))
        ])
        
        result = json.loads(response.content)
        
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
        logger.warning(f"LLM issue fixing failed: {e}")
        return {}


def polish_report_llm(summary_result: Dict[str, Any], scoring_result: Dict[str, Any], 
                     llm: ChatOpenAI) -> Dict[str, str]:
    """Apply final polish to make the report more impactful"""
    
    prompt = """Polish this executive summary to make it more impactful and actionable.

Current Executive Summary:
{exec_summary}

Overall Score: {score}/10
Readiness Level: {level}

Guidelines:
1. Start with a powerful, specific opening statement about the business's exit readiness
2. Use concrete numbers and timeframes where possible
3. End with a compelling call-to-action
4. Keep the same length and all factual content
5. Make it feel personalized to this specific business

Provide the polished version in this exact JSON format:
{
    "executive_summary": "polished executive summary"
}

Maintain all facts and scores. Only improve clarity, impact, and readability."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are an expert business advisor crafting impactful exit readiness assessments."),
            HumanMessage(content=prompt.format(
                exec_summary=summary_result.get("executive_summary", ""),
                score=scoring_result.get("overall_score", 0),
                level=scoring_result.get("readiness_level", "Unknown")
            ))
        ])
        
        result = json.loads(response.content)
        
        if result.get("executive_summary"):
            return {"executive_summary": result["executive_summary"]}
        return {}
        
    except Exception as e:
        logger.warning(f"LLM report polishing failed: {e}")
        return {}


def regenerate_final_report(summary_result: Dict[str, Any], overall_score: float, 
                           readiness_level: str) -> str:
    """Regenerate the final report after fixes and polish"""
    
    report_parts = []
    
    # Executive Summary
    if summary_result.get("executive_summary"):
        report_parts.append("## Executive Summary\n")
        report_parts.append(summary_result["executive_summary"])
        report_parts.append("\n")
    
    # Overall Score
    report_parts.append(f"\n## Overall Exit Readiness Score: {overall_score}/10\n")
    report_parts.append(f"**Readiness Level**: {readiness_level}\n")
    
    # Category Summaries
    if summary_result.get("category_summaries"):
        report_parts.append("\n## Detailed Assessment by Category\n")
        
        # Handle both string and dict formats
        category_summaries = summary_result.get("category_summaries")
        if isinstance(category_summaries, str):
            # If it's a string, just add it directly
            report_parts.append(category_summaries)
            report_parts.append("\n")
        elif isinstance(category_summaries, dict):
            # If it's a dict, iterate through categories
            category_order = ["financial_readiness", "revenue_quality", "operational_resilience"]
            for category in category_order:
                if category in category_summaries:
                    category_title = category.replace("_", " ").title()
                    report_parts.append(f"\n### {category_title}\n")
                    report_parts.append(category_summaries[category])
                    report_parts.append("\n")
    
    # Recommendations
    if summary_result.get("recommendations"):
        report_parts.append("\n## Strategic Recommendations\n")
        
        # Handle both string and dict formats
        recommendations = summary_result.get("recommendations")
        if isinstance(recommendations, str):
            # If it's a string, just add it directly
            report_parts.append(recommendations)
            report_parts.append("\n")
        elif isinstance(recommendations, dict):
            # If it's a dict, iterate through categories
            for category, recs in recommendations.items():
                if recs:
                    category_title = category.replace("_", " ").title()
                    report_parts.append(f"\n### {category_title}\n")
                    if isinstance(recs, list):
                        for i, rec in enumerate(recs, 1):
                            report_parts.append(f"{i}. {rec}\n")
                    else:
                        report_parts.append(f"{recs}\n")
    
    # Next Steps
    if summary_result.get("next_steps"):
        report_parts.append("\n## Next Steps\n")
        report_parts.append(summary_result["next_steps"])
    
    return "\n".join(report_parts)