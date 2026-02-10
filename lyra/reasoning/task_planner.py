"""
Task Planning System
Decomposes high-level goals into executable steps
"""

from typing import List, Dict, Any
from lyra.reasoning.command_schema import Command, RiskLevel
from lyra.core.logger import get_logger


logger = get_logger(__name__)


class TaskPlanner:
    """
    Breaks down commands into executable action sequences
    Handles dependencies and step ordering
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def create_execution_plan(self, command: Command) -> List[Dict[str, Any]]:
        """
        Create execution plan for a command
        
        Args:
            command: Command object with detected intent
        
        Returns:
            List of execution steps
        """
        intent = command.intent
        entities = command.entities
        
        # Map intents to execution plans
        plan_generators = {
            "get_time": self._plan_get_time,
            "get_date": self._plan_get_date,
            "create_file": self._plan_create_file,
            "delete_file": self._plan_delete_file,
            "open_file": self._plan_open_file,
            "open_application": self._plan_open_application,
            "close_application": self._plan_close_application,
            "shutdown_system": self._plan_shutdown_system,
            "restart_system": self._plan_restart_system,
            "search_files": self._plan_search_files,
            "greeting": self._plan_greeting,
            "help": self._plan_help,
        }
        
        generator = plan_generators.get(intent, self._plan_unknown)
        plan = generator(command)
        
        command.execution_plan = plan
        self.logger.info(f"Created execution plan for {intent}: {len(plan)} steps")
        
        return plan
    
    # Plan generators for each intent
    
    def _plan_get_time(self, command: Command) -> List[Dict[str, Any]]:
        return [{"action": "get_system_time", "params": {}}]
    
    def _plan_get_date(self, command: Command) -> List[Dict[str, Any]]:
        return [{"action": "get_system_date", "params": {}}]
    
    def _plan_create_file(self, command: Command) -> List[Dict[str, Any]]:
        filename = command.entities.get("filename", "untitled.txt")
        return [
            {"action": "validate_filename", "params": {"filename": filename}},
            {"action": "create_file", "params": {"filename": filename, "content": ""}}
        ]
    
    def _plan_delete_file(self, command: Command) -> List[Dict[str, Any]]:
        filename = command.entities.get("filename")
        if not filename:
            return [{"action": "error", "params": {"message": "No filename specified"}}]
        
        return [
            {"action": "check_file_exists", "params": {"filename": filename}},
            {"action": "delete_file", "params": {"filename": filename}}
        ]
    
    def _plan_open_file(self, command: Command) -> List[Dict[str, Any]]:
        filename = command.entities.get("filename")
        if not filename:
            return [{"action": "error", "params": {"message": "No filename specified"}}]
        
        return [
            {"action": "check_file_exists", "params": {"filename": filename}},
            {"action": "open_file", "params": {"filename": filename}}
        ]
    
    def _plan_open_application(self, command: Command) -> List[Dict[str, Any]]:
        app_name = command.entities.get("app_name", "").lower()
        return [
            {"action": "launch_application", "params": {"app_name": app_name}}
        ]
    
    def _plan_close_application(self, command: Command) -> List[Dict[str, Any]]:
        app_name = command.entities.get("app_name", "").lower()
        return [
            {"action": "close_application", "params": {"app_name": app_name}}
        ]
    
    def _plan_shutdown_system(self, command: Command) -> List[Dict[str, Any]]:
        return [
            {"action": "shutdown_system", "params": {"delay_seconds": 5}}
        ]
    
    def _plan_restart_system(self, command: Command) -> List[Dict[str, Any]]:
        return [
            {"action": "restart_system", "params": {"delay_seconds": 5}}
        ]
    
    def _plan_search_files(self, command: Command) -> List[Dict[str, Any]]:
        query = command.entities.get("query", "")
        return [
            {"action": "search_files", "params": {"query": query, "max_results": 10}}
        ]
    
    def _plan_greeting(self, command: Command) -> List[Dict[str, Any]]:
        return [
            {"action": "respond", "params": {"message": "Hello! I'm Lyra. How can I help you?"}}
        ]
    
    def _plan_help(self, command: Command) -> List[Dict[str, Any]]:
        return [
            {"action": "show_capabilities", "params": {}}
        ]
    
    def _plan_unknown(self, command: Command) -> List[Dict[str, Any]]:
        return [
            {"action": "respond", "params": {"message": f"I'm not sure how to handle: {command.raw_input}"}}
        ]
