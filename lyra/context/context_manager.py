# -*- coding: utf-8 -*-
"""
Context Manager for Phase 6B
Stores the last structured intent for conversational refinement.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ConversationContext:
    """
    Holds the state of the current conversation session.
    Only persists across a single CLI session (memory implementation).
    """
    last_intent: Optional[Dict[str, Any]] = None
    
    def update_last_intent(self, intent_data: Dict[str, Any]):
        """
        Update the context with the most recent successful intent.
        
        Args:
            intent_data: The structured intent dictionary
        """
        # Deep copy or at least shallow copy to prevent reference issues
        self.last_intent = intent_data.copy() if intent_data else None

    def get_last_intent(self) -> Optional[Dict[str, Any]]:
        """Retrieve the last stored intent."""
        return self.last_intent

    def clear(self):
        """Reset the context (e.g., after execution failure or unrelated command)."""
        self.last_intent = None
