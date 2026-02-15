"""
Lyra Pipeline - Phase 5A
Orchestrates full execution pipeline
Input → Intent → Plan → Execute → Output
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from lyra.reasoning.intent_detector import IntentDetector
from lyra.reasoning.command_schema import Command
from lyra.planning.execution_planner import ExecutionPlanner
from lyra.execution.execution_gateway import ExecutionGateway
from lyra.cli.output_formatter import OutputFormatter
from lyra.core.logger import get_logger


@dataclass
class PipelineResult:
    """Result of pipeline execution"""
    success: bool
    output: str
    cancelled: bool = False
    error: Optional[str] = None


class LyraPipeline:
    """
    Full execution pipeline orchestrator
    Phase 5A: Connect all components
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.intent_detector = IntentDetector()
        self.planner = ExecutionPlanner()
        self.gateway = ExecutionGateway()
        self.formatter = OutputFormatter()
        
        self.logger.info("Lyra pipeline initialized")
    
    def process_command(self, user_input: str, 
                       auto_confirm: bool = False) -> PipelineResult:
        """
        Process user command through full pipeline
        
        Args:
            user_input: User command
            auto_confirm: Auto-confirm without prompting
        
        Returns:
            PipelineResult
        """
        try:
            # 1. Detect intent
            self.logger.info(f"Processing command: {user_input}")
            command = self.intent_detector.detect_intent(user_input)
            
            if not command or command.intent == "unknown":
                return PipelineResult(
                    success=False,
                    output=self.formatter.format_warning("Could not understand command"),
                    error="Unknown intent"
                )
            
            self.logger.info(f"Intent: {command.intent}")
            
            # 2. Generate execution plan
            plan = self.planner.create_plan_from_command(command)
            
            if not plan:
                return PipelineResult(
                    success=False,
                    output=self.formatter.format_warning("Could not create execution plan"),
                    error="Plan generation failed"
                )
            
            self.logger.info(f"Plan created: {plan.plan_id}, {len(plan.steps)} steps")
            
            # 3. Check if confirmation needed
            confirmed = auto_confirm
            if plan.requires_confirmation and not auto_confirm:
                # Show plan to user
                plan_display = self.formatter.format_plan(
                    plan_description=f"{command.intent}: {command.raw_input}",
                    steps=len(plan.steps),
                    risk=plan.total_risk_score
                )
                print(plan_display)
                
                # Ask for confirmation
                response = input(self.formatter.format_confirmation_prompt())
                confirmed = response.lower() in ['y', 'yes']
                
                if not confirmed:
                    return PipelineResult(
                        success=False,
                        output=self.formatter.format_info("Cancelled by user"),
                        cancelled=True
                    )
            
            # 4. Execute plan
            self.logger.info(f"Executing plan: {plan.plan_id}")
            result = self.gateway.execute_plan(plan, confirmed=confirmed)
            
            # 5. Format output
            output = self.formatter.format_result(result)
            
            return PipelineResult(
                success=result.success,
                output=output,
                error=result.error
            )
        
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            return PipelineResult(
                success=False,
                output=self.formatter.format_error_from_exception(e),
                error=str(e)
            )
    
    def simulate_command(self, user_input: str) -> PipelineResult:
        """
        Simulate command execution (dry-run)
        
        Args:
            user_input: User command
        
        Returns:
            PipelineResult
        """
        try:
            # Detect intent
            command = self.intent_detector.detect_intent(user_input)
            
            if not command or command.intent == "unknown":
                return PipelineResult(
                    success=False,
                    output=self.formatter.format_warning("Could not understand command"),
                    error="Unknown intent"
                )
            
            # Generate plan
            plan = self.planner.create_plan_from_command(command)
            
            if not plan:
                return PipelineResult(
                    success=False,
                    output=self.formatter.format_warning("Could not create execution plan"),
                    error="Plan generation failed"
                )
            
            # Simulate execution
            result = self.gateway.execute_plan(plan, confirmed=True, simulate=True)
            
            # Format output
            output = self.formatter.format_result(result)
            
            return PipelineResult(
                success=result.success,
                output=output
            )
        
        except Exception as e:
            self.logger.error(f"Simulation error: {e}")
            return PipelineResult(
                success=False,
                output=self.formatter.format_warning(f"Simulation failed: {e}"),
                error=str(e)
            )
