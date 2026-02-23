# -*- coding: utf-8 -*-
"""
tests/test_task_orchestrator.py
Phase X2: Autonomous Orchestration Tests
"""

import unittest
import json
import time
from unittest.mock import MagicMock, patch
from lyra.orchestration.task_orchestrator import TaskOrchestrator
from lyra.core.pipeline import LyraPipeline
from lyra.reasoning.command_schema import Command
from lyra.core.reasoning_depth import ReasoningLevel

class TestTaskOrchestrator(unittest.TestCase):

    def setUp(self):
        self.orchestrator = TaskOrchestrator()
        self.pipeline = LyraPipeline()

    def test_plan_generation_valid(self):
        """Verify valid plan generation from LLM."""
        mock_advisor = MagicMock()
        mock_advisor._initialize_gemini.return_value = True
        mock_gen = MagicMock()
        mock_advisor._gen_model = mock_gen
        
        mock_gen.generate_content.return_value = MagicMock(text=json.dumps([
            {"step_id": 1, "intent": "create_file", "parameters": {"path": "test.txt"}, "description": "Create file"},
            {"step_id": 2, "intent": "write_file", "parameters": {"path": "test.txt", "content": "hello"}, "description": "Write content"}
        ]))
        
        plan = self.orchestrator.generate_plan("create a file with hello", mock_advisor, "deep")
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["intent"], "create_file")

    def test_reject_untrusted_reasoning(self):
        """Verify plan generation is blocked if reasoning level is not DEEP."""
        mock_llm = MagicMock()
        plan = self.orchestrator.generate_plan("goal", mock_llm, "standard")
        self.assertEqual(plan, [])

    def test_reject_too_many_steps(self):
        """Verify plan length limit (MAX_STEPS = 6)."""
        mock_advisor = MagicMock()
        mock_advisor._initialize_gemini.return_value = True
        mock_gen = MagicMock()
        mock_advisor._gen_model = mock_gen
        
        huge_plan = [{"step_id": i, "intent": "chat", "description": "step"} for i in range(10)]
        mock_gen.generate_content.return_value = MagicMock(text=json.dumps(huge_plan))
        
        plan = self.orchestrator.generate_plan("goal", mock_advisor, "deep")
        self.assertEqual(plan, [])

    def test_reject_repeated_intents(self):
        """Verify loop prevention (3+ same intent)."""
        mock_advisor = MagicMock()
        mock_advisor._initialize_gemini.return_value = True
        mock_gen = MagicMock()
        mock_advisor._gen_model = mock_gen
        
        loop_plan = [
            {"step_id": 1, "intent": "write_file", "description": "1"},
            {"step_id": 2, "intent": "write_file", "description": "2"},
            {"step_id": 3, "intent": "write_file", "description": "3"}
        ]
        mock_gen.generate_content.return_value = MagicMock(text=json.dumps(loop_plan))
        
        plan = self.orchestrator.generate_plan("goal", mock_advisor, "deep")
        self.assertEqual(plan, [])

    def test_execution_timeout(self):
        """Verify 10s global timeout guard."""
        plan = [{"step_id": 1, "intent": "read_file", "description": "step"}]
        
        with patch("time.time") as mock_time:
            # Provide enough side effects for logging and checks
            # Start at 0, check at 11
            mock_time.side_effect = [0] + [11] * 10
            result = self.orchestrator.execute_plan(plan, self.pipeline)
            self.assertEqual(result["status"], "aborted")

    def test_abort_on_safety_failure(self):
        """Verify plan aborts if a step fails safety validation."""
        plan = [{"step_id": 1, "intent": "delete_file", "description": "delete"}]
        
        # Mock pipeline to fail safety gate
        with patch.object(self.pipeline.gateway, 'validate_execution_request') as mock_gate:
            mock_gate.return_value = MagicMock(allowed=False)
            
            result = self.orchestrator.execute_plan(plan, self.pipeline)
            self.assertEqual(result["status"], "aborted")
            self.assertEqual(result["failed_step"], 1)

    def test_abort_on_policy_failure(self):
        """Verify plan aborts if a step violates policy."""
        # Use a supported intent like 'write_file' to pass safety gate first
        plan = [{"step_id": 1, "intent": "write_file", "description": "write"}]
        
        # Mock policy engine to raise violation
        from lyra.policy.policy_engine import PolicyViolationException
        with patch.object(self.pipeline.policy_engine, 'validate') as mock_val:
            mock_val.side_effect = PolicyViolationException("Blocked")
            
            result = self.orchestrator.execute_plan(plan, self.pipeline)
            self.assertEqual(result["status"], "aborted")
            self.assertEqual(result["audit_log"][0]["error"], "Policy Violation")

    def test_consecutive_failure_abort(self):
        """Verify abort after 2 consecutive failures."""
        plan = [
            {"step_id": 1, "intent": "conversation", "description": "1"},
            {"step_id": 2, "intent": "conversation", "description": "2"},
            {"step_id": 3, "intent": "conversation", "description": "3"}
        ]
        
        # Mock internal step processor to fail
        with patch.object(self.pipeline, '_process_autonomous_step') as mock_step:
            mock_step.return_value = MagicMock(success=False, output="err", error="err")
            
            result = self.orchestrator.execute_plan(plan, self.pipeline)
            self.assertEqual(result["steps_executed"], 0)
            self.assertEqual(result["failed_step"], 2) # Aborted at second failure

    def test_pipeline_integration_complex_goal(self):
        """Verify pipeline triggers orchestration for complex_goal."""
        # 1. Mock advisor to return 'complex_goal' with DEEP reasoning
        # 2. Mock orchestrator to return a success plan
        
        with patch.object(self.pipeline.advisor, 'analyze') as mock_adv:
            mock_adv.return_value = {"intent": "complex_goal", "confidence": 0.9}
            
            with patch.object(self.pipeline.orchestrator, 'generate_plan') as mock_gen:
                mock_gen.return_value = [{"step_id": 1, "intent": "conversation", "description": "done"}]
                
                with patch.object(self.pipeline.orchestrator, 'execute_plan') as mock_exec:
                    mock_exec.return_value = {
                        "status": "success", 
                        "steps_executed": 1, 
                        "audit_log": [{"intent": "conversation", "success": True, "description": "done"}]
                    }
                    
                # Force reasoning level to DEEP in determination
                with patch("lyra.core.reasoning_depth.ReasoningDepthController.determine_level") as mock_depth:
                    mock_depth.return_value = ReasoningLevel.DEEP
                    with patch.object(self.pipeline.advisor, '_initialize_gemini', return_value=True):
                        self.pipeline.advisor._gen_model = MagicMock() # Ensure it's not None
                        result = self.pipeline.process_command("i have a big task")
                        self.assertTrue(result.success)
                        self.assertIn("Autonomous Task Result: SUCCESS", result.output)

if __name__ == "__main__":
    unittest.main()
