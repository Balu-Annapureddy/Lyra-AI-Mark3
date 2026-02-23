# -*- coding: utf-8 -*-
"""
lyra/policy/policy_engine.py
Phase X1: Capability & Policy Framework
"""

from typing import Any, Optional
from lyra.capabilities.capability_registry import CapabilityRegistry
from lyra.execution.execution_gateway import RiskLevel
from lyra.core.logger import get_logger

logger = get_logger(__name__)

class PolicyViolationException(Exception):
    """Raised when an execution violates system policy."""
    pass

class PolicyEngine:
    """
    Validates system policies and enforces capability boundaries.
    """

    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        self.registry = registry or CapabilityRegistry()
        self._risk_mapping = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4
        }

    def _get_risk_score(self, risk: Any) -> int:
        """Convert RiskLevel enum or string to integer score."""
        if hasattr(risk, "name"):
            name = risk.name
        else:
            name = str(risk).upper()
        return self._risk_mapping.get(name, 0)

    def validate(self, intent: str, risk_level: Any):
        """
        Validate that an intent is allowed and within risk boundaries.
        
        Rules:
        1. Intent must be registered in a capability.
        2. Command risk_level <= capability max_risk.
        
        Raises:
            PolicyViolationException: If validation fails.
        """
        # 1. Explicit intent check
        if not self.registry.is_intent_allowed(intent):
            logger.error(f"[POLICY] Blocked: Intent '{intent}' not registered in any capability.")
            raise PolicyViolationException(f"Intent '{intent}' not registered in any capability.")

        # 2. Capability existence
        cap_name = self.registry.get_capability_for_intent(intent)
        max_risk_str = self.registry.get_max_risk_for_intent(intent)

        if not cap_name or not max_risk_str:
            logger.error(f"[POLICY] Blocked: No capability configuration found for {intent}")
            raise PolicyViolationException(f"System configuration error: No capability for {intent}")

        # 3. Risk Level Check
        current_score = self._get_risk_score(risk_level)
        max_score = self._get_risk_score(max_risk_str)

        if current_score > max_score:
            logger.error(
                f"[POLICY] Blocked: Intent '{intent}' (Risk: {risk_level}) "
                f"exceeds capability '{cap_name}' max risk ({max_risk_str})"
            )
            raise PolicyViolationException(
                f"Risk level {risk_level} exceeds allowed limit ({max_risk_str}) for {cap_name}."
            )

        logger.info(f"[POLICY] Validated: {intent} (Risk: {risk_level}) is allowed under {cap_name}")
        return True
