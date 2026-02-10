"""
Safety Action Logger
Specialized logger for safety-critical actions and audit trail
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from lyra.reasoning.command_schema import Command
from lyra.core.logger import get_logger


class SafetyActionLogger:
    """
    Logs all actions for safety audit trail
    Separate from general logging for compliance and debugging
    """
    
    def __init__(self, log_file: str = None):
        self.logger = get_logger(__name__)
        
        if log_file is None:
            project_root = Path(__file__).parent.parent.parent
            log_file = str(project_root / "data" / "logs" / "safety_audit.log")
        
        self.log_file = log_file
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    def log_command_execution(self, command: Command, approved: bool, 
                             executed: bool, result: Any = None, error: str = None):
        """
        Log command execution for audit trail
        
        Args:
            command: Command that was executed
            approved: Whether command was approved
            executed: Whether command was actually executed
            result: Execution result
            error: Error message if failed
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "command_id": command.command_id,
            "intent": command.intent,
            "raw_input": command.raw_input,
            "risk_level": command.risk_level.value,
            "approved": approved,
            "executed": executed,
            "success": error is None,
            "result": str(result) if result else None,
            "error": error,
            "execution_time_ms": command.execution_time_ms
        }
        
        self._write_log_entry(log_entry)
    
    def log_permission_request(self, command: Command, granted: bool):
        """
        Log permission request
        
        Args:
            command: Command requesting permission
            granted: Whether permission was granted
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "permission_request",
            "command_id": command.command_id,
            "intent": command.intent,
            "risk_level": command.risk_level.value,
            "granted": granted
        }
        
        self._write_log_entry(log_entry)
    
    def log_safety_violation(self, command: Command, violation_type: str, details: Dict[str, Any]):
        """
        Log safety violation
        
        Args:
            command: Command that violated safety
            violation_type: Type of violation
            details: Violation details
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "safety_violation",
            "command_id": command.command_id,
            "intent": command.intent,
            "violation_type": violation_type,
            "details": details
        }
        
        self._write_log_entry(log_entry)
        self.logger.error(f"Safety violation: {violation_type} - {details}")
    
    def _write_log_entry(self, entry: Dict[str, Any]):
        """Write log entry to file"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write safety log: {e}")
