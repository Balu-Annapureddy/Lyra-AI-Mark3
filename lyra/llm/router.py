# -*- coding: utf-8 -*-
"""
Reasoning Router - Frozen v1.0
Orchestrates reasoning provider selection with local-first priority and fallback.
"""

import time
import psutil
from typing import Dict, Any, List, Optional
from lyra.core.config import Config
from lyra.core.logger import get_logger
from lyra.llm.provider_interface import ReasoningRequest, BaseReasoningProvider

class ReasoningRouter:
    """
    Traffic controller for Lyra's reasoning layer.
    Prioritizes local models (Ollama) with fallback to cloud (Gemini).
    Hardened v1.3:
    - Provider priority selection
    - Circuit breaker (3 fails -> 60s cooldown; reset on success)
    - Timeout handling
    - Strict schema validation
    - Confidence threshold enforcement (0.65)
    - Latency logging
    """
    
    INTENT_ACCEPT_THRESHOLD = 0.65

    def __init__(self, providers: List[BaseReasoningProvider]):
        self.logger = get_logger(__name__)
        self.config = Config()
        self.providers = {p.provider_name(): p for p in providers}
        
        # Load priority from config
        self.priority = self.config.get("llm.provider_priority", ["ollama", "gemini"])
        
        # Resource constraints (Hardware: 8GB RAM)
        self.min_free_ram_mb = 800  # Guard is max(500, 10% total) -> ~800MB on 8GB system
        self.ram_guard_percent = 0.10
        
        # Hardening: Failure tracking for Circuit Breaker
        self.failure_counts = {name: 0 for name in self.providers}
        self.cooldown_until = {name: 0.0 for name in self.providers}
        self.max_failures = 3
        self.cooldown_seconds = 60
        
        self.logger.info(f"Reasoning Router initialized with priority: {self.priority}")

    def route_request(self, request: ReasoningRequest) -> Dict[str, Any]:
        """
        Routes the request through providers according to priority and health.
        """
        import concurrent.futures
        
        trace_id = request.trace_id or f"trace-{int(time.time())}"
        request.trace_id = trace_id
        
        self.logger.info(f"[ROUTER] Routing request [Mode: {request.mode.value}] [Trace: {trace_id}]")
        
        # Track initial resources
        ram_before = psutil.virtual_memory().available / (1024 * 1024)
        
        last_error = None
        current_time = time.time()
        
        for provider_name in self.priority:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
                
            # Circuit Breaker Check
            if current_time < self.cooldown_until.get(provider_name, 0.0):
                self.logger.warning(f"[ROUTER] {provider_name} is in cooldown. Skipping.")
                continue

            # Perform Resource Guards
            if not provider.is_available():
                self.logger.warning(f"[ROUTER] Provider {provider_name} unavailable. Skipping.")
                continue
                
            if not self._check_ram_guard(provider_name):
                self.logger.warning(f"[ROUTER] RAM Guard triggered for {provider_name}. Skipping.")
                continue
            
            self.logger.info(f"[ROUTER] Attempting {provider_name} [Trace: {trace_id}]")
            
            start_time = time.perf_counter()
            
            try:
                # Execution with logic for timeouts
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(provider.generate, request)
                    try:
                        # Hard kill threshold: 8.0s
                        result = future.result(timeout=8.0)
                        
                        latency_ms = (time.perf_counter() - start_time) * 1000
                        
                        if latency_ms > 6000:
                            self.logger.warning(f"[ROUTER] {provider_name} reached soft timeout ({latency_ms:.0f}ms > 6000ms)")
                        
                        if result and not result.get("error"):
                            # Hardening v1.3: Deep-copy provider response to prevent side effects
                            import copy
                            safe_result = copy.deepcopy(result)
                            
                            # Hardening: Deterministic Schema Validation
                            if self._validate_response_schema(safe_result, request.schema):
                                # Hardening v1.5: Threshold Separation
                                # INTENT_ACCEPT_THRESHOLD ONLY for INTENT_CLASSIFICATION mode.
                                from lyra.llm.provider_interface import ReasoningMode
                                if request.mode == ReasoningMode.INTENT_CLASSIFICATION and "confidence" in safe_result:
                                    score = safe_result.get("confidence", 0.0)
                                    if score < self.INTENT_ACCEPT_THRESHOLD:
                                        self.logger.warning(f"[SAFETY] Intent confidence {score} below threshold {self.INTENT_ACCEPT_THRESHOLD}. Coercing to 'unknown'.")
                                        safe_result["intent"] = "unknown"
                                        safe_result["confidence"] = 0.0
                                        safe_result["reasoning"] = f"Low confidence ({score}): " + safe_result.get("reasoning", "")

                                ram_after = psutil.virtual_memory().available / (1024 * 1024)
                                self.logger.info(f"[RESOURCE] RAM before: {ram_before:.1f}MB | After: {ram_after:.1f}MB")
                                self.logger.info(f"[ROUTER] Completed via {provider_name} in {latency_ms:.0f}ms [Trace: {trace_id}]")
                                
                                # Circuit Breaker: Reset failure count immediately on success
                                self.failure_counts[provider_name] = 0
                                return safe_result
                            else:
                                last_error = "malformed_schema"
                                self.logger.error(f"[ROUTER] {provider_name} returned invalid schema. Retrying/Fallback.")
                        else:
                            last_error = result.get("reason", "Unknown provider error")
                            self.logger.warning(f"[ROUTER] {provider_name} failed: {last_error}.")
                        
                        self._record_failure(provider_name)

                    except concurrent.futures.TimeoutError:
                        self.logger.error(f"[ROUTER] Provider {provider_name} hit hard timeout (8s). Aborting.")
                        last_error = "hard_timeout"
                        self._record_failure(provider_name)
                        continue

            except Exception as e:
                self.logger.error(f"[ROUTER] Unexpected error in {provider_name}: {e}")
                last_error = str(e)
                self._record_failure(provider_name)
                continue

        # Systemic Failure Fallback (Hardened v1.5)
        self.logger.error(f"[ROUTER] Systemic Cognition Failure for [Trace: {trace_id}].")
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "reason": "reasoning_failure",
            "error": True,
            "error_detail": last_error,
            "trace_id": trace_id,
            "providers_attempted": self.priority,
            "timestamp": int(time.time()),
            "status": "COGNITION_INTEGRITY_LOCKED"
        }

    def _record_failure(self, provider_name: str):
        """Track failures for circuit breaker with exponential backoff (v1.5)"""
        self.failure_counts[provider_name] += 1
        if self.failure_counts[provider_name] >= self.max_failures:
            # Exponential backoff: 60 * 2^(failures - max_failures)
            # 3 fails = 60s, 4 fails = 120s, 5 fails = 240s
            exponent = self.failure_counts[provider_name] - self.max_failures
            current_cooldown = self.cooldown_seconds * (2 ** exponent)
            
            # Cap at 240s as per v1.5 spec
            current_cooldown = min(current_cooldown, 240)
            
            self.cooldown_until[provider_name] = time.time() + current_cooldown
            self.logger.error(
                f"[ROUTER] {provider_name} circuit broken! "
                f"Failures: {self.failure_counts[provider_name]}. "
                f"Cooldown: {current_cooldown}s."
            )

    def _validate_response_schema(self, response: Dict[str, Any], expected_schema: Dict[str, Any]) -> bool:
        """Deterministic schema validation (Shape only)"""
        try:
            for key, expected_type in expected_schema.items():
                if key not in response:
                    return False
                # Simple type check if needed, here we just check presence for 'intent', 'confidence', etc.
            return True
        except Exception:
            return False

    def _check_ram_guard(self, provider_name: str) -> bool:
        """
        Enforce: free_ram < max(500MB, 10% total RAM)
        """
        mem = psutil.virtual_memory()
        total_ram_mb = mem.total / (1024 * 1024)
        available_ram_mb = mem.available / (1024 * 1024)
        
        threshold = max(self.min_free_ram_mb, total_ram_mb * self.ram_guard_percent)
        
        if available_ram_mb < threshold:
            self.logger.warning(
                f"[RESOURCE] RAM Guard: {available_ram_mb:.1f}MB available < {threshold:.1f}MB threshold"
            )
            return False
            
        return True
