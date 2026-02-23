# -*- coding: utf-8 -*-
"""
lyra/orchestration/task_orchestrator.py
Phase X2: Autonomous Orchestration Layer
"""

import json
import time
from typing import List, Dict, Any, Optional
from lyra.core.logger import get_logger

logger = get_logger(__name__)

class TaskOrchestrator:
    """
    Handles structured multi-step task planning and controlled autonomous execution.
    """

    MAX_STEPS = 6
    MAX_ORCHESTRATION_TIME = 10.0 # seconds

    def __init__(self):
        self.logger = logger

    def generate_plan(self, goal: str, model_advisor: Any, reasoning_level: str) -> List[Dict[str, Any]]:
        """
        Generate a multi-step execution plan using the LLM.
        Only allowed for DEEP reasoning.
        """
        if reasoning_level.lower() != "deep":
            self.logger.warning("Plan generation attempted outside of DEEP reasoning level.")
            return []

        prompt = (
            f"Goal: {goal}\n\n"
            "Break this goal into safe, atomic executable steps.\n"
            "Each step must correspond to a known system intent (e.g., create_file, write_file, run_script).\n"
            "Return a strict JSON list of objects with these keys: step_id (int), intent (str), parameters (dict), description (str).\n"
            "Each step must be a single specific action. Do not exceed 6 steps."
        )

        try:
            # Phase F5/X2: Use Gemini API for structured plan generation
            if not model_advisor._initialize_gemini():
                return []
                
            response = model_advisor._gen_model.generate_content(
                f"Goal: {goal}\n\n{prompt}",
                generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
            )
            raw_output = response.text
            # Find JSON list in output
            start = raw_output.find("[")
            end = raw_output.rfind("]") + 1
            if start == -1 or end == 0:
                self.logger.error("LLM failed to return a valid JSON plan structure.")
                return []
            
            plan = json.loads(raw_output[start:end])
            
            # Validation Rules
            if not isinstance(plan, list):
                self.logger.error("LLM output is not a list.")
                return []

            if len(plan) > self.MAX_STEPS:
                self.logger.warning(f"Plan rejected: {len(plan)} steps exceeds limit of {self.MAX_STEPS}")
                return []

            # Loop Prevention: If same intent appears 3+ times
            intent_counts = {}
            for step in plan:
                intent = step.get("intent")
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
                if intent_counts[intent] >= 3:
                    self.logger.warning(f"Plan rejected: Intent '{intent}' appears 3+ times (potential loop).")
                    return []

            return plan

        except Exception as e:
            self.logger.error(f"Plan generation failed: {e}")
            return []

    def execute_plan(self, plan: List[Dict[str, Any]], pipeline: Any) -> Dict[str, Any]:
        """
        Execute a sequence of steps autonomously.
        Each step goes through full Pipeline validation (Safety Gate -> Policy Engine).
        """
        start_time = time.time()
        audit_log = []
        steps_executed = 0
        failed_step_id = None
        status = "success"
        consecutive_failures = 0

        for step in plan:
            # 1. Global Timeout Guard
            if (time.time() - start_time) > self.MAX_ORCHESTRATION_TIME:
                self.logger.error("Orchestration aborted: Global execution timeout exceeded (10s).")
                status = "aborted"
                break

            step_id = step.get("step_id")
            intent = step.get("intent")
            params = step.get("parameters", {})
            desc = step.get("description", "")

            self.logger.info(f"Executing Step {step_id}: {desc} (Intent: {intent})")

            # 2. Capability Check (Explicit Safeguard)
            if not pipeline.capability_registry.is_intent_allowed(intent):
                self.logger.error(f"Plan step {step_id} uses unknown intent '{intent}'. Aborting.")
                status = "aborted"
                failed_step_id = step_id
                audit_log.append({
                    "step_id": step_id,
                    "status": "failed",
                    "error": f"Unknown intent '{intent}'"
                })
                break

            # 3. Step Execution via Pipeline (Internal methods for validation)
            try:
                # We mock a "user input" for internal trace but use the params
                # To enforce Safety + Policy, we use a controlled path in pipeline
                # For this implementation, we'll use a specialized internal method or normal process_command
                # But since we already HAVE intent and params, we bypass intent detection.
                
                # We call an internal pipeline method that handles validation + execution for a specific Command
                from lyra.reasoning.command_schema import Command
                cmd = Command(raw_input=desc, intent=intent, entities=params, confidence=1.0)
                cmd.decision_source = "orchestrator"
                
                # Run the pipeline validation and execution logic for this command
                # This ensures Safety Gate + Policy Engine are invoked.
                step_result = pipeline._process_autonomous_step(cmd)
                
                audit_log.append({
                    "step_id": step_id,
                    "intent": intent,
                    "description": desc,
                    "success": step_result.success,
                    "output": step_result.output,
                    "error": step_result.error
                })

                if step_result.success:
                    steps_executed += 1
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= 2:
                        self.logger.warning("Orchestration aborted: 2 consecutive step failures.")
                        status = "aborted"
                        failed_step_id = step_id
                        break
                    # If single failure, we continue unless it's a critical safety/policy block
                    if step_result.error in ["Policy Violation", "Execution Blocked"]:
                        self.logger.error(f"Critical security failure in step {step_id}. Aborting plan.")
                        status = "aborted"
                        failed_step_id = step_id
                        break

            except Exception as e:
                self.logger.error(f"Step {step_id} execution exception: {e}")
                status = "aborted"
                failed_step_id = step_id
                audit_log.append({"step_id": step_id, "status": "exception", "error": str(e)})
                break

        result = {
            "status": status,
            "steps_executed": steps_executed,
            "failed_step": failed_step_id,
            "audit_log": audit_log,
            "total_time": round(time.time() - start_time, 2)
        }
        
        # Store in session memory
        if hasattr(pipeline, 'session_memory'):
            pipeline.session_memory.add_interaction(
                role="assistant",
                content=f"Autonomous plan completed: {status}",
                audit_log=result
            )

        return result
