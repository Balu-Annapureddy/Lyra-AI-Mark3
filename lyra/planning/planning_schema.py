# -*- coding: utf-8 -*-
"""
lyra/planning/planning_schema.py
Phase 3+5: Deterministic Planning Schema
Defines the formal structure of execution plans and steps.
Phase 5: Tool version pinning (tool_version, tool_sha256).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib
import json
import uuid

@dataclass
class PlanStep:
    """
    Formal definition of a single execution step.
    Must match registered tool schemas.
    """
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    tool_version: str = ""  # Phase 5: Pinned tool version
    tool_sha256: str = ""  # Phase 5: Pinned tool identity hash
    input_schema: Dict[str, Any] = field(default_factory=dict)
    validated_input: Dict[str, Any] = field(default_factory=dict)
    expected_output_schema: Dict[str, Any] = field(default_factory=dict)
    step_risk: str = "LOW" # LOW, MEDIUM, HIGH, CRITICAL
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {"max_retries": 1})
    timeout_seconds: int = 30
    depends_on: List[str] = field(default_factory=list)
    description: str = ""

    def to_deterministic_string(self) -> str:
        """
        Returns a canonical JSON string for hashing.
        Phase 3.1: Includes all critical fields to prevent bypass.
        """
        data = {
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "tool_sha256": self.tool_sha256,
            "validated_input": self.validated_input,
            "depends_on": sorted(self.depends_on),
            "retry_policy": self.retry_policy,
            "timeout_seconds": self.timeout_seconds,
            "step_risk": self.step_risk
        }
        return json.dumps(data, sort_keys=True)

    def freeze(self):
        """Convert mutable fields to immutable counterparts."""
        self.depends_on = tuple(sorted(self.depends_on))
        self.validated_input = self._freeze_val(self.validated_input)
        self.retry_policy = self._freeze_val(self.retry_policy)

    def _freeze_val(self, v):
        if isinstance(v, dict):
            # Phase 3.1: Immutable protection while preserving dict API
            return {k: self._freeze_val(val) for k, val in v.items()}
        if isinstance(v, list):
            return tuple(self._freeze_val(val) for val in v)
        return v

@dataclass
class ExecutionPlan:
    """
    A full graph of execution steps derived from reasoning.
    Phase 3.1: Supports deep immutability and snapshot hashing.
    """
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    reasoning_id: str = ""
    risk_level: str = "LOW"
    steps: List[PlanStep] = field(default_factory=list)
    requires_confirmation: bool = False
    deterministic_hash: str = ""
    
    _frozen: bool = field(default=False, init=False, repr=False)
    _snapshot: str = field(default="", init=False, repr=False)

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False) and not name.startswith("_"):
            raise AttributeError(f"ExecutionPlan {self.plan_id} is frozen and immutable.")
        super().__setattr__(name, value)

    def compute_canonical_string(self) -> str:
        """Generates the full canonical string for the entire plan."""
        step_strings = [s.to_deterministic_string() for s in self.steps]
        return "|".join(step_strings)

    def compute_hash(self) -> str:
        """Computes SHA256 of the canonical string."""
        return hashlib.sha256(self.compute_canonical_string().encode()).hexdigest()

    def freeze(self):
        """
        Phase 3.1: Deep freeze the plan.
        1. Freeze all steps.
        2. Convert steps list to tuple.
        3. Store canonical snapshot.
        4. Compute and store hash.
        5. Set frozen flag.
        """
        if self._frozen:
            return
            
        # 1. Freeze individual steps
        for step in self.steps:
            step.freeze()
            
        # 2. Convert steps list to tuple
        self.steps = tuple(self.steps)
        
        # 3. Snapshot and Hash
        self._snapshot = self.compute_canonical_string()
        self.deterministic_hash = self.compute_hash()
        
        # 4. Finalize
        self._frozen = True

    def validate_integrity(self) -> bool:
        """
        Verifies that the plan matches its frozen snapshot and hash.
        """
        if not self._frozen:
            return True # Not yet frozen, still in planning
            
        current_snapshot = self.compute_canonical_string()
        current_hash = hashlib.sha256(current_snapshot.encode()).hexdigest()
        
        return current_snapshot == self._snapshot and current_hash == self.deterministic_hash
