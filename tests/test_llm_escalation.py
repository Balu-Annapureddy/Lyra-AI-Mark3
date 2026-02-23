import unittest
from unittest.mock import MagicMock, patch
import os
from lyra.llm.escalation_layer import LLMEscalationAdvisor

class TestLLMEscalation(unittest.TestCase):
    def setUp(self):
        # Mock Gemini API Key
        self.env_patcher = patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'})
        self.env_patcher.start()
        self.advisor = LLMEscalationAdvisor()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('google.generativeai.GenerativeModel')
    def test_advisor_analysis_success(self, mock_gen_model):
        """Test successful analysis with Gemini mock."""
        # Setup mock response
        mock_instance = mock_gen_model.return_value
        mock_response = MagicMock()
        mock_response.text = '{"intent": "write_file", "confidence": 0.9, "needs_confirmation": true, "reasoning": "Test reasoning"}'
        mock_instance.generate_content.return_value = mock_response

        # Mock initialize_gemini to true
        with patch.object(LLMEscalationAdvisor, '_initialize_gemini', return_value=True):
            self.advisor._gen_model = mock_instance
            res = self.advisor.analyze("create a file", reasoning_level="standard")
        
        self.assertEqual(res["intent"], "write_file")
        self.assertEqual(res["confidence"], 0.9)
        self.assertTrue(res["needs_confirmation"])

    @patch('google.generativeai.GenerativeModel')
    def test_advisor_unknown_intent(self, mock_gen_model):
        """Test fallback when LLM suggests unsupported intent."""
        mock_instance = mock_gen_model.return_value
        mock_response = MagicMock()
        mock_response.text = '{"intent": "hack_system", "confidence": 0.9, "needs_confirmation": false, "reasoning": "Unsupported"}'
        mock_instance.generate_content.return_value = mock_response

        with patch.object(LLMEscalationAdvisor, '_initialize_gemini', return_value=True):
            self.advisor._gen_model = mock_instance
            res = self.advisor.analyze("hack me", reasoning_level="standard")
        
        self.assertEqual(res["intent"], "unknown")
        self.assertEqual(res["confidence"], 0.0)

    @patch('google.generativeai.GenerativeModel')
    def test_advisor_api_failure_fallback(self, mock_gen_model):
        """Test graceful fallback on API error."""
        # Mock initialization success but call failure
        with patch.object(LLMEscalationAdvisor, '_initialize_gemini', return_value=True):
            mock_instance = mock_gen_model.return_value
            mock_instance.generate_content.side_effect = Exception("API Down")
            self.advisor._gen_model = mock_instance

            res = self.advisor.analyze("hello", reasoning_level="standard")
        
        self.assertEqual(res["intent"], "unknown")
        self.assertIn("Cognitive engines are temporarily unavailable", res["reasoning"])
        self.assertTrue(res.get("error"))

if __name__ == '__main__':
    unittest.main()
