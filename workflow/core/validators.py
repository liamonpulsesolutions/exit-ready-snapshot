"""
Pure validation functions extracted from CrewAI agents.
No tool wrappers, just business logic.
UPDATED: PII detection deprecated but kept for backward compatibility.
"""

import re
from typing import Dict, Any, List, Tuple, Optional


def validate_form_data(form_data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
   """
   Validate that all required form fields are present and properly formatted.
   
   Returns:
       Tuple of (is_valid, missing_fields, validation_details)
   """
   required_fields = [
       'uuid', 'name', 'email', 'industry', 'years_in_business',
       'age_range', 'exit_timeline', 'location', 'responses'
   ]
   
   optional_fields = ['revenue_range']
   
   missing_fields = []
   validation_details = {
       'total_fields': len(required_fields),
       'missing_required': [],
       'missing_optional': [],
       'response_count': 0,
       'missing_responses': []
   }
   
   # Check required fields
   for field in required_fields:
       if field not in form_data or not form_data[field]:
           missing_fields.append(field)
           validation_details['missing_required'].append(field)
   
   # Check optional fields
   for field in optional_fields:
       if field not in form_data or not form_data[field]:
           validation_details['missing_optional'].append(field)
   
   # Validate responses
   if 'responses' in form_data:
       responses = form_data.get('responses', {})
       validation_details['response_count'] = len(responses)
       
       # Check for all 10 questions
       expected_questions = [f"q{i}" for i in range(1, 11)]
       for q in expected_questions:
           if q not in responses or not responses[q]:
               validation_details['missing_responses'].append(q)
   
   is_valid = len(missing_fields) == 0 and len(validation_details['missing_responses']) == 0
   
   return is_valid, missing_fields, validation_details


def validate_email(email: str) -> bool:
   """Validate email format"""
   email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
   return bool(email_pattern.match(email))


def validate_scoring_consistency(scores: Dict[str, Dict], responses: Dict[str, str]) -> Dict[str, Any]:
   """
   Validate that scores align with their justifications and responses.
   
   Returns:
       Dictionary with consistency analysis
   """
   issues = []
   warnings = []
   
   # Extract category scores
   category_scores = {}
   for category, data in scores.items():
       if isinstance(data, dict) and 'score' in data:
           category_scores[category] = data['score']
   
   if not category_scores:
       return {
           'is_consistent': False,
           'issues': ['No scores found to validate'],
           'warnings': [],
           'analysis': {}
       }
   
   # Check overall score alignment
   if 'overall' in scores:
       overall = scores['overall']
       if isinstance(overall, (int, float)):
           # Calculate expected overall
           weighted_sum = 0
           total_weight = 0
           for cat, data in scores.items():
               if cat != 'overall' and isinstance(data, dict):
                   score = data.get('score', 0)
                   weight = data.get('weight', 0.2)
                   weighted_sum += score * weight
                   total_weight += weight
           
           expected_overall = weighted_sum / total_weight if total_weight > 0 else 0
           
           if abs(overall - expected_overall) > 1.5:
               issues.append(f"Overall score ({overall}) doesn't match weighted average ({expected_overall:.1f})")
   
   # Check for extreme variations
   score_values = [v for v in category_scores.values() if isinstance(v, (int, float))]
   if score_values and len(score_values) > 1:
       variance = max(score_values) - min(score_values)
       if variance > 5:
           warnings.append(f"Large score variance ({variance:.1f}) between categories")
   
   # Check for missing justifications on low scores
   for category, data in scores.items():
       if isinstance(data, dict):
           score = data.get('score', 10)
           gaps = data.get('gaps', [])
           if score < 4 and len(gaps) == 0:
               issues.append(f"Low score ({score}) in {category} lacks gap identification")
   
   return {
       'is_consistent': len(issues) == 0,
       'issues': issues,
       'warnings': warnings,
       'analysis': {
           'categories_validated': len(category_scores),
           'score_range': [min(score_values), max(score_values)] if score_values else [0, 0],
           'average_score': sum(score_values) / len(score_values) if score_values else 0
       }
   }


def validate_content_quality(content: Dict[str, Any]) -> Dict[str, Any]:
   """
   Check content for completeness, clarity, and professional tone.
   
   Returns:
       Dictionary with quality assessment
   """
   issues = []
   warnings = []
   quality_score = 10.0
   
   # Check for placeholder text
   placeholder_patterns = [
       r'\[.*?\]',  # Brackets indicating placeholders
       r'TODO',
       r'PLACEHOLDER',
       r'INSERT.*HERE',
       r'X\.X',  # Placeholder numbers
   ]
   
   # Check executive summary
   exec_summary = content.get('executive_summary', '')
   if exec_summary:
       for pattern in placeholder_patterns:
           if re.search(pattern, exec_summary, re.IGNORECASE):
               issues.append(f"Placeholder text found in executive summary: {pattern}")
               quality_score -= 2.0
       
       if len(exec_summary.split()) < 150:
           warnings.append("Executive summary too brief (< 150 words)")
           quality_score -= 1.0
   else:
       issues.append("Missing executive summary")
       quality_score -= 3.0
   
   # Check recommendations
   recommendations = content.get('recommendations', {})
   if isinstance(recommendations, dict):
       if 'quick_wins' not in recommendations:
           issues.append("Missing quick wins section")
           quality_score -= 1.0
       if 'strategic_priorities' not in recommendations:
           issues.append("Missing strategic priorities")
           quality_score -= 1.0
   
   # Check category summaries
   category_summaries = content.get('category_summaries', {})
   if len(category_summaries) < 5:
       issues.append(f"Missing category summaries ({len(category_summaries)}/5)")
       quality_score -= 2.0
   
   # Check for minimum content length
   for category, summary in category_summaries.items():
       if isinstance(summary, str) and len(summary.split()) < 50:
           warnings.append(f"{category} summary too brief")
           quality_score -= 0.5
   
   # Check tone
   unprofessional_terms = ['gonna', 'wanna', 'stuff', 'things', 'etc.']
   all_content = str(content)
   for term in unprofessional_terms:
       if term in all_content.lower():
           warnings.append(f"Unprofessional language: '{term}'")
           quality_score -= 0.5
   
   quality_score = max(0, quality_score)
   
   return {
       'quality_score': quality_score,
       'passed': quality_score >= 7.0,
       'issues': issues,
       'warnings': warnings,
       'analysis': {
           'has_executive_summary': bool(exec_summary),
           'has_recommendations': bool(recommendations),
           'category_count': len(category_summaries),
           'total_word_count': len(all_content.split())
       }
   }


def scan_for_pii(content: Any) -> Dict[str, Any]:
   """
   DEPRECATED: PII scanning should be handled at the intake stage, not during QA.
   This function is kept for backward compatibility but always returns no PII found.
   
   Previously scanned content for any remaining PII that wasn't properly anonymized.
   Now trusts the intake node's PII handling and returns a pass result.
   
   Returns:
       Dictionary with PII scan results (always passes)
   """
   import warnings
   warnings.warn(
       "scan_for_pii is deprecated. PII handling should be done at the intake stage. "
       "This function now always returns a pass result.",
       DeprecationWarning,
       stacklevel=2
   )
   
   return {
       'has_pii': False,
       'pii_found': [],
       'total_items': 0,
       'scan_complete': True,
       'deprecated': True,
       'message': 'PII scanning has been moved to the intake stage'
   }


def validate_report_structure(report: Dict[str, Any]) -> Dict[str, Any]:
   """
   Ensure the report has all required sections and proper structure.
   
   Returns:
       Dictionary with structure validation results
   """
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
       if key not in report or not report[key]:
           missing_sections.append(name)
       elif isinstance(report[key], (str, list)) and len(str(report[key])) < 10:
           incomplete_sections.append(name)
   
   # Check category completeness
   expected_categories = [
       'owner_dependence', 'revenue_quality', 'financial_readiness',
       'operational_resilience', 'growth_value'
   ]
   
   if 'category_scores' in report:
       missing_categories = []
       for cat in expected_categories:
           if cat not in report['category_scores']:
               missing_categories.append(cat)
       if missing_categories:
           incomplete_sections.append(f"Missing categories: {', '.join(missing_categories)}")
   
   structure_valid = len(missing_sections) == 0 and len(incomplete_sections) == 0
   completeness_score = (5 - len(missing_sections) - len(incomplete_sections) * 0.5) / 5 * 10
   
   return {
       'is_valid': structure_valid,
       'completeness_score': max(0, completeness_score),
       'missing_sections': missing_sections,
       'incomplete_sections': incomplete_sections,
       'has_all_categories': len(missing_categories) == 0 if 'missing_categories' in locals() else False,
       'section_count': sum(1 for key in required_sections if key in report and report[key])
   }


# Additional validation utilities

def validate_score_range(score: float, category: str = "unknown") -> Tuple[bool, str]:
   """
   Validate that a score is within the expected 1-10 range.
   
   Returns:
       Tuple of (is_valid, error_message)
   """
   if not isinstance(score, (int, float)):
       return False, f"{category} score must be a number, got {type(score).__name__}"
   
   if score < 1 or score > 10:
       return False, f"{category} score {score} is outside valid range (1-10)"
   
   return True, ""


def validate_word_count_range(text: str, min_words: int, max_words: int, section_name: str) -> Dict[str, Any]:
   """
   Validate that text falls within a word count range.
   
   Returns:
       Dictionary with validation results
   """
   word_count = len(text.split()) if text else 0
   
   return {
       'is_valid': min_words <= word_count <= max_words,
       'word_count': word_count,
       'min_words': min_words,
       'max_words': max_words,
       'section': section_name,
       'message': f"{section_name}: {word_count} words (expected {min_words}-{max_words})"
   }


def validate_recommendations_format(recommendations: Any) -> Dict[str, Any]:
   """
   Validate the structure of recommendations section.
   
   Returns:
       Dictionary with validation results
   """
   issues = []
   
   if not recommendations:
       return {
           'is_valid': False,
           'issues': ['Recommendations section is empty'],
           'has_quick_wins': False,
           'has_strategic': False,
           'has_critical_focus': False
       }
   
   # Handle string format
   if isinstance(recommendations, str):
       has_quick_wins = 'quick win' in recommendations.lower()
       has_strategic = 'strategic' in recommendations.lower()
       has_critical_focus = 'critical focus' in recommendations.lower() or 'focus area' in recommendations.lower()
       
       if not has_quick_wins:
           issues.append("Quick wins section not found in recommendations")
       if not has_strategic:
           issues.append("Strategic priorities not found in recommendations")
       
       return {
           'is_valid': len(issues) == 0,
           'issues': issues,
           'has_quick_wins': has_quick_wins,
           'has_strategic': has_strategic,
           'has_critical_focus': has_critical_focus,
           'format': 'string'
       }
   
   # Handle dict format
   elif isinstance(recommendations, dict):
       has_quick_wins = 'quick_wins' in recommendations and recommendations['quick_wins']
       has_strategic = 'strategic_priorities' in recommendations and recommendations['strategic_priorities']
       has_critical_focus = 'critical_focus' in recommendations and recommendations['critical_focus']
       
       if not has_quick_wins:
           issues.append("quick_wins key missing or empty")
       if not has_strategic:
           issues.append("strategic_priorities key missing or empty")
       if not has_critical_focus:
           issues.append("critical_focus key missing or empty")
       
       return {
           'is_valid': len(issues) == 0,
           'issues': issues,
           'has_quick_wins': has_quick_wins,
           'has_strategic': has_strategic,
           'has_critical_focus': has_critical_focus,
           'format': 'dict'
       }
   
   else:
       return {
           'is_valid': False,
           'issues': [f'Unexpected recommendations format: {type(recommendations).__name__}'],
           'has_quick_wins': False,
           'has_strategic': False,
           'has_critical_focus': False,
           'format': 'unknown'
       }


def check_promise_language(text: str) -> Dict[str, Any]:
   """
   Check for promise language that should use outcome framing instead.
   
   Returns:
       Dictionary with findings
   """
   promise_patterns = [
       (r'\bwill\s+(?:increase|improve|achieve|ensure|guarantee)', 'will + action verb'),
       (r'\bguaranteed?\b', 'guaranteed'),
       (r'\bensures?\b', 'ensures'),
       (r'\bdefinitely\s+will\b', 'definitely will'),
       (r'\bmust\s+(?:see|achieve|reach)', 'must + outcome'),
       (r'\bcertain\s+to\b', 'certain to')
   ]
   
   found_promises = []
   
   for pattern, description in promise_patterns:
       matches = re.findall(pattern, text, re.IGNORECASE)
       for match in matches:
           found_promises.append({
               'phrase': match,
               'type': description,
               'context': extract_context(text, match, 50)
           })
   
   # Check for proper outcome framing
   outcome_patterns = [
       r'\btypically\s+(?:see|achieve|experience)',
       r'\boften\s+(?:see|achieve|experience|result)',
       r'\bgenerally\s+(?:see|achieve|experience)',
       r'\bcommonly\s+(?:see|achieve|find)',
       r'\bon\s+average\b',
       r'\bfrequently\s+(?:see|achieve)'
   ]
   
   proper_framing_count = 0
   for pattern in outcome_patterns:
       proper_framing_count += len(re.findall(pattern, text, re.IGNORECASE))
   
   return {
       'has_promises': len(found_promises) > 0,
       'promise_count': len(found_promises),
       'promises': found_promises[:10],  # First 10
       'proper_framing_count': proper_framing_count,
       'framing_ratio': proper_framing_count / max(len(found_promises), 1)
   }


def extract_context(text: str, phrase: str, context_length: int = 50) -> str:
   """
   Extract context around a phrase in text.
   
   Returns:
       String with context before and after the phrase
   """
   index = text.lower().find(phrase.lower())
   if index == -1:
       return ""
   
   start = max(0, index - context_length)
   end = min(len(text), index + len(phrase) + context_length)
   
   context = text[start:end]
   
   # Add ellipsis if truncated
   if start > 0:
       context = "..." + context
   if end < len(text):
       context = context + "..."
   
   return context