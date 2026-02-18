# -*- coding: utf-8 -*-
"""
Test Phase 6F: Session Memory & Safety Hardening
Verifies structured short-term memory, strict reference resolution, and enhanced safety guards.
"""
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lyra.core.pipeline import LyraPipeline
from lyra.memory.session_memory import SessionMemory

class TestPhase6FSessionMemory(unittest.TestCase):
    
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
        
        # Reset memory
        self.pipeline.session_memory.clear()

    def test_memory_update_on_success(self):
        """Test that memory updates after successful create_file"""
        # Mock Semantic
        self.pipeline.semantic_engine.parse_semantic_intent.return_value = {
            "intents": [{
                "intent": "create_file", 
                "parameters": {"path": "notes.txt"}, 
                "confidence": 0.9,
                "requires_clarification": False
            }]
        }
        
        # Mock Planner & Gateway
        plan_mock = MagicMock()
        plan_mock.requires_confirmation = False
        self.pipeline.planner.create_plan_from_command.return_value = plan_mock
        
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.output = "Created notes.txt"
        result_mock.total_duration = 0.1
        result_mock.results = []
        self.pipeline.gateway.execute_plan.return_value = result_mock
        
        # Execute
        res = self.pipeline.process_command("create notes.txt", auto_confirm=True)
        
        self.assertTrue(res.success)
        # Check memory
        self.assertEqual(self.pipeline.session_memory.last_created_file, "notes.txt")
        self.assertEqual(self.pipeline.session_memory.last_successful_intent, "create_file")

    def test_resolve_reference_success(self):
        """Test resolving 'last file' to previously created file"""
        # Pre-seed memory
        self.pipeline.session_memory.last_created_file = "data.csv"
        
        # Mock Semantic for "open last file" -> should match "open data.csv"
        # The pipeline resolves BEFORE semantic. So semantic engine sees "open data.csv"
        self.pipeline.semantic_engine.parse_semantic_intent.return_value = {
            "intents": [{
                "intent": "launch_app", 
                "parameters": {"path": "data.csv"}, 
                "confidence": 0.9, 
                "requires_clarification": False
            }]
        }
        
        # Setup mocks for execution
        plan_mock = MagicMock()
        plan_mock.requires_confirmation = False
        self.pipeline.planner.create_plan_from_command.return_value = plan_mock
        
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.total_duration = 0.1
        result_mock.results = []
        self.pipeline.gateway.execute_plan.return_value = result_mock
        
        # Execute inputs
        # We need to verify that semantic_engine was called with RESOLVED input
        res = self.pipeline.process_command("open last file", auto_confirm=True)
        
        self.assertTrue(res.success)
        
        # Verify call to semantic engine
        args, _ = self.pipeline.semantic_engine.parse_semantic_intent.call_args
        self.assertIn("data.csv", args[0])
        self.assertIn("open data.csv", args[0], "Should replace 'last file' with 'data.csv'")

    def test_resolve_strict_pronouns(self):
        """Test that pronouns like 'it' are NOT resolved"""
        self.pipeline.session_memory.last_created_file = "doc.txt"
        
        # Mock semantic just to return something
        self.pipeline.semantic_engine.parse_semantic_intent.return_value = {"intents": []} # No-op
        
        # Execute
        self.pipeline.process_command("open it", auto_confirm=True)
        
        # Verify semantic engine received "open it" (unchanged)
        args, _ = self.pipeline.semantic_engine.parse_semantic_intent.call_args
        self.assertEqual(args[0], "open it") 
        
    def test_safety_guard_wildcard_block(self):
        """Test blocking write followed by delete *"""
        
        # Mock Semantic for multi-intent
        self.pipeline.semantic_engine.parse_semantic_intent.return_value = {
            "intents": [
                {"intent": "write_file", "parameters": {"path": "log.txt"}, "confidence": 0.9, "requires_clarification": False},
                {"intent": "delete_file", "parameters": {"path": "*"}, "confidence": 0.9, "requires_clarification": False}
            ]
        }
        
        # Setup first intent success
        plan_mock = MagicMock()
        plan_mock.requires_confirmation = False
        self.pipeline.planner.create_plan_from_command.return_value = plan_mock
        
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.output = "Written"
        result_mock.total_duration = 0.1
        result_mock.results = []
        self.pipeline.gateway.execute_plan.return_value = result_mock
        
        # Execute
        res = self.pipeline.process_command("write log and delete *", auto_confirm=True)
        
        self.assertFalse(res.success)
        self.assertIn("Safety Guard", res.output)
        self.assertIn("wildcard", res.output.lower())
        
        # Should have executed write, then blocked delete
        self.assertEqual(self.pipeline.gateway.execute_plan.call_count, 1)

if __name__ == '__main__':
    unittest.main()
