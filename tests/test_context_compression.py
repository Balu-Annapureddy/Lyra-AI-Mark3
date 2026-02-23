# -*- coding: utf-8 -*-
"""
tests/test_context_compression.py
Phase F9: Contextual Memory Compression Tests
"""

import unittest
from unittest.mock import MagicMock, patch
from lyra.memory.context_compressor import ContextCompressor
from lyra.core.pipeline import LyraPipeline
from lyra.llm.escalation_layer import LLMEscalationAdvisor

class TestContextCompression(unittest.TestCase):

    def test_should_compress_threshold(self):
        """Verify compression trigger logic."""
        self.assertFalse(ContextCompressor.should_compress(10, trigger_threshold=20))
        self.assertTrue(ContextCompressor.should_compress(21, trigger_threshold=20))

    def test_rule_based_compression_content(self):
        """Verify rule-based summary extracts correct info."""
        history = [
            {"role": "user", "raw_input": "create file test.py", "intent": "create_file"},
            {"role": "assistant", "content": "File created.", "success": True, "intent": "create_file"},
            {"role": "user", "raw_input": "read file test.py", "intent": "read_file"},
            {"role": "assistant", "content": "File content...", "success": True, "intent": "read_file"}
        ]
        
        # We'll compress with preserve_count=0 to check the summary of everything
        compressed = ContextCompressor.compress(history, preserve_count=0)
        
        self.assertEqual(len(compressed), 1)
        summary = compressed[0]["content"]
        self.assertIn("create_file", summary)
        self.assertIn("read_file", summary)
        self.assertIn("test.py", summary)

    def test_safety_preservation(self):
        """Verify that safety records are NOT compressed."""
        history = [
            {"role": "user", "content": "dangerous command", "risk_level": "HIGH"},
            {"role": "assistant", "content": "Warning!", "safety_violation": True},
            {"role": "user", "content": "normal turn 1"},
            {"role": "user", "content": "normal turn 2"},
            {"role": "user", "content": "normal turn 3"},
            {"role": "user", "content": "normal turn 4"}
        ]
        
        # Preserve only last 2 turns. This should force compression of the older ones.
        # But the first two are safety records, so they should be kept.
        compressed = ContextCompressor.compress(history, preserve_count=2)
        
        # Expected: 1 summary turn + 2 safety turns + 2 recent turns = 5 total
        self.assertEqual(len(compressed), 5)
        
        roles = [turn.get("role") for turn in compressed]
        self.assertEqual(roles.count("system"), 1) # Summary
        self.assertIn("dangerous command", [t.get("content") for t in compressed])
        self.assertIn("Warning!", [t.get("content") for t in compressed])

    def test_llm_assisted_compression(self):
        """Verify LLM branch is used when model_advisor is provided."""
        history = [{"role": "user", "content": "turn 1"}, {"role": "user", "content": "turn 2"}]
        
        # We use a spec to avoid MagicMock inheriting everything (like generate_summary)
        mock_llm = MagicMock(spec=LLMEscalationAdvisor)
        mock_llm._initialize_gemini.return_value = True
        mock_gen = MagicMock()
        mock_gen.generate_content.return_value = MagicMock(text="This is an LLM summary.")
        mock_llm._gen_model = mock_gen
        
        compressed = ContextCompressor.compress(history, model_advisor=mock_llm, preserve_count=0)
        
        self.assertEqual(compressed[0]["content"], "[COMPRESSED HISTORY SUMMARY]\nThis is an LLM summary.")

    def test_pipeline_integration_triggers_compression(self):
        """Verify pipeline triggers compression when turn count is high."""
        pipeline = LyraPipeline()
        
        # Fill history with 25 turns (threshold is 20)
        for i in range(25):
            pipeline.session_memory.add_interaction("user", f"turn {i}")
            
        self.assertEqual(len(pipeline.session_memory.interaction_history), 25)
        
        # Force escalation to trigger compression logic in pipeline
        with patch.object(pipeline.advisor, 'analyze') as mock_analyze:
            mock_analyze.return_value = {"intent": "unknown", "confidence": 0.0, "needs_confirmation": False, "reasoning": "test"}
            
            # This should trigger should_compress and compress()
            pipeline.process_command("trigger escalation", auto_confirm=True)
            
            # Check history size after compression
            # Original 25 + 1 new user turn = 26
            # After compression: 1 summary + (any safety? 0) + 6 preserved + 1 new user (not yet in compressed segment but in history)
            # Actually, the pipeline adds the current turn BEFORE checking compression.
            # So 26 turns -> compressed to (1 summary + 6 preserved) = 7.
            # Then it calls advisor with these 7.
            
            self.assertLess(len(pipeline.session_memory.interaction_history), 10)
            self.assertTrue(pipeline.session_memory.interaction_history[0].get("is_compressed_summary"))

    def test_token_reduction_simulation(self):
        """Verify that compression yields a shorter string representation."""
        history = [{"role": "user", "content": "a long turn with lots of text " * 10}] * 20
        original_size = sum(len(str(t)) for t in history)
        
        compressed = ContextCompressor.compress(history, preserve_count=2)
        compressed_size = sum(len(str(t)) for t in compressed)
        
        self.assertLess(compressed_size, original_size * 0.5)

if __name__ == "__main__":
    unittest.main()
