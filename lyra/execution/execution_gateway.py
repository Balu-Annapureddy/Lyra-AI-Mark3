# -*- coding: utf-8 -*-
from __future__ import annotations
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
from lyra.core.logger import get_logger

# Phase 3 Deterministic Planning Imports
from lyra.planning.planning_schema import ExecutionPlan, PlanStep
from lyra.planning.planning_engine import PlanningEngine
from lyra.execution.execution_engine import ExecutionEngine

# Phase 4 Governance Imports
from lyra.safety.safety_policy_registry import SafetyPolicyRegistry, ConfirmationLevel
from lyra.safety.risk_simulator import RiskSimulator, SimulationResult
from lyra.safety.rollback_engine import RollbackEngine
from lyra.safety.audit_ledger import AuditLedger
from lyra.tools.tool_registry import ToolRegistry
from lyra.execution.permission_model import PermissionChecker
from lyra.safety.execution_logger import ExecutionLogger

# Phase 1 Stabilization Tools
from lyra.tools.install_software_tool import InstallSoftwareTool
from lyra.tools.change_config_tool import ChangeConfigTool


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
    "install_software",
    "change_config",
}

# Intent → RiskLevel mapping
INTENT_RISK_MAP: Dict[str, RiskLevel] = {
    "create_file":      RiskLevel.MEDIUM,  # Constitution: Modify files = MEDIUM
    "write_file":       RiskLevel.MEDIUM,  # Constitution: Modify files = MEDIUM
    "read_file":        RiskLevel.LOW,     # Constitution: Read files = LOW
    "open_url":         RiskLevel.MEDIUM,
    "search_web":       RiskLevel.LOW,     # Constitution: Research/Web = LOW
    "launch_app":       RiskLevel.MEDIUM,
    "delete_file":      RiskLevel.HIGH,    # Constitution: Core alterations = HIGH
    "screen_read":      RiskLevel.MEDIUM,
    "code_help":        RiskLevel.LOW,
    "conversation":     RiskLevel.LOW,
    "autonomous_goal":  RiskLevel.HIGH,
    "run_command":      RiskLevel.MEDIUM,
    "get_status":       RiskLevel.LOW,
    "install_software": RiskLevel.MEDIUM,  # Constitution: Install software = MEDIUM
    "change_config":    RiskLevel.MEDIUM,  # Constitution: Change config = MEDIUM
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
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))


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
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))


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
    
    def __init__(self, memory_manager=None, advisor=None):
        self.logger = get_logger(__name__)
        self.tool_registry = ToolRegistry()
        self.permission_checker = PermissionChecker()
        self.execution_logger = ExecutionLogger()
        self.memory_manager = memory_manager  # Phase 2: Dual-layer memory
        from lyra.memory.memory_context_builder import MemoryContextBuilder
        self.context_builder = MemoryContextBuilder(memory_manager) if memory_manager else None
        self.advisor = advisor # Phase F5: Escalation Advisor
        
        # Phase 4: Governance Layer initialization
        self.safety_registry = SafetyPolicyRegistry()
        self.risk_simulator = RiskSimulator(self.safety_registry)
        self.rollback_engine = RollbackEngine()
        self.audit_ledger = AuditLedger()
        
        self.abort_requested = False # Kill-switch flag
        
        self.logger.info("Execution gateway initialized with Lyra Mark-3 Phase 4 Governance")
        
        # Phase 3 Engines
        self.planning_engine = PlanningEngine(self.tool_registry)
        self.execution_engine = ExecutionEngine(
            self.tool_registry, 
            logger=self.logger, 
            memory_writer=self.memory_manager
        )

    def process_reasoning_flow(self, user_input: str, history: List[Dict[str, Any]] = None, trace_id: str = "") -> Dict[str, Any]:
        """
        Phase 2.1: Orchestrates the Memory-Enriched Reasoning Flow.
        Flow: Input -> Gateway -> ContextBuilder -> Router -> Escalation -> Safety
        """
        if not self.advisor or not self.context_builder:
            self.logger.error("Gateway reasoning components not initialized")
            return {"intent": "unknown", "confidence": 0.0, "reason": "internal_error"}

        # 1. Build Memory Context (Gateway -> ContextBuilder)
        memory_context = self.context_builder.build_context(user_input, trace_id=trace_id)
        
        # 2. Enrich and Route (Router remains memory-agnostic)
        # We inject memory into the prompt here or pass it as context to advisor
        # Spec says: Router must remain memory-agnostic. Advisor/Gateway handles injection.
        enriched_input = f"{memory_context}\n\nUser Input: {user_input}" if memory_context else user_input
        
        # 3. Advisor (EscalationLayer) -> Router
        # The advisor uses the router internally to classify and extract entities.
        reasoning_result = self.advisor.analyze(enriched_input, history=history)
        
        # 4. Phase 3: Planning Kernel (Reasoning -> Plan)
        # Structural Isolation: Execution is strictly blocked in GENERAL_QA mode.
        mode = reasoning_result.get("mode")
        intent = reasoning_result.get("intent")
        
        if mode != "general_qa" and intent in SUPPORTED_INTENTS:
            # Map reasoning result to the format expected by planning_engine
            plan_input = {
                "plan_steps": [
                    {
                        "tool": intent,
                        "parameters": reasoning_result.get("entities", {})
                    }
                ]
            }
            plan = self.planning_engine.create_plan(plan_input, reasoning_id=trace_id)
            if plan:
                reasoning_result["plan"] = plan
                self.logger.info(f"[GATEWAY] Reasoning id {trace_id} promoted to Plan {plan.plan_id}")
        elif mode == "general_qa" and intent in SUPPORTED_INTENTS:
            self.logger.warning(f"[SECURITY] GENERAL_QA mode attempted executable promotion for intent '{intent}'. BLOCKED.")

        return reasoning_result

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
            # Hardening v1.3: Execution Isolation Guard
            reasoning_mode = metadata.get("reasoning_mode")
            if reasoning_mode == "general_qa":
                self.logger.warning(f"[SECURITY] GENERAL_QA mode attempted execution: '{intent}'. BLOCKED.")
                return ExecutionRequestResult(
                    allowed=False,
                    risk_level=risk,
                    requires_confirmation=False,
                    reason="Execution not allowed in GENERAL_QA mode",
                )

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
                    simulate: bool = False) -> Dict[str, Any]:
        """
        Execute a validated plan with full governance wrapping.
        Phase 4 Hardened v1.3: Risk Simulation, Confirmation Escalation, 
        Sandbox Routing, Audit Ledger, Rollback.
        """
        start_time = datetime.now()
        
        # 1. Risk Simulation (No plan executes without simulation)
        sim_result = self.risk_simulator.simulate_plan(plan)
        
        # 2. Confirmation Escalation Policy (Hardened v1.3)
        # No implicit confirmations. No silent downgrade.
        if sim_result.requires_confirmation and not confirmed:
            self.logger.warning(f"[CONFIRMATION-REQUIRED] Plan {plan.plan_id} requires explicit approval.")
            
            # Determine if any step has rollback available
            has_rollback = any(
                self.safety_registry.get_policy(s.tool_name).reversible 
                for s in plan.steps
            )
            has_destructive = any(
                self.safety_registry.get_policy(s.tool_name).destructive 
                for s in plan.steps
            )
            
            # Use a dummy ExecutionResult for confirmation required
            return ExecutionResult(
                plan_id=plan.plan_id,
                success=False,
                steps_completed=0,
                steps_failed=0,
                results=[],
                total_duration=0.0,
                error="Confirmation required",
                # Add extra fields if needed for display, but for now we'll stick to the schema
            )
        # 3. Pre-Execution Audit & Setup
        audit_entry = {
            "plan_id": plan.plan_id,
            "deterministic_hash": plan.deterministic_hash,
            "simulation_result": asdict(sim_result),
            "confirmation_status": "confirmed" if confirmed else "not_required",
            "status": "STARTED"
        }
        self.audit_ledger.record_entry(audit_entry)

        high_risk = sim_result.cumulative_risk in ["HIGH", "CRITICAL"]
        
        try:
            # 4. Memory Hardening (Kernel Layer)
            if high_risk and self.memory_manager:
                self.memory_manager.set_write_restriction(True)

            # 5. Rollback Registration (Snapshotting)
            for step in plan.steps:
                policy = self.safety_registry.get_policy(step.tool_name)
                if policy.reversible:
                    self.rollback_engine.capture_pre_state(step.step_id, step.tool_name, step.validated_input)

            if high_risk and self.memory_manager:
                self.memory_manager.set_write_restriction(True)

            # 6. Determine sandbox tools from safety policies
            sandbox_tools = [
                s.tool_name for s in plan.steps 
                if self.safety_registry.get_policy(s.tool_name).requires_sandbox
            ]
            
            # 7. Hand off to Execution Engine
            def check_abort(): return getattr(self, "abort_requested", False)
            exec_res = self.execution_engine.execute_plan(
                plan, confirmed=confirmed, 
                abort_check_func=check_abort,
                sandbox_tools=sandbox_tools
            )

            
            # 8. Post-Execution Audit (Hardened v1.3)
            final_state = exec_res.get("final_state", 
                "COMPLETED" if exec_res["success"] else "FAILED")
            if exec_res.get("aborted"):
                final_state = "ABORTED"
                
            audit_entry["final_state"] = final_state
            audit_entry["outcomes"] = exec_res.get("trace", [])
            audit_entry["aborted"] = exec_res.get("aborted", False)
            self.audit_ledger.record_entry(audit_entry)

            # 9. Rollback Enforcement
            rollback_result = None
            if not exec_res["success"] or exec_res.get("aborted"):
                self.logger.warning(f"[GOVERNANCE] Plan {plan.plan_id} {final_state}. Triggering rollback.")
                rollback_result = self.rollback_engine.execute_rollback()
                
                # Record rollback in audit
                rollback_audit = {
                    "plan_id": plan.plan_id,
                    "final_state": "ROLLBACK_" + rollback_result.get("status", "UNKNOWN"),
                    "rollback_summary": rollback_result
                }
                self.audit_ledger.record_entry(rollback_audit)

            # 10. Log Task History to Memory (TASK_HISTORY only)
            if self.memory_manager:
                from lyra.memory.memory_schema import MemorySource, MemoryType
                self.memory_manager.add_memory(
                    content={
                        "plan_id": plan.plan_id,
                        "success": exec_res["success"],
                        "risk": sim_result.cumulative_risk,
                        "final_state": final_state
                    },
                    source=MemorySource.SYSTEM,
                    memory_type=MemoryType.TASK_HISTORY,
                    priority=4 if exec_res["success"] else 5
                )

            # Step 8. Construct ExecutionResult (Standardized)
            step_results = []
            for i, t in enumerate(exec_res.get("trace", [])):
                step_results.append(StepResult(
                    step_id=t.get("step_id", f"step-{i}"),
                    step_number=i + 1,
                    success=t.get("success", False),
                    output=str(t.get("output", t.get("duration_ms", ""))),
                    error=t.get("error"),
                    duration=t.get("duration_ms", 0) / 1000.0
                ))

            return ExecutionResult(
                plan_id=plan.plan_id,
                success=exec_res["success"],
                steps_completed=sum(1 for t in step_results if t.success),
                steps_failed=sum(1 for t in step_results if not t.success),
                results=step_results,
                total_duration=exec_res.get("duration_ms", 0) / 1000.0,
                error=exec_res.get("error")
            )

        except Exception as e:
            self.logger.error(f"[GATEWAY-CRITICAL] Execution Governance Failure: {e}")
            self.rollback_engine.execute_rollback() 
            return ExecutionResult(
                plan_id=plan.plan_id,
                success=False,
                steps_completed=0,
                steps_failed=0,
                results=[],
                total_duration=0.0,
                error=str(e)
            )
        finally:
            if high_risk and self.memory_manager:
                self.memory_manager.set_write_restriction(False)
            self.rollback_engine.clear()
    
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
    
    def validate_step(self, step: PlanStep) -> ValidationResult:
        """
        Validate single execution step
        
        Args:
            step: Execution step
        
        Returns:
            ValidationResult
        """
        # 1. Tool exists in registry
        tool = self.tool_registry.get_tool(step.tool_name)
        if not tool:
            return ValidationResult(
                valid=False,
                reason=f"Tool '{step.tool_name}' not registered",
                step_id=step.step_id
            )
        
        # 2. Tool is enabled
        if not tool.enabled:
            return ValidationResult(
                valid=False,
                reason=f"Tool '{step.tool_name}' is disabled",
                step_id=step.step_id
            )
        
        # 3. Parameters are valid
        if not self.tool_registry.validate_tool_call(step.tool_name, step.validated_input):
            return ValidationResult(
                valid=False,
                reason=f"Invalid parameters for '{step.tool_name}'",
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
        if step.step_risk == "HIGH": # Confirmation logic handled by confirmed flag
             pass
        
        # 6. Protected paths check (if file operation)
        if tool.action_type == "file" and "path" in step.validated_input:
            path = step.validated_input["path"]
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
    
    def _execute_step(self, step: PlanStep, confirmed: bool = False) -> StepResult:
        """
        Execute single step
        Phase 4B: Real file + app launcher operations
        Phase 1: Stabilization tool stubs
        """
        start_time = datetime.now()
        
        # Real file operations
        if step.tool_name in ["read_file", "write_file"]:
            result = self._execute_file_operation(step)
        # Real app launcher operations
        elif step.tool_name in ["open_url", "launch_app"]:
            result = self._execute_app_launcher_operation(step)
        # Phase 1 Stabilization Tools
        elif step.tool_name in ["install_software", "change_config"]:
            result = self._execute_stabilization_tool(step, confirmed=confirmed)
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

    def _execute_stabilization_tool(self, step: PlanStep, confirmed: bool = False) -> StepResult:
        """Execute Phase 1 stabilization tools (stubs with safety logic)"""
        start_time = datetime.now()
        
        try:
            if step.tool_name == "install_software":
                tool = InstallSoftwareTool()
                package = step.validated_input.get("package", "unknown")
                res = tool.execute(package=package, confirmed=confirmed)
            elif step.tool_name == "change_config":
                tool = ChangeConfigTool()
                setting = step.validated_input.get("setting", "unknown")
                value = step.validated_input.get("value", "unknown")
                res = tool.execute(setting=setting, value=value, confirmed=confirmed)
            else:
                raise ValueError(f"Unknown stabilization tool: {step.tool_name}")

            return StepResult(
                step_id=step.step_id,
                step_number=step.step_number,
                success=res.get("success", False),
                output=res.get("message", ""),
                error=res.get("error"),
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                step_number=step.step_number,
                success=False,
                output=None,
                error=str(e),
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat()
            )

    def _simulate_plan(self, plan: ExecutionPlan, ordered_steps: List[PlanStep],
                      start_time: datetime) -> ExecutionResult:
        """Simulate plan execution without actual operations"""
        self.logger.info(f"[SIMULATION] Plan: {plan.plan_id}")
        self.logger.info(f"[SIMULATION] Steps: {len(ordered_steps)}")

        estimated_duration = 0.0
        results = []

        for i, step in enumerate(ordered_steps, 1):
            self.logger.info(f"[SIMULATION] Step {i}: {step.tool_name}({step.validated_input})")
            self.logger.info(f"[SIMULATION]   -> Would execute: {step.description}")

            if step.reversible:
                self.logger.info(f"[SIMULATION]   -> Snapshot would be created")

            tool_def = self.tool_registry.get_tool(step.tool_name)
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

    def _verify_step(self, step: PlanStep, result: StepResult) -> bool:
        """Verify step execution via tool-defined verify() method"""
        try:
            if step.tool_name in ["read_file", "write_file"]:
                from lyra.tools.safe_file_tool import SafeFileTool, FileOperationResult
                tool = SafeFileTool()
                file_result = FileOperationResult(
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    bytes_read=0,
                    bytes_written=0,
                    operation=step.tool_name,
                    target_path=step.validated_input.get("path")
                )
                return tool.verify(step.tool_name, file_result)

            elif step.tool_name in ["open_url", "launch_app"]:
                from lyra.tools.app_launcher_tool import AppLauncherTool, LaunchResult
                tool = AppLauncherTool()
                launch_result = LaunchResult(
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    target=step.validated_input.get("url") or step.validated_input.get("app_name", ""),
                    operation=step.tool_name
                )
                return tool.verify(step.tool_name, launch_result)

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

    def _execute_file_operation(self, step: PlanStep) -> StepResult:
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
            if step.tool_name == "read_file":
                path = step.validated_input.get("path")
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
            
            elif step.tool_name == "write_file":
                path = step.validated_input.get("path")
                content = step.validated_input.get("content", "")
                append = step.validated_input.get("append", False)
                
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
                    error=f"Unknown file operation: {step.tool_name}",
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
    
    def _execute_app_launcher_operation(self, step: PlanStep) -> StepResult:
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
            if step.tool_name == "open_url":
                url = step.validated_input.get("url")
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
            
            elif step.tool_name == "launch_app":
                app_name = step.validated_input.get("app_name")
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
                    error=f"Unknown app launcher operation: {step.tool_name}",
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
                        workflow_id=step.tool_name,
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
