# -*- coding: utf-8 -*-
"""
Ollama Provider Adapter - Frozen v1.0
Connects Lyra to local Qwen 2.5 via Ollama API.
"""

import json
import requests
import psutil
from typing import Dict, Any, Optional
from lyra.llm.provider_interface import BaseReasoningProvider, ReasoningRequest
from lyra.core.logger import get_logger

class OllamaAdapter(BaseReasoningProvider):
    """
    Adapter for Local Ollama Inference.
    Optimized for Qwen 2.5 3B on 8GB RAM systems.
    """
    
    def __init__(self, model_name: str = "qwen2.5:3b", base_url: str = "http://localhost:11434"):
        self.logger = get_logger(__name__)
        self.model_name = model_name
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/generate"

    def provider_name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        """Check if Ollama service is reachable"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=1.0)
            if response.status_code == 200:
                # Optional: check if model_name is in tags
                models = response.json().get("models", [])
                return any(m["name"].startswith(self.model_name) for m in models)
            return False
        except Exception:
            return False

    def generate(self, request: ReasoningRequest) -> Dict[str, Any]:
        """
        Send request to Ollama with strict JSON enforcement.
        """
        payload = {
            "model": self.model_name,
            "prompt": request.prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
                "num_ctx": request.context_window
            }
        }

        try:
            # Note: Hard timeout is managed by ReasoningRouter, but we add a local safety buffer.
            response = requests.post(self.endpoint, json=payload, timeout=12.0)
            response.raise_for_status()
            
            data = response.json()
            response_text = data.get("response", "")
            
            # Parse and validate JSON result
            return self._parse_json(response_text)

        except requests.exceptions.Timeout:
            self.logger.error(f"[OLLAMA] Request timed out for trace {request.trace_id}")
            return {"error": True, "reason": "timeout"}
        except Exception as e:
            self.logger.error(f"[OLLAMA] Generation error: {e}")
            return {"error": True, "reason": str(e)}

    def get_resource_usage(self) -> Dict[str, float]:
        """Track process-level memory if possible (Ollama runs externally)"""
        # We generally track system-wide in Router, but can check for 'ollama' processes
        total_rss = 0.0
        for proc in psutil.process_iter(['name', 'memory_info']):
            if 'ollama' in proc.info['name'].lower():
                total_rss += proc.info['memory_info'].rss / (1024 * 1024)
        return {"memory_mb": total_rss}

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Robust JSON parsing for LLM output"""
        try:
            text = text.strip()
            # Handle markdown blocks if present despite 'format: json'
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except json.JSONDecodeError:
            self.logger.error(f"[OLLAMA] Failed to parse JSON: {text[:100]}...")
            return {"error": True, "reason": "malformed_json"}
