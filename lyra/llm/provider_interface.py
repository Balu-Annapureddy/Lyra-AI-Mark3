# -*- coding: utf-8 -*-
"""
Reasoning Provider Interface - Frozen v1.0
Defines the contract for all LLM reasoning backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

class ReasoningMode(Enum):
    """
    Discrete reasoning tasks for Lyra.
    DEAR DEVELOPER: Do NOT extend this enum at runtime.
    """
    INTENT_CLASSIFICATION = "intent_classification"
    PLAN_GENERATION = "plan_generation"
    GENERAL_QA = "general_qa"

class SchemaRegistry:
    """
    Central immutable registry for reasoning schemas.
    Frozen v1.5 - Cognition Integrity Locked.
    """
    _SCHEMAS = {
        ReasoningMode.INTENT_CLASSIFICATION: {
            "intent": "string",
            "confidence": "float",
            "reasoning": "string"
        },
        ReasoningMode.PLAN_GENERATION: {
            "steps": "list",
            "risk_summary": "string",
            "reasoning": "string"
        },
        ReasoningMode.GENERAL_QA: {}  # Free-form
    }

    _HASH = None
    _LOCKED = False

    @classmethod
    def _compute_hash(cls) -> str:
        """Compute canonical SHA256 hash of the schema registry."""
        import json
        import hashlib
        # Convert enum keys to strings for JSON stability
        serializable = {k.value: v for k, v in cls._SCHEMAS.items()}
        canonical = json.dumps(serializable, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    @classmethod
    def lock_registry(cls):
        """Standard boot-time lock. Returns the canonical hash."""
        if cls._LOCKED:
            return cls._HASH
        
        cls._HASH = cls._compute_hash()
        cls._LOCKED = True
        
        from lyra.core.logger import get_logger
        logger = get_logger(__name__)
        logger.info(f"[INTEGRITY] Cognition Schema Registry Locked. SHA256: {cls._HASH}")
        return cls._HASH

    @classmethod
    def get_schema(cls, mode: ReasoningMode) -> Dict[str, Any]:
        """Fetch a deep copy of the frozen schema"""
        import copy
        return copy.deepcopy(cls._SCHEMAS.get(mode, {}))

# Auto-lock on import to ensure integrity
SchemaRegistry.lock_registry()

@dataclass
class ReasoningRequest:
    """Standardized reasoning request across all providers"""
    prompt: str
    schema: Dict[str, Any]
    mode: ReasoningMode
    context_window: int = 1536 # Reduced for HP 14s (8GB RAM) stability
    temperature: float = 0.2
    max_tokens: int = 350 # Reduced for HP 14s stability
    trace_id: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)

class BaseReasoningProvider(ABC):
    """Abstract Base Class for LLM Reasoning Providers"""
    
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique name of the provider"""
        pass

    @abstractmethod
    def generate(self, request: ReasoningRequest) -> Dict[str, Any]:
        """Generate structured reasoning from the provider"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is currently available (e.g., service running)"""
        pass

    @abstractmethod
    def get_resource_usage(self) -> Dict[str, float]:
        """Return current resource usage metrics (e.g., memory)"""
        pass
