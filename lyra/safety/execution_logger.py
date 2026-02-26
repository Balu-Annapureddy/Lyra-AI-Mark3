"""
Execution Logger - Phase 2C
Logs command execution with before/after state capture
Supports rollback capabilities
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from lyra.reasoning.command_schema import Command
from lyra.core.logger import get_logger


@dataclass
class ExecutionRecord:
    """Record of a command execution"""
    record_id: str
    command_id: str
    command: Dict[str, Any]
    created_at: int
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    rollback_instructions: Optional[List[Dict[str, Any]]] = None
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ExecutionLogger:
    """
    Logs command execution with state capture
    Enables rollback and audit trail
    """
    
    def __init__(self, log_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if log_path is None:
            project_root = Path(__file__).parent.parent.parent
            log_path = str(project_root / "data" / "execution_logs")
        
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        
        # Current execution log file
        self.current_log_file = self.log_path / f"execution_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        self.logger.info(f"Execution logger initialized: {self.log_path}")
    
    def capture_before_state(self, command: Command, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Capture state before command execution
        
        Args:
            command: Command to execute
            context: Optional context
        
        Returns:
            Before state snapshot
        """
        before_state = {
            "created_at": int(datetime.now().timestamp()),
            "command_id": command.command_id,
            "intent": command.intent,
            "context": context or {}
        }
        
        # Capture file state if file operation
        if "filename" in command.entities:
            filename = command.entities["filename"]
            before_state["file_exists"] = Path(filename).exists()
            if before_state["file_exists"]:
                try:
                    before_state["file_size"] = Path(filename).stat().st_size
                    before_state["file_modified"] = Path(filename).stat().st_mtime
                except Exception as e:
                    self.logger.warning(f"Could not capture file state: {e}")
        
        return before_state
    
    def capture_after_state(self, command: Command, result: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Capture state after command execution
        
        Args:
            command: Executed command
            result: Execution result
            context: Optional context
        
        Returns:
            After state snapshot
        """
        after_state = {
            "created_at": int(datetime.now().timestamp()),
            "command_id": command.command_id,
            "result": str(result) if result else None,
            "status": command.status,
            "context": context or {}
        }
        
        # Capture file state if file operation
        if "filename" in command.entities:
            filename = command.entities["filename"]
            after_state["file_exists"] = Path(filename).exists()
            if after_state["file_exists"]:
                try:
                    after_state["file_size"] = Path(filename).stat().st_size
                    after_state["file_modified"] = Path(filename).stat().st_mtime
                except Exception as e:
                    self.logger.warning(f"Could not capture file state: {e}")
        
        return after_state
    
    def generate_rollback_instructions(self, command: Command, before_state: Dict[str, Any], after_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate rollback instructions based on state changes
        
        Args:
            command: Executed command
            before_state: State before execution
            after_state: State after execution
        
        Returns:
            List of rollback instructions
        """
        instructions = []
        
        intent = command.intent.lower()
        
        # File creation rollback
        if "create" in intent and "file" in intent:
            if not before_state.get("file_exists") and after_state.get("file_exists"):
                instructions.append({
                    "action": "delete_file",
                    "filename": command.entities.get("filename"),
                    "reason": "Rollback file creation"
                })
        
        # File deletion rollback (limited - can't restore content)
        elif "delete" in intent and "file" in intent:
            if before_state.get("file_exists") and not after_state.get("file_exists"):
                instructions.append({
                    "action": "restore_from_backup",
                    "filename": command.entities.get("filename"),
                    "reason": "Rollback file deletion (requires backup)",
                    "warning": "Content cannot be restored without backup"
                })
        
        # File modification rollback
        elif "modify" in intent or "edit" in intent:
            instructions.append({
                "action": "restore_from_backup",
                "filename": command.entities.get("filename"),
                "reason": "Rollback file modification (requires backup)",
                "warning": "Original content cannot be restored without backup"
            })
        
        return instructions
    
    def log_execution(self, command: Command, before_state: Dict[str, Any], after_state: Dict[str, Any], success: bool, error: Optional[str] = None, execution_time_ms: float = 0.0) -> ExecutionRecord:
        """
        Log command execution
        
        Args:
            command: Executed command
            before_state: State before execution
            after_state: State after execution
            success: Whether execution succeeded
            error: Optional error message
            execution_time_ms: Execution time in milliseconds
        
        Returns:
            Execution record
        """
        # Generate rollback instructions
        rollback_instructions = self.generate_rollback_instructions(command, before_state, after_state)
        
        # Create execution record
        record = ExecutionRecord(
            record_id=str(uuid.uuid4()),
            command_id=command.command_id,
            command=command.to_dict(),
            created_at=int(datetime.now().timestamp()),
            before_state=before_state,
            after_state=after_state,
            success=success,
            error=error,
            rollback_instructions=rollback_instructions,
            execution_time_ms=execution_time_ms
        )
        
        # Write to log file (JSONL format)
        try:
            with open(self.current_log_file, 'a') as f:
                f.write(json.dumps(record.to_dict()) + '\n')
            
            self.logger.info(f"Logged execution: {command.command_id} (success={success})")
        except Exception as e:
            self.logger.error(f"Failed to write execution log: {e}")
        
        return record
    
    def get_recent_executions(self, limit: int = 10) -> List[ExecutionRecord]:
        """
        Get recent execution records
        
        Args:
            limit: Maximum number of records
        
        Returns:
            List of execution records
        """
        records = []
        
        try:
            if self.current_log_file.exists():
                with open(self.current_log_file, 'r') as f:
                    lines = f.readlines()
                
                # Get last N lines
                for line in lines[-limit:]:
                    data = json.loads(line)
                    record = ExecutionRecord(**data)
                    records.append(record)
        except Exception as e:
            self.logger.error(f"Failed to read execution log: {e}")
        
        return records
    
    def get_execution_by_id(self, record_id: str) -> Optional[ExecutionRecord]:
        """
        Get execution record by ID
        
        Args:
            record_id: Record ID
        
        Returns:
            Execution record or None
        """
        try:
            if self.current_log_file.exists():
                with open(self.current_log_file, 'r') as f:
                    for line in f:
                        data = json.loads(line)
                        if data["record_id"] == record_id:
                            return ExecutionRecord(**data)
        except Exception as e:
            self.logger.error(f"Failed to find execution record: {e}")
        
        return None
    
    def get_rollback_instructions(self, record_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get rollback instructions for an execution
        
        Args:
            record_id: Record ID
        
        Returns:
            Rollback instructions or None
        """
        record = self.get_execution_by_id(record_id)
        if record:
            return record.rollback_instructions
        return None
