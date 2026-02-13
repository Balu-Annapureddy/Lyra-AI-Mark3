"""
Proactive Agent - Phase 2D
Makes proactive suggestions based on detected patterns
Includes cooldown logic to prevent annoyance
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from lyra.reasoning.pattern_detector import PatternDetector
from lyra.core.system_state import SystemStateManager
from lyra.core.user_profile import UserProfileManager
from lyra.core.logger import get_logger


class ProactiveAgent:
    """
    Makes proactive suggestions based on patterns
    Respects cooldown periods to avoid Clippy syndrome
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.pattern_detector = PatternDetector()
        self.state_manager = SystemStateManager()
        self.profile_manager = UserProfileManager()
        
        # Cooldown settings
        self.default_cooldown_hours = 1
        self.max_cooldown_hours = 24
    
    def get_suggestions(self, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get proactive suggestions based on patterns
        
        Args:
            context: Current execution context
        
        Returns:
            List of suggestions
        """
        # Get all patterns
        all_patterns = self.pattern_detector.get_all_patterns()
        
        suggestions = []
        
        # Check time patterns
        for pattern in all_patterns["time_patterns"]:
            if self.pattern_detector.should_suggest(pattern, context):
                if self._can_suggest(pattern["intent"]):
                    suggestions.append({
                        "type": "time_based",
                        "intent": pattern["intent"],
                        "reason": f"You usually do this at {pattern['time']}",
                        "confidence": pattern["confidence"],
                        "pattern": pattern
                    })
        
        # Check context patterns
        for pattern in all_patterns["context_patterns"]:
            if self.pattern_detector.should_suggest(pattern, context):
                if self._can_suggest(pattern["intent"]):
                    suggestions.append({
                        "type": "context_based",
                        "intent": pattern["intent"],
                        "reason": f"You often do this in this context",
                        "confidence": pattern["confidence"],
                        "pattern": pattern
                    })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return suggestions
    
    def _can_suggest(self, suggestion_type: str) -> bool:
        """
        Check if suggestion is allowed (not in cooldown)
        
        Args:
            suggestion_type: Type of suggestion
        
        Returns:
            True if can suggest
        """
        return self.state_manager.can_suggest(suggestion_type)
    
    def record_suggestion_response(self, suggestion_type: str, accepted: bool):
        """
        Record user response to suggestion
        
        Args:
            suggestion_type: Type of suggestion
            accepted: Whether user accepted
        """
        from lyra.core.system_state import Suggestion
        from datetime import datetime
        import uuid
        
        # Create suggestion object
        suggestion = Suggestion(
            suggestion_id=str(uuid.uuid4()),
            suggestion_type=suggestion_type,
            message=f"Suggestion: {suggestion_type}",
            action=suggestion_type,
            params={},
            confidence=0.8,
            timestamp=datetime.now(),
            accepted=accepted
        )
        
        # Record in state manager
        self.state_manager.record_suggestion(suggestion, accepted)
        
        # Update user profile
        self.profile_manager.record_suggestion(accepted)
        
        self.logger.info(f"Suggestion '{suggestion_type}' {'accepted' if accepted else 'rejected'}")
    
    def should_be_proactive(self) -> bool:
        """
        Check if agent should be proactive based on user trust
        
        Returns:
            True if should be proactive
        """
        trust_score = self.profile_manager.get_trust_score()
        
        # Only be proactive if trust is above threshold
        return trust_score > 0.5
    
    def get_suggestion_summary(self) -> Dict[str, Any]:
        """
        Get summary of suggestion history
        
        Returns:
            Suggestion statistics
        """
        state = self.state_manager.get_state()
        profile = self.profile_manager.get_profile()
        
        total_suggestions = profile.suggestions_accepted + profile.suggestions_rejected
        acceptance_rate = (
            profile.suggestions_accepted / total_suggestions
            if total_suggestions > 0
            else 0.0
        )
        
        return {
            "total_suggestions": total_suggestions,
            "accepted": profile.suggestions_accepted,
            "rejected": profile.suggestions_rejected,
            "acceptance_rate": acceptance_rate,
            "current_cooldowns": len(state.suggestion_history),
            "is_proactive": self.should_be_proactive()
        }
