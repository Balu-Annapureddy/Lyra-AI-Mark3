"""
Risk Scorer - Phase 2C
Dynamic risk assessment for commands and workflows
Integrates with user trust scoring for adaptive confirmation
"""

from typing import Dict, Any
from dataclasses import dataclass
from lyra.reasoning.command_schema import Command, RiskLevel
from lyra.core.user_profile import UserProfileManager
from lyra.core.logger import get_logger


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    risk_level: RiskLevel
    risk_score: float  # 0.0-1.0
    requires_confirmation: bool
    confirmation_threshold: float
    factors: Dict[str, Any]
    reason: str


class RiskScorer:
    """
    Dynamic risk scoring for commands
    Adapts confirmation thresholds based on user trust
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.profile_manager = UserProfileManager()
        
        # Base risk scores for different command types
        self.intent_risk_map = {
            # Critical operations
            "shutdown_system": 1.0,
            "restart_system": 1.0,
            "delete_system_file": 1.0,
            "format_drive": 1.0,
            "install_system": 0.95,
            
            # High risk
            "delete_file": 0.8,
            "delete_folder": 0.85,
            "uninstall": 0.8,
            "modify_registry": 0.9,
            "run_script": 0.75,
            
            # Medium risk
            "create_file": 0.5,
            "modify_file": 0.6,
            "move_file": 0.55,
            "rename_file": 0.5,
            "install_application": 0.7,
            
            # Low risk
            "open_application": 0.3,
            "read_file": 0.2,
            "search": 0.1,
            "get_time": 0.05,
            "get_weather": 0.1,
            
            # Safe
            "help": 0.0,
            "status": 0.0,
            "list": 0.0
        }
    
    def calculate_risk(self, command: Command, context: Dict[str, Any] = None) -> RiskAssessment:
        """
        Calculate risk for a command
        
        Args:
            command: Command to assess
            context: Optional execution context
        
        Returns:
            Risk assessment
        """
        context = context or {}
        
        # Base risk from intent
        base_risk = self._get_intent_risk(command.intent)
        
        # Contextual risk factors
        factors = {
            "base_risk": base_risk,
            "intent": command.intent
        }
        
        # Resource risk (affects important files/folders)
        resource_risk = self._assess_resource_risk(command, context)
        factors["resource_risk"] = resource_risk
        
        # Time-based risk (late night = higher risk)
        time_risk = self._assess_time_risk(context)
        factors["time_risk"] = time_risk
        
        # User history risk (recent errors increase risk)
        history_risk = self._assess_history_risk()
        factors["history_risk"] = history_risk
        
        # Aggregate risk
        total_risk = min(1.0, base_risk + resource_risk + time_risk + history_risk)
        factors["total_risk"] = total_risk
        
        # Get user trust score
        trust_score = self.profile_manager.get_trust_score()
        factors["user_trust"] = trust_score
        
        # Get confirmation threshold (adapts to trust)
        confirmation_threshold = self.get_confirmation_threshold(context)
        factors["confirmation_threshold"] = confirmation_threshold
        
        # Determine if confirmation required
        requires_confirmation = total_risk > confirmation_threshold
        
        # Map to risk level
        risk_level = self._score_to_level(total_risk)
        
        # Build reason
        reason = self._build_reason(command, total_risk, factors)
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=total_risk,
            requires_confirmation=requires_confirmation,
            confirmation_threshold=confirmation_threshold,
            factors=factors,
            reason=reason
        )
    
    def _get_intent_risk(self, intent: str) -> float:
        """Get base risk from intent"""
        # Exact match
        if intent in self.intent_risk_map:
            return self.intent_risk_map[intent]
        
        # Partial match (check for keywords)
        intent_lower = intent.lower()
        for key, risk in self.intent_risk_map.items():
            if key in intent_lower:
                return risk
        
        # Default medium risk for unknown intents
        return 0.5
    
    def _assess_resource_risk(self, command: Command, context: Dict[str, Any]) -> float:
        """Assess risk based on affected resources"""
        risk = 0.0
        
        # Check entities for file/folder paths
        entities = command.entities
        
        # System directories
        system_paths = ["windows", "system32", "program files", "users"]
        for path_key in ["filename", "path", "folder"]:
            if path_key in entities:
                path = str(entities[path_key]).lower()
                if any(sys_path in path for sys_path in system_paths):
                    risk += 0.3
        
        # Important files
        important_extensions = [".exe", ".dll", ".sys", ".bat", ".ps1"]
        for ext in important_extensions:
            if any(ext in str(v).lower() for v in entities.values()):
                risk += 0.2
        
        return min(0.3, risk)
    
    def _assess_time_risk(self, context: Dict[str, Any]) -> float:
        """Assess risk based on time of day"""
        # Late night commands are riskier (user might be tired)
        from datetime import datetime
        hour = datetime.now().hour
        
        if 23 <= hour or hour < 6:  # 11 PM - 6 AM
            return 0.1
        return 0.0
    
    def _assess_history_risk(self) -> float:
        """Assess risk based on user history"""
        profile = self.profile_manager.get_profile()
        
        risk = 0.0
        
        # Recent errors increase risk
        if profile.total_commands > 0:
            error_rate = profile.error_count / profile.total_commands
            if error_rate > 0.2:  # More than 20% errors
                risk += 0.15
        
        # Recent rollbacks increase risk significantly
        if profile.rollback_count > 0:
            risk += min(0.2, profile.rollback_count * 0.05)
        
        return min(0.3, risk)
    
    def get_confirmation_threshold(self, context: Dict[str, Any] = None) -> float:
        """
        Get dynamic confirmation threshold
        Lower trust = lower threshold (more confirmations)
        
        Args:
            context: Optional context
        
        Returns:
            Threshold (0.0-1.0)
        """
        base_threshold = 0.6  # Default threshold
        
        # Adjust based on user trust
        trust_score = self.profile_manager.get_trust_score()
        
        # Low trust = lower threshold (more confirmations)
        # High trust = higher threshold (fewer confirmations)
        adjusted_threshold = base_threshold + (trust_score - 0.5) * 0.4
        
        # Clamp to reasonable range
        return max(0.3, min(0.9, adjusted_threshold))
    
    def requires_confirmation(self, command: Command, context: Dict[str, Any] = None) -> bool:
        """
        Quick check if command requires confirmation
        
        Args:
            command: Command to check
            context: Optional context
        
        Returns:
            True if confirmation required
        """
        assessment = self.calculate_risk(command, context)
        return assessment.requires_confirmation
    
    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert risk score to risk level"""
        if score >= 0.9:
            return RiskLevel.CRITICAL
        elif score >= 0.7:
            return RiskLevel.HIGH
        elif score >= 0.4:
            return RiskLevel.MEDIUM
        elif score >= 0.2:
            return RiskLevel.LOW
        else:
            return RiskLevel.SAFE
    
    def _build_reason(self, command: Command, risk_score: float, factors: Dict[str, Any]) -> str:
        """Build human-readable reason for risk assessment"""
        reasons = []
        
        if factors["base_risk"] > 0.7:
            reasons.append(f"High-risk operation: {command.intent}")
        
        if factors["resource_risk"] > 0.2:
            reasons.append("Affects system resources")
        
        if factors["time_risk"] > 0:
            reasons.append("Late night execution")
        
        if factors["history_risk"] > 0.1:
            reasons.append("Recent errors detected")
        
        if factors["user_trust"] < 0.4:
            reasons.append("Low user trust score")
        
        if not reasons:
            reasons.append("Standard operation")
        
        level = self._score_to_level(risk_score)
        return f"{level.value.upper()}: {', '.join(reasons)}"
