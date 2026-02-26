# -*- coding: utf-8 -*-
"""
Config Change Tool Stub - Frozen v1.0
Implements Phase 1 stabilization with strict safety guards.
"""

from typing import Dict, Any
from lyra.core.logger import get_logger
from lyra.safety.execution_logger import ExecutionLogger

class ChangeConfigTool:
    """
    Stub for changing system configuration. 
    Enforces deny-by-default and mandatory confirmation.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.exec_logger = ExecutionLogger()

    def execute(self, setting: str, value: Any, confirmed: bool = False) -> Dict[str, Any]:
        """
        Simulate config change with safety check.
        """
        # CRITICAL SAFETY: Deny by default
        if not confirmed:
            self.logger.warning(f"[SAFETY] Attempted to change {setting} without confirmation. DENIED.")
            return {
                "success": False,
                "error": "ConfirmationRequiredError",
                "message": f"Changing {setting} requires explicit user confirmation."
            }

        self.logger.info(f"[EXECUTION] Changing config stub: {setting} -> {value}")
        
        # Log plan before simulated execution
        self.exec_logger.log_execution(
            intent="change_config",
            command=f"set {setting}={value}",
            parameters={"setting": setting, "value": value},
            result="SIMULATED_SUCCESS",
            rollback_info=f"Revert {setting} to previous value (Placeholder)"
        )

        return {
            "success": True,
            "setting": setting,
            "value": value,
            "status": "changed (simulated)",
            "message": f"Successfully updated {setting} to {value} (Phase 1 Stub)"
        }
