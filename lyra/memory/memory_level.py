"""
Memory Levels - User Refinement #3
Classification system for different types of memories
Prevents painful refactors later by establishing clear memory taxonomy
"""

from enum import Enum


class MemoryLevel(Enum):
    """
    Memory classification levels
    Determines storage duration and retrieval priority
    """
    
    SHORT_TERM = "short_term"      # Current session, conversation context
    LONG_TERM = "long_term"         # Persistent across sessions, important events
    PREFERENCE = "preference"       # User preferences and settings
    SYSTEM_EVENT = "system_event"   # System actions, errors, audit trail
