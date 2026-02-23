# -*- coding: utf-8 -*-
"""
tests/test_integrity_watchdog.py
Phase F10: Self-Diagnostics & Integrity Watchdog Tests
"""

import unittest
from unittest.mock import MagicMock, patch
from lyra.core.integrity_watchdog import IntegrityWatchdog
from lyra.core.pipeline import LyraPipeline

class TestIntegrityWatchdog(unittest.TestCase):

    def setUp(self):
        self.watchdog = IntegrityWatchdog()

    def test_counter_increments(self):
        """Verify basic metric tracking."""
        self.watchdog.record_command()
        self.watchdog.record_escalation()
        self.watchdog.record_compression()
        self.watchdog.record_safety_violation()
        self.watchdog.record_execution_failure()
        self.watchdog.record_reasoning_level("deep")
        
        report = self.watchdog.generate_health_report()
        metrics = report["metrics"]
        
        self.assertEqual(metrics["commands"], 1)
        self.assertEqual(metrics["escalations"], 1)
        self.assertEqual(metrics["compression_events"], 1)
        self.assertEqual(metrics["safety_violations"], 1)
        self.assertEqual(metrics["execution_failures"], 1)
        self.assertEqual(metrics["reasoning_distribution"]["deep"], 1)

    def test_escalation_loop_detection(self):
        """Verify loop detection rule: 3+ consecutive same intent without success + not shallow."""
        # Turn 1: Advisory recommendation
        self.watchdog.record_command()
        self.watchdog.record_reasoning_level("standard")
        self.watchdog.detect_escalation_loop("run_script")
        
        # Turn 2: User retries, advisory repeat
        self.watchdog.record_command()
        self.watchdog.record_reasoning_level("standard")
        self.watchdog.detect_escalation_loop("run_script")
        
        # Turn 3: Still no success, third repeat
        self.watchdog.record_command()
        self.watchdog.record_reasoning_level("standard")
        self.watchdog.detect_escalation_loop("run_script")
        
        self.assertEqual(self.watchdog.escalation_loops_detected, 1)
        self.assertIn("Escalation loop detected", self.watchdog.generate_health_report()["anomalies"])

    def test_no_loop_on_shallow(self):
        """Verify SHALLOW reasoning ignores loops (false positive prevention)."""
        for _ in range(5):
            self.watchdog.record_command()
            self.watchdog.record_reasoning_level("shallow")
            self.watchdog.detect_escalation_loop("run_script")
            
        self.assertEqual(self.watchdog.escalation_loops_detected, 0)

    def test_no_loop_on_success(self):
        """Verify success breaks the loop."""
        # Turn 1: Advisory recommendation
        self.watchdog.record_command()
        self.watchdog.record_reasoning_level("standard")
        self.watchdog.detect_escalation_loop("run_script")
        self.watchdog.record_execution_success("run_script")
        
        # Turn 2: Repeat recommendation (but Turn 1 was successful)
        self.watchdog.record_command()
        self.watchdog.record_reasoning_level("standard")
        self.watchdog.detect_escalation_loop("run_script")
        
        # Turn 3: Repeat again
        self.watchdog.record_command()
        self.watchdog.record_reasoning_level("standard")
        self.watchdog.detect_escalation_loop("run_script")
        
        self.assertEqual(self.watchdog.escalation_loops_detected, 0)

    def test_malformed_llm_anomaly_rolling(self):
        """Verify malformed rates based on last 10 commands."""
        # 1-4: OK
        for _ in range(4):
            self.watchdog.record_command()
        
        # 5-8: Malformed
        for _ in range(4):
            self.watchdog.record_command()
            self.watchdog.record_malformed_llm_output()
            
        report = self.watchdog.generate_health_report()
        self.assertEqual(report["status"], "warning")
        self.assertIn("High malformed LLM rate (last 10 commands)", report["anomalies"])

        # Record 10 more commands (all OK)
        for _ in range(10):
            self.watchdog.record_command()
            
        report = self.watchdog.generate_health_report()
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(len(report["anomalies"]), 0)

    def test_status_transitions(self):
        """Verify healthy -> warning -> critical transitions."""
        self.assertEqual(self.watchdog.generate_health_report()["status"], "healthy")
        
        # Warning: Loops
        self.watchdog.escalation_loops_detected = 1
        self.assertEqual(self.watchdog.generate_health_report()["status"], "warning")
        
        # Critical: Safety
        for _ in range(6):
            self.watchdog.record_safety_violation()
        self.assertEqual(self.watchdog.generate_health_report()["status"], "critical")

    def test_pipeline_integration_hooks(self):
        """Verify pipeline actually calls the watchdog."""
        pipeline = LyraPipeline()
        
        # Mock advisor to simulate escalation
        with patch.object(pipeline.advisor, 'analyze') as mock_analyze:
            mock_analyze.return_value = {
                "intent": "create_file", 
                "confidence": 0.9, 
                "needs_confirmation": False, 
                "reasoning": "test"
            }
            # Trigger escalation with low confidence
            pipeline.process_command("create something", auto_confirm=True)
            
            report = pipeline.watchdog.generate_health_report()
            self.assertGreater(report["metrics"]["commands"], 0)
            self.assertGreater(report["metrics"]["escalations"], 0)
            self.assertIn("standard", report["metrics"]["reasoning_distribution"] or "deep")

if __name__ == "__main__":
    unittest.main()
