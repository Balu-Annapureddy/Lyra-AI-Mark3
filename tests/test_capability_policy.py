# -*- coding: utf-8 -*-
"""
tests/test_capability_policy.py
Phase X1: Capability & Policy Framework Tests
"""

import unittest
from unittest.mock import MagicMock, patch
from lyra.capabilities.capability_registry import CapabilityRegistry, CapabilityRegistrationError
from lyra.policy.policy_engine import PolicyEngine, PolicyViolationException
from lyra.execution.execution_gateway import RiskLevel
from lyra.core.pipeline import LyraPipeline

class TestCapabilityPolicy(unittest.TestCase):

    def setUp(self):
        self.registry = CapabilityRegistry()
        self.policy = PolicyEngine(self.registry)

    def test_registration_and_mapping(self):
        """Verify registration and lookup."""
        self.registry.register_capability(
            "TestCap", ["test_intent"], "MEDIUM"
        )
        self.assertTrue(self.registry.is_intent_allowed("test_intent"))
        self.assertEqual(self.registry.get_capability_for_intent("test_intent"), "TestCap")
        self.assertEqual(self.registry.get_max_risk_for_intent("test_intent"), "MEDIUM")

    def test_duplicate_intent_registration(self):
        """Verify single ownership enforcement."""
        self.registry.register_capability("CapA", ["intent1"], "LOW")
        with self.assertRaises(CapabilityRegistrationError):
            self.registry.register_capability("CapB", ["intent1"], "HIGH")

    def test_policy_validation_success(self):
        """Verify valid intent/risk combinations."""
        self.registry.register_capability("CapA", ["intent1"], "MEDIUM")
        
        # Risk LOW <= MEDIUM
        self.assertTrue(self.policy.validate("intent1", RiskLevel.LOW))
        # Risk MEDIUM <= MEDIUM
        self.assertTrue(self.policy.validate("intent1", RiskLevel.MEDIUM))

    def test_policy_rejection_unknown_intent(self):
        """Verify rejection of unregistered intents."""
        with self.assertRaises(PolicyViolationException) as cm:
            self.policy.validate("mystery_intent", RiskLevel.LOW)
        self.assertIn("not registered", str(cm.exception))

    def test_policy_rejection_high_risk(self):
        """Verify rejection when risk exceeds capability limit."""
        self.registry.register_capability("LowCap", ["chat"], "LOW")
        
        with self.assertRaises(PolicyViolationException) as cm:
            self.policy.validate("chat", RiskLevel.HIGH)
        self.assertIn("exceeds allowed limit", str(cm.exception))

    def test_pipeline_policy_blocking(self):
        """Verify pipeline aborts execution on policy violation."""
        pipeline = LyraPipeline()
        # 'create_file' is in FileSystemCapability (Max Risk: HIGH)
        # Mock safety gate to return CRITICAL (which is > HIGH)
        
        with patch.object(pipeline.gateway, 'validate_execution_request') as mock_gate:
            mock_gate.return_value = MagicMock(
                allowed=True, # Safety gate allows it
                risk_level=RiskLevel.CRITICAL, # But risk is CRITICAL
                requires_confirmation=False
            )
            
            # Process command that triggers 'create_file'
            # (assuming 'create file test.txt' maps to 'create_file')
            with patch.object(pipeline.embedding_router, 'classify') as mock_classify:
                 mock_classify.return_value = {"intent": "create_file", "confidence": 0.9}
                 
                 result = pipeline.process_command("create file test.txt")
                 
                 self.assertFalse(result.success)
                 self.assertEqual(result.error, "Policy Violation")
                 # Verify it was recorded in watchdog
                 self.assertGreater(pipeline.watchdog.generate_health_report()["metrics"]["safety_violations"], 0)

if __name__ == "__main__":
    unittest.main()
