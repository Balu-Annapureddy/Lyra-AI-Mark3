"""
Execution Gateway - Phase 4A
Single controlled entry point for ALL tool execution
Validates, enforces safety, logs all executions
NO direct OS access - validation only for Phase 4A
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from lyra.planning.execution_planner import ExecutionPlan, ExecutionStep
from lyra.tools.tool_registry import ToolRegistry
from lyra.execution.permission_model import PermissionChecker
from lyra.safety.execution_logger import ExecutionLogger
from lyra.memory.behavioral_memory import BehavioralMemory
from lyra.core.logger import get_logger


@dataclass
class ValidationResult:
    """Result of step validation"""
    valid: bool
    reason: str
    step_id: str


@dataclass
class StepResult:
    """Result of single step execution"""
    step_id: str
    step_number: int
    success: bool
    output: Any
    error: Optional[str]
    duration: float
    timestamp: str


@dataclass
class ExecutionResult:
    """Result of complete plan execution"""
    plan_id: str
    success: bool
    steps_completed: int
    steps_failed: int
    results: List[StepResult]
    total_duration: float
    error: Optional[str]
    timestamp: str


class ExecutionGateway:
    """
    Single controlled entry point for ALL tool execution
    Enforces safety, validates, logs
    Phase 4A: Validation only, no actual execution
    """
    
    # Protected paths that cannot be accessed
    PROTECTED_PATHS = [
        "/etc", "/sys", "/proc", "/boot", "/dev",
        "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)"
    ]
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.tool_registry = ToolRegistry()
        self.permission_checker = PermissionChecker()
        self.execution_logger = ExecutionLogger()
        self.behavioral_memory = BehavioralMemory()
        
        # Execution state
        self.active_executions: Dict[str, ExecutionPlan] = {}
        self.aborted_executions: set = set()
        
        self.logger.info("Execution gateway initialized")
    
    def execute_plan(self, plan: ExecutionPlan, 
                    confirmed: bool = False) -> ExecutionResult:
        """
        Execute a validated plan
        Phase 4A: Validation only, returns stub results
        
        Args:
            plan: Execution plan
            confirmed: Whether user has confirmed
        
        Returns:
            ExecutionResult
        """
        start_time = datetime.now()
        
        # Log plan before execution
        self._log_plan(plan)
        
        # Pre-execution validation
        validation_errors = self._validate_plan(plan)
        if validation_errors:
            return self._create_error_result(
                plan,
                f"Validation failed: {validation_errors[0].reason}",
                start_time
            )
        
        # Check confirmation requirement
        if plan.requires_confirmation and not confirmed:
            return self._create_error_result(
                plan,
                "Confirmation required but not provided",
                start_time
            )
        
        # Mark as active
        self.active_executions[plan.plan_id] = plan
        
        # Execute steps
        results = []
        for step in plan.steps:
            # Check if aborted
            if plan.plan_id in self.aborted_executions:
                return self._create_error_result(
                    plan,
                    "Execution aborted by user",
                    start_time
                )
            
            # Execute step (stub for Phase 4A)
            step_result = self._execute_step(step)
            results.append(step_result)
            
            # Stop on failure
            if not step_result.success:
                break
        
        # Remove from active
        del self.active_executions[plan.plan_id]
        
        # Calculate metrics
        duration = (datetime.now() - start_time).total_seconds()
        steps_completed = sum(1 for r in results if r.success)
        steps_failed = len(results) - steps_completed
        
        # Create result
        result = ExecutionResult(
            plan_id=plan.plan_id,
            success=steps_failed == 0,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            results=results,
            total_duration=duration,
            error=None if steps_failed == 0 else "Some steps failed",
            timestamp=datetime.now().isoformat()
        )
        
        # Log execution
        self._log_execution(plan, result)
        
        return result
    
    def _validate_plan(self, plan: ExecutionPlan) -> List[ValidationResult]:
        """
        Validate entire plan
        
        Args:
            plan: Execution plan
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for step in plan.steps:
            validation = self.validate_step(step)
            if not validation.valid:
                errors.append(validation)
        
        return errors
    
    def validate_step(self, step: ExecutionStep) -> ValidationResult:
        """
        Validate single execution step
        
        Args:
            step: Execution step
        
        Returns:
            ValidationResult
        """
        # 1. Tool exists in registry
        tool = self.tool_registry.get_tool(step.tool_required)
        if not tool:
            return ValidationResult(
                valid=False,
                reason=f"Tool '{step.tool_required}' not registered",
                step_id=step.step_id
            )
        
        # 2. Tool is enabled
        if not tool.enabled:
            return ValidationResult(
                valid=False,
                reason=f"Tool '{step.tool_required}' is disabled",
                step_id=step.step_id
            )
        
        # 3. Parameters are valid
        if not self.tool_registry.validate_tool_call(step.tool_required, step.parameters):
            return ValidationResult(
                valid=False,
                reason=f"Invalid parameters for '{step.tool_required}'",
                step_id=step.step_id
            )
        
        # 4. Permission level satisfied
        permission = self.permission_checker.check_permission(tool)
        if not permission.allowed:
            return ValidationResult(
                valid=False,
                reason=f"Permission denied: {permission.reason}",
                step_id=step.step_id
            )
        
        # 5. Risk threshold respected
        if step.risk_level == "HIGH" and not step.requires_confirmation:
            return ValidationResult(
                valid=False,
                reason="HIGH risk requires confirmation",
                step_id=step.step_id
            )
        
        # 6. Protected paths check (if file operation)
        if tool.action_type == "file" and "path" in step.parameters:
            path = step.parameters["path"]
            if self._is_protected_path(path):
                return ValidationResult(
                    valid=False,
                    reason=f"Access to protected path denied: {path}",
                    step_id=step.step_id
                )
        
        return ValidationResult(
            valid=True,
            reason="Validation passed",
            step_id=step.step_id
        )
    
    def _execute_step(self, step: ExecutionStep) -> StepResult:
        """
        Execute single step
        Phase 4B: Real file + app launcher operations
        
        Args:
            step: Execution step
        
        Returns:
            StepResult
        """
        start_time = datetime.now()
        
        # Phase 4B: Real file operations
        if step.tool_required in ["read_file", "write_file"]:
            result = self._execute_file_operation(step)
        # Phase 4B Step 2: Real app launcher operations
        elif step.tool_required in ["open_url", "launch_app"]:
            result = self._execute_app_launcher_operation(step)
        else:
            # Other tools still stubbed
            self.logger.info(f"[STUB] Executing step {step.step_number}: {step.description}")
            import time
            time.sleep(0.01)  # Minimal delay
            
            result = StepResult(
                step_id=step.step_id,
                step_number=step.step_number,
                success=True,
                output=f"[STUB] {step.description} completed",
                error=None,
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat()
            )
        
        return result
    
    def _execute_file_operation(self, step: ExecutionStep) -> StepResult:
        """
        Execute file operation using SafeFileTool
        
        Args:
            step: Execution step
        
        Returns:
            StepResult
        """
        from lyra.tools.safe_file_tool import SafeFileTool
        
        start_time = datetime.now()
        file_tool = SafeFileTool()
        
        try:
            if step.tool_required == "read_file":
                path = step.parameters.get("path")
                if not path:
                    return StepResult(
                        step_id=step.step_id,
                        step_number=step.step_number,
                        success=False,
                        output=None,
                        error="Missing required parameter: path",
                        duration=(datetime.now() - start_time).total_seconds(),
                        timestamp=datetime.now().isoformat()
                    )
                
                result = file_tool.read_file(path)
                
                return StepResult(
                    step_id=step.step_id,
                    step_number=step.step_number,
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    duration=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now().isoformat()
                )
            
            elif step.tool_required == "write_file":
                path = step.parameters.get("path")
                content = step.parameters.get("content", "")
                append = step.parameters.get("append", False)
                
                if not path:
                    return StepResult(
                        step_id=step.step_id,
                        step_number=step.step_number,
                        success=False,
                        output=None,
                        error="Missing required parameter: path",
                        duration=(datetime.now() - start_time).total_seconds(),
                        timestamp=datetime.now().isoformat()
                    )
                
                result = file_tool.write_file(path, content, append)
                
                return StepResult(
                    step_id=step.step_id,
                    step_number=step.step_number,
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    duration=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now().isoformat()
                )
            
            else:
                return StepResult(
                    step_id=step.step_id,
                    step_number=step.step_number,
                    success=False,
                    output=None,
                    error=f"Unknown file operation: {step.tool_required}",
                    duration=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now().isoformat()
                )
        
        except Exception as e:
            self.logger.error(f"File operation error: {e}")
            return StepResult(
                step_id=step.step_id,
                step_number=step.step_number,
                success=False,
                output=None,
                error=str(e),
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat()
            )
    
    def _execute_app_launcher_operation(self, step: ExecutionStep) -> StepResult:
        """
        Execute app launcher operation using AppLauncherTool
        
        Args:
            step: Execution step
        
        Returns:
            StepResult
        """
        from lyra.tools.app_launcher_tool import AppLauncherTool
        
        start_time = datetime.now()
        app_launcher = AppLauncherTool()
        
        try:
            if step.tool_required == "open_url":
                url = step.parameters.get("url")
                if not url:
                    return StepResult(
                        step_id=step.step_id,
                        step_number=step.step_number,
                        success=False,
                        output=None,
                        error="Missing required parameter: url",
                        duration=(datetime.now() - start_time).total_seconds(),
                        timestamp=datetime.now().isoformat()
                    )
                
                result = app_launcher.open_url(url)
                
                return StepResult(
                    step_id=step.step_id,
                    step_number=step.step_number,
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    duration=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now().isoformat()
                )
            
            elif step.tool_required == "launch_app":
                app_name = step.parameters.get("app_name")
                if not app_name:
                    return StepResult(
                        step_id=step.step_id,
                        step_number=step.step_number,
                        success=False,
                        output=None,
                        error="Missing required parameter: app_name",
                        duration=(datetime.now() - start_time).total_seconds(),
                        timestamp=datetime.now().isoformat()
                    )
                
                result = app_launcher.launch_app(app_name)
                
                return StepResult(
                    step_id=step.step_id,
                    step_number=step.step_number,
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    duration=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now().isoformat()
                )
            
            else:
                return StepResult(
                    step_id=step.step_id,
                    step_number=step.step_number,
                    success=False,
                    output=None,
                    error=f"Unknown app launcher operation: {step.tool_required}",
                    duration=(datetime.now() - start_time).total_seconds(),
                    timestamp=datetime.now().isoformat()
                )
        
        except Exception as e:
            self.logger.error(f"App launcher operation error: {e}")
            return StepResult(
                step_id=step.step_id,
                step_number=step.step_number,
                success=False,
                output=None,
                error=str(e),
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat()
            )
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path is protected"""
        for protected in self.PROTECTED_PATHS:
            if path.startswith(protected):
                return True
        return False
    
    def _log_plan(self, plan: ExecutionPlan):
        """Log execution plan"""
        self.logger.info(f"Plan {plan.plan_id}: {len(plan.steps)} steps, risk={plan.total_risk_score:.2f}")
        
        # Log to file for auditability
        log_dir = Path(__file__).parent.parent.parent / "data" / "execution_plans"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{plan.plan_id}.json"
        with open(log_file, 'w') as f:
            json.dump({
                "plan_id": plan.plan_id,
                "request": plan.request,
                "steps": [asdict(step) for step in plan.steps],
                "total_risk_score": plan.total_risk_score,
                "requires_confirmation": plan.requires_confirmation,
                "created_at": plan.created_at
            }, f, indent=2)
    
    def _log_execution(self, plan: ExecutionPlan, result: ExecutionResult):
        """Log execution result"""
        self.logger.info(
            f"Execution {plan.plan_id}: "
            f"success={result.success}, "
            f"completed={result.steps_completed}/{len(plan.steps)}"
        )
        
        # Record in behavioral memory
        for step_result in result.results:
            if step_result.success:
                # Find corresponding step
                step = next((s for s in plan.steps if s.step_id == step_result.step_id), None)
                if step:
                    self.behavioral_memory.record_workflow_execution(
                        workflow_id=step.tool_required,
                        workflow_name=step.description,
                        execution_time=step_result.duration
                    )
    
    def _create_error_result(self, plan: ExecutionPlan, error: str,
                            start_time: datetime) -> ExecutionResult:
        """Create error result"""
        duration = (datetime.now() - start_time).total_seconds()
        
        return ExecutionResult(
            plan_id=plan.plan_id,
            success=False,
            steps_completed=0,
            steps_failed=len(plan.steps),
            results=[],
            total_duration=duration,
            error=error,
            timestamp=datetime.now().isoformat()
        )
    
    def abort_execution(self, plan_id: str, reason: str = "User abort"):
        """
        Abort active execution
        
        Args:
            plan_id: Plan ID to abort
            reason: Abort reason
        """
        if plan_id in self.active_executions:
            self.aborted_executions.add(plan_id)
            self.logger.warning(f"Execution {plan_id} aborted: {reason}")
        else:
            self.logger.warning(f"Cannot abort {plan_id}: not active")
    
    def get_active_executions(self) -> List[str]:
        """Get list of active execution plan IDs"""
        return list(self.active_executions.keys())
