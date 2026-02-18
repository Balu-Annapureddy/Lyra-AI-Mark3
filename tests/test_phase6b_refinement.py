# -*- coding: utf-8 -*-
"""
Test Phase 6B: Conversational Refinement
Verifies context management and intent refinement logic.
"""
import unittest
import sys
import os

# Ensure we can import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lyra.context.context_manager import ConversationContext
from lyra.context.refinement_engine import RefinementEngine
from lyra.core.pipeline import LyraPipeline

class TestPhase6BRefinement(unittest.TestCase):
    
    def setUp(self):
        self.context = ConversationContext()
        self.engine = RefinementEngine()
        self.pipeline = LyraPipeline()
        self.pipeline.use_semantic_layer = True
        
    def test_context_storage(self):
        """Test storing and retrieving intent"""
        intent = {"intent": "write_file", "parameters": {"path": "foo.txt"}, "confidence": 1.0}
        self.context.update_last_intent(intent)
        
        saved = self.context.get_last_intent()
        self.assertEqual(saved["intent"], "write_file")
        self.assertEqual(saved["parameters"]["path"], "foo.txt")
        
    def test_refinement_detection(self):
        """Test detection of refinement phrases"""
        prev_intent = {
            "intent": "write_file", 
            "parameters": {"path": "notes.txt", "content": "hello"}, 
            "confidence": 0.9,
            "requires_clarification": False
        }
        self.context.update_last_intent(prev_intent)
        
        # "change name to X"
        input1 = "change name to diary.md"
        res1 = self.engine.refine_intent(input1, self.context)
        
        self.assertIsNotNone(res1)
        self.assertEqual(res1["intent"], "write_file")
        self.assertEqual(res1["parameters"]["path"], "diary.md") # Mutated
        self.assertEqual(res1["parameters"]["content"], "hello") # Preserved
        
        # "make it shorter" (Content mutation)
        input2 = "make it shorter"
        res2 = self.engine.refine_intent(input2, self.context)
        self.assertIsNotNone(res2)
        self.assertNotEqual(res2["parameters"]["content"], "hello") # Should change
        
    def test_no_context_refinement(self):
        """Refinement should fail if no context exists"""
        self.context.clear()
        res = self.engine.refine_intent("change name to diary.md", self.context)
        self.assertIsNone(res)
        
    def test_pipeline_flow(self):
        """Test full pipeline integration"""
        # 1. Initial Command
        cmd1 = "create file test_refine.txt with content initial"
        res1 = self.pipeline.process_command(cmd1, auto_confirm=True)
        self.assertTrue(res1.success)
        
        # Context should be updated
        last = self.pipeline.context.get_last_intent()
        self.assertIsNotNone(last)
        self.assertEqual(last["intent"], "write_file")
        
        # 2. Refinement Command
        cmd2 = "change content to refined"
        res2 = self.pipeline.process_command(cmd2, auto_confirm=True) # Should reuse write_file intent
        self.assertTrue(res2.success)
        
        # Check if actual execution logic would verify this (we rely on pipeline logs/result)
        # Note: In real execution, it would write to test_refine.txt again with new content.
        
        # 3. Invalid Refinement (should assume new command or fail)
        cmd3 = "open calculator"
        res3 = self.pipeline.process_command(cmd3, auto_confirm=True)
        self.assertTrue(res3.success) # It's a valid command
        
        # But context should now be launch_app, not write_file
        last_new = self.pipeline.context.get_last_intent()
        self.assertEqual(last_new["intent"], "launch_app")

if __name__ == '__main__':
    unittest.main()
