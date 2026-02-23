# -*- coding: utf-8 -*-
"""
tests/test_reasoning_depth.py
Phase F8: Adaptive Reasoning Depth Tests
"""

import unittest
from unittest.mock import MagicMock, patch
from lyra.core.reasoning_depth import ReasoningDepthController, ReasoningLevel
from lyra.core.pipeline import LyraPipeline
from lyra.llm.escalation_layer import LLMEscalationAdvisor
from lyra.reasoning.command_schema import Command

class TestReasoningDepth(unittest.TestCase):

    def test_level_determination_shallow(self):
        # High confidence, no planning, early turn
        level = ReasoningDepthController.determine_level(
            intent="delete_file",
            embedding_confidence=0.9,
            ambiguity_score=0.1,
            conversation_turn_count=1,
            contains_planning_keywords=False,
            user_input="delete test.txt"
        )
        self.assertEqual(level, ReasoningLevel.SHALLOW)

    def test_level_determination_standard_mid_conf(self):
        # Mid confidence triggers STANDARD
        level = ReasoningDepthController.determine_level(
            intent="delete_file",
            embedding_confidence=0.7,
            ambiguity_score=0.3,
            conversation_turn_count=1,
            contains_planning_keywords=False,
            user_input="maybe delete file"
        )
        self.assertEqual(level, ReasoningLevel.STANDARD)

    def test_level_determination_deep_planning(self):
        # Planning keyword triggers DEEP
        level = ReasoningDepthController.determine_level(
            intent="unknown",
            embedding_confidence=0.5,
            ambiguity_score=0.5,
            conversation_turn_count=1,
            contains_planning_keywords=True,
            user_input="help me organize my workspace"
        )
        self.assertEqual(level, ReasoningLevel.DEEP)

    def test_level_determination_deep_multi_step(self):
        # Multi-step indicator triggers DEEP
        level = ReasoningDepthController.determine_level(
            intent="unknown",
            embedding_confidence=0.6,
            ambiguity_score=0.4,
            conversation_turn_count=1,
            contains_planning_keywords=False,
            user_input="do this and then do that"
        )
        self.assertEqual(level, ReasoningLevel.DEEP)

    def test_emotion_refinement(self):
        # High confidence but angry -> STANDARD
        level = ReasoningDepthController.determine_level(
            intent="delete_file",
            embedding_confidence=0.95,
            ambiguity_score=0.05,
            conversation_turn_count=1,
            contains_planning_keywords=False,
            user_input="delete the damn file",
            emotion_state="angry"
        )
        self.assertEqual(level, ReasoningLevel.STANDARD)

    def test_pipeline_shallow_skips_escalation(self):
        pipeline = LyraPipeline()
        pipeline.use_embedding_router = True
        
        # Mock high confidence result
        with patch.object(pipeline.embedding_router, 'classify') as mock_classify:
            mock_classify.return_value = {"intent": "delete_file", "confidence": 0.95, "requires_escalation": False}
            
            with patch.object(pipeline.advisor, 'analyze') as mock_advisor:
                pipeline.process_command("delete test.txt", auto_confirm=True)
                # Advisor should NOT have been called due to SHALLOW reasoning
                mock_advisor.assert_not_called()

    def test_pipeline_deep_escalation_injection(self):
        pipeline = LyraPipeline()
        # "organize" triggers DEEP
        user_input = "organize my downloads"
        
        with patch.object(pipeline.advisor, '_initialize_gemini', return_value=True):
            pipeline.advisor._gen_model = MagicMock()
            with patch.object(pipeline.advisor._gen_model, 'generate_content') as mock_gen:
                # Mock LLM response
                mock_gen.return_value = MagicMock(text='{"intent": "unknown", "confidence": 0.0, "needs_confirmation": true, "reasoning": "test"}')
                
                pipeline.process_command(user_input, auto_confirm=True)
                
                # Check if DEEP instruction was injected
                call_args = mock_gen.return_value.generate_content.call_args if hasattr(pipeline.advisor, '_gen_model') and pipeline.advisor._gen_model else mock_gen.call_args
                # The mock_gen might be the generate_content itself if patched that way, 
                # but here advisor._gen_model is a MagicMock. 
                # Let's check how it's patched in the test:
                # with patch.object(pipeline.advisor._gen_model, 'generate_content') as mock_gen:
                
                call_args = mock_gen.call_args
                prompt_with_system = call_args[0][0]
                self.assertIn("Break down the problem step-by-step", prompt_with_system)

    def test_escalation_layer_shallow_return(self):
        advisor = LLMEscalationAdvisor()
        # Mocking initialization to False
        with patch.object(advisor, '_initialize_gemini', return_value=False):
            result = advisor.analyze("test", reasoning_level="shallow")
            self.assertEqual(result["reasoning"], "Reasoning skipped")

if __name__ == "__main__":
    unittest.main()
