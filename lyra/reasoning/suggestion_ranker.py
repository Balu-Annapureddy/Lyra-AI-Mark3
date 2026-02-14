"""
Suggestion Ranking Engine - Phase 3B
Multi-factor suggestion scoring and ranking
All inputs normalized to 0-1 range
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from lyra.memory.behavioral_memory import BehavioralMemory
from lyra.learning.rejection_learner import RejectionLearner
from lyra.safety.risk_scorer import RiskScorer
from lyra.core.user_profile import UserProfileManager
from lyra.core.logger import get_logger


@dataclass
class ScoredSuggestion:
    """Suggestion with score breakdown"""
    suggestion_type: str
    suggestion_data: Dict[str, Any]
    total_score: float  # 0.0-1.0
    score_breakdown: Dict[str, float]  # Individual factor scores
    rank: int = 0


class SuggestionRanker:
    """
    Ranks suggestions using multi-factor scoring
    All inputs normalized to prevent skewing
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.behavioral_memory = BehavioralMemory()
        self.rejection_learner = RejectionLearner()
        self.risk_scorer = RiskScorer()
        self.profile_manager = UserProfileManager()
        
        # Scoring weights (must sum to 1.0)
        self.trust_weight = 0.25
        self.context_weight = 0.20
        self.history_weight = 0.25
        self.risk_weight = 0.20
        self.recency_weight = 0.10
    
    def normalize_trust_score(self, trust_score: Optional[float] = None) -> float:
        """
        Normalize trust score to 0-1
        
        Args:
            trust_score: Trust score (already 0-1) or None
        
        Returns:
            Normalized trust (0-1)
        """
        if trust_score is None:
            trust_score = self.profile_manager.get_trust_score()
        
        # Already normalized
        return max(0.0, min(1.0, trust_score))
    
    def normalize_context_relevance(self, suggestion_type: str,
                                    current_context: Dict[str, Any]) -> float:
        """
        Normalize context relevance to 0-1
        
        Args:
            suggestion_type: Type of suggestion
            current_context: Current execution context
        
        Returns:
            Context relevance (0-1)
        """
        # Get suggestion effectiveness by context
        effectiveness = self.behavioral_memory.get_suggestion_effectiveness(suggestion_type)
        context_patterns = effectiveness.get("context_patterns", {})
        
        if not context_patterns:
            return 0.5  # Neutral default if no data
        
        # Check current context match
        current_project = current_context.get("project", "default")
        
        if current_project in context_patterns:
            ctx_data = context_patterns[current_project]
            if ctx_data["total"] > 0:
                return ctx_data["accepted"] / ctx_data["total"]
        
        return 0.5  # Neutral if no match
    
    def normalize_historical_acceptance(self, suggestion_type: str) -> float:
        """
        Normalize historical acceptance rate to 0-1
        
        Args:
            suggestion_type: Type of suggestion
        
        Returns:
            Acceptance rate (0-1)
        """
        effectiveness = self.behavioral_memory.get_suggestion_effectiveness(suggestion_type)
        acceptance_rate = effectiveness.get("acceptance_rate", 0.5)
        
        # Apply rejection learning weight
        rejection_weight = self.rejection_learner.get_suggestion_weight(suggestion_type)
        
        # Combine: historical acceptance * rejection weight
        combined = acceptance_rate * rejection_weight
        
        return max(0.0, min(1.0, combined))
    
    def normalize_risk_score(self, suggestion_data: Dict[str, Any]) -> float:
        """
        Normalize risk score to 0-1 (inverted: lower risk = higher score)
        
        Args:
            suggestion_data: Suggestion data
        
        Returns:
            Inverted risk score (0-1)
        """
        # Get risk from suggestion data or use default
        risk_score = suggestion_data.get("risk_score", 0.3)  # Default medium-low risk
        
        # Invert: lower risk = higher score
        inverted = 1.0 - risk_score
        
        return max(0.0, min(1.0, inverted))
    
    def normalize_recency_factor(self, suggestion_type: str,
                                 current_context: Dict[str, Any]) -> float:
        """
        Normalize recency factor to 0-1
        
        Args:
            suggestion_type: Type of suggestion
            current_context: Current context
        
        Returns:
            Recency factor (0-1)
        """
        effectiveness = self.behavioral_memory.get_suggestion_effectiveness(suggestion_type)
        last_suggested = effectiveness.get("last_suggested")
        
        if not last_suggested:
            return 0.5  # Neutral if never suggested
        
        # Calculate time since last suggestion
        last_time = datetime.fromisoformat(last_suggested)
        hours_since = (datetime.now() - last_time).total_seconds() / 3600
        
        # Recency curve: 0 hours = 0.0, 24 hours = 0.5, 168 hours (1 week) = 1.0
        if hours_since >= 168:
            return 1.0
        elif hours_since >= 24:
            return 0.5 + (hours_since - 24) / (168 - 24) * 0.5
        else:
            return hours_since / 24 * 0.5
    
    def score_suggestion(self, suggestion_type: str,
                        suggestion_data: Dict[str, Any],
                        current_context: Dict[str, Any] = None) -> ScoredSuggestion:
        """
        Score a single suggestion with normalized inputs
        
        Args:
            suggestion_type: Type of suggestion
            suggestion_data: Suggestion data
            current_context: Current context
        
        Returns:
            ScoredSuggestion
        """
        current_context = current_context or {}
        
        # Normalize all inputs to 0-1
        normalized_trust = self.normalize_trust_score()
        normalized_context = self.normalize_context_relevance(suggestion_type, current_context)
        normalized_history = self.normalize_historical_acceptance(suggestion_type)
        normalized_risk = self.normalize_risk_score(suggestion_data)
        normalized_recency = self.normalize_recency_factor(suggestion_type, current_context)
        
        # Calculate weighted score
        total_score = (
            self.trust_weight * normalized_trust +
            self.context_weight * normalized_context +
            self.history_weight * normalized_history +
            self.risk_weight * normalized_risk +
            self.recency_weight * normalized_recency
        )
        
        # Build score breakdown
        score_breakdown = {
            "trust": normalized_trust,
            "context": normalized_context,
            "history": normalized_history,
            "risk": normalized_risk,
            "recency": normalized_recency,
            "trust_weighted": self.trust_weight * normalized_trust,
            "context_weighted": self.context_weight * normalized_context,
            "history_weighted": self.history_weight * normalized_history,
            "risk_weighted": self.risk_weight * normalized_risk,
            "recency_weighted": self.recency_weight * normalized_recency
        }
        
        return ScoredSuggestion(
            suggestion_type=suggestion_type,
            suggestion_data=suggestion_data,
            total_score=total_score,
            score_breakdown=score_breakdown
        )
    
    def rank_suggestions(self, suggestions: List[Dict[str, Any]],
                        current_context: Dict[str, Any] = None,
                        top_n: int = 5) -> List[ScoredSuggestion]:
        """
        Rank multiple suggestions
        
        Args:
            suggestions: List of suggestion dictionaries
            current_context: Current context
            top_n: Number of top suggestions to return
        
        Returns:
            Ranked list of ScoredSuggestion
        """
        current_context = current_context or {}
        
        # Score all suggestions
        scored = []
        for suggestion in suggestions:
            suggestion_type = suggestion.get("type", "unknown")
            scored_suggestion = self.score_suggestion(
                suggestion_type,
                suggestion,
                current_context
            )
            scored.append(scored_suggestion)
        
        # Sort by total score (descending)
        scored.sort(key=lambda x: x.total_score, reverse=True)
        
        # Assign ranks
        for i, suggestion in enumerate(scored[:top_n], 1):
            suggestion.rank = i
        
        return scored[:top_n]
    
    def get_best_suggestion(self, suggestions: List[Dict[str, Any]],
                           current_context: Dict[str, Any] = None) -> Optional[ScoredSuggestion]:
        """
        Get the single best suggestion
        
        Args:
            suggestions: List of suggestions
            current_context: Current context
        
        Returns:
            Best ScoredSuggestion or None
        """
        if not suggestions:
            return None
        
        ranked = self.rank_suggestions(suggestions, current_context, top_n=1)
        return ranked[0] if ranked else None
