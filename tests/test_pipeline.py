# -*- coding: utf-8 -*-
"""
Lyra AI Core Test Suite
Tests pipeline initialization, intent detection, dry-run simulation, capability validation, and policy checks.
"""

import unittest
from lyra.core.pipeline import LyraPipeline
from lyra.reasoning.intent_detector import IntentDetector
from lyra.capabilities.capability_registry import CapabilityRegistry


class TestLyraPipeline(unittest.TestCase):

    def test_pipeline_initialization(self):
        """Verify that the Lyra pipeline initializes correctly and locks capability registry."""
        pipeline = LyraPipeline()
        self.assertIsNotNone(pipeline)
        self.assertTrue(pipeline.capability_registry._locked)

    def test_intent_detector_rule_matching(self):
        """Test intent detection for standard commands."""
        detector = IntentDetector()
        
        cmd = detector.detect_intent('create file notes.txt with content "Meeting notes"')
        self.assertEqual(cmd.intent, "write_file")
        self.assertEqual(cmd.entities.get("path"), "notes.txt")
        self.assertEqual(cmd.entities.get("content"), "Meeting notes")

        cmd_url = detector.detect_intent("open https://google.com")
        self.assertEqual(cmd_url.intent, "open_url")
        self.assertEqual(cmd_url.entities.get("url"), "https://google.com")

        cmd_app = detector.detect_intent("launch notepad")
        self.assertEqual(cmd_app.intent, "launch_app")
        self.assertEqual(cmd_app.entities.get("app_name"), "notepad")

    def test_dry_run_simulation(self):
        """Test simulate_command dry-run execution without modifying filesystem state."""
        pipeline = LyraPipeline()
        result = pipeline.simulate_command('create file test_dry_run.txt with content "Dry Run Test"')
        self.assertTrue(result.success)
        self.assertIsNotNone(result.output)
        self.assertGreater(len(result.output), 0)

    def test_capability_registry(self):
        """Test capability registry mapping and intent permission checks."""
        registry = CapabilityRegistry()
        registry.register_capability("FileSystemCapability", ["write_file", "read_file"], "HIGH")
        registry.lock()

        self.assertTrue(registry.is_intent_allowed("write_file"))
        self.assertFalse(registry.is_intent_allowed("unauthorized_action"))
        self.assertEqual(registry.get_capability_for_intent("write_file"), "FileSystemCapability")


if __name__ == "__main__":
    unittest.main()
