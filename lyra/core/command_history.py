# -*- coding: utf-8 -*-
"""
Command History - Phase 5B
Tracks recent commands in memory (no disk persistence)
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class CommandEntry:
    """Single command history entry"""
    timestamp: str
    command: str
    success: bool
    index: int


class CommandHistory:
    """
    Tracks last N commands in memory
    Phase 5B: No disk persistence
    """
    
    def __init__(self, max_size: int = 20):
        """
        Initialize command history
        
        Args:
            max_size: Maximum number of commands to store
        """
        self.max_size = max_size
        self.commands = deque(maxlen=max_size)
        self._counter = 0
    
    def add(self, command: str, success: bool = True):
        """
        Add command to history
        
        Args:
            command: Command text
            success: Whether command succeeded
        """
        entry = CommandEntry(
            timestamp=datetime.now().isoformat(),
            command=command,
            success=success,
            index=self._counter
        )
        self.commands.append(entry)
        self._counter += 1
    
    def get_recent(self, count: Optional[int] = None) -> List[CommandEntry]:
        """
        Get recent commands
        
        Args:
            count: Number of commands to return (None = all)
        
        Returns:
            List of command entries (newest first)
        """
        if count is None:
            count = len(self.commands)
        
        # Return newest first
        return list(reversed(list(self.commands)))[:count]
    
    def clear(self):
        """Clear all history"""
        self.commands.clear()
        self._counter = 0
    
    def get_count(self) -> int:
        """Get total number of commands stored"""
        return len(self.commands)
