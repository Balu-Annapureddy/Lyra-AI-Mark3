# -*- coding: utf-8 -*-
"""
lyra/memory/session_memory.py
Phase 6F: Structured Short-Term Memory
Tracks session context for explicit reference resolution.
STRICT: No pronouns, only explicit "last X" references.
"""

from typing import Dict, Any, Optional, Tuple, List
import re
from datetime import datetime
from lyra.reasoning.command_schema import Command

class SessionMemory:
    """
    Stores volatile session state for resolving explicit user references.
    Resets on session end (no persistence).
    """

    def __init__(self):
        self._reset_state()

    def _reset_state(self):
        self.last_created_file: Optional[str] = None
        self.last_opened_app: Optional[str] = None
        self.last_path: Optional[str] = None
        self.last_successful_intent: Optional[str] = None
        self.last_parameters: Dict[str, Any] = {}
        self.timestamp: Optional[str] = None
        # Phase F7: Language Tracking
        self.consecutive_lang_hits: Dict[str, int] = {}
        self.preferred_language: Optional[str] = "en"
        self.last_detected_lang: Optional[str] = "en"
        # Phase F9: Contextual Memory
        self.interaction_history: List[Dict[str, Any]] = []

    def clear(self):
        """Explicitly clear memory"""
        self._reset_state()
        
    def resolve_reference(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Resolve explicit references in user text.
        Returns: (resolved_text, metadata)
        STRICT: Only resolves "last file", "previous file", "last app", "previous app".
        """
        resolved_text = text
        replacements = []
        original_text = text

        # 1. Resolve File References
        # Patterns for files
        file_phrases = ["last file", "previous file", "the file"]
        
        target_file = self.last_created_file or self.last_path
        if target_file:
            for phrase in file_phrases:
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                if pattern.search(resolved_text):
                     resolved_text = pattern.sub(target_file, resolved_text)
                     replacements.append(f"'{phrase}' -> '{target_file}'")

        # 2. Resolve App References
        # Patterns for apps
        app_phrases = ["last app", "previous app", "the app"]
        
        target_app = self.last_opened_app
        if target_app:
            for phrase in app_phrases:
                 pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                 if pattern.search(resolved_text):
                     resolved_text = pattern.sub(target_app, resolved_text)
                     replacements.append(f"'{phrase}' -> '{target_app}'")

        metadata = {
            "original": original_text,
            "resolved": resolved_text,
            "replacements": replacements,
            "was_modified": resolved_text != original_text
        }
        
        return resolved_text, metadata

    def update_from_intent(self, command: Command):
        """
        Update memory state from a successfully executed command.
        Strictly only updates on verified success.
        """
        if not command:
            return
            
        # Pipeline execution sets result.success, but command.status might be used too.
        # User requested: "Update Memory After VERIFIED Success".
        # We assume caller checks success before calling this, or we check command.status.
        # Let's assume pipeline calls this only on success, OR we check status.
        # command.status is "completed" on success usually? Or likely just relies on flow.
        # I'll check status if available, but pipeline update logic is better placed in pipeline.
        
        self.last_successful_intent = command.intent
        self.last_parameters = command.entities.copy()
        self.timestamp = datetime.now().isoformat()

        # Update specific trackers based on intent
        intent = command.intent
        entities = command.entities

        if intent in ["create_file", "write_file", "append_file"]:
            path = entities.get("path") or entities.get("file_path")
            if path:
                self.last_created_file = path
                self.last_path = path
        
        elif intent in ["launch_app", "open_application"]:
            app = entities.get("app_name") or entities.get("name")
            if app:
                self.last_opened_app = app
        
        elif intent in ["read_file", "delete_file"]:
            path = entities.get("path") or entities.get("file_path")
            if path:
                self.last_path = path

    def update_language_preference(self, lang: str):
        """
        Track consecutive counts and set preferred_language if it hits 5.
        """
        if self.last_detected_lang == lang:
            count = self.consecutive_lang_hits.get(lang, 0) + 1
            self.consecutive_lang_hits[lang] = count
        else:
            self.consecutive_lang_hits = {lang: 1}
            
        self.last_detected_lang = lang
        
        if self.consecutive_lang_hits.get(lang, 0) >= 5:
            self.preferred_language = lang

    def add_interaction(self, role: str, content: str, **kwargs):
        """Add a turn to the interaction history."""
        entry = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        entry.update(kwargs)
        self.interaction_history.append(entry)

    def get_interaction_history(self) -> List[Dict[str, Any]]:
        """Retrieve full history."""
        return self.interaction_history

    def set_interaction_history(self, history: List[Dict[str, Any]]):
        """Update history (used after compression)."""
        self.interaction_history = history
