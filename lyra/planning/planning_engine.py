# -*- coding: utf-8 -*-
"""
lyra/planning/planning_engine.py
Phase 3: Deterministic Planning Engine
Converts reasoning output into validated, structured ExecutionPlans.
"""

from typing import List, Dict, Any, Optional
from lyra.planning.planning_schema import ExecutionPlan, PlanStep
from lyra.tools.tool_registry import ToolRegistry
from lyra.core.logger import get_logger
import uuid

class PlanningEngine:
    """
    Responsibilities:
    - Convert reasoning output to ExecutionPlan.
    - Validate every step against ToolRegistry schema.
    - Assign risk_level and compute deterministic hash.
    - Reject malformed or unknown tool calls.
    """

    def __init__(self, tool_registry: ToolRegistry):
        self.logger = get_logger(__name__)
        self.tool_registry = tool_registry

    def create_plan(self, reasoning_output: Dict[str, Any], reasoning_id: str = "") -> Optional[ExecutionPlan]:
        """
        Reasoning output format expected:
        {
            "plan_steps": [
                {"tool": "read_file", "parameters": {"path": "..."}},
                ...
            ]
        }
        """
        raw_steps = reasoning_output.get("plan_steps", [])
        if not raw_steps:
            self.logger.warning("Reasoning output contains no plan steps")
            return None

        plan_steps = []
        max_risk = "LOW"
        risk_hierarchy = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        inv_risk_hierarchy = {v: k for k, v in risk_hierarchy.items()}

        for raw_step in raw_steps:
            tool_name = raw_step.get("tool")
            params = raw_step.get("parameters", {})
            depends_on = raw_step.get("depends_on", [])

            # 1. Validate tool exists and is enabled
            tool_def = self.tool_registry.get_tool(tool_name)
            if not tool_def:
                self.logger.error(f"[PLAN-REJECT] Unknown tool: {tool_name}")
                return None
            if not tool_def.enabled:
                self.logger.error(f"[PLAN-REJECT] Tool disabled: {tool_name}")
                return None

            # 2. Validate parameters against tool schema
            # Simple validation for now, could use jsonschema
            if not self.tool_registry.validate_tool_call(tool_name, params):
                self.logger.error(f"[PLAN-REJECT] Invalid parameters for {tool_name}")
                return None

            # 3. Build PlanStep
            step = PlanStep(
                tool_name=tool_name,
                input_schema=tool_def.input_schema,
                validated_input=params,
                expected_output_schema=tool_def.output_schema,
                step_risk=tool_def.risk_category,
                depends_on=depends_on,
                description=tool_def.description
            )
            plan_steps.append(step)

            if risk_hierarchy[step.step_risk] > risk_hierarchy[max_risk]:
                max_risk = step.step_risk

        # 4. Detect Circular Dependencies
        if self._has_circular_dependencies(plan_steps):
            self.logger.error("[PLAN-REJECT] [PLAN-INVALID-CYCLE] Circular dependencies detected")
            return None

        # 5. Build ExecutionPlan
        plan = ExecutionPlan(
            reasoning_id=reasoning_id,
            risk_level=max_risk,
            steps=plan_steps,
            requires_confirmation=any(r in ["HIGH", "CRITICAL"] for r in [s.step_risk for s in plan_steps])
        )
        
        # Phase 3.1: Freeze plan to lock immutability and compute canonical hash
        plan.freeze()

        self.logger.info(f"[PLAN-CREATED] Plan {plan.plan_id} with {len(plan_steps)} steps. Risk: {max_risk}")
        return plan

    def _has_circular_dependencies(self, steps: List[PlanStep]) -> bool:
        """Simple cycle detection using DFS."""
        adj = {s.step_id: s.depends_on for s in steps}
        visited = set()
        path = set()

        def visit(u):
            if u in path: return True
            if u in visited: return False
            visited.add(u)
            path.add(u)
            for v in adj.get(u, []):
                if visit(v): return True
            path.remove(u)
            return False

        for step in steps:
            if visit(step.step_id):
                return True
        return False
