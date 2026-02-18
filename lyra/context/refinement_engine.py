# -*- coding: utf-8 -*-
"""
Refinement Engine for Phase 6B
Handles safe mutation of structured intents based on user feedback.
"""
from typing import Dict, Any, Optional
import re
from lyra.context.context_manager import ConversationContext

class RefinementEngine:
    """
    Detects refinement phrases and mutates the previous intent.
    Strictly rule-based intent mutation.
    """
    
    # Phrases that trigger intent refinement
    REFINEMENT_PHRASES = [
        "make it shorter",
        "change name to",
        "rename to",
        "use different",
        "modify that",
        "edit that",
        "update it",
        "instead use",
        "change content to",
        "change contents to",
        "make it"
    ]

    def refine_intent(self, user_input: str, context: ConversationContext) -> Optional[Dict[str, Any]]:
        """
        Attempt to refine the last intent based on user input.
        
        Args:
            user_input: The user's natural language command
            context: The current conversation context
            
        Returns:
            New intent dict if refinement detected, else None
        """
        last_intent = context.get_last_intent()
        if not last_intent:
            return None
            
        text = user_input.lower().strip()
        
        # 1. Detection: Is this a refinement?
        matches_refinement = any(phrase in text for phrase in self.REFINEMENT_PHRASES)
        
        # Also check for implicit "no, X" or "actually X" pattern
        if text.startswith("no ") or text.startswith("actually "):
            matches_refinement = True

        if not matches_refinement:
            return None

        # 2. Mutation Logic
        refined_intent = last_intent.copy()
        refined_intent["parameters"] = last_intent["parameters"].copy()
        mutated = False

        # Rule A: "Change name/rename to X"
        if "name" in text or "rename" in text:
            # Extract new name
            match = re.search(r"(?:name|rename)(?:\s+to)?\s+([^\s]+)", text)
            if match and "path" in refined_intent["parameters"]:
                refined_intent["parameters"]["path"] = match.group(1)
                mutated = True
            elif match and "app_name" in refined_intent["parameters"]:
                refined_intent["parameters"]["app_name"] = match.group(1)
                mutated = True

        # Rule B: "Change content/text to X" or "make it X"
        if "content" in text or "text" in text:
            match = re.search(r"(?:contents?|text)(?:\s+to)?\s+[\"']?(.+?)[\"']?$", text)
            if match and "content" in refined_intent["parameters"]:
                refined_intent["parameters"]["content"] = match.group(1)
                mutated = True
                
        # Rule C: "Make it shorter/longer" (Content modification stub)
        if "shorter" in text and "content" in refined_intent["parameters"]:
             # Heuristic: just truncate or append "(shortened)" as we can't really summarize without LLM
             # For Phase 6B, we'll simple append a marker to show mutation happened
             current_content = refined_intent["parameters"].get("content", "")
             refined_intent["parameters"]["content"] = current_content[:len(current_content)//2]
             mutated = True
             
        # Rule D: "instead use X" (Generic parameter swap)
        if "instead use" in text:
            match = re.search(r"instead use\s+(.+)", text)
            if match:
                val = match.group(1)
                # Try to guess which param to update based on value
                if "path" in refined_intent["parameters"] and "." in val:
                    refined_intent["parameters"]["path"] = val
                    mutated = True
                elif "url" in refined_intent["parameters"] and ("http" in val or ".com" in val):
                    refined_intent["parameters"]["url"] = val
                    mutated = True
                elif "app_name" in refined_intent["parameters"]:
                    refined_intent["parameters"]["app_name"] = val
                    mutated = True

        if mutated:
            # 3. Adjust Confidence
            # Refinement implies user certitude, but we reduce slightly to trigger confirmation if high risk
            refined_intent["confidence"] = max(0.0, refined_intent["confidence"] - 0.05)
            refined_intent["requires_clarification"] = False # User explicitly corrected, so less ambiguous
            return refined_intent
            
        return None
