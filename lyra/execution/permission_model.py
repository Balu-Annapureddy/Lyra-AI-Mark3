"""
Permission Model - Phase 4A
Defines and enforces permission tiers
Integrates with AdaptiveRiskScorer
"""

from typing import Dict, Any
from dataclasses import dataclass
from lyra.tools.tool_registry import ToolDefinition
from lyra.safety.adaptive_risk_scorer import AdaptiveRiskScorer
from lyra.core.user_profile import UserProfileManager
from lyra.core.logger import get_logger


@dataclass
class PermissionResult:
    """Result of permission check"""
    allowed: bool
    reason: str
    requires_confirmation: bool
    permission_tier: str


class PermissionChecker:
    """
    Enforces permission tiers for tool execution
    Integrates with adaptive risk scoring and user trust
    """
    
    # Permission tier definitions
    TIERS = {
        "LOW": {
            "description": "Non-destructive, read-only operations",
            "risk_threshold": 0.3,
            "trust_requirement": 0.3,
            "auto_execute": True,
            "examples": ["read_file", "get_system_info", "list_directory"]
        },
        "MEDIUM": {
            "description": "Modifies environment, potentially reversible",
            "risk_threshold": 0.7,
            "trust_requirement": 0.5,
            "auto_execute": False,
            "examples": ["write_file", "create_directory", "modify_config"]
        },
        "HIGH": {
            "description": "Destructive, system-level, irreversible",
            "risk_threshold": 1.0,  # Always requires confirmation
            "trust_requirement": 0.7,
            "auto_execute": False,
            "examples": ["delete_file", "run_command", "install_software"]
        }
    }
    
    def __init__(self, risk_scorer: AdaptiveRiskScorer = None,
                 profile_manager: UserProfileManager = None):
        self.logger = get_logger(__name__)
        self.risk_scorer = risk_scorer or AdaptiveRiskScorer()
        self.profile_manager = profile_manager or UserProfileManager()
    
    def check_permission(self, tool: ToolDefinition, 
                        context: Dict[str, Any] = None) -> PermissionResult:
        """
        Check if tool execution is permitted
        
        Args:
            tool: Tool definition
            context: Execution context
        
        Returns:
            PermissionResult
        """
        context = context or {}
        
        # Get user trust score
        trust_score = self.profile_manager.get_trust_score()
        
        # Get tier requirements
        tier = tool.permission_level_required
        tier_config = self.TIERS.get(tier, self.TIERS["MEDIUM"])
        
        # Check trust requirement
        if trust_score < tier_config["trust_requirement"]:
            return PermissionResult(
                allowed=False,
                reason=f"Insufficient trust ({trust_score:.2f} < {tier_config['trust_requirement']:.2f})",
                requires_confirmation=True,
                permission_tier=tier
            )
        
        # Check if tool requires confirmation
        requires_confirmation = tool.requires_confirmation
        
        # HIGH tier always requires confirmation
        if tier == "HIGH":
            requires_confirmation = True
        
        # MEDIUM tier requires confirmation if trust is low
        if tier == "MEDIUM" and trust_score < 0.6:
            requires_confirmation = True
        
        # Tool is allowed
        return PermissionResult(
            allowed=True,
            reason="Permission granted",
            requires_confirmation=requires_confirmation,
            permission_tier=tier
        )
    
    def get_tier_info(self, tier: str) -> Dict[str, Any]:
        """Get information about a permission tier"""
        return self.TIERS.get(tier, {})
    
    def can_auto_execute(self, tool: ToolDefinition) -> bool:
        """
        Check if tool can auto-execute
        
        Args:
            tool: Tool definition
        
        Returns:
            True if can auto-execute
        """
        tier = tool.permission_level_required
        tier_config = self.TIERS.get(tier, self.TIERS["MEDIUM"])
        
        # Only LOW tier can auto-execute
        if not tier_config["auto_execute"]:
            return False
        
        # Check trust
        trust_score = self.profile_manager.get_trust_score()
        if trust_score < tier_config["trust_requirement"]:
            return False
        
        return True
