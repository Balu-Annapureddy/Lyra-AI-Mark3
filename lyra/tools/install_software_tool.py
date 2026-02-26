# -*- coding: utf-8 -*-
"""
Software Installation Tool Stub - Frozen v1.0
Implements Phase 1 stabilization with strict safety guards.
"""

from typing import Dict, Any
from lyra.core.logger import get_logger
from lyra.safety.execution_logger import ExecutionLogger

class InstallSoftwareTool:
    """
    Stub for installing software. 
    Enforces deny-by-default and mandatory confirmation.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.exec_logger = ExecutionLogger()

    def execute(self, package: str, confirmed: bool = False) -> Dict[str, Any]:
        """
        Simulate software installation with safety check.
        """
        # CRITICAL SAFETY: Deny by default
        if not confirmed:
            self.logger.warning(f"[SAFETY] Attempted to install {package} without confirmation. DENIED.")
            return {
                "success": False,
                "error": "ConfirmationRequiredError",
                "message": f"Installation of {package} requires explicit user confirmation."
            }

        self.logger.info(f"[EXECUTION] Installing software stub: {package}")
        
        # Log plan before simulated execution
        self.exec_logger.log_execution(
            intent="install_software",
            command=f"install {package}",
            parameters={"package": package},
            result="SIMULATED_SUCCESS",
            rollback_info=f"Uninstall {package} (Placeholder)"
        )

        return {
            "success": True,
            "package": package,
            "status": "installed (simulated)",
            "message": f"Successfully installed {package} (Phase 1 Stub)"
        }
