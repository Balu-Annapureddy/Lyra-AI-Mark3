"""
Command Schema - User Refinement #1
Explicit structure for commands flowing through Lyra
Enables safety validation, logging, learning, and explainability
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


class RiskLevel(Enum):
    """Risk classification for commands"""
    SAFE = "safe"              # No side effects (e.g., "what time is it?")
    LOW = "low"                # Minimal risk (e.g., "open calculator")
    MEDIUM = "medium"          # Some risk (e.g., "create a file")
    HIGH = "high"              # Significant risk (e.g., "delete files")
    CRITICAL = "critical"      # Dangerous (e.g., "shutdown system")


@dataclass
class Command:
    """
    Structured command representation
    Central data structure for all Lyra operations
    """
    
    # Core identification
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # User input
    raw_input: str = ""
    
    # Intent understanding
    intent: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    
    # Safety assessment
    risk_level: RiskLevel = RiskLevel.SAFE
    requires_confirmation: bool = False
    
    # Execution planning
    execution_plan: List[Dict[str, Any]] = field(default_factory=list)
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Execution tracking
    status: str = "pending"  # pending, approved, executing, completed, failed, cancelled
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Learning metadata
    user_feedback: Optional[str] = None
    execution_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary for logging/storage"""
        return {
            "command_id": self.command_id,
            "timestamp": self.timestamp,
            "raw_input": self.raw_input,
            "intent": self.intent,
            "entities": self.entities,
            "confidence": self.confidence,
            "risk_level": self.risk_level.value,
            "requires_confirmation": self.requires_confirmation,
            "execution_plan": self.execution_plan,
            "context": self.context,
            "status": self.status,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "user_feedback": self.user_feedback,
            "execution_time_ms": self.execution_time_ms,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Command':
        """Create command from dictionary"""
        cmd = cls()
        cmd.command_id = data.get("command_id", cmd.command_id)
        cmd.timestamp = data.get("timestamp", cmd.timestamp)
        cmd.raw_input = data.get("raw_input", "")
        cmd.intent = data.get("intent", "")
        cmd.entities = data.get("entities", {})
        cmd.confidence = data.get("confidence", 0.0)
        cmd.risk_level = RiskLevel(data.get("risk_level", "safe"))
        cmd.requires_confirmation = data.get("requires_confirmation", False)
        cmd.execution_plan = data.get("execution_plan", [])
        cmd.context = data.get("context", {})
        cmd.status = data.get("status", "pending")
        cmd.result = data.get("result")
        cmd.error = data.get("error")
        cmd.user_feedback = data.get("user_feedback")
        cmd.execution_time_ms = data.get("execution_time_ms")
        return cmd
    
    def get_explanation(self) -> str:
        """
        Generate human-readable explanation of the command
        Supports "why did you do this?" queries
        """
        explanation = f"Command: {self.raw_input}\n"
        explanation += f"Intent: {self.intent} (confidence: {self.confidence:.2%})\n"
        explanation += f"Risk Level: {self.risk_level.value}\n"
        
        if self.entities:
            explanation += f"Extracted Information: {self.entities}\n"
        
        if self.execution_plan:
            explanation += "Execution Steps:\n"
            for i, step in enumerate(self.execution_plan, 1):
                explanation += f"  {i}. {step.get('action', 'Unknown')}\n"
        
        if self.result:
            explanation += f"Result: {self.result}\n"
        
        if self.error:
            explanation += f"Error: {self.error}\n"
        
        return explanation
