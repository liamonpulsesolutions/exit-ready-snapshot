"""
Sentiment analysis for Exit Ready Snapshot responses.
Analyzes emotional tone, confidence levels, and urgency indicators
to adapt report voice and recommendations appropriately.

IMPORTANT: This module works with anonymized data that has already been
processed by the intake node. It analyzes patterns and language choices
to determine the appropriate tone for the personalized report.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


def analyze_response_sentiment(anonymized_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze emotional tone and confidence in anonymized responses.
    
    Args:
        anonymized_data: Dictionary containing anonymized form data with 'responses' sub-dict
        
    Returns:
        Dictionary with sentiment analysis including recommended report voice
    """
    logger.info("Starting sentiment analysis for response tone adaptation")
    
    # Extract responses and metadata
    responses = anonymized_data.get('responses', {})
    exit_timeline = anonymized_data.get('exit_timeline', '')
    
    sentiment_data = {
        "overall_confidence": 0.0,
        "urgency_level": 0.0,
        "emotional_tone": "neutral",
        "concerns": [],
        "strengths_confidence": [],
        "recommended_voice": "professional",
        "key_emotions": defaultdict(int),
        "readiness_indicators": {
            "prepared": 0,
            "unprepared": 0,
            "uncertain": 0
        },
        "language_sophistication": "moderate",
        "owner_stress_level": "moderate",
        "detail_level": "moderate"
    }
    
    # Analyze each response
    confidence_scores = []
    urgency_scores = []
    
    for q_id, response in responses.items():
        if not isinstance(response, str) or not response.strip():
            continue
        
        # Calculate confidence for this response
        conf_score = calculate_confidence_level(response)
        confidence_scores.append(conf_score)
        
        # Calculate urgency
        urg_score = calculate_urgency_level(response, exit_timeline)
        urgency_scores.append(urg_score)
        
        # Extract emotions
        emotions = extract_emotions(response)
        for emotion, count in emotions.items():
            sentiment_data["key_emotions"][emotion] += count
        
        # Identify concerns
        concerns = identify_concerns(response, q_id)
        sentiment_data["concerns"].extend(concerns)
        
        # Identify confident statements
        confident_statements = identify_confident_statements(response, q_id)
        sentiment_data["strengths_confidence"].extend(confident_statements)
        
        # Update readiness indicators
        update_readiness_indicators(response, sentiment_data["readiness_indicators"])
    
    # Calculate overall metrics
    if confidence_scores:
        sentiment_data["overall_confidence"] = sum(confidence_scores) / len(confidence_scores)
    
    if urgency_scores:
        sentiment_data["urgency_level"] = sum(urgency_scores) / len(urgency_scores)
    
    # Determine emotional tone
    sentiment_data["emotional_tone"] = determine_emotional_tone(sentiment_data["key_emotions"])
    
    # Assess language sophistication
    sentiment_data["language_sophistication"] = assess_language_sophistication(responses)
    
    # Calculate owner stress level
    sentiment_data["owner_stress_level"] = calculate_stress_level(
        sentiment_data["concerns"],
        sentiment_data["urgency_level"],
        sentiment_data["overall_confidence"]
    )
    
    # Assess detail level in responses
    sentiment_data["detail_level"] = assess_detail_level(responses)
    
    # Determine recommended report voice
    sentiment_data["recommended_voice"] = determine_report_voice(sentiment_data)
    
    # Add voice recommendations
    sentiment_data["voice_guidelines"] = generate_voice_guidelines(sentiment_data)
    
    logger.info(f"Sentiment analysis complete - Confidence: {sentiment_data['overall_confidence']:.1f}, "
                f"Urgency: {sentiment_data['urgency_level']:.1f}, Voice: {sentiment_data['recommended_voice']}")
    
    return sentiment_data


def calculate_confidence_level(text: str) -> float:
    """
    Score confidence level from 0-10 based on language patterns.
    
    Returns:
        Float score where 10 = extremely confident, 0 = very uncertain
    """
    score = 5.0  # Start neutral
    
    # High confidence indicators
    high_confidence_patterns = [
        (r'\b(excellent|outstanding|exceptional|superior|unmatched)\b', 1.5),
        (r'\b(strong|solid|robust|proven|established)\b', 1.0),
        (r'\b(confident|certain|sure|definitely|absolutely)\b', 1.2),
        (r'\b(leader|leading|best|top|premier)\b', 1.3),
        (r'\b(successful|thriving|growing|profitable)\b', 1.0),
        (r'\b(unique|exclusive|proprietary|patented)\b', 1.1)
    ]
    
    # Low confidence indicators
    low_confidence_patterns = [
        (r'\b(struggling|difficult|challenging|problematic)\b', -1.5),
        (r'\b(worried|concerned|anxious|uncertain)\b', -1.3),
        (r'\b(maybe|perhaps|possibly|might|could)\b', -0.8),
        (r'\b(trying|attempting|hoping|working on)\b', -0.6),
        (r'\b(weak|poor|lacking|inadequate)\b', -1.2),
        (r'\b(only|just|barely|merely)\b', -0.5)
    ]
    
    text_lower = text.lower()
    
    # Apply patterns
    for pattern, adjustment in high_confidence_patterns:
        matches = len(re.findall(pattern, text_lower))
        score += matches * adjustment
    
    for pattern, adjustment in low_confidence_patterns:
        matches = len(re.findall(pattern, text_lower))
        score += matches * adjustment
    
    # Consider response length (longer = more confident generally)
    word_count = len(text.split())
    if word_count > 50:
        score += 0.5
    elif word_count < 10:
        score -= 0.5
    
    # Normalize to 0-10 range
    return max(0, min(10, score))


def calculate_urgency_level(text: str, exit_timeline: str) -> float:
    """
    Calculate urgency based on language and exit timeline.
    
    Returns:
        Float score where 10 = extremely urgent, 0 = no urgency
    """
    score = 3.0  # Start low
    
    # Timeline-based base urgency
    timeline_urgency = {
        "Already considering offers": 10.0,
        "6 months or less": 9.0,
        "6-12 months": 7.0,
        "1-2 years": 5.0,
        "2-3 years": 3.0,
        "3-5 years": 2.0,
        "5-10 years": 1.0,
        "More than 10 years": 0.5,
        "Not actively considering": 0.0
    }
    
    # Set base score from timeline
    for timeline_key, base_score in timeline_urgency.items():
        if timeline_key in exit_timeline:
            score = base_score
            break
    
    # Urgency language patterns
    urgency_patterns = [
        (r'\b(urgent|immediately|asap|quickly|rapidly)\b', 2.0),
        (r'\b(soon|shortly|near|approaching|imminent)\b', 1.5),
        (r'\b(retiring|retired|succession|health)\b', 1.8),
        (r'\b(must|need to|have to|critical)\b', 1.2),
        (r'\b(deadline|timeframe|timeline|pressure)\b', 1.0)
    ]
    
    text_lower = text.lower()
    
    for pattern, adjustment in urgency_patterns:
        if re.search(pattern, text_lower):
            score += adjustment
    
    return min(10, score)


def extract_emotions(text: str) -> Dict[str, int]:
    """
    Extract emotional indicators from text.
    
    Returns:
        Dictionary of emotion types and their counts
    """
    emotions = defaultdict(int)
    
    emotion_patterns = {
        "pride": [r'\b(proud|pride|achievement|accomplished|built)\b'],
        "worry": [r'\b(worried|concern|anxious|nervous|uncertain)\b'],
        "frustration": [r'\b(frustrated|annoyed|difficult|struggling|stuck)\b'],
        "excitement": [r'\b(excited|enthusiastic|eager|looking forward|opportunity)\b'],
        "confidence": [r'\b(confident|certain|sure|strong|capable)\b'],
        "nostalgia": [r'\b(years ago|remember when|used to|history|legacy)\b'],
        "determination": [r'\b(determined|committed|focused|dedicated|will)\b'],
        "overwhelm": [r'\b(overwhelmed|too much|complex|complicated|confused)\b']
    }
    
    text_lower = text.lower()
    
    for emotion, patterns in emotion_patterns.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            emotions[emotion] += len(matches)
    
    return dict(emotions)


def identify_concerns(text: str, question_id: str) -> List[Dict[str, str]]:
    """
    Identify specific concerns expressed in responses.
    
    Returns:
        List of concerns with context
    """
    concerns = []
    
    concern_patterns = [
        (r'(?:worried|concerned?)\s+(?:about|that|with)\s+([^.]+)', "explicit_worry"),
        (r'(?:difficult|hard|challenging)\s+to\s+([^.]+)', "difficulty"),
        (r'(?:don\'t|do not)\s+(?:know|understand)\s+([^.]+)', "knowledge_gap"),
        (r'(?:struggle|struggling)\s+(?:with|to)\s+([^.]+)', "struggle"),
        (r'(?:no one|nobody)\s+(?:else|knows|can)\s+([^.]+)', "dependency"),
        (r'(?:only|just)\s+(?:I|me|myself)\s+([^.]+)', "sole_responsibility")
    ]
    
    for pattern, concern_type in concern_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            concern_text = match.group(1).strip()
            concerns.append({
                "type": concern_type,
                "text": concern_text,
                "question": question_id,
                "full_context": text[:100] + "..." if len(text) > 100 else text
            })
    
    return concerns


def identify_confident_statements(text: str, question_id: str) -> List[Dict[str, str]]:
    """
    Identify confident, positive statements about the business.
    
    Returns:
        List of confident statements with context
    """
    confident_statements = []
    
    confidence_patterns = [
        (r'(?:we have|we\'ve built|we possess)\s+([^.]+)', "asset"),
        (r'(?:proud of|pride in)\s+([^.]+)', "pride"),
        (r'(?:strong|excellent|exceptional)\s+([^.]+)', "strength"),
        (r'(?:leader|leading|best)\s+(?:in|at)\s+([^.]+)', "leadership"),
        (r'(?:unique|proprietary|exclusive)\s+([^.]+)', "differentiation")
    ]
    
    for pattern, statement_type in confidence_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            statement_text = match.group(1).strip()
            confident_statements.append({
                "type": statement_type,
                "text": statement_text,
                "question": question_id
            })
    
    return confident_statements


def update_readiness_indicators(text: str, indicators: Dict[str, int]):
    """
    Update readiness indicators based on response content.
    
    Modifies indicators dict in place.
    """
    # Prepared indicators
    prepared_patterns = [
        r'\b(ready|prepared|organized|documented|systematized)\b',
        r'\b(process|procedure|system)\s+in\s+place\b',
        r'\b(succession plan|exit plan|transition plan)\b'
    ]
    
    # Unprepared indicators
    unprepared_patterns = [
        r'\b(not ready|unprepared|disorganized|undocumented)\b',
        r'\b(no\s+(?:plan|process|system|documentation))\b',
        r'\b(haven\'t|have not|don\'t have|lack)\b'
    ]
    
    # Uncertain indicators
    uncertain_patterns = [
        r'\b(maybe|perhaps|possibly|might|could be)\b',
        r'\b(not sure|uncertain|unclear|don\'t know)\b',
        r'\b(thinking about|considering|exploring)\b'
    ]
    
    text_lower = text.lower()
    
    for pattern in prepared_patterns:
        if re.search(pattern, text_lower):
            indicators["prepared"] += 1
    
    for pattern in unprepared_patterns:
        if re.search(pattern, text_lower):
            indicators["unprepared"] += 1
    
    for pattern in uncertain_patterns:
        if re.search(pattern, text_lower):
            indicators["uncertain"] += 1


def determine_emotional_tone(emotions: Dict[str, int]) -> str:
    """
    Determine overall emotional tone from emotion counts.
    
    Returns:
        String describing predominant emotional tone
    """
    if not emotions:
        return "neutral"
    
    # Sort emotions by count
    sorted_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
    
    if not sorted_emotions or sorted_emotions[0][1] == 0:
        return "neutral"
    
    predominant = sorted_emotions[0][0]
    
    # Map to tone categories
    tone_mapping = {
        "pride": "confident",
        "confidence": "confident",
        "excitement": "optimistic",
        "determination": "motivated",
        "worry": "anxious",
        "frustration": "frustrated",
        "overwhelm": "overwhelmed",
        "nostalgia": "reflective"
    }
    
    return tone_mapping.get(predominant, "neutral")


def assess_language_sophistication(responses: Dict[str, str]) -> str:
    """
    Assess the sophistication level of language used.
    
    Returns:
        "basic", "moderate", or "sophisticated"
    """
    total_words = 0
    complex_words = 0
    sentence_count = 0
    
    # Industry/business terminology that indicates sophistication
    sophisticated_terms = [
        'strategic', 'operational', 'scalable', 'proprietary', 'differentiation',
        'optimization', 'integration', 'methodology', 'framework', 'synergy',
        'leverage', 'capitalize', 'monetize', 'infrastructure', 'ecosystem'
    ]
    
    sophisticated_count = 0
    
    for response in responses.values():
        if not isinstance(response, str):
            continue
        
        words = response.split()
        total_words += len(words)
        
        # Count complex words (3+ syllables as proxy)
        complex_words += sum(1 for word in words if len(word) > 8)
        
        # Count sentences
        sentence_count += len(re.findall(r'[.!?]+', response))
        
        # Count sophisticated terms
        response_lower = response.lower()
        sophisticated_count += sum(1 for term in sophisticated_terms if term in response_lower)
    
    if total_words == 0:
        return "moderate"
    
    # Calculate metrics
    avg_words_per_response = total_words / len([r for r in responses.values() if r])
    complexity_ratio = complex_words / total_words if total_words > 0 else 0
    
    # Determine sophistication
    if sophisticated_count >= 5 and complexity_ratio > 0.15:
        return "sophisticated"
    elif sophisticated_count >= 2 or complexity_ratio > 0.10:
        return "moderate"
    else:
        return "basic"


def calculate_stress_level(concerns: List[Dict], urgency: float, confidence: float) -> str:
    """
    Calculate owner's stress level based on multiple factors.
    
    Returns:
        "low", "moderate", "high", or "critical"
    """
    stress_score = 0.0
    
    # Factor in number and severity of concerns
    stress_score += len(concerns) * 0.5
    critical_concerns = [c for c in concerns if c['type'] in ['dependency', 'sole_responsibility']]
    stress_score += len(critical_concerns) * 1.0
    
    # Factor in urgency
    if urgency > 8:
        stress_score += 3.0
    elif urgency > 6:
        stress_score += 2.0
    elif urgency > 4:
        stress_score += 1.0
    
    # Factor in low confidence (inverse relationship)
    if confidence < 3:
        stress_score += 2.0
    elif confidence < 5:
        stress_score += 1.0
    
    # Determine level
    if stress_score >= 7:
        return "critical"
    elif stress_score >= 5:
        return "high"
    elif stress_score >= 3:
        return "moderate"
    else:
        return "low"


def assess_detail_level(responses: Dict[str, str]) -> str:
    """
    Assess how detailed/thorough the responses are.
    
    Returns:
        "minimal", "moderate", or "comprehensive"
    """
    response_lengths = []
    
    for response in responses.values():
        if isinstance(response, str) and response.strip():
            response_lengths.append(len(response.split()))
    
    if not response_lengths:
        return "minimal"
    
    avg_length = sum(response_lengths) / len(response_lengths)
    
    if avg_length > 50:
        return "comprehensive"
    elif avg_length > 20:
        return "moderate"
    else:
        return "minimal"


def determine_report_voice(sentiment_data: Dict[str, Any]) -> str:
    """
    Determine the appropriate voice/tone for the report.
    
    Returns:
        Recommended voice style
    """
    confidence = sentiment_data["overall_confidence"]
    urgency = sentiment_data["urgency_level"]
    stress = sentiment_data["owner_stress_level"]
    tone = sentiment_data["emotional_tone"]
    sophistication = sentiment_data["language_sophistication"]
    
    # Decision tree for voice selection
    if stress in ["critical", "high"] and urgency > 7:
        return "supportive_urgent"
    elif stress in ["critical", "high"] and confidence < 4:
        return "reassuring_educational"
    elif confidence > 7 and sophistication == "sophisticated":
        return "peer_strategic"
    elif confidence > 7 and urgency < 3:
        return "aspirational_growth"
    elif tone == "anxious" or tone == "overwhelmed":
        return "calming_systematic"
    elif tone == "frustrated":
        return "empathetic_solution"
    elif tone == "confident" and urgency > 6:
        return "direct_action"
    elif sophistication == "basic":
        return "clear_educational"
    else:
        return "professional_balanced"


def generate_voice_guidelines(sentiment_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate specific guidelines for report writing based on sentiment.
    
    Returns:
        Dictionary of voice guidelines
    """
    voice = sentiment_data["recommended_voice"]
    
    voice_guidelines = {
        "supportive_urgent": {
            "opening": "Acknowledge their urgent timeline while providing reassurance",
            "tone": "Supportive but action-oriented, emphasizing quick wins",
            "structure": "Lead with immediate actions, minimize theory",
            "language": "Clear, direct, avoiding overwhelming detail",
            "emphasis": "What can be done NOW to improve position"
        },
        "reassuring_educational": {
            "opening": "Normalize their concerns - many owners feel this way",
            "tone": "Patient, educational, building confidence step-by-step",
            "structure": "Progressive difficulty, starting with easy wins",
            "language": "Simple explanations, avoid jargon",
            "emphasis": "You're not alone, and there's a clear path forward"
        },
        "peer_strategic": {
            "opening": "Recognize their business acumen and success",
            "tone": "Peer-to-peer strategic discussion",
            "structure": "High-level insights with sophisticated analysis",
            "language": "Business terminology appropriate, data-driven",
            "emphasis": "Maximizing already strong position"
        },
        "aspirational_growth": {
            "opening": "Frame exit planning as next stage of growth",
            "tone": "Visionary, focusing on potential and opportunity",
            "structure": "Future-focused with transformational themes",
            "language": "Inspirational but grounded in specifics",
            "emphasis": "Building lasting value and legacy"
        },
        "calming_systematic": {
            "opening": "Acknowledge complexity but emphasize manageability",
            "tone": "Calm, systematic, breaking down into steps",
            "structure": "Clear phases with defined milestones",
            "language": "Reassuring, avoiding pressure",
            "emphasis": "One step at a time approach"
        },
        "empathetic_solution": {
            "opening": "Validate their frustrations are common and solvable",
            "tone": "Understanding but solution-focused",
            "structure": "Problem → Solution format throughout",
            "language": "Acknowledge difficulties, provide alternatives",
            "emphasis": "Practical solutions to specific pain points"
        },
        "direct_action": {
            "opening": "Respect their confidence with direct assessment",
            "tone": "Straightforward, action-oriented",
            "structure": "Clear priorities and timelines",
            "language": "Direct, minimal fluff, specific",
            "emphasis": "Execution and timeline adherence"
        },
        "clear_educational": {
            "opening": "Set clear expectations about the process",
            "tone": "Educational without condescension",
            "structure": "Logical progression with examples",
            "language": "Plain language, define terms",
            "emphasis": "Building understanding and capability"
        },
        "professional_balanced": {
            "opening": "Professional acknowledgment of their situation",
            "tone": "Balanced, professional, supportive",
            "structure": "Standard report flow with clear sections",
            "language": "Professional but accessible",
            "emphasis": "Comprehensive analysis with clear next steps"
        }
    }
    
    return voice_guidelines.get(voice, voice_guidelines["professional_balanced"])


def get_sentiment_summary(sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a simplified summary of sentiment analysis for easy use.
    
    Args:
        sentiment_data: Full sentiment analysis results
        
    Returns:
        Simplified summary for report generation
    """
    return {
        "confidence_level": sentiment_data["overall_confidence"],
        "is_confident": sentiment_data["overall_confidence"] > 6,
        "urgency_level": sentiment_data["urgency_level"],
        "is_urgent": sentiment_data["urgency_level"] > 6,
        "stress_level": sentiment_data["owner_stress_level"],
        "is_stressed": sentiment_data["owner_stress_level"] in ["high", "critical"],
        "recommended_voice": sentiment_data["recommended_voice"],
        "voice_guidelines": sentiment_data["voice_guidelines"],
        "primary_emotion": sentiment_data["emotional_tone"],
        "top_concerns": sentiment_data["concerns"][:3] if sentiment_data["concerns"] else [],
        "response_quality": sentiment_data["detail_level"],
        "sophistication": sentiment_data["language_sophistication"]
    }


def adapt_message_to_sentiment(message: str, sentiment_summary: Dict[str, Any]) -> str:
    """
    Adapt a standard message based on sentiment analysis.
    
    Args:
        message: Original message text
        sentiment_summary: Simplified sentiment summary
        
    Returns:
        Adapted message matching owner's emotional state
    """
    voice = sentiment_summary["recommended_voice"]
    
    # Voice-specific adaptations
    adaptations = {
        "supportive_urgent": {
            "prefix": "Given your timeline, let's focus on what matters most: ",
            "suffix": " We'll help you move quickly and effectively."
        },
        "reassuring_educational": {
            "prefix": "Many business owners share these concerns. ",
            "suffix": " We'll guide you through each step."
        },
        "peer_strategic": {
            "prefix": "Building on your strong foundation, ",
            "suffix": " Let's optimize your already impressive position."
        },
        "calming_systematic": {
            "prefix": "While this may seem overwhelming, ",
            "suffix": " We'll break this down into manageable steps."
        }
    }
    
    adaptation = adaptations.get(voice, {"prefix": "", "suffix": ""})
    
    # Apply adaptation
    if sentiment_summary["is_urgent"] and "timeline" not in message.lower():
        message = f"With your exit timeline in mind, {message.lower()}"
    
    return f"{adaptation['prefix']}{message}{adaptation['suffix']}"