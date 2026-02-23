# -*- coding: utf-8 -*-
"""
lyra/context/emotion/detector.py
Phase F6: Emotion & Sarcasm Detection Layer

Lightweight, rule-based emotion detection with optional LLM assistance.
Detects frustration, anger, confusion, happiness, and sarcasm.
"""

import re
import json
from typing import Dict, Any, Optional, List

from lyra.core.config import Config
from lyra.core.logger import get_logger
from lyra.llm.escalation_layer import LLMEscalationAdvisor

logger = get_logger(__name__)

class EmotionDetector:
    """
    Detects user emotion and sarcasm from input text.
    Uses Layer 1 (Rule-based) as primary and Layer 2 (LLM) as optional fallback.
    """

    # Keyword sets for rule-based detection
    FRUSTRATION_KEYWORDS = {
        "frustrated", "annoyed", "why does this", "broken again", "not working",
        "doesn't work", "tried everything", "ugh", "stuck", "annoying"
    }
    ANGER_KEYWORDS = {
        "stupid", "useless", "hate this", "damn", "crap", "garbage", "trash",
        "idiot", "nonsense", "terrible", "shut up", "angry", "pissed", "furious"
    }
    CONFUSION_KEYWORDS = {
        "what is this", "why is", "how does", "makes no sense", "don't understand",
        "confused", "meaning of", "what do you mean", "help me understand"
    }
    HAPPINESS_KEYWORDS = {
        "awesome", "great", "thanks", "nice", "perfect", "brilliant", "good job",
        "excellent", "thank you", "love it", "cool"
    }
    SARCASM_PATTERNS = [
        r"(?i)yeah\s+right",
        r"(?i)just\s+perfect",
        r"(?i)oh\s+great",
        r"(?i)wonderful",
        r"(?i)nice\s+job",  # Context dependent, but we'll score it
        r".*\.\.\.\s*$"    # Sentence ending in ...
    ]

    def __init__(self, config: Optional[Config] = None, model_advisor: Optional[LLMEscalationAdvisor] = None):
        self._config = config or Config()
        self._advisor = model_advisor or LLMEscalationAdvisor()
        
        # Resource settings
        self._llm_assisted = self._config.get("emotion.llm_assisted_enabled", True)
        
        logger.info("EmotionDetector initialized")

    def detect(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main detection interface.
        """
        # Layer 1: Rule-based
        result = self._analyze_rules(text)
        
        # Intensity adjustment
        result["intensity"] = self._calculate_intensity(text, result)
        
        # Behavioral flags
        result["requires_softening"] = result["emotion"] in ["frustrated", "angry"]
        result["requires_confirmation"] = result["emotion"] == "sarcastic" or (result["emotion"] == "angry" and result["intensity"] > 0.7)
        
        # Layer 2: Optional LLM assist
        if result["confidence"] < 0.6 and self._llm_assisted and self._advisor._initialize_gemini():
            llm_result = self._analyze_llm(text, context)
            if llm_result:
                # Merge or replace based on confidence
                if llm_result.get("confidence", 0) > result["confidence"]:
                    result.update(llm_result)
                    # Re-calc flags after LLM update
                    result["requires_softening"] = result["emotion"] in ["frustrated", "angry"]
                    result["requires_confirmation"] = result["emotion"] == "sarcastic" or (result["emotion"] == "angry" and result["intensity"] > 0.7)

        return result

    def _analyze_rules(self, text: str) -> Dict[str, Any]:
        """Perform keyword and pattern matching."""
        low_text = text.lower()
        scores = {
            "frustrated": 0.0,
            "angry": 0.0,
            "confused": 0.0,
            "happy": 0.0,
            "sarcastic": 0.0
        }

        # Keyword matching
        for word in self.FRUSTRATION_KEYWORDS:
            if word in low_text: scores["frustrated"] += 0.4
        for word in self.ANGER_KEYWORDS:
            if word in low_text: scores["angry"] += 0.5
        for word in self.CONFUSION_KEYWORDS:
            if word in low_text: scores["confused"] += 0.4
        for word in self.HAPPINESS_KEYWORDS:
            if word in low_text: scores["happy"] += 0.3

        # Sarcasm patterns
        for pattern in self.SARCASM_PATTERNS:
            if re.search(pattern, text):
                scores["sarcastic"] += 0.5

        # Pick best
        best_emotion = "neutral"
        best_score = 0.0
        for emotion, score in scores.items():
            if score > best_score:
                best_score = score
                best_emotion = emotion
        
        # Normalize score to 1.0 peak (roughly)
        confidence = min(best_score, 1.0)
        if best_score == 0:
            best_emotion = "neutral"
            confidence = 1.0 # High confidence it's neutral if nothing found

        return {
            "emotion": best_emotion,
            "confidence": confidence,
            "intensity": 0.0 # set later
        }

    def _calculate_intensity(self, text: str, result: Dict[str, Any]) -> float:
        """Score emotional intensity based on formatting."""
        if result["emotion"] == "neutral":
            return 0.1
            
        intensity = 0.3 # Baseline for emotional context
        
        if result["emotion"] == "neutral":
            return 0.1

        # CAPS check (if significant portion is caps and length > 4)
        if len(text) > 4:
            caps_count = sum(1 for c in text if c.isupper())
            if caps_count / len(text) > 0.6:
                intensity += 0.4
        
        # Punctuation check
        if "!!!" in text:
            intensity += 0.3
        elif "!" in text:
            intensity += 0.1
            
        # Profanity/Strong keyword check
        if any(word in text.lower() for word in self.ANGER_KEYWORDS):
            intensity += 0.2

        return min(intensity, 1.0)

    def _analyze_llm(self, text: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Optional LLM analysis using the already-loaded model."""
        system_prompt = """You are an emotion detection module. Analyze the user message for subtle cues of sarcasm, frustration, or confusion.
Respond ONLY in valid JSON: {"emotion": "string", "confidence": float, "reasoning": "string"}
Allowed emotions: neutral, frustrated, angry, happy, confused, sarcastic."""

        prompt = f"User Input: '{text}'"
        if context:
            prompt += f"\nContext: {json.dumps(context)}"
            
        try:
            # Re-use Gemini via advisor's model
            if not self._advisor._initialize_gemini():
                return None
                
            response = self._advisor._gen_model.generate_content(
                f"{system_prompt}\n\n{prompt}",
                generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
            )
            raw_output = response.text
            # Find JSON block
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {
                    "emotion": data.get("emotion", "neutral"),
                    "confidence": data.get("confidence", 0.0),
                    "reasoning_llm": data.get("reasoning", "")
                }
        except Exception as e:
            logger.error("LLM emotion analysis failed: %s", e)
        
        return None
