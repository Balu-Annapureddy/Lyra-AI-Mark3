"""
Permission Manager
Handles permission levels and user confirmation for actions
"""

from enum import Enum
from typing import Dict, Any, Optional
from lyra.reasoning.command_schema import Command, RiskLevel
from lyra.core.logger import get_logger
from lyra.core.state_manager import StateManager, LyraState
from lyra.core.exceptions import PermissionDeniedError


class PermissionLevel(Enum):
    """Permission strictness levels"""
    STRICT = "strict"      # Confirm all risky actions
    MODERATE = "moderate"  # Confirm high/critical only
    RELAXED = "relaxed"    # Confirm critical only


class PermissionManager:
    """
    Manages permissions and user confirmations
    Ensures safe-by-default behavior
    """
    
    def __init__(self, permission_level: PermissionLevel = PermissionLevel.STRICT):
        self.logger = get_logger(__name__)
        self.state_manager = StateManager()
        self.permission_level = permission_level
        
        # Track granted permissions for this session
        self.granted_permissions: Dict[str, bool] = {}
    
    def requires_confirmation(self, command: Command) -> bool:
        """
        Check if command requires user confirmation
        
        Args:
            command: Command to check
        
        Returns:
            True if confirmation required
        """
        risk_level = command.risk_level
        
        # Check permission level
        if self.permission_level == PermissionLevel.STRICT:
            return risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        elif self.permission_level == PermissionLevel.MODERATE:
            return risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        elif self.permission_level == PermissionLevel.RELAXED:
            return risk_level == RiskLevel.CRITICAL
        
        return False
    
    def request_confirmation(self, command: Command) -> bool:
        """
        Request user confirmation for command
        
        Args:
            command: Command to confirm
        
        Returns:
            True if approved, False if denied
        
        Raises:
            PermissionDeniedError: If user denies permission
        """
        # Update state
        self.state_manager.set_state(
            LyraState.WAITING_CONFIRMATION,
            {"command_id": command.command_id, "intent": command.intent}
        )
        
        # Show confirmation prompt
        print(f"\n{'='*60}")
        print(f"CONFIRMATION REQUIRED")
        print(f"{'='*60}")
        print(f"Intent: {command.intent}")
        print(f"Risk Level: {command.risk_level.value.upper()}")
        print(f"Input: {command.raw_input}")
        
        if command.execution_plan:
            print(f"\nPlanned Actions:")
            for i, step in enumerate(command.execution_plan, 1):
                print(f"  {i}. {step.get('action')} - {step.get('params', {})}")
        
        print(f"\n{'='*60}")
        
        # Get user input
        while True:
            response = input("Approve this action? (yes/no): ").strip().lower()
            
            if response in ['yes', 'y']:
                self.granted_permissions[command.command_id] = True
                self.logger.info(f"Permission granted for command: {command.command_id}")
                return True
            elif response in ['no', 'n']:
                self.granted_permissions[command.command_id] = False
                self.logger.warning(f"Permission denied for command: {command.command_id}")
                raise PermissionDeniedError(
                    f"User denied permission for: {command.intent}",
                    {"command_id": command.command_id}
                )
            else:
                print("Please answer 'yes' or 'no'")
    
    def check_permission(self, command: Command) -> bool:
        """
        Check if command has permission to execute
        
        Args:
            command: Command to check
        
        Returns:
            True if permitted
        
        Raises:
            PermissionDeniedError: If permission denied
        """
        # Check if already granted
        if command.command_id in self.granted_permissions:
            return self.granted_permissions[command.command_id]
        
        # Check if confirmation required
        if self.requires_confirmation(command):
            return self.request_confirmation(command)
        
        # Auto-approve safe actions
        return True
    
    def set_permission_level(self, level: PermissionLevel):
        """Set permission strictness level"""
        self.permission_level = level
        self.logger.info(f"Permission level set to: {level.value}")
    
    def clear_session_permissions(self):
        """Clear all granted permissions for this session"""
        self.granted_permissions.clear()
        self.logger.info("Cleared session permissions")
