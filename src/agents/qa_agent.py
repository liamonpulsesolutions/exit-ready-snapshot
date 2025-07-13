from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Type
import logging
import json
import re
from ..utils.json_helper import safe_parse_json

logger = logging.getLogger(__name__)

# Tool Input Schemas
class CheckScoringConsistencyInput(BaseModel):
    scoring_data: str = Field(
        default="{}",
        description="JSON string containing scores, justifications, and responses"
    )

class VerifyContentQualityInput(BaseModel):
    content_data: str = Field(
        default="{}",
        description="JSON string containing summary, recommendations, and category_summaries"
    )

class ScanForPIIInput(BaseModel):
    full_content: str = Field(
        default="{}",
        description="JSON string or plain text containing all report content to scan"
    )

class ValidateReportStructureInput(BaseModel):
    report_data: str = Field(
        default="{}",
        description="JSON string containing all report sections and data"
    )

# Tool Classes
class CheckScoringConsistencyTool(BaseTool):
    name: str = "check_scoring_consistency"
    description: str = """
    Verify that scores align with their justifications and responses.
    Check for logical consistency across categories.
    
    Input should be JSON string containing:
    {"scores": {"owner_dependence": 6.5, "revenue_quality": 7.0}, "justifications": {"owner_dependence": "Good delegation structure..."}, "responses": {"q1": "I handle client meetings", "q2": "Less than 3 days"}}
    
    Returns consistency analysis with any issues identified.
    """
    args_schema: Type[BaseModel] = CheckScoringConsistencyInput
    
    def _run(self, scoring_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== CHECK SCORING CONSISTENCY CALLED ===")
            logger.info(f"Input type: {type(scoring_data)}")
            logger.info(f"Input preview: {str(scoring_data)[:200] if scoring_data else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not scoring_data or scoring_data == "{}":
                logger.warning("No scoring data provided - using default consistency check")
                return json.dumps({
                    "consistent": False,
                    "error": "No scoring data provided",
                    "scores_reviewed": 0
                })
            
            # Handle CrewAI passing dict vs string
            if isinstance(scoring_data, dict):
                # CrewAI passes the actual data as a dict
                data = scoring_data
            else:
                # Direct string input - try to parse as JSON
                data = safe_parse_json(scoring_data, {}, "check_scoring_consistency")
                
            if not data:
                return json.dumps({
                    "consistent": False,
                    "error": "No scoring data provided",
                    "scores_reviewed": 0
                })
            
            scores = data.get('scores', {})
            justifications = data.get('justifications', {})
            responses = data.get('responses', {})
            
            # If data structure is different, try to extract from nested structure
            if not scores and isinstance(data, dict):
                # Look for scores in various possible locations
                for key, value in data.items():
                    if isinstance(value, dict) and 'score' in value:
                        scores[key] = value.get('score', 0)
                        if 'justifications' in value:
                            justifications[key] = value['justifications']
            
            inconsistencies = []
            
            # Check if overall score aligns with category scores
            category_scores = [v for k, v in scores.items() if k != 'overall' and isinstance(v, (int, float))]
            if category_scores:
                expected_overall = sum(category_scores) / len(category_scores)
                actual_overall = scores.get('overall', 0)
                
                if abs(expected_overall - actual_overall) > 1.5:
                    inconsistencies.append({
                        "type": "overall_score_mismatch",
                        "severity": "major",
                        "details": f"Overall score ({actual_overall}) doesn't align with category average ({expected_overall:.1f})"
                    })
            
            # Check for extreme score variations
            if category_scores:
                score_variance = max(category_scores) - min(category_scores)
                if score_variance > 5:
                    inconsistencies.append({
                        "type": "high_score_variance",
                        "severity": "minor",
                        "details": f"Large variance in category scores (range: {score_variance})"
                    })
            
            # Check if low scores have appropriate justifications
            for category, score in scores.items():
                if isinstance(score, (int, float)) and score < 4 and category in justifications:
                    justification_text = justifications[category]
                    if isinstance(justification_text, str) and len(justification_text) < 50:
                        inconsistencies.append({
                            "type": "insufficient_justification",
                            "severity": "major",
                            "details": f"Low score ({score}) in {category} lacks detailed justification"
                        })
            
            return json.dumps({
                "consistent": len(inconsistencies) == 0,
                "inconsistencies": inconsistencies,
                "scores_reviewed": len(scores)
            })
            
        except Exception as e:
            logger.error(f"Error checking scoring consistency: {str(e)}")
            return json.dumps({"error": str(e), "consistent": False})

class VerifyContentQualityTool(BaseTool):
    name: str = "verify_content_quality"
    description: str = """
    Check content for completeness, clarity, and professional tone.
    Identify any placeholder text or generic content.
    
    Input should be JSON string containing:
    {"summary": "Executive summary text...", "recommendations": ["Improve delegation", "Document processes"], "category_summaries": {"owner_dependence": "Analysis text..."}}
    
    Returns quality assessment with any issues identified.
    """
    args_schema: Type[BaseModel] = VerifyContentQualityInput
    
    def _run(self, content_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== VERIFY CONTENT QUALITY CALLED ===")
            logger.info(f"Input type: {type(content_data)}")
            logger.info(f"Input preview: {str(content_data)[:200] if content_data else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not content_data or content_data == "{}":
                logger.warning("No content data provided - using default quality check")
                return json.dumps({
                    "quality_acceptable": False,
                    "error": "No content data provided",
                    "issues": []
                })
            
            # Handle CrewAI passing dict vs string
            if isinstance(content_data, dict):
                data = content_data
            else:
                data = safe_parse_json(content_data, {}, "verify_content_quality")
                
            if not data:
                return json.dumps({
                    "quality_acceptable": False,
                    "error": "No content data provided",
                    "issues": []
                })
            
            summary_content = data.get('summary', '')
            recommendations = data.get('recommendations', [])
            category_summaries = data.get('category_summaries', {})
            
            issues = []
            
            # Check for placeholder text
            placeholder_patterns = [
                r'\[.*?\]',  # Brackets indicating placeholders
                r'TODO',
                r'PLACEHOLDER',
                r'INSERT.*HERE',
                r'X\.X',  # Placeholder numbers
            ]
            
            for pattern in placeholder_patterns:
                if re.search(pattern, summary_content, re.IGNORECASE):
                    issues.append({
                        "type": "placeholder_text",
                        "severity": "critical",
                        "details": f"Found placeholder text pattern: {pattern}"
                    })
            
            # Check recommendation quality
            generic_phrases = [
                "improve your business",
                "make improvements",
                "consider options",
                "think about"
            ]
            
            vague_recommendations = 0
            if isinstance(recommendations, list):
                for rec in recommendations:
                    if isinstance(rec, str) and any(phrase in rec.lower() for phrase in generic_phrases):
                        vague_recommendations += 1
            
                if len(recommendations) > 0 and vague_recommendations > len(recommendations) * 0.3:
                    issues.append({
                        "type": "generic_recommendations",
                        "severity": "major",
                        "details": f"{vague_recommendations} out of {len(recommendations)} recommendations are too generic"
                    })
            
            # Check for minimum content length
            for category, summary in category_summaries.items():
                if isinstance(summary, str) and len(summary.split()) < 20:
                    issues.append({
                        "type": "insufficient_content",
                        "severity": "major",
                        "details": f"{category} summary is too brief (less than 20 words)"
                    })
            
            # Check tone indicators
            overly_negative_words = ['terrible', 'awful', 'horrible', 'disaster', 'failing']
            overly_casual_words = ['gonna', 'wanna', 'stuff', 'things', 'whatever']
            
            content_to_check = summary_content + ' ' + ' '.join(str(s) for s in category_summaries.values())
            
            for word in overly_negative_words:
                if word in content_to_check.lower():
                    issues.append({
                        "type": "inappropriate_tone",
                        "severity": "major",
                        "details": f"Overly negative language: '{word}'"
                    })
            
            for word in overly_casual_words:
                if word in content_to_check.lower():
                    issues.append({
                        "type": "inappropriate_tone",
                        "severity": "minor",
                        "details": f"Too casual language: '{word}'"
                    })
            
            return json.dumps({
                "quality_acceptable": len([i for i in issues if i['severity'] == 'critical']) == 0,
                "issues": issues,
                "total_content_length": len(content_to_check.split())
            })
            
        except Exception as e:
            logger.error(f"Error verifying content quality: {str(e)}")
            return json.dumps({"error": str(e), "quality_acceptable": False})

class ScanForPIITool(BaseTool):
    name: str = "scan_for_pii"
    description: str = """
    Scan all content for any remaining PII that wasn't properly anonymized.
    This is critical for privacy compliance.
    
    Input can be JSON string or plain text:
    {"content": "Report text with potential PII...", "sections": {...}}
    Or plain text: "Report content to scan for PII..."
    
    Returns PII compliance status with any violations found.
    """
    args_schema: Type[BaseModel] = ScanForPIIInput
    
    def _run(self, full_content: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== SCAN FOR PII CALLED ===")
            logger.info(f"Input type: {type(full_content)}")
            logger.info(f"Input preview: {str(full_content)[:200] if full_content else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not full_content or full_content == "{}":
                logger.warning("No content provided for PII scan - using default scan")
                return json.dumps({
                    "pii_compliant": False,
                    "error": "No content provided for scanning",
                    "pii_found": [],
                    "scan_complete": True
                })
            
            # Handle CrewAI passing dict vs string
            if isinstance(full_content, dict):
                # Combine all text content from the dict
                all_text = json.dumps(full_content)
            else:
                data = safe_parse_json(full_content, {}, "scan_for_pii")
                all_text = json.dumps(data) if data else full_content
            
            pii_patterns = {
                'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'phone': r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
                'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
                'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
                'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            }
            
            pii_found = []
            
            for pii_type, pattern in pii_patterns.items():
                matches = re.findall(pattern, all_text)
                if matches:
                    # Filter out obvious non-PII (like scores that might match IP pattern)
                    filtered_matches = []
                    for match in matches:
                        if pii_type == 'ip_address':
                            # Check if it's actually a score like "8.5.7.6"
                            parts = match.split('.')
                            try:
                                if all(0 <= int(part) <= 10 for part in parts):
                                    continue
                            except:
                                pass
                        filtered_matches.append(match)
                    
                    if filtered_matches:
                        pii_found.append({
                            "type": pii_type,
                            "count": len(filtered_matches),
                            "severity": "critical"
                        })
            
            # Check for potential names (basic check)
            # Look for patterns like "John Smith" but exclude our placeholders
            name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
            potential_names = re.findall(name_pattern, all_text)
            
            # Filter out known safe phrases
            safe_phrases = ['Exit Ready', 'Quick Wins', 'Strategic Priorities', 'Professional Services']
            real_names = [name for name in potential_names if name not in safe_phrases]
            
            if real_names:
                pii_found.append({
                    "type": "potential_names",
                    "count": len(real_names),
                    "severity": "major",
                    "examples": real_names[:3]  # Show first 3 examples
                })
            
            return json.dumps({
                "pii_compliant": len(pii_found) == 0,
                "pii_found": pii_found,
                "scan_complete": True
            })
            
        except Exception as e:
            logger.error(f"Error scanning for PII: {str(e)}")
            return json.dumps({"error": str(e), "pii_compliant": False})

class ValidateReportStructureTool(BaseTool):
    name: str = "validate_report_structure"
    description: str = """
    Ensure the report has all required sections and proper structure.
    
    Input should be JSON string containing all report sections:
    {"executive_summary": "Summary text...", "category_scores": {"owner_dependence": {...}}, "category_summaries": {...}, "recommendations": {...}, "next_steps": "Next steps text..."}
    
    Returns structure validation with any missing or incomplete sections.
    """
    args_schema: Type[BaseModel] = ValidateReportStructureInput
    
    def _run(self, report_data: str = "{}", **kwargs) -> str:
        try:
            logger.info(f"=== VALIDATE REPORT STRUCTURE CALLED ===")
            logger.info(f"Input type: {type(report_data)}")
            logger.info(f"Input preview: {str(report_data)[:200] if report_data else 'No data provided'}...")
            
            # Handle case where CrewAI doesn't pass any arguments or passes empty data
            if not report_data or report_data == "{}":
                logger.warning("No report data provided - using default structure validation")
                return json.dumps({
                    "structure_valid": False,
                    "error": "No report data provided",
                    "missing_sections": ["all"]
                })
            
            # Handle CrewAI passing dict vs string
            if isinstance(report_data, dict):
                data = report_data
            else:
                data = safe_parse_json(report_data, {}, "validate_report_structure")
                
            if not data:
                return json.dumps({
                    "structure_valid": False,
                    "error": "No report data provided",
                    "missing_sections": ["all"]
                })
            
            required_sections = {
                'executive_summary': 'Executive Summary',
                'category_scores': 'Category Scores',
                'category_summaries': 'Category Summaries',
                'recommendations': 'Recommendations',
                'next_steps': 'Next Steps'
            }
            
            missing_sections = []
            incomplete_sections = []
            
            for key, name in required_sections.items():
                if key not in data or not data[key]:
                    missing_sections.append(name)
                elif isinstance(data[key], (str, list)) and len(str(data[key])) < 10:
                    incomplete_sections.append(name)
            
            # Check category completeness
            expected_categories = ['owner_dependence', 'revenue_quality', 'financial_readiness', 
                                 'operational_resilience', 'growth_value']
            
            if 'category_scores' in data:
                missing_categories = [cat for cat in expected_categories 
                                    if cat not in data['category_scores']]
                if missing_categories:
                    incomplete_sections.append(f"Missing categories: {', '.join(missing_categories)}")
            
            structure_valid = len(missing_sections) == 0 and len(incomplete_sections) == 0
            
            return json.dumps({
                "structure_valid": structure_valid,
                "missing_sections": missing_sections,
                "incomplete_sections": incomplete_sections,
                "completeness_score": (5 - len(missing_sections) - len(incomplete_sections)*0.5) / 5 * 10
            })
            
        except Exception as e:
            logger.error(f"Error validating report structure: {str(e)}")
            return json.dumps({"error": str(e), "structure_valid": False})

# Create tool instances
check_scoring_consistency = CheckScoringConsistencyTool()
verify_content_quality = VerifyContentQualityTool()
scan_for_pii = ScanForPIITool()
validate_report_structure = ValidateReportStructureTool()

def create_qa_agent(llm, prompts: Dict[str, Any]) -> Agent:
    """Create the QA agent for quality assurance"""
    
    # Get agent configuration from prompts
    config = prompts.get('qa_agent', {})
    
    # Create tools list using instances
    tools = [
        check_scoring_consistency,
        verify_content_quality,
        scan_for_pii,
        validate_report_structure
    ]
    
    return Agent(
        role=config.get('role'),
        goal=config.get('goal'),
        backstory=config.get('backstory'),
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=4
    )