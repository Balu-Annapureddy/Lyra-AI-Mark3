# -*- coding: utf-8 -*-
"""
tests/test_execution_safety.py
Phase F4: Execution Safety Core Tests

Covers:
  - Supported intent whitelist validation
  - RiskLevel classification
  - HIGH risk confirmation requirements
  - CRITICAL risk blocking
  - LLM-bypass protection
  - Metadata propagation
  - UnsupportedIntentError
"""

import pytest
from unittest.mock import patch, MagicMock

from lyra.execution.execution_gateway import (
    ExecutionGateway,
    RiskLevel,
    SUPPORTED_INTENTS,
    INTENT_RISK_MAP,
    UnsupportedIntentError,
    ExecutionRequestResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_config():
    from lyra.core.config import Config
    Config._instance = None
    Config._config_data = {}
    yield
    Config._instance = None
    Config._config_data = {}


@pytest.fixture
def gateway():
    return ExecutionGateway()


# =====================================================================
# SUPPORTED_INTENTS & INTENT_RISK_MAP Constants
# =====================================================================

class TestConstants:

    def test_supported_intents_contains_expected(self):
        expected = {
            "create_file", "write_file", "delete_file", "read_file", "open_url",
            "launch_app", "search_web", "screen_read", "code_help",
            "conversation", "run_command", "get_status", "autonomous_goal",
        }
        assert SUPPORTED_INTENTS == expected

    def test_risk_map_covers_all_supported(self):
        for intent in SUPPORTED_INTENTS:
            assert intent in INTENT_RISK_MAP

    def test_risk_level_enum_values(self):
        assert RiskLevel.LOW.value == 1
        assert RiskLevel.MEDIUM.value == 2
        assert RiskLevel.HIGH.value == 3
        assert RiskLevel.CRITICAL.value == 4

    def test_delete_file_is_high_risk(self):
        assert INTENT_RISK_MAP["delete_file"] == RiskLevel.HIGH

    def test_create_file_is_low_risk(self):
        assert INTENT_RISK_MAP["create_file"] == RiskLevel.LOW

    def test_launch_app_is_medium_risk(self):
        assert INTENT_RISK_MAP["launch_app"] == RiskLevel.MEDIUM


# =====================================================================
# Unsupported Intent → Blocked
# =====================================================================

class TestUnsupportedIntent:

    def test_unsupported_intent_blocked(self, gateway):
        result = gateway.validate_execution_request(
            intent="install_package",
            params={},
            metadata={"source": "regex"},
        )
        assert not result.allowed
        assert result.risk_level == RiskLevel.CRITICAL
        assert "Unsupported" in result.reason

    def test_empty_intent_blocked(self, gateway):
        result = gateway.validate_execution_request(
            intent="",
            params={},
        )
        assert not result.allowed

    def test_hallucinated_intent_blocked(self, gateway):
        result = gateway.validate_execution_request(
            intent="format_hard_drive",
            params={},
            metadata={"source": "llm"},
        )
        assert not result.allowed
        assert result.risk_level == RiskLevel.CRITICAL

    def test_unsupported_intent_error_class(self):
        with pytest.raises(UnsupportedIntentError):
            raise UnsupportedIntentError("test_intent")


# =====================================================================
# Supported Intent → Allowed
# =====================================================================

class TestSupportedIntent:

    def test_create_file_allowed(self, gateway):
        result = gateway.validate_execution_request(
            intent="create_file",
            params={"filename": "test.txt"},
            metadata={"source": "embedding"},
        )
        assert result.allowed
        assert result.risk_level == RiskLevel.LOW
        assert not result.requires_confirmation

    def test_read_file_allowed(self, gateway):
        result = gateway.validate_execution_request(
            intent="read_file",
            params={"filepath": "test.txt"},
            metadata={"source": "semantic"},
        )
        assert result.allowed

    def test_conversation_allowed(self, gateway):
        result = gateway.validate_execution_request(
            intent="conversation",
            params={},
        )
        assert result.allowed

    def test_search_web_allowed(self, gateway):
        result = gateway.validate_execution_request(
            intent="search_web",
            params={"query": "python"},
            metadata={"source": "regex"},
        )
        assert result.allowed

    def test_screen_read_allowed(self, gateway):
        result = gateway.validate_execution_request(
            intent="screen_read",
            params={},
        )
        assert result.allowed
        assert result.risk_level == RiskLevel.MEDIUM


# =====================================================================
# HIGH Risk Without Confirmation → requires_confirmation=True
# =====================================================================

class TestHighRiskConfirmation:

    def test_delete_file_without_confirmation(self, gateway):
        result = gateway.validate_execution_request(
            intent="delete_file",
            params={"filepath": "/tmp/test.txt"},
            metadata={"source": "semantic", "confirmed": False},
        )
        assert not result.allowed
        assert result.risk_level == RiskLevel.HIGH
        assert result.requires_confirmation is True
        assert "confirmation" in result.reason.lower()

    def test_delete_file_with_confirmation(self, gateway):
        result = gateway.validate_execution_request(
            intent="delete_file",
            params={"filepath": "/tmp/test.txt"},
            metadata={"source": "semantic", "confirmed": True},
        )
        assert result.allowed
        assert result.risk_level == RiskLevel.HIGH
        assert not result.requires_confirmation

    def test_delete_file_no_metadata(self, gateway):
        """No metadata → no confirmation → blocked."""
        result = gateway.validate_execution_request(
            intent="delete_file",
            params={"filepath": "/tmp/test.txt"},
        )
        assert not result.allowed
        assert result.requires_confirmation is True


# =====================================================================
# CRITICAL Intent → Always Blocked
# =====================================================================

class TestCriticalBlocked:

    def test_unknown_intent_maps_to_critical(self, gateway):
        """Intent in whitelist but not in risk map → CRITICAL."""
        # Simulate by temporarily adding a supported intent without risk mapping
        original = SUPPORTED_INTENTS.copy()
        SUPPORTED_INTENTS.add("_test_critical_intent")
        try:
            result = gateway.validate_execution_request(
                intent="_test_critical_intent",
                params={},
                metadata={"source": "regex", "confirmed": True},
            )
            assert not result.allowed
            assert result.risk_level == RiskLevel.CRITICAL
            assert "CRITICAL" in result.reason
        finally:
            SUPPORTED_INTENTS.discard("_test_critical_intent")

    def test_unsupported_is_critical(self, gateway):
        result = gateway.validate_execution_request(
            intent="sudo_rm_rf",
            params={},
            metadata={"source": "regex", "confirmed": True},
        )
        assert not result.allowed
        assert result.risk_level == RiskLevel.CRITICAL


# =====================================================================
# LLM-Source Unsupported Intent → Blocked
# =====================================================================

class TestLLMBypassProtection:

    def test_llm_unsupported_intent_blocked(self, gateway):
        result = gateway.validate_execution_request(
            intent="execute_arbitrary_code",
            params={"code": "os.system('rm -rf /')"},
            metadata={"source": "llm"},
        )
        assert not result.allowed
        assert result.risk_level == RiskLevel.CRITICAL

    def test_llm_high_risk_without_confirmation_blocked(self, gateway):
        result = gateway.validate_execution_request(
            intent="delete_file",
            params={"filepath": "/tmp/test.txt"},
            metadata={"source": "llm", "confirmed": False},
        )
        assert not result.allowed
        assert result.requires_confirmation is True
        assert "LLM" in result.reason

    def test_llm_high_risk_with_confirmation_allowed(self, gateway):
        result = gateway.validate_execution_request(
            intent="delete_file",
            params={"filepath": "/tmp/test.txt"},
            metadata={"source": "llm", "confirmed": True, "semantic_valid": True},
        )
        assert result.allowed

    def test_llm_semantic_not_valid_blocked(self, gateway):
        result = gateway.validate_execution_request(
            intent="create_file",
            params={"filename": "test.txt"},
            metadata={"source": "llm", "semantic_valid": False},
        )
        assert not result.allowed
        assert "semantic validation" in result.reason.lower()

    def test_llm_low_risk_valid_allowed(self, gateway):
        result = gateway.validate_execution_request(
            intent="read_file",
            params={"filepath": "test.txt"},
            metadata={"source": "llm", "semantic_valid": True},
        )
        assert result.allowed

    def test_llm_medium_risk_valid_allowed(self, gateway):
        result = gateway.validate_execution_request(
            intent="open_url",
            params={"url": "https://example.com"},
            metadata={"source": "llm", "semantic_valid": True},
        )
        assert result.allowed


# =====================================================================
# Metadata Propagation
# =====================================================================

class TestMetadataPropagation:

    def test_no_metadata_defaults(self, gateway):
        """No metadata → defaults to source=unknown, confirmed=False."""
        result = gateway.validate_execution_request(
            intent="create_file",
            params={"filename": "test.txt"},
        )
        assert result.allowed  # LOW risk, no confirmation needed

    def test_metadata_source_embedding(self, gateway):
        result = gateway.validate_execution_request(
            intent="create_file",
            params={"filename": "test.txt"},
            metadata={"source": "embedding"},
        )
        assert result.allowed

    def test_metadata_source_regex(self, gateway):
        result = gateway.validate_execution_request(
            intent="open_url",
            params={"url": "https://example.com"},
            metadata={"source": "regex"},
        )
        assert result.allowed

    def test_metadata_confirmed_propagates(self, gateway):
        result = gateway.validate_execution_request(
            intent="delete_file",
            params={"filepath": "/tmp/x.txt"},
            metadata={"source": "embedding", "confirmed": True},
        )
        assert result.allowed
        assert result.risk_level == RiskLevel.HIGH


# =====================================================================
# Backward Compatibility
# =====================================================================

class TestBackwardCompat:

    def test_execution_request_result_dataclass(self):
        r = ExecutionRequestResult(
            allowed=True,
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
        )
        assert r.allowed is True
        assert r.reason is None

    def test_gateway_still_has_execute_plan(self, gateway):
        assert hasattr(gateway, "execute_plan")

    def test_gateway_still_has_validate_step(self, gateway):
        assert hasattr(gateway, "validate_step")

    def test_gateway_still_has_panic_stop(self, gateway):
        assert hasattr(gateway, "panic_stop")
        assert hasattr(gateway, "resume_execution")
        assert hasattr(gateway, "is_panic_stopped")
