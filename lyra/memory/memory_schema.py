# -*- coding: utf-8 -*-
"""
lyra/memory/memory_schema.py
Phase 2: Structured Memory Schema v1
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

class MemorySource(Enum):
    USER = "user"
    SYSTEM = "system"
    LEARNED = "learned"

class MemoryType(Enum):
    USER_PREFERENCE = "user_preference"
    LEARNED_PROCEDURE = "learned_procedure"
    TASK_HISTORY = "task_history"
    CONTEXT_SUMMARY = "context_summary"
    GOAL_MEMORY = "goal_memory"
    PLAN_OUTCOME_MEMORY = "plan_outcome_memory"
    PERFORMANCE_METRICS = "performance_metrics"

@dataclass
class MemoryEntry:
    """
    Standardized entry for Lyra's structured memory.
    Ensures queryability, versioning, and governance.
    """
    id: str
    content: Dict[str, Any]
    source: MemorySource
    memory_type: MemoryType = MemoryType.TASK_HISTORY
    priority: int = 3 # 1 (lowest) to 5 (highest)
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    version: int = 1
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    approval_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source.value,
            "memory_type": self.memory_type.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "version": self.version,
            "tags": self.tags,
            "metadata": self.metadata,
            "approval_required": self.approval_required
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        return cls(
            id=data["id"],
            content=data["content"],
            source=MemorySource(data["source"]),
            memory_type=MemoryType(data.get("memory_type", "task_history")),
            priority=data.get("priority", 3),
            created_at=data.get("created_at", int(datetime.now().timestamp())),
            version=data["version"],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            approval_required=data.get("approval_required", False)
        )
