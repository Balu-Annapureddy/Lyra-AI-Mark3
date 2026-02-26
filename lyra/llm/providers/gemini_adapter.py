# -*- coding: utf-8 -*-
"""
Gemini Provider Adapter - Frozen v1.0
Connects Lyra to Google Gemini API for cloud fallback.
"""

import json
import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from lyra.llm.provider_interface import BaseReasoningProvider, ReasoningRequest
from lyra.core.config import Config
from lyra.core.logger import get_logger

class GeminiAdapter(BaseReasoningProvider):
    """
    Adapter for Google Gemini API reasoning.
    Used as primary fallback for complex or local-fail scenarios.
    """
    
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.logger = get_logger(__name__)
        self.config = Config()
        self.model_name = model_name
        self._api_key = self.config.get("llm.api_key") or os.environ.get("GEMINI_API_KEY")
        self._initialized = False
        self._model = None

    def provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        """Check if API key is present"""
        return bool(self._api_key)

    def _initialize(self):
        if not self._initialized:
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(self.model_name)
            self._initialized = True

    def generate(self, request: ReasoningRequest) -> Dict[str, Any]:
        """Call Gemini API"""
        self._initialize()
        
        try:
            # Combine history if available? (Future Phase)
            generation_config = {
                "temperature": request.temperature,
                "max_output_tokens": request.max_tokens,
                "response_mime_type": "application/json"
            }
            
            response = self._model.generate_content(
                request.prompt,
                generation_config=generation_config
            )
            
            if not response or not response.text:
                return {"error": True, "reason": "empty_response"}
                
            return self._parse_json(response.text)

        except Exception as e:
            self.logger.error(f"[GEMINI] Generation error: {e}")
            return {"error": True, "reason": str(e)}

    def get_resource_usage(self) -> Dict[str, float]:
        """Cloud provider usage is negligible locally"""
        return {"memory_mb": 0.0}

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return {"error": True, "reason": "malformed_json"}
