"""
User Profile Manager - Phase 2A Critical Component
Dynamic trust modeling and behavior tracking
Adaptive confirmation thresholds based on user behavior
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime
from lyra.core.logger import get_logger


@dataclass
class UserProfile:
    """
    User profile with dynamic trust scoring
    Trust decays based on rejections, errors, and rollbacks
    """
    user_id: str = "default_user"
    trust_score: float = 0.5  # 0.0-1.0, starts neutral
    
    # Behavior metrics
    suggestion_acceptance_rate: float = 0.5
    total_suggestions: int = 0
    accepted_suggestions: int = 0
    rejected_suggestions: int = 0
    
    rollback_count: int = 0
    error_count: int = 0
    total_commands: int = 0
    successful_commands: int = 0
    
    # Preferences
    preferences: Dict[str, Any] = None
    
    # Timestamps
    created_at: str = ""
    last_updated: str = ""
    
    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()


class UserProfileManager:
    """
    Manages user profile with dynamic trust scoring
    Trust adapts based on user behavior
    """
    
    def __init__(self, profile_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if profile_path is None:
            project_root = Path(__file__).parent.parent.parent
            profile_path = str(project_root / "data" / "user_profile.json")
        
        self.profile_path = profile_path
        Path(profile_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.profile = self._load_profile()
    
    def _load_profile(self) -> UserProfile:
        """Load user profile from disk"""
        try:
            if Path(self.profile_path).exists():
                with open(self.profile_path, 'r') as f:
                    data = json.load(f)
                    profile = UserProfile(**data)
                    self.logger.info(f"Loaded user profile (trust: {profile.trust_score:.2f})")
                    return profile
            else:
                self.logger.info("No existing profile, creating new one")
                return UserProfile()
        except Exception as e:
            self.logger.error(f"Failed to load profile: {e}, creating new one")
            return UserProfile()
    
    def _save_profile(self):
        """Save user profile to disk"""
        try:
            self.profile.last_updated = datetime.now().isoformat()
            with open(self.profile_path, 'w') as f:
                json.dump(asdict(self.profile), f, indent=2)
            self.logger.debug("User profile saved")
        except Exception as e:
            self.logger.error(f"Failed to save profile: {e}")
    
    def calculate_trust_score(self) -> float:
        """
        Calculate dynamic trust score based on behavior
        
        Returns:
            Trust score (0.0-1.0)
        """
        base_trust = 0.5
        trust = base_trust
        
        # Increase trust for good behavior
        if self.profile.total_suggestions > 0:
            trust += self.profile.suggestion_acceptance_rate * 0.3
        
        if self.profile.total_commands > 0:
            success_rate = self.profile.successful_commands / self.profile.total_commands
            trust += success_rate * 0.2
        
        # Decrease trust for bad behavior
        if self.profile.total_commands > 0:
            error_rate = self.profile.error_count / self.profile.total_commands
            trust -= error_rate * 0.3
        
        if self.profile.rollback_count > 0:
            # Rollbacks are serious trust violations
            rollback_penalty = min(0.3, (self.profile.rollback_count / 100) * 0.3)
            trust -= rollback_penalty
        
        # Clamp to valid range
        return max(0.0, min(1.0, trust))
    
    def update_trust_score(self):
        """Recalculate and update trust score"""
        self.profile.trust_score = self.calculate_trust_score()
        self._save_profile()
    
    def record_suggestion(self, accepted: bool):
        """
        Record a suggestion outcome
        
        Args:
            accepted: Whether user accepted the suggestion
        """
        self.profile.total_suggestions += 1
        
        if accepted:
            self.profile.accepted_suggestions += 1
        else:
            self.profile.rejected_suggestions += 1
        
        # Update acceptance rate
        self.profile.suggestion_acceptance_rate = \
            self.profile.accepted_suggestions / self.profile.total_suggestions
        
        self.update_trust_score()
    
    def record_command(self, success: bool):
        """
        Record a command execution
        
        Args:
            success: Whether command succeeded
        """
        self.profile.total_commands += 1
        
        if success:
            self.profile.successful_commands += 1
        else:
            self.profile.error_count += 1
        
        self.update_trust_score()
    
    def record_error(self):
        """Record an error occurrence"""
        self.profile.error_count += 1
        self.update_trust_score()
    
    def record_rollback(self):
        """Record a rollback (serious trust violation)"""
        self.profile.rollback_count += 1
        self.update_trust_score()
    
    def get_confirmation_threshold(self) -> float:
        """
        Get dynamic confirmation threshold
        Lower trust = higher threshold (more confirmations)
        
        Returns:
            Threshold (0.0-1.0)
        """
        # Inverse relationship: low trust = high threshold
        return 1.0 - self.profile.trust_score
    
    def get_trust_score(self) -> float:
        """Get current trust score"""
        return self.profile.trust_score
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference"""
        self.profile.preferences[key] = value
        self._save_profile()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference"""
        return self.profile.preferences.get(key, default)
    
    def get_profile(self) -> UserProfile:
        """Get the full user profile"""
        return self.profile
    
    def reset_trust(self):
        """Reset trust to neutral"""
        self.profile.trust_score = 0.5
        self._save_profile()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        return {
            "trust_score": self.profile.trust_score,
            "confirmation_threshold": self.get_confirmation_threshold(),
            "suggestion_acceptance_rate": self.profile.suggestion_acceptance_rate,
            "total_suggestions": self.profile.total_suggestions,
            "total_commands": self.profile.total_commands,
            "success_rate": self.profile.successful_commands / max(1, self.profile.total_commands),
            "error_count": self.profile.error_count,
            "rollback_count": self.profile.rollback_count
        }
