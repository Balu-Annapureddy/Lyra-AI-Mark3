# -*- coding: utf-8 -*-
"""
lyra/safety/safety_policy_registry.py
Phase 4: Safety Governance Layer — Hardened v1.3
Defines structured safety rules for tools and enforcement policies.
Integrity-locked at boot via SHA256 hash.
"""

import json
import hashlib
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from lyra.core.logger import get_logger

class ConfirmationLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class SafetyPolicy:
    """Structured safety metadata for a tool."""
    tool_name: str
    reversible: bool = False
    rollback_strategy: Optional[str] = None  # Reference to a rollback function/method
    confirmation_required_level: ConfirmationLevel = ConfirmationLevel.LOW
    destructive: bool = False
    requires_sandbox: bool = False
    pre_state_capture: Optional[str] = None  # Reference to a state capture method
    resource_locks: list = field(default_factory=list)  # Phase 5: declared resource locks
    cpu_cost: int = 1  # Phase 6: Resource cost (1-100)
    memory_cost: int = 1 # Phase 6: Memory overhead (1-100)
    network_cost: int = 0 # Phase 6: External network usage (1-100)
    risk_weight: int = 1 # Phase 6: Impact multiplier for risk calculations

class SafetyPolicyRegistry:
    """
    Registry for hardware and system safety policies.
    No tool may exist without a safety policy.
    
    Hardened v1.3:
    - Immutable post-initialization
    - SHA256 hashed at boot
    - Logged via [SAFETY-POLICY-LOCK]
    - Missing policy = system refuses to proceed
    """
    def __init__(self, lock_on_init: bool = True):
        self.logger = get_logger(__name__)
        self._policies: Dict[str, SafetyPolicy] = {}
        self._hash: Optional[str] = None
        self._locked: bool = False
        self._initialize_default_policies()
        if lock_on_init:
            self.lock_registry()

    def _initialize_default_policies(self):
        """Initialize policies for core Lyra tools."""
        defaults = [
            SafetyPolicy(
                tool_name="read_file",
                reversible=True,
                confirmation_required_level=ConfirmationLevel.LOW,
                destructive=False,
                requires_sandbox=False
            ),
            SafetyPolicy(
                tool_name="write_file",
                reversible=True,
                rollback_strategy="restore_backup",
                pre_state_capture="capture_file_content",
                confirmation_required_level=ConfirmationLevel.MEDIUM,
                destructive=True,
                requires_sandbox=True
            ),
            SafetyPolicy(
                tool_name="delete_file",
                reversible=False,
                confirmation_required_level=ConfirmationLevel.HIGH,
                destructive=True,
                resource_locks=["file_system", "system_state"],
                cpu_cost=5,
                memory_cost=5,
                network_cost=0,
                risk_weight=10
            ),
            SafetyPolicy(
                tool_name="run_command",
                reversible=False,
                confirmation_required_level=ConfirmationLevel.CRITICAL,
                destructive=True,
                requires_sandbox=True,
                resource_locks=["shell", "system_processes"],
                cpu_cost=50,
                memory_cost=30,
                network_cost=10,
                risk_weight=20
            ),
            SafetyPolicy(
                tool_name="get_system_info",
                reversible=True,
                confirmation_required_level=ConfirmationLevel.LOW,
                destructive=False,
                requires_sandbox=False,
                resource_locks=["system_info"],
                cpu_cost=2,
                memory_cost=5,
                network_cost=0,
                risk_weight=1
            ),
            SafetyPolicy(
                tool_name="open_url",
                reversible=True,
                confirmation_required_level=ConfirmationLevel.LOW,
                destructive=False,
                requires_sandbox=False,
                resource_locks=["network"],
                cpu_cost=10,
                memory_cost=50,
                network_cost=80,
                risk_weight=5
            ),
            SafetyPolicy(
                tool_name="launch_app",
                reversible=True,
                confirmation_required_level=ConfirmationLevel.MEDIUM,
                destructive=False,
                requires_sandbox=False,
                resource_locks=["application_state", "system_info"],
                cpu_cost=30,
                memory_cost=60,
                network_cost=0,
                risk_weight=10
            ),
            SafetyPolicy(
                tool_name="install_software",
                reversible=False,
                confirmation_required_level=ConfirmationLevel.HIGH,
                destructive=False,
                requires_sandbox=False,
                resource_locks=["system_processes", "disk"],
                cpu_cost=40,
                memory_cost=50,
                network_cost=100,
                risk_weight=15
            ),
            SafetyPolicy(
                tool_name="change_config",
                reversible=True,
                rollback_strategy="restore_config",
                pre_state_capture="capture_config_value",
                confirmation_required_level=ConfirmationLevel.MEDIUM,
                destructive=True,
                requires_sandbox=False
            ),
            SafetyPolicy(
                tool_name="search_web",
                reversible=True,
                confirmation_required_level=ConfirmationLevel.LOW,
                destructive=False,
                requires_sandbox=False
            ),
            SafetyPolicy(
                tool_name="screen_read",
                reversible=True,
                confirmation_required_level=ConfirmationLevel.LOW,
                destructive=False,
                requires_sandbox=False
            ),
            SafetyPolicy(
                tool_name="code_help",
                reversible=True,
                confirmation_required_level=ConfirmationLevel.LOW,
                destructive=False,
                requires_sandbox=False
            ),
            SafetyPolicy(
                tool_name="create_file",
                reversible=True,
                rollback_strategy="delete_created_file",
                confirmation_required_level=ConfirmationLevel.MEDIUM,
                destructive=False,
                requires_sandbox=False,
                resource_locks=["file_system"],
                cpu_cost=5,
                memory_cost=10,
                network_cost=0,
                risk_weight=1
            ),
            SafetyPolicy(
                tool_name="get_status",
                reversible=True,
                confirmation_required_level=ConfirmationLevel.LOW,
                destructive=False,
                requires_sandbox=False
            ),
            SafetyPolicy(
                tool_name="conversation",
                reversible=True,
                confirmation_required_level=ConfirmationLevel.LOW,
                destructive=False,
                requires_sandbox=False
            ),
            SafetyPolicy(
                tool_name="autonomous_goal",
                reversible=False,
                confirmation_required_level=ConfirmationLevel.HIGH,
                destructive=True,
                requires_sandbox=True
            ),
        ]
        
        for p in defaults:
            self._policies[p.tool_name] = p

    def lock_registry(self):
        """Compute SHA256 hash and lock the registry. No mutations allowed after this."""
        serializable = {}
        for name, policy in sorted(self._policies.items()):
            serializable[name] = {
                "reversible": policy.reversible,
                "destructive": policy.destructive,
                "confirmation_required_level": policy.confirmation_required_level.value,
                "requires_sandbox": policy.requires_sandbox,
                "rollback_strategy": policy.rollback_strategy,
                "pre_state_capture": policy.pre_state_capture,
            }
        
        canonical = json.dumps(serializable, sort_keys=True)
        self._hash = hashlib.sha256(canonical.encode()).hexdigest()
        self._locked = True
        
        self.logger.info(
            f"[SAFETY-POLICY-LOCK] Registry locked with {len(self._policies)} policies. "
            f"SHA256: {self._hash}"
        )

    def register_policy(self, policy: SafetyPolicy):
        """Register a new safety policy. Blocked after lock."""
        if self._locked:
            self.logger.error(
                f"[SAFETY-VIOLATION] Attempted to register policy for '{policy.tool_name}' "
                f"after registry lock. REJECTED."
            )
            raise RuntimeError(
                f"SafetyPolicyRegistry is locked. Cannot register '{policy.tool_name}' at runtime."
            )
        self._policies[policy.tool_name] = policy
        self.logger.debug(f"Registered safety policy for tool: {policy.tool_name}")

    def get_policy(self, tool_name: str) -> SafetyPolicy:
        """
        Retrieve policy for a tool.
        Hardened v1.3: Missing policy = system refuses to proceed.
        """
        if tool_name not in self._policies:
            self.logger.error(
                f"[SAFETY-VIOLATION] Tool '{tool_name}' has NO safety policy. "
                f"Execution REFUSED. Register policy before use."
            )
            raise RuntimeError(
                f"No safety policy registered for tool '{tool_name}'. "
                f"System refuses to execute un-governed tools."
            )
        return self._policies[tool_name]

    def has_policy(self, tool_name: str) -> bool:
        """Check if a tool has a registered safety policy."""
        return tool_name in self._policies

    def get_registry_hash(self) -> Optional[str]:
        """Return the SHA256 hash of the locked registry."""
        return self._hash

    def list_policies(self) -> Dict[str, SafetyPolicy]:
        """List all registered policies."""
        return self._policies.copy()
