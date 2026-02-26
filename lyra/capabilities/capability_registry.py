# -*- coding: utf-8 -*-
"""
lyra/capabilities/capability_registry.py
Phase X1: Capability & Policy Framework
"""

from typing import List, Dict, Any, Optional

class CapabilityRegistrationError(Exception):
    """Raised when an intent is registered to multiple capabilities."""
    pass

class CapabilityRegistry:
    """
    Registry for system capabilities and their allowed intents.
    Enforces single ownership of intents.
    """

    def __init__(self):
        self._capabilities = {}  # name -> {allowed_intents, max_risk}
        self._intent_to_capability = {} # intent -> capability_name
        self._locked = False

    def lock(self):
        """Lock the registry to prevent further modifications."""
        self._locked = True

    def register_capability(self, name: str, allowed_intents: List[str], max_risk: str):
        """
        Register a new capability.
        """
        if self._locked:
            raise RuntimeError("CapabilityRegistry is locked and cannot be modified.")

        for intent in allowed_intents:
            if intent in self._intent_to_capability:
                existing = self._intent_to_capability[intent]
                if existing != name:
                    raise CapabilityRegistrationError(
                        f"Intent '{intent}' is already mapped to capability '{existing}'"
                    )

        self._capabilities[name] = {
            "allowed_intents": set(allowed_intents),
            "max_risk": max_risk.upper()
        }

        for intent in allowed_intents:
            self._intent_to_capability[intent] = name

    def get_capability_for_intent(self, intent: str) -> Optional[str]:
        """Return the name of the capability governing this intent."""
        return self._intent_to_capability.get(intent)

    def is_intent_allowed(self, intent: str) -> bool:
        """Check if an intent is registered in any capability."""
        return intent in self._intent_to_capability

    def get_max_risk_for_intent(self, intent: str) -> Optional[str]:
        """Return max risk level allowed for an intent's capability."""
        cap_name = self.get_capability_for_intent(intent)
        if cap_name:
            return self._capabilities[cap_name]["max_risk"]
        return None
