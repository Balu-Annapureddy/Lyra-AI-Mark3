"""
Lyra AI Operating System - Main Entry Point
A local-first, modular personal AI assistant
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lyra.core.config import Config
from lyra.core.logger import get_logger
from lyra.core.state_manager import StateManager, LyraState
from lyra.core.exceptions import LyraException

from lyra.interaction.text_interface import TextInterface
from lyra.reasoning.intent_detector import IntentDetector
from lyra.reasoning.task_planner import TaskPlanner
from lyra.reasoning.context_manager import ContextManager
from lyra.memory.event_memory import EventMemory
from lyra.memory.preference_store import PreferenceStore
from lyra.memory.memory_level import MemoryLevel
from lyra.automation.task_executor import TaskExecutor
from lyra.safety.permission_manager import PermissionManager, PermissionLevel
from lyra.safety.validator import InputValidator
from lyra.learning.outcome_tracker import OutcomeTracker


class LyraSystem:
    """
    Main Lyra system orchestrator
    Coordinates all layers and manages the main loop
    """
    
    def __init__(self):
        # Initialize configuration
        self.config = Config()
        self.logger = get_logger(__name__)
        self.state_manager = StateManager()
        
        # Initialize components
        self.logger.info("Initializing Lyra AI Operating System...")
        
        # Interaction
        self.interface = TextInterface()
        
        # Reasoning
        self.intent_detector = IntentDetector()
        self.task_planner = TaskPlanner()
        self.context_manager = ContextManager()
        
        # Memory
        self.event_memory = EventMemory()
        self.preference_store = PreferenceStore()
        
        # Automation
        dry_run_default = self.config.get('safety.dry_run_by_default', True)
        self.task_executor = TaskExecutor(dry_run_mode=dry_run_default)
        
        # Safety
        permission_level_str = self.config.get('safety.permission_level', 'strict')
        permission_level = PermissionLevel[permission_level_str.upper()]
        self.permission_manager = PermissionManager(permission_level=permission_level)
        self.validator = InputValidator()
        
        # Learning
        self.outcome_tracker = OutcomeTracker()
        
        self.logger.info("Lyra initialized successfully")
    
    def run(self):
        """Main execution loop"""
        try:
            self.state_manager.set_state(LyraState.IDLE)
            
            # Start interface
            for user_input in self.interface.start():
                if not user_input:
                    continue
                
                try:
                    self._process_input(user_input)
                except LyraException as e:
                    self.interface.display_error(str(e))
                    self.logger.error(f"Lyra exception: {e}")
                except Exception as e:
                    self.interface.display_error(f"Unexpected error: {e}")
                    self.logger.exception("Unexpected error")
        
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        finally:
            self.shutdown()
    
    def _process_input(self, user_input: str):
        """
        Process user input through the full pipeline
        
        Args:
            user_input: Raw user input
        """
        # Validate input
        self.validator.validate_command_input(user_input)
        sanitized_input = self.validator.sanitize_input(user_input)
        
        # Detect intent
        self.state_manager.set_state(LyraState.THINKING)
        self.interface.display_thinking()
        
        command = self.intent_detector.detect_intent(sanitized_input)
        
        # Add context
        command.context = self.context_manager.get_context_for_command(command)
        
        # Create execution plan
        self.task_planner.create_execution_plan(command)
        
        # Add to context
        self.context_manager.add_command(command)
        
        # Check if dry-run mode
        dry_run_mode = self.config.get('safety.dry_run_by_default', True)
        
        if dry_run_mode:
            # Show dry-run simulation
            result = self.task_executor.execute_command(command, dry_run=True)
            self.interface.display_dry_run_result(result)
            
            # Ask if user wants to execute
            response = input("Execute this command? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                self.interface.display_response("Command cancelled", "warning")
                return
        
        # Check permissions
        try:
            self.permission_manager.check_permission(command)
        except LyraException as e:
            self.interface.display_error(str(e))
            return
        
        # Execute command
        try:
            result = self.task_executor.execute_command(command, dry_run=False)
            
            # Display result
            if isinstance(result, dict) and 'results' in result:
                # Extract meaningful result
                final_result = result['results'][-1] if result['results'] else "Done"
            else:
                final_result = result
            
            self.interface.display_response(str(final_result), "success")
            
            # Store in memory
            self.event_memory.store_command(command, MemoryLevel.SHORT_TERM)
            
            # Track outcome
            self.outcome_tracker.record_outcome(command, success=True)
        
        except LyraException as e:
            self.interface.display_error(str(e))
            self.outcome_tracker.record_outcome(command, success=False, error=str(e))
    
    def shutdown(self):
        """Clean shutdown"""
        self.logger.info("Shutting down Lyra...")
        self.interface.stop()
        self.state_manager.set_state(LyraState.IDLE)
        self.logger.info("Lyra shutdown complete")


def main():
    """Main entry point"""
    lyra = LyraSystem()
    lyra.run()


if __name__ == "__main__":
    main()
