"""
Adaptive Risk Scorer - Phase 3B
Extends RiskScorer with adaptive threshold calibration
Enforces non-adaptive safety floors for critical operations
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from lyra.safety.risk_scorer import RiskScorer, RiskAssessment
from lyra.reasoning.command_schema import Command
from lyra.memory.behavioral_memory import BehavioralMemory
from lyra.core.user_profile import UserProfileManager
from lyra.core.logger import get_logger


# Non-negotiable safety floors for critical operations
CRITICAL_OPERATIONS = {
    "shutdown_system": 0.85,
    "restart_system": 0.85,
    "delete_system_file": 0.85,
    "format_drive": 0.90,
    "modify_registry": 0.85,
    "install_system": 0.85,
    "uninstall_system": 0.85,
    "delete_database": 0.90,
    "drop_table": 0.90
}


class AdaptiveRiskScorer(RiskScorer):
    """
    Adaptive risk scorer with learning capabilities
    Thresholds adapt to user behavior while maintaining safety floors
    """
    
    def __init__(self, adjustments_path: Optional[str] = None):
        super().__init__()
        self.logger = get_logger(__name__)
        
        if adjustments_path is None:
            project_root = Path(__file__).parent.parent.parent
            adjustments_path = str(project_root / "data" / "risk_adjustments.json")
        
        self.adjustments_path = adjustments_path
        Path(adjustments_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.behavioral_memory = BehavioralMemory()
        self.profile_manager = UserProfileManager()
        
        # Load threshold adjustments
        self.threshold_adjustments = self._load_adjustments()
        self.adjustment_history = []
        self.last_calibration = datetime.now()
        
        # Calibration settings
        self.max_adjustment_per_week = 0.05
        self.max_total_adjustment = 0.2
        self.decay_rate_per_month = 0.1
        
        self.logger.info("Adaptive risk scorer initialized")
    
    def _load_adjustments(self) -> Dict[str, float]:
        """Load threshold adjustments from disk"""
        try:
            if Path(self.adjustments_path).exists():
                with open(self.adjustments_path, 'r') as f:
                    data = json.load(f)
                    return data.get("adjustments", {})
        except Exception as e:
            self.logger.error(f"Failed to load adjustments: {e}")
        
        return {}
    
    def _save_adjustments(self):
        """Save threshold adjustments to disk"""
        try:
            data = {
                "adjustments": self.threshold_adjustments,
                "last_calibration": self.last_calibration.isoformat(),
                "history": self.adjustment_history[-100:]  # Keep last 100
            }
            with open(self.adjustments_path, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug("Adjustments saved")
        except Exception as e:
            self.logger.error(f"Failed to save adjustments: {e}")
    
    def get_threshold(self, operation: str, base_threshold: float = 0.6) -> float:
        """
        Get threshold with safety floor enforcement
        
        Args:
            operation: Operation name
            base_threshold: Base threshold
        
        Returns:
            Adjusted threshold with safety floor applied
        """
        # Get adjustment
        adjustment = self.threshold_adjustments.get(operation, 0.0)
        adjusted = base_threshold + adjustment
        
        # Enforce safety floor for critical operations
        if operation in CRITICAL_OPERATIONS:
            safety_floor = CRITICAL_OPERATIONS[operation]
            final_threshold = max(adjusted, safety_floor)
            
            # Log if safety floor was enforced
            if final_threshold > adjusted:
                self.logger.info(
                    f"Safety floor enforced for {operation}: "
                    f"{adjusted:.2f} -> {final_threshold:.2f}"
                )
            
            return final_threshold
        
        return adjusted
    
    def calculate_risk(self, command: Command, context: Dict[str, Any] = None) -> RiskAssessment:
        """
        Calculate risk with adaptive thresholds
        
        Args:
            command: Command to assess
            context: Optional context
        
        Returns:
            Risk assessment with adaptive threshold
        """
        # Get base risk assessment
        assessment = super().calculate_risk(command, context)
        
        # Apply adaptive threshold
        adaptive_threshold = self.get_threshold(
            command.intent,
            assessment.confirmation_threshold
        )
        
        # Update assessment with adaptive threshold
        assessment.confirmation_threshold = adaptive_threshold
        assessment.requires_confirmation = assessment.risk_score > adaptive_threshold
        
        return assessment
    
    def record_override(self, operation: str, accepted: bool):
        """
        Record a manual override of risk warning
        
        Args:
            operation: Operation that was overridden
            accepted: Whether user accepted despite warning
        """
        # Record in behavioral memory
        trust_score = self.profile_manager.get_trust_score()
        self.behavioral_memory.record_risk_action(
            risk_level="high",
            operation=operation,
            user_action="overridden" if accepted else "rejected",
            trust_score=trust_score
        )
        
        # Adjust threshold if accepted
        if accepted:
            current_adjustment = self.threshold_adjustments.get(operation, 0.0)
            new_adjustment = min(
                self.max_total_adjustment,
                current_adjustment + 0.02
            )
            self.threshold_adjustments[operation] = new_adjustment
            
            self.adjustment_history.append({
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "adjustment": new_adjustment,
                "reason": "manual_override"
            })
            
            self._save_adjustments()
            self.logger.info(f"Threshold adjusted for {operation}: +0.02")
    
    def calibrate_thresholds(self):
        """
        Perform periodic threshold calibration
        Applies trust-based adjustments and decay
        """
        now = datetime.now()
        days_since_calibration = (now - self.last_calibration).days
        
        if days_since_calibration < 7:
            return  # Only calibrate weekly
        
        self.logger.info("Performing threshold calibration")
        
        # Get current trust score
        trust_score = self.profile_manager.get_trust_score()
        
        # Trust-based adjustment
        if trust_score > 0.7:
            # High trust: slightly increase thresholds (more lenient)
            trust_adjustment = min(0.05, self.max_adjustment_per_week)
        elif trust_score < 0.3:
            # Low trust: slightly decrease thresholds (more strict)
            trust_adjustment = max(-0.05, -self.max_adjustment_per_week)
        else:
            trust_adjustment = 0.0
        
        # Apply decay to existing adjustments
        months_since_calibration = days_since_calibration / 30
        decay_factor = 1.0 - (self.decay_rate_per_month * months_since_calibration)
        
        for operation in list(self.threshold_adjustments.keys()):
            # Apply decay
            self.threshold_adjustments[operation] *= decay_factor
            
            # Apply trust adjustment (only for non-critical operations)
            if operation not in CRITICAL_OPERATIONS:
                self.threshold_adjustments[operation] += trust_adjustment
            
            # Clamp to max adjustment
            self.threshold_adjustments[operation] = max(
                -self.max_total_adjustment,
                min(self.max_total_adjustment, self.threshold_adjustments[operation])
            )
            
            # Remove if close to zero
            if abs(self.threshold_adjustments[operation]) < 0.01:
                del self.threshold_adjustments[operation]
        
        self.last_calibration = now
        self._save_adjustments()
        
        self.logger.info(
            f"Calibration complete. Trust adjustment: {trust_adjustment:+.3f}, "
            f"Decay factor: {decay_factor:.3f}"
        )
    
    def get_adjustment_summary(self) -> Dict[str, Any]:
        """Get summary of current adjustments"""
        return {
            "total_adjustments": len(self.threshold_adjustments),
            "adjustments": self.threshold_adjustments.copy(),
            "last_calibration": self.last_calibration.isoformat(),
            "critical_operations": list(CRITICAL_OPERATIONS.keys()),
            "safety_floors": CRITICAL_OPERATIONS.copy()
        }
