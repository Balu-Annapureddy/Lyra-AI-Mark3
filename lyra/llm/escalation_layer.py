import json
import time
import os
from typing import Dict, Any, Optional, List

from lyra.core.config import Config
from lyra.core.logger import get_logger
from lyra.execution.execution_gateway import SUPPORTED_INTENTS

logger = get_logger(__name__)

class LLMEscalationAdvisor:
    """
    Advisor module that uses Gemini API to reason about user input.
    Provides structured reasoning and intent recommendations for ambiguous inputs.
    """
    
    SYSTEM_PROMPT = f"""You are an advisory reasoning module for Lyra AI. 
Your goal is to interpret ambiguous user commands and recommend the most likely intent and parameters.

SUPPORTED INTENTS:
{', '.join(SUPPORTED_INTENTS)}

RULES:
1. ONLY return valid JSON. No conversational filler.
2. DO NOT invent new intents. Use 'unknown' if no supported intent fits.
3. You are an advisor, NOT an executor. Do not suggest shell scripts or direct code execution.
4. If the user input is a statement without an action, use intent: 'conversation'.

OUTPUT SCHEMA (JSON):
{{
    "intent": "string",
    "confidence": float (0.0 to 1.0),
    "needs_confirmation": boolean,
    "emotion": "string or null",
    "clarification_question": "string or null",
    "reasoning": "brief explanation of your choice"
}}
"""

    def __init__(self):
        self._config = Config()
        self._api_key = self._config.get("llm.api_key", os.environ.get("GEMINI_API_KEY"))
        self._model_name = self._config.get("llm.model_name", "gemini-1.5-flash")
        self._gen_model = None
        self._initialized = False
        logger.info("LLMEscalationAdvisor (Gemini API) initialized")

    def _initialize_gemini(self) -> bool:
        """Initialize the Gemini generative model."""
        if self._initialized:
            return True
            
        if not self._api_key:
            logger.error("[LLM-ADVISOR] Gemini API key not found in config or environment.")
            return False
            
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._gen_model = genai.GenerativeModel(
                model_name=self._model_name,
                system_instruction=self.SYSTEM_PROMPT
            )
            self._initialized = True
            return True
        except ImportError:
            logger.error("[LLM-ADVISOR] google-generativeai package missing. Run 'pip install google-generativeai'.")
            return False
        except Exception as e:
            logger.error(f"[LLM-ADVISOR] Failed to initialize Gemini API: {e}")
            return False

    def analyze(self, user_input: str, embedding_result: Optional[Dict[str, Any]] = None, 
                context: Optional[Dict[str, Any]] = None, language: str = "en", 
                reasoning_level: str = "standard", history: Optional[List[Dict[str, Any]]] = None, 
                watchdog: Optional[Any] = None) -> Dict[str, Any]:
        """
        Analyze user input and return a structured advisory result using Gemini API.
        """
        if reasoning_level == "shallow":
             return {"intent": "unknown", "confidence": 0.0, "needs_confirmation": False, "reasoning": "Reasoning skipped"}

        if not self._initialize_gemini():
            return self._get_fallback_result("Cognitive engines are temporarily unavailable due to initialization failure.")

        prompt = f"User Input: '{user_input}'\n"
        if language != "en":
            prompt += f"System Language: {language}\n"
        
        if history:
            prompt += "\nInteraction History:\n"
            for turn in history:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                prompt += f"- {role.upper()}: {content}\n"
        
        if reasoning_level == "deep":
            prompt += "\nReasoning Level: DEEP. Break down the problem step-by-step.\n"
        elif reasoning_level == "standard":
            prompt += "\nReasoning Level: STANDARD.\n"
            
        prompt += "\nRespond ONLY with the validated JSON object matching the schema."

        # Attempt generation with retry logic
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self._gen_model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
                )
                
                if not response or not response.text:
                    raise ValueError("Empty response from Gemini API")
                
                result = self._parse_and_validate_json(response.text)
                if result:
                    # Double-validate intent whitelist
                    if result.get("intent") not in SUPPORTED_INTENTS:
                        logger.warning(f"[LLM-ADVISOR] Unsupported intent: {result.get('intent')}. Forcing 'unknown'.")
                        result["intent"] = "unknown"
                        result["confidence"] = 0.0
                    return result
                
                logger.warning(f"[LLM-ADVISOR] JSON parse failed on attempt {attempt + 1}")
                time.sleep(1) # Brief backoff
                
            except Exception as e:
                logger.error(f"[LLM-ADVISOR] Gemini API call failed on attempt {attempt + 1}: {e}")
                time.sleep(1)

        if watchdog:
            watchdog.record_malformed_llm_output()
        return self._get_fallback_result("Cognitive engines are temporarily unavailable due to system resource limits or connectivity.")

    def _parse_and_validate_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Attempt to parse JSON and validate basic structure."""
        try:
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            
            required_keys = ["intent", "confidence", "needs_confirmation", "reasoning"]
            if all(k in data for k in required_keys):
                return data
            return None
        except json.JSONDecodeError:
            return None

    def _get_fallback_result(self, reason: str) -> Dict[str, Any]:
        """Safe fallback response when API fails."""
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "needs_confirmation": False,
            "clarification_question": None,
            "reasoning": reason,
            "emotion": None,
            "error": True
        }
