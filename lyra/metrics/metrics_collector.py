# -*- coding: utf-8 -*-
"""
lyra/metrics/metrics_collector.py
Phase 6G: Internal Decision Metrics & Telemetry
Lightweight, in-memory performance and behavioral tracking.
"""

from typing import Dict, Any, List
import time

class MetricsCollector:
    """
    Collects internal decision metrics.
    Storage strictly in-memory.
    Uses running averages for O(1) space complexity.
    """
    
    def __init__(self):
        self._reset()
        
    def _reset(self):
        # Counters
        self.counters: Dict[str, int] = {
            "total_commands": 0,
            "semantic_calls": 0,
            "refinement_calls": 0,
            "clarification_triggers": 0,
            "clarification_failures": 0,
            "multi_intent_chains": 0,
            "memory_resolutions": 0,
            "normalization_applied": 0,
            "conversation_adjustments": 0,
            "tone_detected": 0
        }
        
        # Latency Trackers (Running Average)
        # Store (current_avg, count)
        self.latencies: Dict[str, Dict[str, float]] = {
            "semantic": {"avg": 0.0, "count": 0.0},
            "total":    {"avg": 0.0, "count": 0.0}
        }
        
        # Decision Source Breakdown
        self.decision_sources: Dict[str, int] = {
            "semantic": 0,
            "regex": 0,
            "refinement": 0,
            "clarification": 0,
            "unknown": 0
        }

    def increment(self, counter_name: str):
        """Increment a standard counter"""
        if counter_name in self.counters:
            self.counters[counter_name] += 1

    def increment_decision_source(self, source: str):
        """Increment decision source counter"""
        key = source.lower() if source else "unknown"
        if key not in self.decision_sources:
            self.decision_sources[key] = 0
        self.decision_sources[key] += 1

    def record_latency(self, metric_name: str, duration_ms: float):
        """
        Update running average latency.
        Formula: new_avg = (old_avg * count + new_value) / (count + 1)
        """
        if metric_name not in self.latencies:
            return
            
        tracker = self.latencies[metric_name]
        old_avg = tracker["avg"]
        count = tracker["count"]
        
        new_count = count + 1
        new_avg = (old_avg * count + duration_ms) / new_count
        
        tracker["avg"] = new_avg
        tracker["count"] = new_count

    def get_report(self) -> str:
        """Format metrics for CLI display"""
        report = []
        report.append("Lyra Internal Metrics:")
        report.append("-" * 30)
        
        # Counters
        report.append(f"Total Commands:       {self.counters['total_commands']}")
        report.append(f"Semantic Calls:       {self.counters['semantic_calls']}")
        report.append(f"Refinement Calls:     {self.counters['refinement_calls']}")
        report.append(f"Clarifications:       {self.counters['clarification_triggers']}")
        report.append(f"Clarification Fails:  {self.counters['clarification_failures']}")
        report.append(f"Multi-Intent Chains:  {self.counters['multi_intent_chains']}")
        report.append(f"Memory Resolutions:   {self.counters['memory_resolutions']}")
        report.append(f"Normalization Applied:{self.counters['normalization_applied']}")
        report.append(f"Conv. Adjustments:    {self.counters['conversation_adjustments']}")
        report.append(f"Tone Detected:        {self.counters['tone_detected']}")

        
        report.append("-" * 30)
        
        # Latency
        sem_lat = self.latencies["semantic"]["avg"]
        tot_lat = self.latencies["total"]["avg"]
        report.append(f"Avg Semantic Latency: {sem_lat:.2f} ms")
        report.append(f"Avg Total Latency:    {tot_lat:.2f} ms")
        
        report.append("-" * 30)
        
        # Decision Sources
        report.append("Decision Sources:")
        for source, count in self.decision_sources.items():
            report.append(f"  {source}: {count}")
            
        return "\n".join(report)

    def reset(self):
        """Reset all metrics"""
        self._reset()
