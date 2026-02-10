"""
Outcome Tracker
Tracks command execution outcomes for learning
Phase 1: Basic tracking, foundation for future ML
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from lyra.reasoning.command_schema import Command
from lyra.core.logger import get_logger


class OutcomeTracker:
    """
    Tracks execution outcomes for learning
    Phase 1: Basic success/failure tracking
    Future: Pattern detection, workflow optimization
    """
    
    def __init__(self, outcomes_file: str = None):
        self.logger = get_logger(__name__)
        
        if outcomes_file is None:
            project_root = Path(__file__).parent.parent.parent
            outcomes_file = str(project_root / "data" / "outcomes.jsonl")
        
        self.outcomes_file = outcomes_file
        Path(outcomes_file).parent.mkdir(parents=True, exist_ok=True)
    
    def record_outcome(self, command: Command, success: bool, 
                      error: str = None, user_feedback: str = None):
        """
        Record command execution outcome
        
        Args:
            command: Executed command
            success: Whether execution succeeded
            error: Error message if failed
            user_feedback: Optional user feedback
        """
        outcome = {
            "timestamp": datetime.now().isoformat(),
            "command_id": command.command_id,
            "intent": command.intent,
            "confidence": command.confidence,
            "risk_level": command.risk_level.value,
            "success": success,
            "error": error,
            "execution_time_ms": command.execution_time_ms,
            "user_feedback": user_feedback
        }
        
        self._write_outcome(outcome)
        self.logger.info(f"Recorded outcome for {command.intent}: {'success' if success else 'failure'}")
    
    def _write_outcome(self, outcome: Dict[str, Any]):
        """Write outcome to file"""
        try:
            with open(self.outcomes_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(outcome) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write outcome: {e}")
    
    def get_recent_outcomes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent outcomes
        
        Args:
            limit: Number of outcomes to retrieve
        
        Returns:
            List of recent outcomes
        """
        try:
            if not Path(self.outcomes_file).exists():
                return []
            
            outcomes = []
            with open(self.outcomes_file, 'r', encoding='utf-8') as f:
                for line in f:
                    outcomes.append(json.loads(line))
            
            return outcomes[-limit:]
        
        except Exception as e:
            self.logger.error(f"Failed to read outcomes: {e}")
            return []
    
    def get_success_rate(self, intent: str = None) -> float:
        """
        Calculate success rate
        
        Args:
            intent: Optional filter by intent
        
        Returns:
            Success rate (0.0 to 1.0)
        """
        outcomes = self.get_recent_outcomes(limit=100)
        
        if intent:
            outcomes = [o for o in outcomes if o.get('intent') == intent]
        
        if not outcomes:
            return 0.0
        
        successes = sum(1 for o in outcomes if o.get('success', False))
        return successes / len(outcomes)
    
    def get_error_patterns(self) -> Dict[str, int]:
        """
        Get common error patterns
        
        Returns:
            Dictionary of error types and counts
        """
        outcomes = self.get_recent_outcomes(limit=100)
        error_counts = {}
        
        for outcome in outcomes:
            if not outcome.get('success', True):
                error = outcome.get('error', 'Unknown error')
                error_counts[error] = error_counts.get(error, 0) + 1
        
        return error_counts
