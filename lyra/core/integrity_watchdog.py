# -*- coding: utf-8 -*-
"""
lyra/core/integrity_watchdog.py
Phase F10: Self-Diagnostics & Integrity Watchdog (Subsystem N)
"""

from typing import List, Dict, Any, Optional
from collections import deque
from lyra.core.logger import get_logger

logger = get_logger(__name__)

class IntegrityWatchdog:
    """
    Monitors internal system health and detects anomalies.
    Purely event-driven, session-scoped.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all counters and state."""
        self.total_commands_processed = 0
        self.llm_escalations = 0
        self.reasoning_distribution = {
            "shallow": 0,
            "standard": 0,
            "deep": 0
        }
        self.compression_events = 0
        self.malformed_llm_outputs = 0
        self.safety_violations = 0
        self.escalation_loops_detected = 0
        self.execution_failures = 0
        
        # Rolling window for malformed outputs (last 10 commands)
        self._malformed_window = deque(maxlen=10)
        
        # Unified history for anomaly detection
        # Each entry: {"intent": str, "success": bool, "reasoning": str, "is_escalation": bool}
        self._history = []

    def record_command(self):
        """Record a new command processing start."""
        self.total_commands_processed += 1
        self._malformed_window.append(False)
        self._history.append({
            "intent": "unknown", 
            "success": False, 
            "reasoning": "shallow",
            "is_escalation": False
        })

    def record_reasoning_level(self, level: str):
        """Record chosen reasoning level."""
        level = level.lower()
        if level in self.reasoning_distribution:
            self.reasoning_distribution[level] += 1
        if self._history:
            self._history[-1]["reasoning"] = level

    def record_escalation(self):
        """Record an LLM escalation event."""
        self.llm_escalations += 1
        if self._history:
            self._history[-1]["is_escalation"] = True

    def record_compression(self):
        """Record a history compression event."""
        self.compression_events += 1

    def record_malformed_llm_output(self):
        """Record a malformed JSON/structure event from LLM."""
        self.malformed_llm_outputs += 1
        if self._malformed_window:
            self._malformed_window[-1] = True
        logger.warning(f"[WATCHDOG] Malformed LLM output detected. Session total: {self.malformed_llm_outputs}")

    def record_safety_violation(self):
        """Record a blocked safety violation."""
        self.safety_violations += 1
        logger.warning(f"[WATCHDOG] Safety violation recorded. Session total: {self.safety_violations}")

    def record_execution_failure(self):
        """Record a top-level execution exception."""
        self.execution_failures += 1
        if self._history:
            self._history[-1]["success"] = False

    def record_execution_success(self, intent: str):
        """Record a successful execution turn."""
        if self._history:
            self._history[-1]["intent"] = intent
            self._history[-1]["success"] = True

    def detect_escalation_loop(self, recommended_intent: str):
        """
        Detect if we are repeating the same advisory intent without success.
        Rule: 3+ consecutive same intent AND no success AND last_reasoning != SHALLOW.
        """
        if not self._history:
            return
            
        # Update current turn intent from advisor
        self._history[-1]["intent"] = recommended_intent
        
        # Check back 3 turns
        if len(self._history) < 3:
            return

        last_three = self._history[-3:]
        
        # Check if all 3 are the same intent
        intents = [h["intent"] for h in last_three]
        if len(set(intents)) == 1 and intents[0] != "unknown":
            # Check if any successfully executed
            if not any(h["success"] for h in last_three):
                # Check reasoning levels (only if at least one was not shallow)
                if any(h["reasoning"] != "shallow" for h in last_three):
                    self.escalation_loops_detected += 1
                    logger.error(f"[WATCHDOG] Escalation loop detected for intent: {recommended_intent}")

    def generate_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive health report."""
        anomalies = []
        
        # Malformed check (rolling window)
        malformed_rate = sum(self._malformed_window)
        if malformed_rate > 3:
            anomalies.append("High malformed LLM rate (last 10 commands)")
            
        if self.escalation_loops_detected > 0:
            anomalies.append("Escalation loop detected")
            
        if self.safety_violations > 0:
            anomalies.append(f"Safety violations detected ({self.safety_violations})")
            
        if self.execution_failures > 3:
            anomalies.append("Excessive execution failures")

        # Status logic
        status = "healthy"
        if self.safety_violations > 5 or self.malformed_llm_outputs > 6:
            status = "critical"
        elif malformed_rate > 3 or self.escalation_loops_detected > 0 or self.execution_failures > 3:
            status = "warning"
            
        return {
            "status": status,
            "metrics": {
                "commands": self.total_commands_processed,
                "escalations": self.llm_escalations,
                "compression_events": self.compression_events,
                "malformed_llm_outputs": self.malformed_llm_outputs,
                "safety_violations": self.safety_violations,
                "execution_failures": self.execution_failures,
                "reasoning_distribution": self.reasoning_distribution,
                "escalation_loops": self.escalation_loops_detected
            },
            "anomalies": anomalies
        }
