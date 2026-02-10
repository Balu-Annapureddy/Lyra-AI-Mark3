"""
Task Executor - User Refinement #2
Unified task execution with dry-run mode support
Simulates actions before execution for safety
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from lyra.reasoning.command_schema import Command, RiskLevel
from lyra.automation.pc_controller import PCController
from lyra.automation.phone_controller import PhoneController
from lyra.core.logger import get_logger, ActionLogger
from lyra.core.state_manager import StateManager, LyraState
from lyra.core.exceptions import ExecutionError


class TaskExecutor:
    """
    Unified task execution engine with dry-run mode
    Dispatches actions to appropriate controllers
    """
    
    def __init__(self, dry_run_mode: bool = True):
        self.logger = get_logger(__name__)
        self.action_logger = ActionLogger()
        self.state_manager = StateManager()
        
        self.dry_run_mode = dry_run_mode
        self.pc_controller = PCController()
        self.phone_controller = PhoneController()
    
    def execute_command(self, command: Command, dry_run: Optional[bool] = None) -> Any:
        """
        Execute a command with optional dry-run
        
        Args:
            command: Command to execute
            dry_run: Override dry-run mode for this execution
        
        Returns:
            Execution result
        
        Raises:
            ExecutionError: If execution fails
        """
        use_dry_run = dry_run if dry_run is not None else self.dry_run_mode
        
        # Update state
        if use_dry_run:
            self.state_manager.set_state(LyraState.THINKING, {"command_id": command.command_id})
        else:
            self.state_manager.set_state(LyraState.EXECUTING, {"command_id": command.command_id})
        
        start_time = time.time()
        
        try:
            if use_dry_run:
                result = self._dry_run_command(command)
            else:
                result = self._execute_command(command)
            
            # Record execution time
            execution_time = (time.time() - start_time) * 1000  # ms
            command.execution_time_ms = execution_time
            command.status = "completed"
            command.result = result
            
            # Log success
            self.action_logger.log_action(
                action_type=command.intent,
                details={"command_id": command.command_id, "dry_run": use_dry_run},
                success=True
            )
            
            self.state_manager.set_state(LyraState.IDLE)
            return result
        
        except Exception as e:
            command.status = "failed"
            command.error = str(e)
            
            self.action_logger.log_action(
                action_type=command.intent,
                details={"command_id": command.command_id, "error": str(e)},
                success=False
            )
            
            self.state_manager.set_state(LyraState.ERROR, {"error": str(e)})
            raise ExecutionError(f"Command execution failed: {e}", {"command_id": command.command_id})
    
    def _dry_run_command(self, command: Command) -> Dict[str, Any]:
        """
        Simulate command execution without actually performing actions
        
        Args:
            command: Command to simulate
        
        Returns:
            Simulation result
        """
        self.logger.info(f"[DRY RUN] Simulating command: {command.intent}")
        
        simulation_result = {
            "dry_run": True,
            "command_id": command.command_id,
            "intent": command.intent,
            "steps": [],
            "would_execute": True,
            "estimated_risk": command.risk_level.value
        }
        
        # Simulate each step in execution plan
        for step in command.execution_plan:
            action = step.get("action")
            params = step.get("params", {})
            
            step_simulation = {
                "action": action,
                "params": params,
                "would_succeed": True,
                "side_effects": self._predict_side_effects(action, params)
            }
            
            simulation_result["steps"].append(step_simulation)
        
        return simulation_result
    
    def _predict_side_effects(self, action: str, params: Dict[str, Any]) -> List[str]:
        """
        Predict side effects of an action
        
        Args:
            action: Action name
            params: Action parameters
        
        Returns:
            List of predicted side effects
        """
        side_effects = []
        
        if action == "create_file":
            side_effects.append(f"Create file: {params.get('filename', 'unknown')}")
        elif action == "delete_file":
            side_effects.append(f"Delete file: {params.get('filename', 'unknown')}")
        elif action == "shutdown_system":
            side_effects.append("System will shutdown")
        elif action == "restart_system":
            side_effects.append("System will restart")
        elif action == "launch_application":
            side_effects.append(f"Launch application: {params.get('app_name', 'unknown')}")
        
        return side_effects
    
    def _execute_command(self, command: Command) -> Any:
        """
        Actually execute command
        
        Args:
            command: Command to execute
        
        Returns:
            Execution result
        """
        self.logger.info(f"Executing command: {command.intent}")
        
        results = []
        
        for step in command.execution_plan:
            action = step.get("action")
            params = step.get("params", {})
            
            result = self._execute_action(action, params)
            results.append(result)
        
        return {"results": results, "success": True}
    
    def _execute_action(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Execute a single action
        
        Args:
            action: Action name
            params: Action parameters
        
        Returns:
            Action result
        """
        # Map actions to controller methods
        action_map = {
            # System info
            "get_system_time": lambda: datetime.now().strftime("%H:%M:%S"),
            "get_system_date": lambda: datetime.now().strftime("%Y-%m-%d"),
            
            # File operations
            "create_file": lambda: self.pc_controller.create_file(**params),
            "delete_file": lambda: self.pc_controller.delete_file(**params),
            "open_file": lambda: self.pc_controller.open_file(**params),
            "check_file_exists": lambda: self.pc_controller.file_exists(**params),
            "search_files": lambda: self.pc_controller.search_files(**params),
            
            # Application control
            "launch_application": lambda: self.pc_controller.launch_application(**params),
            "close_application": lambda: self.pc_controller.close_application(**params),
            
            # System control
            "shutdown_system": lambda: self.pc_controller.shutdown_system(**params),
            "restart_system": lambda: self.pc_controller.restart_system(**params),
            
            # Responses
            "respond": lambda: params.get("message", ""),
            "show_capabilities": lambda: self._get_capabilities(),
            
            # Validation
            "validate_filename": lambda: self._validate_filename(params.get("filename", "")),
            
            # Error
            "error": lambda: self._raise_error(params.get("message", "Unknown error"))
        }
        
        if action in action_map:
            return action_map[action]()
        else:
            raise ExecutionError(f"Unknown action: {action}")
    
    def _get_capabilities(self) -> str:
        """Get Lyra's capabilities"""
        return """I can help you with:
- File operations (create, delete, open, search)
- Application control (launch, close)
- System information (time, date)
- System control (shutdown, restart) [requires confirmation]

Try saying things like:
- "What time is it?"
- "Create a file called test.txt"
- "Open calculator"
- "Search for documents"
"""
    
    def _validate_filename(self, filename: str) -> bool:
        """Validate filename"""
        import re
        # Basic filename validation
        if not filename or len(filename) > 255:
            raise ExecutionError("Invalid filename length")
        
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, filename):
            raise ExecutionError("Filename contains invalid characters")
        
        return True
    
    def _raise_error(self, message: str):
        """Raise execution error"""
        raise ExecutionError(message)
    
    def set_dry_run_mode(self, enabled: bool):
        """Enable or disable dry-run mode"""
        self.dry_run_mode = enabled
        self.logger.info(f"Dry-run mode: {'enabled' if enabled else 'disabled'}")
