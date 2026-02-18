# -*- coding: utf-8 -*-
"""
Execution History - Phase 5B
Tracks recent execution results in memory
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ExecutionEntry:
    """Single execution history entry"""
    timestamp: str
    plan_id: str
    success: bool
    duration: float
    command: str
    error: Optional[str] = None


class ExecutionHistory:
    """
    Tracks last N execution results in memory
    Phase 5B: No disk persistence
    """
    
    def __init__(self, max_size: int = 10):
        """
        Initialize execution history
        
        Args:
            max_size: Maximum number of executions to store
        """
        self.max_size = max_size
        self.executions = deque(maxlen=max_size)
    
    def add(self, plan_id: str, success: bool, duration: float, 
            command: str, error: Optional[str] = None):
        """
        Add execution result to history
        
        Args:
            plan_id: Execution plan ID
            success: Whether execution succeeded
            duration: Execution duration in seconds
            command: Original command
            error: Error message if failed
        """
        entry = ExecutionEntry(
            timestamp=datetime.now().isoformat(),
            plan_id=plan_id,
            success=success,
            duration=duration,
            command=command,
            error=error
        )
        self.executions.append(entry)
    
    def get_recent(self, count: Optional[int] = None) -> List[ExecutionEntry]:
        """
        Get recent executions
        
        Args:
            count: Number of executions to return (None = all)
        
        Returns:
            List of execution entries (newest first)
        """
        if count is None:
            count = len(self.executions)
        
        # Return newest first
        return list(reversed(list(self.executions)))[:count]
    
    def clear(self):
        """Clear all history"""
        self.executions.clear()
    
    def get_count(self) -> int:
        """Get total number of executions stored"""
        return len(self.executions)
