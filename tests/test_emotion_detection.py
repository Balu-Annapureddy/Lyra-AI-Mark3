# -*- coding: utf-8 -*-
"""
tests/test_emotion_detection.py
Phase F6: Emotion & Sarcasm Detection Tests
"""

import unittest
from unittest.mock import MagicMock, patch
import json

from lyra.context.emotion.detector import EmotionDetector
from lyra.llm.escalation_layer import LLMEscalationAdvisor
from lyra.core.pipeline import LyraPipeline
from lyra.core.config import Config
from lyra.reasoning.command_schema import Command

class TestEmotionDetection(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.detector = EmotionDetector(self.config)

    def test_frustration_detection(self):
        result = self.detector.detect("broken again ugh not working")
        self.assertEqual(result["emotion"], "frustrated")
        self.assertTrue(result["requires_softening"])

    def test_anger_detection(self):
        result = self.detector.detect("stupid useless hate this trash")
        self.assertEqual(result["emotion"], "angry")
        self.assertTrue(result["requires_softening"])

    def test_happiness_detection(self):
        result = self.detector.detect("awesome thanks great job")
        self.assertEqual(result["emotion"], "happy")
        self.assertFalse(result["requires_softening"])

    def test_confusion_detection(self):
        result = self.detector.detect("what is this makes no sense")
        self.assertEqual(result["emotion"], "confused")
        self.assertFalse(result["requires_softening"])

    def test_sarcasm_detection(self):
        result = self.detector.detect("oh great...")
        self.assertEqual(result["emotion"], "sarcastic")
        self.assertTrue(result["requires_confirmation"])

    def test_intensity_scoring(self):
        # Normal
        res1 = self.detector.detect("i am angry")
        # CAPS + Punctuation
        res2 = self.detector.detect("I AM ANGRY!!!")
        self.assertGreater(res2["intensity"], res1["intensity"])

    @patch("lyra.llm.escalation_layer.LLMEscalationAdvisor._initialize_gemini", return_value=True)
    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_llm_assisted_fallback(self, mock_generate, mock_init):
        # Rule-based will have low confidence for ambiguous input
        mock_resp = MagicMock()
        mock_resp.text = '{"emotion": "sarcastic", "confidence": 0.95, "reasoning": "detective"}'
        mock_generate.return_value = mock_resp
        
        # Inject mock advisor into detector
        mock_advisor = LLMEscalationAdvisor()
        mock_advisor._gen_model = MagicMock()
        mock_advisor._gen_model.generate_content.return_value = mock_resp
        self.detector._advisor = mock_advisor
        
        result = self.detector.detect("Nice job on deleting my database.")
        self.assertEqual(result["emotion"], "sarcastic")
        self.assertGreater(result["confidence"], 0.9)

    def test_pipeline_integration_softening(self):
        pipeline = LyraPipeline()
        # Mock successful command
        with patch.object(pipeline, '_execute_command') as mock_exec:
            mock_exec.return_value = MagicMock(success=True, output="File deleted.")
            # Angry input - intensity should be > 0.3
            result = pipeline.process_command("STUPID LYRA DELETE my_file.txt!!!", auto_confirm=True)
            # It could be "Apologies" or "I understand you're upset" depending on intensity
            self.assertTrue("Apologies" in result.output or "understand" in result.output)

    def test_pipeline_integration_sarcasm_confirmation(self):
        pipeline = LyraPipeline()
        # Mock command
        with patch.object(pipeline.embedding_router, 'classify', return_value={"intent": "delete_file", "confidence": 0.9}):
            # Sarcastic input
            # We need to ensure it reaches the confirmation check
            # requires_confirmation should be set on the command
            with patch.object(pipeline, '_execute_command') as mock_exec:
                pipeline.process_command("Oh great, just delete everything...", auto_confirm=True)
                # Check if cmd.requires_confirmation was passed
                cmd = mock_exec.call_args[0][0]
                self.assertTrue(cmd.requires_confirmation)

if __name__ == "__main__":
    unittest.main()
