# -*- coding: utf-8 -*-
"""
lyra/safety/risk_simulator.py
Phase 4: Pre-Execution Risk Simulation Engine — Hardened v1.3
Inspects plans for compound risk patterns and enforces governance gates.
No plan executes without simulation.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from lyra.planning.planning_schema import ExecutionPlan, PlanStep
from lyra.safety.safety_policy_registry import SafetyPolicyRegistry, ConfirmationLevel
from lyra.core.logger import get_logger

@dataclass
class SimulationResult:
    """Outcome of the risk simulation."""
    cumulative_risk: str  # LOW, MEDIUM, HIGH, CRITICAL
    requires_confirmation: bool = False
    requires_sandbox: bool = False
    rollback_required: bool = False
    risk_factors: List[str] = field(default_factory=list)

class RiskSimulator:
    """
    Engine for simulating risk profile of an ExecutionPlan.
    Must approve plan before execution begins.
    
    Hardened v1.3 Escalation Rules:
    - 2+ HIGH steps → escalate to CRITICAL
    - destructive + network → escalate one level
    - Irreversible step present → requires_confirmation = True
    - Multiple destructive steps → CRITICAL
    """
    
    _RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    def __init__(self, policy_registry: SafetyPolicyRegistry):
        self.logger = get_logger(__name__)
        self.policy_registry = policy_registry

    def _escalate_risk(self, current: str, levels: int = 1) -> str:
        """Escalate risk level by N levels, capped at CRITICAL."""
        idx = self._RISK_LEVELS.index(current)
        new_idx = min(idx + levels, len(self._RISK_LEVELS) - 1)
        return self._RISK_LEVELS[new_idx]

    def simulate_plan(self, plan: ExecutionPlan) -> SimulationResult:
        """
        Inspect full ExecutionPlan and calculate compound risk.
        Execution cannot proceed without SimulationResult approval.
        """
        result = SimulationResult(cumulative_risk="LOW")
        
        destructive_count = 0
        high_risk_count = 0
        irreversible_count = 0
        has_file_op = False
        has_network_op = False
        
        for step in plan.steps:
            policy = self.policy_registry.get_policy(step.tool_name)
            
            # 1. Track destructive operations
            if policy.destructive:
                destructive_count += 1
                result.risk_factors.append(f"Destructive step: {step.tool_name}")
            
            # 2. Track sandbox requirements
            if policy.requires_sandbox:
                result.requires_sandbox = True
                result.risk_factors.append(f"Sandbox required: {step.tool_name}")
            
            # 3. Track reversibility
            if policy.reversible:
                result.rollback_required = True
            else:
                irreversible_count += 1
                result.risk_factors.append(f"Irreversible step: {step.tool_name}")
                
            # 4. Track operation domains for cross-domain detection
            tool_cat = step.tool_name.split('_')[0]
            if tool_cat in ["read", "write", "delete", "create"]:
                has_file_op = True
            if tool_cat in ["open", "download", "post", "search"]:
                has_network_op = True
            
            # 5. Individual step risk classification
            if step.step_risk == "CRITICAL":
                result.cumulative_risk = "CRITICAL"
                result.requires_confirmation = True
            elif step.step_risk == "HIGH":
                high_risk_count += 1
                if result.cumulative_risk != "CRITICAL":
                    result.cumulative_risk = "HIGH"
                result.requires_confirmation = True

        # ====================================================================
        # Compound Risk Detection (Hardened v1.3)
        # ====================================================================
        
        # Rule 1: 2+ HIGH steps → escalate to CRITICAL
        if high_risk_count >= 2:
            result.cumulative_risk = "CRITICAL"
            result.requires_confirmation = True
            result.risk_factors.append(
                f"COMPOUND-RISK: {high_risk_count} HIGH-risk steps chained → CRITICAL."
            )
            
        # Rule 2: Multiple destructive steps → CRITICAL
        if destructive_count > 1:
            result.cumulative_risk = "CRITICAL"
            result.requires_confirmation = True
            result.risk_factors.append(
                f"COMPOUND-RISK: {destructive_count} destructive operations → CRITICAL."
            )
            
        # Rule 3: Destructive + Network → escalate one level
        if destructive_count > 0 and has_network_op:
            result.cumulative_risk = self._escalate_risk(result.cumulative_risk, 1)
            result.requires_confirmation = True
            result.risk_factors.append(
                "COMPOUND-RISK: Destructive + Network cross-domain → escalated."
            )

        # Rule 4: File + Network → data exfiltration risk
        if has_file_op and has_network_op:
            if result.cumulative_risk in ["LOW", "MEDIUM"]:
                result.cumulative_risk = "HIGH"
            result.requires_confirmation = True
            result.risk_factors.append(
                "COMPOUND-RISK: File + Network operations → exfiltration risk."
            )

        # Rule 5: Any irreversible step → requires confirmation
        if irreversible_count > 0:
            result.requires_confirmation = True
            result.risk_factors.append(
                f"IRREVERSIBLE: {irreversible_count} non-reversible step(s) present."
            )

        self.logger.info(
            f"[SIMULATION] plan_id={plan.plan_id} risk={result.cumulative_risk} "
            f"confirmation={result.requires_confirmation} sandbox={result.requires_sandbox} "
            f"factors={len(result.risk_factors)}"
        )
        return result
