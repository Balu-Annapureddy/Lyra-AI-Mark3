"""
Execution Gateway - Phase 4A + Phase F4
Single controlled entry point for ALL tool execution
Validates, enforces safety, logs all executions
Phase F4: Formalized risk classification, intent whitelisting,
          execution validation gate, LLM-bypass protection.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from lyra.planning.execution_planner import ExecutionPlan, ExecutionStep
from lyra.tools.tool_registry import ToolRegistry
from lyra.execution.permission_model import PermissionChecker
from lyra.safety.execution_logger import ExecutionLogger
from lyra.memory.behavioral_memory import BehavioralMemory
from lyra.core.logger import get_logger

# Phase 4C imports
from lyra.execution.dependency_resolver import DependencyResolver
from lyra.execution.rollback_manager import RollbackManager


# ======================================================================
# Phase F4: Risk Level Enum
# ======================================================================

class RiskLevel(Enum):
    """Formalized risk classification for execution safety."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ======================================================================
# Phase F4: Supported Intents Whitelist
# ======================================================================

SUPPORTED_INTENTS = {
    "create_file",
    "write_file",
    "delete_file",
    "read_file",
    "open_url",
    "launch_app",
    "search_web",
    "screen_read",
    "code_help",
    "conversation",
    "autonomous_goal",
    "run_command",
    "get_status",
}

# Intent → RiskLevel mapping
INTENT_RISK_MAP: Dict[str, RiskLevel] = {
    "create_file":  RiskLevel.LOW,
    "write_file":   RiskLevel.LOW,
    "read_file":    RiskLevel.LOW,
    "open_url":     RiskLevel.MEDIUM,
    "search_web":   RiskLevel.LOW,
    "launch_app":   RiskLevel.MEDIUM,
    "delete_file":  RiskLevel.HIGH,
    "screen_read":  RiskLevel.MEDIUM,
    "code_help":    RiskLevel.LOW,
    "conversation": RiskLevel.LOW,
    "autonomous_goal": RiskLevel.HIGH,
    "run_command":  RiskLevel.MEDIUM,
    "get_status":   RiskLevel.LOW,
}


# ======================================================================
# Phase F4: Custom Exception
# ======================================================================

class UnsupportedIntentError(Exception):
    """Raised when an intent is not in the supported whitelist."""
    pass


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


@dataclass
class ExecutionRequestResult:
    """Phase F4: Result of execution validation gate."""
    allowed: bool
    risk_level: RiskLevel
    requires_confirmation: bool
    reason: Optional[str] = None


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
        
        # Phase 4C: Dependency resolution, rollback, panic stop
        self.dependency_resolver = DependencyResolver()
        self.rollback_manager = RollbackManager()
        
        # Execution state
        self.active_executions: Dict[str, ExecutionPlan] = {}
        self.aborted_executions: set = set()
        
        # Phase 4C: Atomic panic stop flag
        self._panic_stop = False
        self._panic_reason = ""
        
        self.logger.info("Execution gateway initialized with Phase 4C + F4 safety features")

    # ------------------------------------------------------------------
    # Phase F4: Execution Validation Gate
    # ------------------------------------------------------------------

    def validate_execution_request(
        self,
        intent: str,
        params: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionRequestResult:
        """
        Phase F4: Validate an execution request before it reaches
        plan creation or tool dispatch.

        Checks:
            1. Intent is in SUPPORTED_INTENTS whitelist
            2. Risk level classification
            3. HIGH-risk commands require explicit confirmation
            4. CRITICAL-risk commands are always blocked
            5. LLM-sourced commands face stricter validation

        Args:
            intent:   Classified intent string
            params:   Extracted parameters
            metadata: Source information, e.g. {"source": "embedding"}

        Returns:
            ExecutionRequestResult
        """
        if metadata is None:
            metadata = {}

        source = metadata.get("source", "unknown")
        confirmed = metadata.get("confirmed", False)
        semantic_valid = metadata.get("semantic_valid", True)

        # === 1. Whitelist check ===
        if intent not in SUPPORTED_INTENTS:
            self.logger.warning(
                f"[SECURITY] Unsupported intent rejected: '{intent}' "
                f"(source={source})"
            )
            return ExecutionRequestResult(
                allowed=False,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=False,
                reason=f"Unsupported intent: '{intent}'",
            )

        # === 2. Risk classification ===
        risk = INTENT_RISK_MAP.get(intent, RiskLevel.CRITICAL)

        # === 3. CRITICAL risk — always blocked ===
        if risk == RiskLevel.CRITICAL:
            self.logger.warning(
                f"[SECURITY] CRITICAL risk intent blocked: '{intent}'"
            )
            return ExecutionRequestResult(
                allowed=False,
                risk_level=risk,
                requires_confirmation=False,
                reason="CRITICAL risk level — execution always blocked",
            )

        # === 4. LLM-bypass guard ===
        if source == "llm":
            self.logger.info(
                f"[LLM-GUARD] LLM-sourced execution request: "
                f"intent={intent}, risk={risk.name}"
            )

            # LLM cannot bypass semantic validation
            if not semantic_valid:
                self.logger.warning(
                    f"[SECURITY] LLM-source rejected: semantic validation "
                    f"not passed for '{intent}'"
                )
                return ExecutionRequestResult(
                    allowed=False,
                    risk_level=risk,
                    requires_confirmation=False,
                    reason="LLM-sourced command rejected: "
                           "semantic validation not passed",
                )

            # LLM HIGH-risk requires confirmation
            if risk == RiskLevel.HIGH and not confirmed:
                self.logger.warning(
                    f"[SECURITY] LLM-source HIGH risk without "
                    f"confirmation: '{intent}'"
                )
                return ExecutionRequestResult(
                    allowed=False,
                    risk_level=risk,
                    requires_confirmation=True,
                    reason="LLM-sourced HIGH risk command requires "
                           "explicit confirmation",
                )

        # === 5. HIGH risk confirmation check (all sources) ===
        if risk == RiskLevel.HIGH and not confirmed:
            self.logger.info(
                f"HIGH risk intent '{intent}' requires confirmation"
            )
            return ExecutionRequestResult(
                allowed=False,
                risk_level=risk,
                requires_confirmation=True,
                reason="HIGH risk command requires confirmation",
            )

        # === 6. All checks passed ===
        return ExecutionRequestResult(
            allowed=True,
            risk_level=risk,
            requires_confirmation=False,
            reason=None,
        )
    
    def execute_plan(self, plan: ExecutionPlan, 
                    confirmed: bool = False,
                    simulate: bool = False) -> ExecutionResult:
        """
        Execute a validated plan
        Phase 4C: Dependency resolution, rollback, verification, simulation
        
        Args:
            plan: Execution plan
            confirmed: Whether user has confirmed
            simulate: If True, dry-run without execution
        
        Returns:
            ExecutionResult
        """
        start_time = datetime.now()
        
        # 1. Check panic stop flag
        if self._panic_stop:
            return self._create_error_result(
                plan,
                f"Execution halted: {self._panic_reason}",
                start_time
            )
        
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
        if plan.requires_confirmation and not confirmed and not simulate:
            return self._create_error_result(
                plan,
                "Confirmation required but not provided",
                start_time
            )
        
        # 2. Resolve dependencies
        try:
            ordered_steps = self.dependency_resolver.resolve_execution_order(plan.steps)
        except ValueError as e:
            return self._create_error_result(
                plan,
                f"Dependency resolution failed: {e}",
                start_time
            )
        
        # 3. If simulation mode, print plan and return
        if simulate:
            return self._simulate_plan(plan, ordered_steps, start_time)
        
        # Mark as active
        self.active_executions[plan.plan_id] = plan
        
        # Execution context (for output substitution)
        context = {}
        
        # Execute steps
        results = []
        completed_step_ids = []
        
        for step in ordered_steps:
            # Check panic stop before each step
            if self._panic_stop:
                self.logger.warning(f"Panic stop triggered: {self._panic_reason}")
                # Rollback completed steps
                self.rollback_manager.rollback_plan(plan.plan_id, completed_step_ids)
                return self._create_error_result(
                    plan,
                    f"Execution halted: {self._panic_reason}",
                    start_time
                )
            
            # Substitute outputs from previous steps
            if step.depends_on:
                step = self.dependency_resolver.substitute_outputs(step, context)
            
            # 4. If reversible, create snapshot
            snapshot = None
            if step.reversible:
                snapshot = self.rollback_manager.create_snapshot(step)
            
            # 5. Execute step
            step_result = self._execute_step(step)
            results.append(step_result)
            
            # 6. Verify via tool.verify()
            if step_result.success:
                verified = self._verify_step(step, step_result)
                if not verified:
                    self.logger.error(f"Verification failed for step {step.step_id}")
                    step_result.success = False
                    step_result.error = "Verification failed"
            
            # 7. On failure, rollback
            if not step_result.success:
                self.logger.error(f"Step {step.step_id} failed: {step_result.error}")
                # Rollback this step if snapshot exists
                if snapshot:
                    self.rollback_manager.rollback_step(step.step_id)
                # Rollback all completed steps
                self.rollback_manager.rollback_plan(plan.plan_id, completed_step_ids)
                break
            
            # Store outputs for dependencies
            context[step.step_id] = {
                "output": step_result.output,
                "success": step_result.success
            }
            completed_step_ids.append(step.step_id)
        
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
        
        # Clear snapshots on success
        if result.success:
            self.rollback_manager.clear_snapshots(plan.plan_id)
        
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

    def _simulate_plan(self, plan: ExecutionPlan, ordered_steps: List[ExecutionStep],
                      start_time: datetime) -> ExecutionResult:
        """Simulate plan execution without actual operations"""
        self.logger.info(f"[SIMULATION] Plan: {plan.plan_id}")
        self.logger.info(f"[SIMULATION] Steps: {len(ordered_steps)}")

        estimated_duration = 0.0
        results = []

        for i, step in enumerate(ordered_steps, 1):
            self.logger.info(f"[SIMULATION] Step {i}: {step.tool_required}({step.parameters})")
            self.logger.info(f"[SIMULATION]   -> Would execute: {step.description}")

            if step.reversible:
                self.logger.info(f"[SIMULATION]   -> Snapshot would be created")

            tool_def = self.tool_registry.get_tool(step.tool_required)
            if tool_def:
                estimated_duration += tool_def.max_execution_time

            results.append(StepResult(
                step_id=step.step_id,
                step_number=step.step_number,
                success=True,
                output=f"[SIMULATED] {step.description}",
                error=None,
                duration=0.0,
                timestamp=datetime.now().isoformat()
            ))

        self.logger.info(f"[SIMULATION] Total estimated duration: ~{estimated_duration:.2f}s")

        return ExecutionResult(
            plan_id=plan.plan_id,
            success=True,
            steps_completed=len(results),
            steps_failed=0,
            results=results,
            total_duration=(datetime.now() - start_time).total_seconds(),
            error=None,
            timestamp=datetime.now().isoformat()
        )

    def _verify_step(self, step: ExecutionStep, result: StepResult) -> bool:
        """Verify step execution via tool-defined verify() method"""
        try:
            if step.tool_required in ["read_file", "write_file"]:
                from lyra.tools.safe_file_tool import SafeFileTool, FileOperationResult
                tool = SafeFileTool()
                file_result = FileOperationResult(
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    bytes_read=0,
                    bytes_written=0,
                    operation=step.tool_required,
                    target_path=step.parameters.get("path")
                )
                return tool.verify(step.tool_required, file_result)

            elif step.tool_required in ["open_url", "launch_app"]:
                from lyra.tools.app_launcher_tool import AppLauncherTool, LaunchResult
                tool = AppLauncherTool()
                launch_result = LaunchResult(
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    target=step.parameters.get("url") or step.parameters.get("app_name", ""),
                    operation=step.tool_required
                )
                return tool.verify(step.tool_required, launch_result)

            else:
                return True

        except Exception as e:
            self.logger.error(f"Verification error: {e}")
            return False

    def panic_stop(self, reason: str = "User interrupt"):
        """Immediately halt all active executions"""
        self._panic_stop = True
        self._panic_reason = reason
        self.logger.warning(f"PANIC STOP activated: {reason}")

    def resume_execution(self):
        """Clear panic stop flag"""
        self._panic_stop = False
        self._panic_reason = ""
        self.logger.info("Panic stop cleared, execution resumed")

    def is_panic_stopped(self) -> bool:
        """Check if panic stop is active"""
        return self._panic_stop

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
