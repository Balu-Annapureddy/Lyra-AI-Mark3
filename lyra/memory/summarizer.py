"""
Memory Summarizer
Compresses long-term memory for efficient storage
"""

from typing import List, Dict, Any
from lyra.core.logger import get_logger


class MemorySummarizer:
    """
    Summarizes and compresses memory for long-term storage
    Phase 1: Basic implementation, will be enhanced in later phases
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def summarize_events(self, events: List[Dict[str, Any]]) -> str:
        """
        Create summary of events
        
        Args:
            events: List of events to summarize
        
        Returns:
            Summary string
        """
        if not events:
            return "No events to summarize"
        
        summary_parts = []
        summary_parts.append(f"Summary of {len(events)} events:")
        
        # Group by event type
        event_types = {}
        for event in events:
            event_type = event.get("event_type", "unknown")
            if event_type not in event_types:
                event_types[event_type] = 0
            event_types[event_type] += 1
        
        for event_type, count in event_types.items():
            summary_parts.append(f"- {event_type}: {count}")
        
        return "\n".join(summary_parts)
    
    def extract_key_information(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract key information from events
        
        Args:
            events: List of events
        
        Returns:
            Dictionary of key information
        """
        key_info = {
            "total_events": len(events),
            "event_types": {},
            "important_events": []
        }
        
        for event in events:
            event_type = event.get("event_type", "unknown")
            if event_type not in key_info["event_types"]:
                key_info["event_types"][event_type] = 0
            key_info["event_types"][event_type] += 1
            
            # Track high-importance events
            if event.get("importance", 0) > 0.7:
                key_info["important_events"].append({
                    "event_id": event.get("event_id"),
                    "timestamp": event.get("timestamp"),
                    "type": event_type
                })
        
        return key_info
