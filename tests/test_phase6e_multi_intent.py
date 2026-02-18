# -*- coding: utf-8 -*-
"""
Test Phase 6E: Controlled Multi-Intent Support
Verifies sequential execution, safety constraints, and chain aborts.
"""
import unittest
from unittest.mock import MagicMock
import sys
import os

# Ensure we can import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lyra.core.pipeline import LyraPipeline
# from lyra.reasoning.command_schema import Command

class TestPhase6EMultiIntent(unittest.TestCase):
    
    def setUp(self):
        self.pipeline = LyraPipeline()
        self.pipeline.use_semantic_layer = True
        # Mock internal components
        self.pipeline.semantic_engine = MagicMock()
        self.pipeline.gateway = MagicMock()
        self.pipeline.planner = MagicMock()
        self.pipeline.refinement_engine = MagicMock()
        self.pipeline.refinement_engine.refine_intent.return_value = None
        self.pipeline.clarification_manager = MagicMock()
        self.pipeline.clarification_manager.has_pending.return_value = False
        
    def test_multi_intent_execution_success(self):
        """Test executing two valid intents sequentially"""
        # Mock Semantic Response
        self.pipeline.semantic_engine.parse_semantic_intent.return_value = {
            "intents": [
                {"intent": "create_file", "parameters": {"path": "A.txt"}, "confidence": 0.9, "requires_clarification": False},
                {"intent": "launch_app", "parameters": {"app_name": "notepad"}, "confidence": 0.9, "requires_clarification": False}
            ],
            "confidence": 0.9,
            "requires_clarification": False
        }
        
        # Mock Planner
        plan_mock = MagicMock()
        plan_mock.plan_id = "test_plan"
        plan_mock.requires_confirmation = False
        plan_mock.steps = ["step1"]
        self.pipeline.planner.create_plan_from_command.return_value = plan_mock
        
        # Mock Gateway Success
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.output = "Executed" # This takes precedence in some formatters, but Lyra's iterates results
        result_mock.error = None
        result_mock.total_duration = 0.5
        
        # Populate results list for formatter
        step_res = MagicMock()
        step_res.success = True
        step_res.output = "Executed"
        result_mock.results = [step_res]
        
        self.pipeline.gateway.execute_plan.return_value = result_mock
        
        # Execute
        res = self.pipeline.process_command("create A and open it", auto_confirm=True)
        
        # Verify
        self.assertTrue(res.success)
        self.assertEqual(self.pipeline.gateway.execute_plan.call_count, 2)
        self.assertIn("Executed", res.output)
        
        # Verify Decision Source
        # Planner called twice. Check first call args.
        args, _ = self.pipeline.planner.create_plan_from_command.call_args_list[0]
        cmd_arg = args[0]
        self.assertEqual(cmd_arg.decision_source, "semantic")

    def test_safety_guard_write_delete(self):
        """Test blocking write + delete chain"""
        # Setup Success for first call
        plan_mock = MagicMock()
        plan_mock.requires_confirmation = False
        self.pipeline.planner.create_plan_from_command.return_value = plan_mock
        
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.output = "Write Done"
        result_mock.error = None
        result_mock.total_duration = 0.5
        result_mock.results = []
        self.pipeline.gateway.execute_plan.return_value = result_mock
        
        self.pipeline.semantic_engine.parse_semantic_intent.return_value = {
            "intents": [
                {"intent": "write_file", "parameters": {}, "confidence": 0.9, "requires_clarification": False},
                {"intent": "delete_file", "parameters": {}, "confidence": 0.9, "requires_clarification": False}
            ]
        }
        
        res = self.pipeline.process_command("write then delete", auto_confirm=True)
        
        self.assertFalse(res.success)
        self.assertIn("Safety Guard", res.output)
        self.assertIn("Blocked ambiguous destructive chain", res.output)
        
        # Should execute first (write) but not second
        self.assertEqual(self.pipeline.gateway.execute_plan.call_count, 1)

    def test_abort_on_failure(self):
        """Test chain aborts if first intent fails"""
        self.pipeline.semantic_engine.parse_semantic_intent.return_value = {
            "intents": [
                {"intent": "create_file", "parameters": {}, "confidence": 0.9, "requires_clarification": False},
                {"intent": "launch_app", "parameters": {}, "confidence": 0.9, "requires_clarification": False}
            ]
        }
        
        plan_mock = MagicMock()
        plan_mock.requires_confirmation = False
        self.pipeline.planner.create_plan_from_command.return_value = plan_mock
        
        # Mock Gateway: First fails
        result_fail = MagicMock()
        result_fail.success = False
        result_fail.output = "Failed"
        result_fail.error = "Error"
        result_fail.total_duration = 0.1
        result_fail.results = []
        
        result_success = MagicMock()
        result_success.success = True
        result_success.total_duration = 0.1
        result_success.results = []
        
        # side_effect to return fail first, then success (if called)
        self.pipeline.gateway.execute_plan.side_effect = [result_fail, result_success]
        
        res = self.pipeline.process_command("fail then succeed", auto_confirm=True)
        
        self.assertFalse(res.success)
        # Should execute only once
        self.assertEqual(self.pipeline.gateway.execute_plan.call_count, 1)
        self.assertIn("Failed", res.output)

    def test_chain_clarification_pause(self):
        """Test chain pauses if one intent needs clarification"""
        # First intent needs clarification
        self.pipeline.semantic_engine.parse_semantic_intent.return_value = {
            "intents": [
                {"intent": "create_file", "parameters": {}, "confidence": 0.5, "requires_clarification": True},
                {"intent": "launch_app", "parameters": {}, "confidence": 0.9, "requires_clarification": False}
            ],
            "requires_clarification": True # Aggregated flag
        }
        
        # Mock Clarification Manager Create
        self.pipeline.clarification_manager.create_clarification.return_value = "Confused?"
        
        res = self.pipeline.process_command("ambiguous then valid", auto_confirm=True)
        
        self.assertFalse(res.success)
        self.assertIn("Requires Clarification", res.error or "")
        # Gateway should NOT be called
        self.assertEqual(self.pipeline.gateway.execute_plan.call_count, 0)
        # Should have called create_clarification
        self.pipeline.clarification_manager.create_clarification.assert_called()

if __name__ == '__main__':
    unittest.main()
