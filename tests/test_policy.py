# -*- coding: utf-8 -*-
"""
Lyra AI Policy & Safety Test Suite
Tests security policy enforcement, risk scoring, locked registry checks, and unauthorized tool invocation prevention.
"""

import unittest
from lyra.core.pipeline import LyraPipeline
from lyra.execution.execution_gateway import ExecutionGateway, RiskLevel
from lyra.capabilities.capability_registry import CapabilityRegistry


class TestLyraPolicyAndSafety(unittest.TestCase):

    def setUp(self):
        self.pipeline = LyraPipeline()
        self.gateway = ExecutionGateway()

    def test_unregistered_intent_blocking(self):
        """Verify that unauthorized or unregistered intents are blocked by capability registry."""
        registry = CapabilityRegistry()
        registry.register_capability("CoreCapability", ["read_file"], "LOW")
        registry.lock()

        self.assertFalse(registry.is_intent_allowed("format_disk"))
        self.assertFalse(registry.is_intent_allowed("exfiltrate_data"))

    def test_execution_gateway_validation(self):
        """Verify that execution gateway validates whitelisted intents and risk levels."""
        res_allowed = self.gateway.validate_execution_request("read_file", {"path": "test.txt"})
        self.assertTrue(res_allowed.allowed)
        self.assertEqual(res_allowed.risk_level, RiskLevel.LOW)

        res_unsupported = self.gateway.validate_execution_request("malicious_unsupported_cmd", {})
        self.assertFalse(res_unsupported.allowed)
        self.assertEqual(res_unsupported.risk_level, RiskLevel.CRITICAL)


if __name__ == "__main__":
    unittest.main()
