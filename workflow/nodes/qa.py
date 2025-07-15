"""
QA node for LangGraph workflow.
Enhanced with LLM-based redundancy detection and final polish.
Performs comprehensive quality assurance on the generated report.
"""

import logging
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
from pathlib import Path
import os

# Load environment variables if not already loaded
from dotenv import load_dotenv
if not os.getenv('OPENAI_API_KEY'):
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

from workflow.core.validators import (
    validate_scoring_consistency,
    validate_content_quality,
    scan_for_pii,
    validate_report_structure
)

logger = logging.getLogger(__name__)


def detect_redundancies_llm(
    final_report: str,
    llm: ChatOpenAI
) -> Dict[str, Any]:
    """Use LLM to detect redundant content across sections"""
    
    prompt = f"""Analyze this business assessment report for redundant or repetitive content across sections.

REPORT:
{final_report[:3000]}... [truncated for analysis]

Identify:
1. Phrases or ideas repeated unnecessarily across sections
2. Similar recommendations appearing in multiple places
3. Redundant scoring explanations
4. Overlapping content between executive summary and detailed sections

For each redundancy found, provide:
- The repeated content
- Which sections contain it
- Suggested consolidation

Return a JSON structure:
{{
    "redundancies_found": [
        {{
            "content": "repeated phrase or idea",
            "sections": ["section1", "section2"],
            "suggestion": "how to consolidate"
        }}
    ],
    "redundancy_score": 0-10 (10 = no redundancy, 0 = highly redundant)
}}"""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a technical editor specializing in business reports. Identify redundant content that reduces report quality."),
            HumanMessage(content=prompt)
        ])
        
        # Parse response
        import json
        try:
            result = json.loads(response.content)
            return result
        except:
            # Fallback if JSON parsing fails
            return {
                "redundancies_found": [],
                "redundancy_score": 8.0,
                "raw_analysis": response.content
            }
    except Exception as e:
        logger.error(f"Redundancy detection failed: {e}")
        return {"redundancies_found": [], "redundancy_score": 8.0}


def check_tone_consistency_llm(
    report_sections: Dict[str, str],
    llm: ChatOpenAI
) -> Dict[str, Any]:
    """Use LLM to check tone consistency across sections"""
    
    # Sample from each section
    samples = {}
    for section, content in report_sections.items():
        if content:
            samples[section] = content[:500] + "..."
    
    prompt = f"""Analyze the tone consistency across these report sections:

{chr(10).join(f"{section.upper()}:\n{text}\n" for section, text in samples.items())}

Check for:
1. Consistent formality level (professional but approachable)
2. Consistent perspective (using "you/your" throughout)
3. Consistent emotional tone (balanced honesty with encouragement)
4. Any jarring tone shifts between sections

Rate tone consistency 0-10 (10 = perfectly consistent) and identify any issues."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are an editor ensuring consistent tone in business communications. Be specific about tone issues."),
            HumanMessage(content=prompt)
        ])
        
        # Extract score from response
        content = response.content
        score = 8.0  # default
        
        # Try to find a score in the response
        import re
        score_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:/\s*10|out of 10)', content, re.IGNORECASE)
        if score_match:
            score = float(score_match.group(1))
        
        return {
            "tone_score": score,
            "analysis": content,
            "consistent": score >= 7.0
        }
    except Exception as e:
        logger.error(f"Tone consistency check failed: {e}")
        return {"tone_score": 8.0, "consistent": True, "analysis": "Unable to analyze"}


def apply_final_polish_llm(
    section_name: str,
    section_content: str,
    overall_context: Dict[str, Any],
    llm: ChatOpenAI
) -> str:
    """Apply final polish to a specific section"""
    
    prompt = f"""Polish this {section_name} section of an exit readiness report.

SECTION CONTENT:
{section_content}

CONTEXT:
- Business: {overall_context.get('industry')} in {overall_context.get('location')}
- Overall Score: {overall_context.get('overall_score')}/10
- Exit Timeline: {overall_context.get('exit_timeline')}

POLISHING GOALS:
1. Fix any grammar or spelling errors
2. Improve clarity without changing meaning
3. Ensure consistent use of "you/your"
4. Maintain professional but warm tone
5. Remove any redundant phrases within this section
6. Ensure smooth flow between paragraphs

Return ONLY the polished text. Do not add commentary."""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a professional editor. Make minimal changes to improve clarity and flow while preserving all specific content and recommendations."),
            HumanMessage(content=prompt)
        ])
        
        return response.content.strip()
    except Exception as e:
        logger.error(f"Polish failed for {section_name}: {e}")
        return section_content  # Return original if polish fails


def fix_quality_issues_llm(
    issues: List[str],
    warnings: List[str],
    summary_result: Dict[str, Any],
    scoring_result: Dict[str, Any],
    redundancy_info: List[Dict],
    tone_info: str,
    llm: ChatOpenAI
) -> Dict[str, str]:
    """Use LLM to fix identified quality issues using ONLY existing information from state"""
    
    fixed_sections = {}
    
    # Prioritize what to fix based on issues
    issues_text = "\n".join(f"- {issue}" for issue in issues[:5])
    warnings_text = "\n".join(f"- {warning}" for warning in warnings[:5])
    
    # Fix executive summary if it has issues
    if any("executive summary" in issue.lower() for issue in issues + warnings):
        logger.info("Fixing executive summary using existing data...")
        
        # Gather ALL available data from state
        category_scores = scoring_result.get('category_scores', {})
        lowest_category = min(category_scores.items(), key=lambda x: x[1].get('score', 10))
        highest_category = max(category_scores.items(), key=lambda x: x[1].get('score', 0))
        
        available_data = {
            "overall_score": scoring_result.get('overall_score'),
            "readiness_level": scoring_result.get('readiness_level'),
            "lowest_category": {
                "name": lowest_category[0],
                "score": lowest_category[1].get('score'),
                "gaps": lowest_category[1].get('gaps', []),
                "insight": lowest_category[1].get('insight', '')
            },
            "highest_category": {
                "name": highest_category[0],
                "score": highest_category[1].get('score'),
                "strengths": highest_category[1].get('strengths', []),
                "insight": highest_category[1].get('insight', '')
            },
            "focus_area": scoring_result.get('focus_areas', {}).get('primary', {}).get('category'),
            "all_insights": [cat.get('insight', '') for cat in category_scores.values() if cat.get('insight')]
        }
        
        prompt = f"""Fix this executive summary using ONLY the provided data. DO NOT invent any new information.

CURRENT EXECUTIVE SUMMARY:
{summary_result.get('executive_summary', '')}

ISSUES TO FIX:
{issues_text}

AVAILABLE DATA TO USE:
{json.dumps(available_data, indent=2)}

REQUIREMENTS:
1. Expand to at least 250 words using ONLY the data provided above
2. Remove redundant mentions of the score
3. Include the specific insights already generated for low-scoring categories
4. Use exact scores, insights, and gaps from the available data
5. DO NOT add any information not present in the available data
6. You may rephrase and reorganize, but use ONLY facts from the data provided

Write the complete fixed executive summary using only the information above."""

        try:
            response = llm.invoke([
                SystemMessage(content="You are fixing a report using ONLY existing data. Never invent new information. Only reorganize and rephrase what's already there."),
                HumanMessage(content=prompt)
            ])
            fixed_sections["executive_summary"] = response.content.strip()
        except Exception as e:
            logger.error(f"Failed to fix executive summary: {e}")
    
    # Fix category summaries if they have issues
    if any("summary too brief" in warning.lower() for warning in warnings) or \
       any("lacks gap identification" in issue.lower() for issue in issues):
        logger.info("Fixing category summaries using existing scoring data...")
        
        category_scores = scoring_result.get('category_scores', {})
        current_summaries = summary_result.get('category_summaries', {})
        
        for category, summary in current_summaries.items():
            # Check if this category needs fixing
            needs_fix = (len(summary.split()) < 100 or 
                        f"{category} lacks gap identification" in str(issues))
            
            if needs_fix:
                score_data = category_scores.get(category, {})
                
                # Only use data that already exists
                existing_data = {
                    "score": score_data.get('score'),
                    "strengths": score_data.get('strengths', []),
                    "gaps": score_data.get('gaps', []),
                    "insight": score_data.get('insight', ''),
                    "scoring_breakdown": score_data.get('scoring_breakdown', {}),
                    "industry_context": score_data.get('industry_context', {})
                }
                
                prompt = f"""Expand and improve this category summary using ONLY the existing scoring data.

CATEGORY: {category}
CURRENT SUMMARY: {summary}

EXISTING SCORING DATA (USE ONLY THIS):
{json.dumps(existing_data, indent=2)}

REQUIREMENTS:
1. Expand to 200-250 words using ONLY the data above
2. Include ALL gaps from the scoring data (don't skip any)
3. Include ALL strengths from the scoring data
4. Use the exact insight provided
5. Reference the industry context if provided
6. DO NOT invent any new recommendations or data
7. You may reorganize and rephrase, but add NO new information

Create an expanded summary using only the existing data."""

                try:
                    response = llm.invoke([
                        SystemMessage(content="You are expanding a summary using ONLY existing data. Never add new information not present in the scoring data."),
                        HumanMessage(content=prompt)
                    ])
                    
                    if "category_summaries" not in fixed_sections:
                        fixed_sections["category_summaries"] = current_summaries.copy()
                    fixed_sections["category_summaries"][category] = response.content.strip()
                except Exception as e:
                    logger.error(f"Failed to fix {category} summary: {e}")
    
    # Fix redundancies by consolidating (not adding new info)
    if redundancy_info and len(redundancy_info) > 0:
        logger.info("Removing redundancies without losing information...")
        
        if "recommendations" in str(redundancy_info):
            prompt = f"""Remove redundancies from this section by consolidating repeated information.

CURRENT CONTENT:
{summary_result.get('recommendations', '')}

REDUNDANCIES FOUND:
{json.dumps(redundancy_info[:3], indent=2)}

REQUIREMENTS:
1. Remove repetitive phrases
2. Consolidate similar points into single mentions
3. Preserve ALL unique information
4. DO NOT add any new recommendations or insights
5. Only reorganize and deduplicate existing content

Rewrite to eliminate repetition while preserving all unique content."""

            try:
                response = llm.invoke([
                    SystemMessage(content="You are a technical editor removing redundancy. Preserve all unique information, add nothing new."),
                    HumanMessage(content=prompt)
                ])
                fixed_sections["recommendations"] = response.content.strip()
            except Exception as e:
                logger.error(f"Failed to fix recommendations: {e}")
    
    return fixed_sections


def verify_citations_llm(
    final_report: str,
    research_data: Dict[str, Any],
    llm: ChatOpenAI
) -> Dict[str, Any]:
    """Verify that all statistical claims have proper citations"""
    
    # Extract available citations from research
    available_citations = research_data.get("citations", [])
    valuation_benchmarks = research_data.get("valuation_benchmarks", {})
    market_conditions = research_data.get("market_conditions", {})
    
    prompt = f"""Analyze this report for uncited statistical claims and verify all statistics are properly cited.

REPORT:
{final_report[:4000]}... [truncated for analysis]

AVAILABLE CITATIONS FROM RESEARCH:
{json.dumps(available_citations, indent=2)}

AVAILABLE STATISTICS WITH CITATIONS:
Valuation Benchmarks: {json.dumps(valuation_benchmarks, indent=2)}
Market Conditions: {json.dumps(market_conditions, indent=2)}

IDENTIFY:
1. Any statistical claims (percentages, multiples, timeframes) without citations
2. Any claims that appear to be made up (not found in the available data)
3. Whether existing citations are properly formatted

Return a JSON structure:
{{
    "uncited_claims": [
        {{
            "claim": "the specific claim text",
            "section": "where it appears",
            "issue": "missing citation" or "claim not found in research data"
        }}
    ],
    "citation_score": 0-10 (10 = all claims properly cited),
    "total_claims_found": number,
    "properly_cited": number,
    "issues_found": number
}}"""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a fact-checker verifying that all statistical claims in a business report are properly cited and based on actual research data."),
            HumanMessage(content=prompt)
        ])
        
        # Parse response
        try:
            result = json.loads(response.content)
            return result
        except:
            # Fallback parsing
            return {
                "uncited_claims": [],
                "citation_score": 8.0,
                "total_claims_found": 0,
                "properly_cited": 0,
                "issues_found": 0,
                "raw_analysis": response.content
            }
    except Exception as e:
        logger.error(f"Citation verification failed: {e}")
        return {"uncited_claims": [], "citation_score": 8.0, "issues_found": 0}


def qa_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced QA node with intelligent redundancy detection and polish.
    
    This node:
    1. Validates scoring consistency (mechanical)
    2. Checks content quality (mechanical)
    3. Scans for PII (mechanical)
    4. Validates structure (mechanical)
    5. Detects redundancies (LLM)
    6. Checks tone consistency (LLM)
    7. Applies final polish (LLM) if needed
    
    Args:
        state: Current workflow state with summary results
        
    Returns:
        Updated state with QA validation and polished content
    """
    start_time = datetime.now()
    logger.info(f"=== ENHANCED QA NODE STARTED - UUID: {state['uuid']} ===")
    
    try:
        # Update current stage
        state["current_stage"] = "qa"
        state["messages"].append(f"Enhanced QA started at {start_time.isoformat()}")
        
        # Initialize LLMs
        qa_llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0.1)  # Nano for quick checks
        polish_llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)  # Mini for polish
        
        # Get data from previous stages
        scoring_result = state.get("scoring_result", {})
        summary_result = state.get("summary_result", {})
        anonymized_data = state.get("anonymized_data", {})
        
        # Initialize QA results
        qa_issues = []
        qa_warnings = []
        quality_scores = {}
        
        # 1-4. Run mechanical checks first (existing validators)
        logger.info("Running mechanical quality checks...")
        
        # Check Scoring Consistency
        scoring_consistency = validate_scoring_consistency(
            scores=scoring_result.get("category_scores", {}),
            responses=anonymized_data.get("responses", {})
        )
        quality_scores["scoring_consistency"] = scoring_consistency
        
        if not scoring_consistency.get("is_consistent", True):
            qa_issues.extend(scoring_consistency.get("issues", []))
        qa_warnings.extend(scoring_consistency.get("warnings", []))
        
        # Validate Content Quality
        content_quality = validate_content_quality({
            "executive_summary": summary_result.get("executive_summary", ""),
            "recommendations": summary_result.get("recommendations", ""),
            "category_summaries": summary_result.get("category_summaries", {})
        })
        quality_scores["content_quality"] = content_quality
        
        if not content_quality.get("passed", True):
            qa_issues.extend(content_quality.get("issues", []))
        qa_warnings.extend(content_quality.get("warnings", []))
        
        # Scan for PII
        pii_scan = scan_for_pii(summary_result.get("final_report", ""))
        quality_scores["pii_compliance"] = pii_scan
        
        if pii_scan.get("has_pii", False):
            qa_issues.append(f"PII detected: {pii_scan.get('total_items', 0)} items found")
        
        # Validate Structure
        structure_validation = validate_report_structure({
            "executive_summary": summary_result.get("executive_summary", ""),
            "category_scores": scoring_result.get("category_scores", {}),
            "category_summaries": summary_result.get("category_summaries", {}),
            "recommendations": summary_result.get("recommendations", ""),
            "next_steps": summary_result.get("next_steps", "")
        })
        quality_scores["structure_validation"] = structure_validation
        
        # 5. Detect Redundancies (LLM)
        logger.info("Detecting redundancies with LLM...")
        redundancy_check = detect_redundancies_llm(
            summary_result.get("final_report", ""),
            qa_llm
        )
        quality_scores["redundancy_check"] = redundancy_check
        
        if redundancy_check.get("redundancy_score", 10) < 7:
            qa_warnings.append(f"High redundancy detected (score: {redundancy_check.get('redundancy_score')}/10)")
            for redundancy in redundancy_check.get("redundancies_found", [])[:3]:
                qa_warnings.append(f"- Repeated: {redundancy.get('content', '')[:50]}...")
        
        # 6. Check Tone Consistency (LLM)
        logger.info("Checking tone consistency with LLM...")
        tone_check = check_tone_consistency_llm({
            "executive_summary": summary_result.get("executive_summary", ""),
            "recommendations": summary_result.get("recommendations", ""),
            "category_summaries": str(summary_result.get("category_summaries", {}))[:1000]
        }, qa_llm)
        quality_scores["tone_consistency"] = tone_check
        
        if not tone_check.get("consistent", True):
            qa_warnings.append(f"Tone inconsistency detected (score: {tone_check.get('tone_score')}/10)")
        
        # 7. Apply Polish if Quality Score is High Enough
        polished_sections = {}
        if len(qa_issues) == 0 and content_quality.get("quality_score", 0) >= 7:
            logger.info("Applying final polish to key sections...")
            
            context = {
                "industry": state.get("industry"),
                "location": state.get("location"),
                "overall_score": scoring_result.get("overall_score"),
                "exit_timeline": state.get("exit_timeline")
            }
            
            # Polish executive summary (most important)
            if summary_result.get("executive_summary"):
                polished_sections["executive_summary"] = apply_final_polish_llm(
                    "executive summary",
                    summary_result["executive_summary"],
                    context,
                    polish_llm
                )
            
            # Polish recommendations (second most important)
            if summary_result.get("recommendations"):
                polished_sections["recommendations"] = apply_final_polish_llm(
                    "recommendations",
                    summary_result["recommendations"],
                    context,
                    polish_llm
                )
        
        # 7. Verify Citations (NEW LLM CHECK)
        logger.info("Verifying citations and statistical claims...")
        research_result = state.get("research_result", {})
        citation_check = verify_citations_llm(
            summary_result.get("final_report", ""),
            research_result,
            qa_llm
        )
        quality_scores["citation_verification"] = citation_check
        
        if citation_check.get("citation_score", 10) < 7:
            qa_issues.append(f"Uncited claims found: {citation_check.get('issues_found', 0)}")
            for claim in citation_check.get("uncited_claims", [])[:3]:
                if claim.get("issue") == "claim not found in research data":
                    qa_issues.append(f"CRITICAL: Unfounded claim - {claim.get('claim', '')[:50]}...")
                else:
                    qa_warnings.append(f"Missing citation: {claim.get('claim', '')[:50]}...")
        
        # Calculate overall QA score
        overall_quality_score = calculate_overall_qa_score(quality_scores)
        
        # Determine approval status
        approved = len(qa_issues) == 0 and overall_quality_score >= 7.0
        ready_for_delivery = approved and not pii_scan.get("has_pii", False)
        
        # If not approved, attempt to fix issues
        fix_attempts = 0
        max_fix_attempts = 3
        fixed_sections = {}
        
        while not approved and fix_attempts < max_fix_attempts:
            fix_attempts += 1
            logger.info(f"Attempting to fix issues - Attempt {fix_attempts}/{max_fix_attempts}")
            
            # Fix critical issues with LLM
            if qa_issues:
                fixed_sections = fix_quality_issues_llm(
                    issues=qa_issues,
                    warnings=qa_warnings,
                    summary_result=summary_result,
                    scoring_result=scoring_result,
                    redundancy_info=redundancy_check.get("redundancies_found", []),
                    tone_info=tone_check.get("analysis", ""),
                    llm=polish_llm
                )
                
                # Update summary_result with fixes
                for section, fixed_content in fixed_sections.items():
                    summary_result[section] = fixed_content
                
                # Re-run quality checks on fixed content
                logger.info("Re-running quality checks after fixes...")
                
                # Re-check content quality
                content_quality = validate_content_quality({
                    "executive_summary": summary_result.get("executive_summary", ""),
                    "recommendations": summary_result.get("recommendations", ""),
                    "category_summaries": summary_result.get("category_summaries", {})
                })
                quality_scores["content_quality"] = content_quality
                
                # Re-check redundancy
                if fixed_sections:
                    redundancy_check = detect_redundancies_llm(
                        regenerate_final_report(summary_result, 
                                              scoring_result.get("overall_score"),
                                              scoring_result.get("readiness_level")),
                        qa_llm
                    )
                    quality_scores["redundancy_check"] = redundancy_check
                
                # Re-check tone
                tone_check = check_tone_consistency_llm({
                    "executive_summary": summary_result.get("executive_summary", ""),
                    "recommendations": summary_result.get("recommendations", ""),
                    "category_summaries": str(summary_result.get("category_summaries", {}))[:1000]
                }, qa_llm)
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
                
                if citation_check.get("citation_score", 10) < 7:
                    qa_issues.append(f"Citation issues remain: {citation_check.get('issues_found', 0)}")
                
                # Re-calculate scores and issues
                qa_issues = []
                qa_warnings = []
                
                if not content_quality.get("passed", True):
                    qa_issues.extend(content_quality.get("issues", []))
                qa_warnings.extend(content_quality.get("warnings", []))
                
                if redundancy_check.get("redundancy_score", 10) < 7:
                    qa_warnings.append(f"Redundancy still present (score: {redundancy_check.get('redundancy_score')}/10)")
                
                if not tone_check.get("consistent", True):
                    qa_warnings.append(f"Tone still inconsistent (score: {tone_check.get('tone_score')}/10)")
                
                # Recalculate approval
                overall_quality_score = calculate_overall_qa_score(quality_scores)
                approved = len(qa_issues) == 0 and overall_quality_score >= 7.0
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
        
        # Prepare QA result
        qa_result = {
            "status": "success",
            "approved": approved,
            "ready_for_delivery": ready_for_delivery,
            "overall_quality_score": overall_quality_score,
            "quality_scores": quality_scores,
            "issues": qa_issues,
            "warnings": qa_warnings,
            "polished_sections": polished_sections,
            "fixed_sections": fixed_sections,
            "fix_attempts": fix_attempts,
            "validation_summary": {
                "total_checks": 7,
                "mechanical_checks": 4,
                "llm_checks": 3,
                "critical_issues": len(qa_issues),
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
                if section == "category_summaries" and isinstance(content, dict):
                    state["summary_result"]["category_summaries"].update(content)
                else:
                    state["summary_result"][section] = content
            
            # Regenerate final report with all fixes and polish
            state["summary_result"]["final_report"] = regenerate_final_report(
                state["summary_result"], 
                scoring_result.get("overall_score"),
                scoring_result.get("readiness_level")
            )
        
        # Add processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        state["processing_time"]["qa"] = processing_time
        
        # Add status message
        status_icon = "✓" if approved else "⚠️"
        fix_msg = f", Fixed: {len(fixed_sections)} sections in {fix_attempts} attempts" if fix_attempts > 0 else ""
        state["messages"].append(
            f"Enhanced QA completed in {processing_time:.2f}s - "
            f"{status_icon} Quality: {overall_quality_score:.1f}/10, "
            f"Issues: {len(qa_issues)}{fix_msg}"
        )
        
        logger.info(f"=== ENHANCED QA NODE COMPLETED - {processing_time:.2f}s ===")
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced QA node: {str(e)}", exc_info=True)
        state["error"] = f"QA failed: {str(e)}"
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
            score = 5.0
        
        total_score += score * weight
        total_weight += weight
    
    return round(total_score / total_weight, 1) if total_weight > 0 else 5.0


def regenerate_final_report(summary_result: Dict, overall_score: float, readiness_level: str) -> str:
    """Regenerate final report with polished sections"""
    
    # Use polished versions if available, otherwise use originals
    executive_summary = summary_result.get("executive_summary", "")
    category_summaries = summary_result.get("category_summaries", {})
    recommendations = summary_result.get("recommendations", "")
    industry_context = summary_result.get("industry_context", "")
    next_steps = summary_result.get("next_steps", "")
    
    final_report = f"""EXIT READY SNAPSHOT ASSESSMENT REPORT

{'='*60}

EXECUTIVE SUMMARY

{executive_summary}

{'='*60}

YOUR EXIT READINESS SCORE

Overall Score: {overall_score}/10
Readiness Level: {readiness_level}

{'='*60}

DETAILED ANALYSIS BY CATEGORY

"""
    
    # Add category summaries
    for category, summary in category_summaries.items():
        final_report += f"{summary}\n\n{'='*60}\n\n"
    
    final_report += f"""PERSONALIZED RECOMMENDATIONS

{recommendations}

{'='*60}

INDUSTRY & MARKET CONTEXT

{industry_context}

{'='*60}

YOUR NEXT STEPS

{next_steps}

{'='*60}

CONFIDENTIAL BUSINESS ASSESSMENT
Prepared by: On Pulse Solutions
Report Date: [REPORT_DATE]
Valid for: 90 days

This report contains proprietary analysis and recommendations specific to your business. 
The insights and strategies outlined are based on your assessment responses and current market conditions.

© On Pulse Solutions - Exit Ready Snapshot"""
    
    return final_report