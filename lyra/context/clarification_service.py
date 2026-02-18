# -*- coding: utf-8 -*-
"""
Clarification Service for Phase 6C/6D
Handles ambiguous intents by managing a clarification loop.
Renamed from clarification_manager due to file system lock issues.
"""
from typing import Dict, Any, Optional
from lyra.core.logger import get_logger

class ClarificationManager:
    """
    Manages the state of ambiguous intents and resolves them via user interaction.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.pending_intent: Optional[Dict[str, Any]] = None
        self.missing_fields: list = []
        self.attempt_count = 0
        self.last_question = ""
        
    def has_pending(self) -> bool:
        """Check if we are waiting for clarification."""
        return self.pending_intent is not None
        
    def create_clarification(self, intent_data: Dict[str, Any]) -> str:
        """
        Store the ambiguous intent and generate a clarification question.
        
        Args:
            intent_data: The intent dict with 'intent', 'parameters', etc.
            
        Returns:
            Question string to present to the user.
        """
        self.pending_intent = intent_data
        self.missing_fields = []
        self.attempt_count = 0
        
        # Analyze what's missing or ambiguous
        intent_type = intent_data.get("intent")
        params = intent_data.get("parameters", {})
        
        question = ""
        if intent_type == "write_file":
            if not params.get("path") or params.get("path") == "untitled.txt":
                self.missing_fields.append("path")
                question = "What should I name the file?"
            elif not params.get("content"): # Use elif to ask one thing at a time
                self.missing_fields.append("content")
                question = "What content should I write in the file?"
                
        elif intent_type == "launch_app":
            if not params.get("app_name"):
                self.missing_fields.append("app_name")
                question = "Which application would you like to open?"
                
        elif intent_type == "read_file":
             if not params.get("path"):
                self.missing_fields.append("path")
                question = "Which file would you like me to read?"

        if not question:
            question = f"I understood you want to {intent_type}, but I need more details. Can you be more specific?"
            
        self.last_question = question
        return question

    def resolve_clarification(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Resolve the pending intent with the user's answer.
        Returns None if invalid or aborted.
        Check has_pending() to see if we are still waiting.
        """
        if not self.pending_intent:
            return None
            
        self.attempt_count += 1
        text = user_input.strip()
        
        # 1. Validation Guard
        is_valid = True
        if not text:
            is_valid = False
        elif len(text) < 2 and ("path" in self.missing_fields or "app_name" in self.missing_fields):
            is_valid = False
        elif "path" in self.missing_fields:
            # Check for invalid filename chars (windows)
            if any(c in text for c in '<>:"/\\|?*'):
                is_valid = False
        
        if not is_valid:
            if self.attempt_count >= 3:
                self.clear() # Abort
            return None # Keep pending if attempts < 3
            
        updated_intent = self.pending_intent.copy()
        updated_intent["parameters"] = self.pending_intent["parameters"].copy()
        
        # Merge logic
        if "path" in self.missing_fields:
            updated_intent["parameters"]["path"] = text
        elif "content" in self.missing_fields:
            updated_intent["parameters"]["content"] = text
        elif "app_name" in self.missing_fields:
            updated_intent["parameters"]["app_name"] = text
            
        # Clear pending state
        self.pending_intent = None
        self.missing_fields = []
        
        # 2. Cap Confidence
        # boost = min(current + 0.25, 0.90)
        current = updated_intent.get("confidence", 0.0)
        updated_intent["confidence"] = min(current + 0.25, 0.90)
        updated_intent["requires_clarification"] = False
        
        return updated_intent

    def clear(self):
        """Reset the clarification state."""
        self.pending_intent = None
        self.missing_fields = []
        self.attempt_count = 0
        self.last_question = ""
