# -*- coding: utf-8 -*-
"""
Command Suggester - Phase 5B
Lightweight suggestion system using difflib
Suggests similar commands when intent is unknown
"""

import difflib
from typing import List, Optional, Tuple


class CommandSuggester:
    """
    Suggest similar commands using difflib
    Phase 5B: Simple, lightweight, no ML
    """
    
    def __init__(self):
        # Known command patterns (from intent_detector)
        self.known_patterns = [
            # File operations
            "create file",
            "write file",
            "make file",
            "read file",
            "open file",
            "delete file",
            "remove file",
            
            # Web operations
            "open url",
            "browse",
            "visit",
            "go to",
            
            # App operations
            "launch app",
            "open app",
            "start app",
            "run app",
            
            # System
            "help",
            "history",
            "logs",
            "simulate",
        ]
        
        # Common typos and variations
        self.common_variations = {
            "creat": "create",
            "opne": "open",
            "lunach": "launch",
            "brows": "browse",
            "delet": "delete",
            "remov": "remove",
        }
    
    def suggest(self, user_input: str, cutoff: float = 0.6) -> Optional[Tuple[str, float]]:
        """
        Suggest a similar command
        
        Args:
            user_input: User's input command
            cutoff: Similarity threshold (0.0-1.0)
        
        Returns:
            Tuple of (suggestion, confidence) or None
        """
        if not user_input:
            return None
        
        # Normalize input
        normalized = user_input.lower().strip()
        
        # Check for common typos first
        for typo, correction in self.common_variations.items():
            if typo in normalized:
                normalized = normalized.replace(typo, correction)
        
        # Find close matches
        matches = difflib.get_close_matches(
            normalized,
            self.known_patterns,
            n=1,
            cutoff=cutoff
        )
        
        if matches:
            best_match = matches[0]
            # Calculate similarity ratio
            similarity = difflib.SequenceMatcher(
                None,
                normalized,
                best_match
            ).ratio()
            return (best_match, similarity)
        
        # Try matching individual words
        words = normalized.split()
        if len(words) > 0:
            for word in words:
                word_matches = difflib.get_close_matches(
                    word,
                    [p.split()[0] for p in self.known_patterns],
                    n=1,
                    cutoff=cutoff
                )
                if word_matches:
                    # Find full pattern starting with this word
                    for pattern in self.known_patterns:
                        if pattern.startswith(word_matches[0]):
                            similarity = difflib.SequenceMatcher(
                                None,
                                word,
                                word_matches[0]
                            ).ratio()
                            return (pattern, similarity)
        
        return None
    
    def get_hint(self, user_input: str) -> Optional[str]:
        """
        Get a helpful hint message
        
        Args:
            user_input: User's input command
        
        Returns:
            Hint message or None
        """
        suggestion = self.suggest(user_input)
        
        if suggestion:
            pattern, confidence = suggestion
            if confidence > 0.7:
                return f"Did you mean: '{pattern}'?"
            elif confidence > 0.5:
                return f"Similar command: '{pattern}' (try 'help' for examples)"
        
        return "Command not recognized. Type 'help' for available commands."
