"""
Pattern Detector - Phase 2D
Detects patterns in user behavior for proactive suggestions
Uses heuristic-based pattern matching (no ML)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from lyra.memory.event_memory import EventMemory
from lyra.core.logger import get_logger


class PatternDetector:
    """
    Detects behavioral patterns for proactive suggestions
    Rule-based pattern matching (no ML in Phase 2)
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.event_memory = EventMemory()
        
        # Pattern thresholds
        self.time_pattern_threshold = 3  # Need 3+ occurrences
        self.sequence_pattern_threshold = 3  # Need 3+ sequences
        self.time_window_minutes = 30  # Time window for "same time"
    
    def detect_time_patterns(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Detect time-based patterns (e.g., "check email every morning at 9am")
        
        Args:
            days_back: Number of days to analyze
        
        Returns:
            List of detected patterns
        """
        # Get recent events
        events = self.event_memory.retrieve_recent(limit=1000)
        
        # Group by intent and time of day
        intent_times = defaultdict(list)
        
        for event in events:
            try:
                timestamp = datetime.fromisoformat(event["timestamp"])
                intent = event["data"].get("intent", "")
                
                if intent:
                    # Round to nearest 30 minutes
                    rounded_time = timestamp.replace(minute=(timestamp.minute // 30) * 30, second=0, microsecond=0)
                    intent_times[intent].append(rounded_time)
            except Exception as e:
                continue
        
        # Find patterns
        patterns = []
        
        for intent, times in intent_times.items():
            if len(times) < self.time_pattern_threshold:
                continue
            
            # Group by time of day
            time_groups = defaultdict(list)
            for t in times:
                time_key = (t.hour, t.minute)
                time_groups[time_key].append(t)
            
            # Check for recurring times
            for time_key, occurrences in time_groups.items():
                if len(occurrences) >= self.time_pattern_threshold:
                    # Check if spread across multiple days
                    unique_days = len(set(t.date() for t in occurrences))
                    
                    if unique_days >= 3:
                        patterns.append({
                            "type": "time_pattern",
                            "intent": intent,
                            "time": f"{time_key[0]:02d}:{time_key[1]:02d}",
                            "occurrences": len(occurrences),
                            "unique_days": unique_days,
                            "confidence": min(1.0, unique_days / 7),
                            "suggestion": f"Run '{intent}' at {time_key[0]:02d}:{time_key[1]:02d}"
                        })
        
        return patterns
    
    def detect_sequence_patterns(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Detect command sequences (e.g., "open email then open calendar")
        
        Args:
            limit: Number of recent events to analyze
        
        Returns:
            List of detected sequence patterns
        """
        # Get recent events
        events = self.event_memory.retrieve_recent(limit=limit)
        
        # Extract command sequences
        sequences = []
        for i in range(len(events) - 1):
            try:
                current = events[i]
                next_event = events[i + 1]
                
                current_time = datetime.fromisoformat(current["timestamp"])
                next_time = datetime.fromisoformat(next_event["timestamp"])
                
                # Check if events are close in time (within 5 minutes)
                if (next_time - current_time).total_seconds() < 300:
                    current_intent = current["data"].get("intent", "")
                    next_intent = next_event["data"].get("intent", "")
                    
                    if current_intent and next_intent:
                        sequences.append((current_intent, next_intent))
            except Exception:
                continue
        
        # Count sequence occurrences
        sequence_counts = defaultdict(int)
        for seq in sequences:
            sequence_counts[seq] += 1
        
        # Find patterns
        patterns = []
        for seq, count in sequence_counts.items():
            if count >= self.sequence_pattern_threshold:
                patterns.append({
                    "type": "sequence_pattern",
                    "sequence": list(seq),
                    "occurrences": count,
                    "confidence": min(1.0, count / 10),
                    "suggestion": f"After '{seq[0]}', suggest '{seq[1]}'"
                })
        
        return patterns
    
    def detect_context_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect context-based patterns (e.g., "always open IDE when working on project X")
        
        Returns:
            List of detected context patterns
        """
        # Get recent events with context
        events = self.event_memory.retrieve_recent(limit=500)
        
        # Group by context and intent
        context_intents = defaultdict(lambda: defaultdict(int))
        
        for event in events:
            try:
                context = event.get("context", {})
                intent = event["data"].get("intent", "")
                
                if context and intent:
                    # Use project as context key
                    project = context.get("project", "")
                    if project:
                        context_intents[project][intent] += 1
            except Exception:
                continue
        
        # Find patterns
        patterns = []
        for project, intents in context_intents.items():
            for intent, count in intents.items():
                if count >= self.time_pattern_threshold:
                    patterns.append({
                        "type": "context_pattern",
                        "context": {"project": project},
                        "intent": intent,
                        "occurrences": count,
                        "confidence": min(1.0, count / 10),
                        "suggestion": f"In project '{project}', suggest '{intent}'"
                    })
        
        return patterns
    
    def get_all_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all detected patterns
        
        Returns:
            Dictionary of pattern types and their patterns
        """
        return {
            "time_patterns": self.detect_time_patterns(),
            "sequence_patterns": self.detect_sequence_patterns(),
            "context_patterns": self.detect_context_patterns()
        }
    
    def should_suggest(self, pattern: Dict[str, Any], current_context: Dict[str, Any] = None) -> bool:
        """
        Check if a pattern should trigger a suggestion now
        
        Args:
            pattern: Pattern to check
            current_context: Current execution context
        
        Returns:
            True if should suggest
        """
        pattern_type = pattern["type"]
        
        if pattern_type == "time_pattern":
            # Check if current time matches pattern time
            now = datetime.now()
            pattern_time = pattern["time"]
            hour, minute = map(int, pattern_time.split(":"))
            
            # Within 5 minutes of pattern time
            time_diff = abs((now.hour * 60 + now.minute) - (hour * 60 + minute))
            return time_diff <= 5
        
        elif pattern_type == "context_pattern":
            # Check if current context matches
            if current_context:
                pattern_context = pattern.get("context", {})
                return all(
                    current_context.get(k) == v
                    for k, v in pattern_context.items()
                )
        
        return False
