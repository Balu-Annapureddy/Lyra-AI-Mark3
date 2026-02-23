# -*- coding: utf-8 -*-
"""
lyra/core/reasoning_depth.py
Phase F8: Adaptive Reasoning Depth (Subsystem L)
"""

from enum import Enum
from typing import List, Optional

class ReasoningLevel(Enum):
    SHALLOW = "shallow"
    STANDARD = "standard"
    DEEP = "deep"

class ReasoningDepthController:
    """
    Dynamically scale reasoning depth before LLM escalation.
    Logic is based on rules + scoring to minimize resource usage.
    """
    
    PLANNING_KEYWORDS = {
        "plan", "schedule", "organize", "setup", "configure", 
        "architecture", "design", "blueprint", "sequence"
    }
    
    MULTI_STEP_INDICATORS = {"then", "after that", "also", "finally", "next", "and then"}

    @staticmethod
    def determine_level(
        intent: str,
        embedding_confidence: float,
        ambiguity_score: float,
        conversation_turn_count: int,
        contains_planning_keywords: bool,
        user_input: str = "",
        emotion_state: str = "neutral"
    ) -> ReasoningLevel:
        """
        Determine the required reasoning level based on input complexity and confidence.
        """
        lower_input = user_input.lower()
        
        # Check for multi-step indicators
        has_multi_step = any(indicator in lower_input for indicator in ReasoningDepthController.MULTI_STEP_INDICATORS)

        # ── DEEP Criteria ─────────────────────────────────────────────────────
        if (
            contains_planning_keywords or 
            ambiguity_score > 0.5 or 
            intent == "organize_workspace" or 
            has_multi_step
        ):
            return ReasoningLevel.DEEP

        # ── SHALLOW Criteria ──────────────────────────────────────────────────
        # Preliminary check for SHALLOW
        is_shallow_eligible = (
            embedding_confidence >= 0.85 and 
            ambiguity_score < 0.2 and 
            conversation_turn_count <= 2 and 
            not contains_planning_keywords
        )

        if is_shallow_eligible:
            # Micro-refinement: High emotion requires STANDARD at minimum
            if emotion_state in ["angry", "frustrated", "sarcastic"]:
                return ReasoningLevel.STANDARD
            return ReasoningLevel.SHALLOW

        # ── STANDARD Criteria (Fallback) ──────────────────────────────────────
        # Returns STANDARD if:
        # - embedding_confidence between 0.6–0.85
        # - OR ambiguity_score between 0.2–0.5
        # - OR conversation_turn_count > 2
        return ReasoningLevel.STANDARD
