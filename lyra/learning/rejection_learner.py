"""
Rejection Learner - Phase 3A
Learns from user rejections to improve future suggestions
Uses logarithmic penalty system to prevent over-penalization
"""

import json
import math
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from lyra.core.logger import get_logger


@dataclass
class RejectionRecord:
    """Record of a suggestion rejection"""
    rejection_id: str
    suggestion_type: str
    timestamp: str
    reason: Optional[str]
    context: Dict[str, Any]
    similarity_features: List[str]  # Features for finding similar suggestions
    weight_adjustment: float  # Calculated penalty


class RejectionLearner:
    """
    Learns from user rejections
    Applies logarithmic penalties to prevent over-penalization
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if storage_path is None:
            project_root = Path(__file__).parent.parent.parent
            storage_path = str(project_root / "data" / "rejections.json")
        
        self.storage_path = storage_path
        Path(storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.rejections = self._load_rejections()
        self.logger.info(f"Rejection learner initialized: {storage_path}")
    
    def _load_rejections(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load rejection history from disk"""
        try:
            if Path(self.storage_path).exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded {len(data)} rejection types")
                    return data
        except Exception as e:
            self.logger.error(f"Failed to load rejections: {e}")
        
        return {}
    
    def _save_rejections(self):
        """Save rejection history to disk"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.rejections, f, indent=2)
            self.logger.debug("Rejections saved")
        except Exception as e:
            self.logger.error(f"Failed to save rejections: {e}")
    
    def calculate_penalty(self, rejection_count: int) -> float:
        """
        Calculate logarithmic penalty
        Prevents over-penalization while still learning
        
        Args:
            rejection_count: Number of rejections
        
        Returns:
            Penalty (0.0-0.5)
        
        Examples:
            1 rejection:  0.069 (6.9% penalty)
            3 rejections: 0.139 (13.9% penalty)
            5 rejections: 0.179 (17.9% penalty)
            10 rejections: 0.240 (24.0% penalty)
            100 rejections: 0.461 (46.1% penalty)
        """
        penalty = min(0.5, 0.1 * math.log(1 + rejection_count))
        return penalty
    
    def record_rejection(self, suggestion_type: str, reason: Optional[str] = None,
                        context: Dict[str, Any] = None):
        """
        Record a suggestion rejection
        
        Args:
            suggestion_type: Type of suggestion rejected
            reason: Optional reason for rejection
            context: Context when rejection occurred
        """
        context = context or {}
        
        # Extract similarity features
        similarity_features = [
            suggestion_type,
            context.get("project", ""),
            context.get("time_of_day", ""),
            context.get("activity", "")
        ]
        
        # Calculate current penalty
        current_count = len(self.rejections.get(suggestion_type, []))
        penalty = self.calculate_penalty(current_count + 1)
        
        # Create rejection record
        record = RejectionRecord(
            rejection_id=str(uuid.uuid4()),
            suggestion_type=suggestion_type,
            timestamp=datetime.now().isoformat(),
            reason=reason,
            context=context,
            similarity_features=similarity_features,
            weight_adjustment=penalty
        )
        
        # Store rejection
        if suggestion_type not in self.rejections:
            self.rejections[suggestion_type] = []
        
        self.rejections[suggestion_type].append(asdict(record))
        self._save_rejections()
        
        self.logger.info(f"Rejection recorded: {suggestion_type} (penalty: {penalty:.3f})")
    
    def get_suggestion_weight(self, suggestion_type: str, 
                             context: Dict[str, Any] = None) -> float:
        """
        Get current weight for a suggestion type
        Applies decay for old rejections
        
        Args:
            suggestion_type: Type of suggestion
            context: Current context (for context-aware weighting)
        
        Returns:
            Weight (0.5-1.0)
        """
        if suggestion_type not in self.rejections:
            return 1.0  # No rejections, full weight
        
        rejections = self.rejections[suggestion_type]
        
        # Filter by context if provided
        if context:
            context_key = context.get("project", "")
            relevant_rejections = [
                r for r in rejections
                if r.get("context", {}).get("project", "") == context_key
            ]
        else:
            relevant_rejections = rejections
        
        if not relevant_rejections:
            return 1.0
        
        # Calculate base penalty
        rejection_count = len(relevant_rejections)
        base_penalty = self.calculate_penalty(rejection_count)
        
        # Apply decay (5% recovery per week)
        now = datetime.now()
        last_rejection = max(
            datetime.fromisoformat(r["timestamp"]) 
            for r in relevant_rejections
        )
        
        weeks_since_last = (now - last_rejection).days / 7
        decay_recovery = min(base_penalty, 0.05 * weeks_since_last)
        
        # Calculate final weight
        adjusted_weight = 1.0 - base_penalty
        final_weight = min(1.0, adjusted_weight + decay_recovery)
        
        return final_weight
    
    def get_rejection_stats(self, suggestion_type: str) -> Dict[str, Any]:
        """
        Get rejection statistics for a suggestion type
        
        Args:
            suggestion_type: Type of suggestion
        
        Returns:
            Statistics dictionary
        """
        if suggestion_type not in self.rejections:
            return {
                "total_rejections": 0,
                "current_weight": 1.0,
                "current_penalty": 0.0,
                "last_rejection": None,
                "common_reasons": []
            }
        
        rejections = self.rejections[suggestion_type]
        rejection_count = len(rejections)
        
        # Get reasons
        reasons = [r.get("reason") for r in rejections if r.get("reason")]
        reason_counts = {}
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        common_reasons = sorted(
            reason_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Get last rejection
        last_rejection = max(r["timestamp"] for r in rejections)
        
        return {
            "total_rejections": rejection_count,
            "current_weight": self.get_suggestion_weight(suggestion_type),
            "current_penalty": self.calculate_penalty(rejection_count),
            "last_rejection": last_rejection,
            "common_reasons": [r for r, _ in common_reasons]
        }
    
    def should_suggest(self, suggestion_type: str, 
                      context: Dict[str, Any] = None,
                      min_weight: float = 0.6) -> bool:
        """
        Check if suggestion should be made based on rejection history
        
        Args:
            suggestion_type: Type of suggestion
            context: Current context
            min_weight: Minimum weight threshold
        
        Returns:
            True if should suggest
        """
        weight = self.get_suggestion_weight(suggestion_type, context)
        return weight >= min_weight
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all suggestion types"""
        stats = {}
        for suggestion_type in self.rejections.keys():
            stats[suggestion_type] = self.get_rejection_stats(suggestion_type)
        return stats
    
    def reset_suggestion(self, suggestion_type: str):
        """
        Reset rejection history for a suggestion type
        Useful for manual override
        
        Args:
            suggestion_type: Type to reset
        """
        if suggestion_type in self.rejections:
            del self.rejections[suggestion_type]
            self._save_rejections()
            self.logger.info(f"Reset rejections for: {suggestion_type}")
