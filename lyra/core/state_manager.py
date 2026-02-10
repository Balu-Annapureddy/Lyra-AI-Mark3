"""
Lyra State Manager - User Refinement #4
Manages Lyra's operational state for better UX and debugging
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import threading


class LyraState(Enum):
    """Lyra's operational states"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    ERROR = "error"


class StateManager:
    """
    Manages Lyra's current state and state transitions
    Thread-safe singleton implementation
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._state = LyraState.IDLE
            self._state_history = []
            self._state_metadata = {}
            self._state_lock = threading.Lock()
            self._initialized = True
    
    @property
    def current_state(self) -> LyraState:
        """Get current state"""
        with self._state_lock:
            return self._state
    
    def set_state(self, new_state: LyraState, metadata: Optional[Dict[str, Any]] = None):
        """
        Set new state with optional metadata
        
        Args:
            new_state: The new state to transition to
            metadata: Optional metadata about the state (e.g., task being executed)
        """
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            
            # Record state transition
            transition = {
                "from": old_state.value,
                "to": new_state.value,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            self._state_history.append(transition)
            
            # Update current metadata
            self._state_metadata = metadata or {}
            
            # Keep history limited to last 100 transitions
            if len(self._state_history) > 100:
                self._state_history = self._state_history[-100:]
    
    def get_state_metadata(self) -> Dict[str, Any]:
        """Get metadata for current state"""
        with self._state_lock:
            return self._state_metadata.copy()
    
    def get_state_history(self, limit: int = 10) -> list:
        """
        Get recent state history
        
        Args:
            limit: Number of recent transitions to return
        
        Returns:
            List of recent state transitions
        """
        with self._state_lock:
            return self._state_history[-limit:]
    
    def is_busy(self) -> bool:
        """Check if Lyra is currently busy (not idle or error)"""
        with self._state_lock:
            return self._state not in [LyraState.IDLE, LyraState.ERROR]
    
    def reset(self):
        """Reset to idle state"""
        self.set_state(LyraState.IDLE, {"reason": "manual_reset"})
