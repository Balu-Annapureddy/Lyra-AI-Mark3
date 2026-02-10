"""
Context Manager
Tracks conversation state, active tasks, and temporal context
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from lyra.reasoning.command_schema import Command
from lyra.core.logger import get_logger


class ContextManager:
    """
    Manages conversation context and state
    Tracks active commands, user preferences, and session information
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conversation_history: List[Command] = []
        self.active_commands: Dict[str, Command] = {}
        self.user_preferences: Dict[str, Any] = {}
        self.session_metadata: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "command_count": 0
        }
    
    def add_command(self, command: Command):
        """
        Add command to conversation history
        
        Args:
            command: Command to add
        """
        self.conversation_history.append(command)
        self.session_metadata["command_count"] += 1
        
        if command.status == "executing":
            self.active_commands[command.command_id] = command
        
        self.logger.debug(f"Added command to context: {command.command_id}")
    
    def update_command_status(self, command_id: str, status: str, 
                             result: Optional[Any] = None, error: Optional[str] = None):
        """
        Update command status
        
        Args:
            command_id: Command ID to update
            status: New status
            result: Optional result
            error: Optional error message
        """
        if command_id in self.active_commands:
            command = self.active_commands[command_id]
            command.status = status
            command.result = result
            command.error = error
            
            if status in ["completed", "failed", "cancelled"]:
                del self.active_commands[command_id]
    
    def get_recent_commands(self, limit: int = 5) -> List[Command]:
        """
        Get recent commands from history
        
        Args:
            limit: Number of recent commands to return
        
        Returns:
            List of recent commands
        """
        return self.conversation_history[-limit:]
    
    def get_context_for_command(self, command: Command) -> Dict[str, Any]:
        """
        Build context dictionary for a command
        
        Args:
            command: Command to build context for
        
        Returns:
            Context dictionary
        """
        recent_intents = [cmd.intent for cmd in self.get_recent_commands(3)]
        
        context = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "recent_intents": recent_intents,
            "active_command_count": len(self.active_commands),
            "total_commands": self.session_metadata["command_count"],
            "user_preferences": self.user_preferences.copy()
        }
        
        return context
    
    def set_preference(self, key: str, value: Any):
        """Set user preference"""
        self.user_preferences[key] = value
        self.logger.info(f"Set preference: {key} = {value}")
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference"""
        return self.user_preferences.get(key, default)
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        self.active_commands.clear()
        self.logger.info("Cleared conversation history")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        return {
            "session_id": self.session_id,
            "start_time": self.session_metadata["start_time"],
            "duration_seconds": (datetime.now() - datetime.fromisoformat(
                self.session_metadata["start_time"])).total_seconds(),
            "total_commands": self.session_metadata["command_count"],
            "active_commands": len(self.active_commands),
            "history_size": len(self.conversation_history)
        }
