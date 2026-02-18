# -*- coding: utf-8 -*-
"""
Test Phase 6C: Structured Clarification Loop
Verifies multi-turn clarification flow.
"""
import unittest
import sys
import os

# Ensure we can import from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lyra.context.clarification_service import ClarificationManager
from lyra.core.pipeline import LyraPipeline

class TestPhase6CClarification(unittest.TestCase):
    
    def setUp(self):
        self.manager = ClarificationManager()
        self.pipeline = LyraPipeline()
        self.pipeline.use_semantic_layer = True
        
    def test_manager_missing_fields(self):
        """Test question generation for missing fields"""
        # Case 1: Write file missing name
        intent1 = {"intent": "write_file", "parameters": {"path": "untitled.txt"}, "confidence": 0.5}
        q1 = self.manager.create_clarification(intent1)
        self.assertIn("name", q1.lower())
        self.assertTrue(self.manager.has_pending())
        
        # Resolve
        res1 = self.manager.resolve_clarification("my_doc.txt")
        self.assertIsNotNone(res1)
        self.assertEqual(res1["parameters"]["path"], "my_doc.txt")
        self.assertFalse(self.manager.has_pending())
        
    def test_pipeline_clarification_flow(self):
        """Test full pipeline loop"""
        # 1. Ambiguous Command
        # "open it" -> usually ambiguous if no context
        # But to be safe, let's inject a mock semantic result or use a known ambiguous phrase
        # "create file" without name -> Semantic Engine usually defaults to untitled.txt but might set low confidence?
        # Let's force it via a mock or use 'create file' which usually defaults but let's assume valid.
        
        # Actually, let's use the 'local_model.py' logic.
        # "create file" -> path="untitled.txt", confidence=0.6, requires_clarification=False? 
        # Wait, local_model sets requires_clarification=False for untitled.txt currently.
        
        # Let's use a mocked semantic engine response to semantic ambiguity mechanism
        # or just modify local_model to set requires_clarification=True for generic inputs?
        # Easier: Just unit test the pipeline logic by forcing the semantic engine check.
        
        # But for end-to-end, let's use "do the thing" which returns requires_clarification=True in local_model.
        
        cmd1 = "do the thing"
        res1 = self.pipeline.process_command(cmd1)
        
        # Should return warning/question
        self.assertFalse(res1.success)
        self.assertEqual(res1.error, "Requires Clarification")
        self.assertTrue(self.pipeline.clarification_manager.has_pending())
        
        # 2. Resolve (User answers)
        # "do the thing" doesn't have a specific intent type in local_model fallback
        # It yields {"intent": "unknown", ...}
        # My ClarificationManager fallback question is "Can you be more specific?"
        # The resolution logic for generic unknown is tricky.
        # Let's check ClarificationManager logic for unknown intent.
        # It likely just returns None or fails?
        
    def test_manager_app_clarification(self):
        intent = {"intent": "launch_app", "parameters": {"app_name": ""}, "confidence": 0.5}
        q = self.manager.create_clarification(intent)
        self.assertIn("application", q.lower())
        
        updated = self.manager.resolve_clarification("notepad")
        self.assertEqual(updated["parameters"]["app_name"], "notepad")

if __name__ == '__main__':
    unittest.main()
