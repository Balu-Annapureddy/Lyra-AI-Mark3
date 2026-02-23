# -*- coding: utf-8 -*-
"""
tests/test_multilingual.py
Phase F7: Multilingual Support Layer Tests
"""

import unittest
from unittest.mock import MagicMock, patch
from lyra.context.language_mirror import LanguageMirror
from lyra.core.pipeline import LyraPipeline
from lyra.memory.session_memory import SessionMemory
from lyra.llm.escalation_layer import LLMEscalationAdvisor

class TestMultilingualSupport(unittest.TestCase):

    def setUp(self):
        self.mirror = LanguageMirror()

    def test_language_detection(self):
        # English (Longer string for stability)
        self.assertEqual(LanguageMirror.detect_language("Please delete the temporary system logs immediately"), "en")
        # Telugu (Pekala - "Tell me")
        # "దయచేసి నా ఫైల్‌ను సిస్టమ్ నుండి తొలగించండి" - "Please delete my file from system"
        self.assertEqual(LanguageMirror.detect_language("దయచేసి నా ఫైల్‌ను సిస్టమ్ నుండి తొలగించండి"), "te")
        # Hindi
        # "कृपया मेरे कंप्यूटर से फाइल हटा दें" - "Please delete file from my computer"
        self.assertEqual(LanguageMirror.detect_language("कृपया मेरे कंप्यूटर से फाइल हटा दें"), "hi")
        # Spanish
        self.assertEqual(LanguageMirror.detect_language("Por favor elimine los archivos temporales"), "es")

    def test_system_phrase_mirroring(self):
        # Telugu
        te_msg = LanguageMirror.mirror_response("Are you sure?", "te")
        self.assertEqual(te_msg, "మీరు ఖచ్చితంగా ఉన్నారా?")
        
        # Hindi
        hi_msg = LanguageMirror.mirror_response("Operation completed successfully.", "hi")
        self.assertEqual(hi_msg, "ऑपरेशन सफलतापूर्वक पूरा हुआ।")

    def test_session_preference_logic(self):
        memory = SessionMemory()
        # Ensure preferred is en by default
        memory.preferred_language = "en"
        
        # 1-4 hits: no change to preferred_language
        for _ in range(4):
            memory.update_language_preference("te")
        self.assertEqual(memory.preferred_language, "en")
        
        # 5th hit: triggers preference
        memory.update_language_preference("te")
        self.assertEqual(memory.preferred_language, "te")

    def test_pipeline_integration_mirroring(self):
        pipeline = LyraPipeline()
        pipeline.use_embedding_router = False
        pipeline.use_semantic_layer = False # Force it to regex fallback
        
        # Force a successful intent match
        with patch.object(pipeline.intent_detector, 'detect_intent') as mock_regex:
            from lyra.reasoning.command_schema import Command
            mock_regex.return_value = Command(intent="delete_file", raw_input="నన్ను తొలగించు", confidence=0.9, entities={"path": "test.txt"})
            
            with patch.object(pipeline, '_execute_command') as mock_exec:
                mock_exec.return_value = MagicMock(success=True, output="Operation completed successfully.")
                
                result = pipeline.process_command("నన్ను తొలగించు", auto_confirm=True)
                # Should mirror the output. Use assertIn to ignore ANSI codes.
                self.assertIn("ఆపరేషన్ విజయవంతంగా పూర్తయింది.", result.output)

    def test_llm_prompt_injection(self):
        advisor = LLMEscalationAdvisor()
        with patch.object(advisor, '_initialize_gemini', return_value=True):
            advisor._gen_model = MagicMock()
            with patch.object(advisor._gen_model, 'generate_content') as mock_gen:
                mock_gen.return_value = MagicMock(text='{"intent": "unknown", "confidence": 0.0, "needs_confirmation": true, "reasoning": "test"}')
                advisor.analyze("నన్ను తొలగించు", language="te")
            
                # Check if Telugu instruction was injected into prompt (it's the first arg in our new advisor)
                call_args = mock_gen.call_args
                prompt_with_system = call_args[0][0]
                self.assertIn("System Language: te", prompt_with_system)

    def test_fallback_behavior(self):
        # Short ambiguous input should use preferred language
        pipeline = LyraPipeline()
        pipeline.session_memory.preferred_language = "hi"
        pipeline.use_embedding_router = False
        pipeline.use_semantic_layer = False
        
        # Mock detect_language to return 'en' for short input
        with patch("lyra.context.language_mirror.LanguageMirror.detect_language", return_value="en"):
            with patch.object(pipeline.intent_detector, 'detect_intent') as mock_regex:
                 mock_regex.return_value = MagicMock(intent="unknown")
                 # Fallback message "Could not understand command" is mirrored
                 result = pipeline.process_command("abc", auto_confirm=True)
                 # "Could not understand command" -> "आदेश समझ में नहीं आया"
                 self.assertIn("आदेश समझ में नहीं आया", result.output)

if __name__ == "__main__":
    unittest.main()
