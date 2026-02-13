"""
System State Manager - Phase 2A Critical Component
Centralized state management to prevent fragmentation
Single source of truth for Lyra's operational context
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from lyra.reasoning.command_schema import Command


@dataclass
class Suggestion:
    """Proactive suggestion data structure"""
    suggestion_id: str
    suggestion_type: str
    message: str
    action: str
    params: Dict[str, Any]
    confidence: float
    timestamp: datetime
    accepted: Optional[bool] = None


@dataclass
class SystemState:
    """
    Centralized system state
    Prevents state fragmentation across modules
    """
    # Context tracking
    current_context: Dict[str, Any] = field(default_factory=dict)
    active_project: Optional[str] = None
    current_workflow: Optional[str] = None
    last_command: Optional[Command] = None
    
    # Session state
    session_state: Dict[str, Any] = field(default_factory=dict)
    session_start: datetime = field(default_factory=datetime.now)
    
    # Trust and suggestions
    user_trust_score: float = 0.5  # Start neutral (0.0-1.0)
    suggestion_history: List[Suggestion] = field(default_factory=list)
    rejection_cooldowns: Dict[str, datetime] = field(default_factory=dict)
    
    # Workflow state
    workflow_recording: bool = False
    workflow_steps: List[Command] = field(default_factory=list)


class SystemStateManager:
    """
    Single source of truth for Lyra's state
    Thread-safe, prevents fragmentation
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.state = SystemState()
            self._initialized = True
    
    # Context management
    def update_context(self, key: str, value: Any):
        """Update a context value"""
        self.state.current_context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value"""
        return self.state.current_context.get(key, default)
    
    def clear_context(self):
        """Clear all context"""
        self.state.current_context.clear()
    
    # Project management
    def set_active_project(self, project: str):
        """Set the active project"""
        self.state.active_project = project
        self.update_context("project", project)
    
    def get_active_project(self) -> Optional[str]:
        """Get the active project"""
        return self.state.active_project
    
    # Workflow management
    def set_current_workflow(self, workflow_id: str):
        """Set the current workflow"""
        self.state.current_workflow = workflow_id
    
    def get_current_workflow(self) -> Optional[str]:
        """Get the current workflow"""
        return self.state.current_workflow
    
    def start_workflow_recording(self):
        """Start recording a workflow"""
        self.state.workflow_recording = True
        self.state.workflow_steps.clear()
    
    def stop_workflow_recording(self) -> List[Command]:
        """Stop recording and return steps"""
        self.state.workflow_recording = False
        steps = self.state.workflow_steps.copy()
        self.state.workflow_steps.clear()
        return steps
    
    def record_workflow_step(self, command: Command):
        """Record a workflow step"""
        if self.state.workflow_recording:
            self.state.workflow_steps.append(command)
    
    def is_recording_workflow(self) -> bool:
        """Check if currently recording a workflow"""
        return self.state.workflow_recording
    
    # Command tracking
    def set_last_command(self, command: Command):
        """Set the last executed command"""
        self.state.last_command = command
    
    def get_last_command(self) -> Optional[Command]:
        """Get the last executed command"""
        return self.state.last_command
    
    # Trust management
    def update_trust_score(self, delta: float):
        """
        Update user trust score
        
        Args:
            delta: Change in trust (-1.0 to 1.0)
        """
        self.state.user_trust_score = max(0.0, min(1.0, self.state.user_trust_score + delta))
    
    def get_trust_score(self) -> float:
        """Get current trust score"""
        return self.state.user_trust_score
    
    def set_trust_score(self, score: float):
        """Set trust score directly"""
        self.state.user_trust_score = max(0.0, min(1.0, score))
    
    # Suggestion management
    def record_suggestion(self, suggestion: Suggestion, accepted: bool):
        """
        Record a suggestion and its outcome
        
        Args:
            suggestion: The suggestion that was presented
            accepted: Whether user accepted it
        """
        suggestion.accepted = accepted
        self.state.suggestion_history.append(suggestion)
        
        # Keep history limited
        if len(self.state.suggestion_history) > 100:
            self.state.suggestion_history = self.state.suggestion_history[-100:]
        
        # Update trust based on acceptance
        if accepted:
            self.update_trust_score(0.05)  # Small trust increase
        else:
            self.update_trust_score(-0.02)  # Smaller trust decrease
    
    def get_suggestion_history(self, limit: int = 10) -> List[Suggestion]:
        """Get recent suggestion history"""
        return self.state.suggestion_history[-limit:]
    
    def set_cooldown(self, suggestion_type: str, until: datetime):
        """Set a cooldown for a suggestion type"""
        self.state.rejection_cooldowns[suggestion_type] = until
    
    def is_in_cooldown(self, suggestion_type: str) -> bool:
        """Check if a suggestion type is in cooldown"""
        if suggestion_type in self.state.rejection_cooldowns:
            return datetime.now() < self.state.rejection_cooldowns[suggestion_type]
        return False
    
    def clear_cooldown(self, suggestion_type: str):
        """Clear cooldown for a suggestion type"""
        if suggestion_type in self.state.rejection_cooldowns:
            del self.state.rejection_cooldowns[suggestion_type]
    
    # Session management
    def update_session_state(self, key: str, value: Any):
        """Update session state"""
        self.state.session_state[key] = value
    
    def get_session_state(self, key: str, default: Any = None) -> Any:
        """Get session state value"""
        return self.state.session_state.get(key, default)
    
    def get_session_duration(self) -> float:
        """Get session duration in seconds"""
        return (datetime.now() - self.state.session_start).total_seconds()
    
    def reset_session(self):
        """Reset session state"""
        self.state.session_state.clear()
        self.state.session_start = datetime.now()
    
    # Full state access
    def get_full_state(self) -> SystemState:
        """Get the full system state (for debugging/logging)"""
        return self.state
    
    def reset(self):
        """Reset to initial state"""
        self.state = SystemState()
