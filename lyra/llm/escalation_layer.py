import json
import time
import os
from typing import Dict, Any, Optional, List

from lyra.core.config import Config
from lyra.core.logger import get_logger
from lyra.execution.execution_gateway import SUPPORTED_INTENTS

logger = get_logger(__name__)

from lyra.llm.provider_interface import ReasoningRequest
from lyra.llm.router import ReasoningRouter
from lyra.llm.providers.ollama_adapter import OllamaAdapter
from lyra.llm.providers.gemini_adapter import GeminiAdapter

logger = get_logger(__name__)

class LLMEscalationAdvisor:
    """
    Advisor module that uses a ReasoningRouter to get structured reasoning.
    Phase 1 Stabilization: Local-first delegated reasoning.
    Hardened v1.3: Focused on business logic mapping; relies on Router for safety/schema.
    """
    
    SYSTEM_PROMPT = f"""You are Lyra AI Advisor. Recommend the most likely intent and parameters.
SUPPORTED INTENTS: {', '.join(SUPPORTED_INTENTS)}
RULES:
1. ONLY return valid JSON.
2. DO NOT invent new intents.
3. If no action, use 'conversation'.
"""

    def __init__(self):
        self._config = Config()
        
        # Initialize providers based on config if needed, here we use defaults
        ollama = OllamaAdapter(
            model_name=self._config.get("llm.ollama.model", "qwen2.5:3b")
        )
        gemini = GeminiAdapter(
            model_name=self._config.get("llm.gemini.model", "gemini-1.5-flash")
        )
        
        self.router = ReasoningRouter(providers=[ollama, gemini])
        logger.info("LLMEscalationAdvisor with Hardened ReasoningRouter initialized")

    def analyze(self, user_input: str, embedding_result: Optional[Dict[str, Any]] = None, 
                context: Optional[Dict[str, Any]] = None, language: str = "en", 
                reasoning_level: str = "standard", history: Optional[List[Dict[str, Any]]] = None, 
                watchdog: Optional[Any] = None) -> Dict[str, Any]:
        """
        Analyze user input via the ReasoningRouter with Hardening v1.3.
        """
        from lyra.llm.provider_interface import ReasoningMode, SchemaRegistry
        
        if reasoning_level == "shallow":
             return {"intent": "unknown", "confidence": 0.0, "reasoning": "Reasoning skipped"}

        # Construct request following Hardened Spec v1.3
        prompt = self._build_prompt(user_input, language, history, reasoning_level)
        
        # Determine Mode
        mode = ReasoningMode.INTENT_CLASSIFICATION if reasoning_level != "deep" else ReasoningMode.PLAN_GENERATION
        
        # Fetch frozen schema from central registry (Integrity Locked v1.3)
        schema = SchemaRegistry.get_schema(mode)
        
        request = ReasoningRequest(
            prompt=prompt,
            schema=schema,
            mode=mode,
            temperature=0.2 if reasoning_level == "standard" else 0.4,
            max_tokens=350,
            history=history or []
        )

        # Router performs selection, circuit breaking, timeout, schema validation, and confidence gating
        result = self.router.route_request(request)
        
        if result.get("error"):
            if watchdog:
                watchdog.record_malformed_llm_output()
            return self._get_fallback_result(result.get("reason", "Reasoning failure"))

        # Double-validate intent whitelist for safety (final sanity check)
        if result.get("intent") not in SUPPORTED_INTENTS:
            logger.warning(f"[LLM-ADVISOR] Unsupported intent: {result.get('intent')}. Forcing 'unknown'.")
            result["intent"] = "unknown"
            result["confidence"] = 0.0
            
        return result

    def _build_prompt(self, user_input: str, language: str, history: Optional[List[Dict[str, Any]]], level: str) -> str:
        prompt = self.SYSTEM_PROMPT + f"\nUser Input: '{user_input}'\n"
        if language != "en":
            prompt += f"System Language: {language}\n"
        
        if history:
            prompt += "\nHistory:\n"
            for turn in history[-5:]: # Limit to last 5 for context
                prompt += f"- {turn.get('role', 'user')}: {turn.get('content')}\n"
        
        if level == "deep":
            prompt += "\nReasoning: DEEP. Break down step-by-step.\n"
            
        prompt += "\nRespond ONLY with JSON matching the schema."
        return prompt

    def _get_fallback_result(self, reason: str) -> Dict[str, Any]:
        """Safe fallback response when routing fails."""
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "needs_confirmation": False,
            "reasoning": f"Reasoning failure: {reason}",
            "error": True
        }
