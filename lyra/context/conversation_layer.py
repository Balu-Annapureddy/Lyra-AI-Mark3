# -*- coding: utf-8 -*-
"""
lyra/context/conversation_layer.py
Phase 6I: Conversational Intelligence Layer

Softens casual/polite phrasing into clean command intent.
Conservative by design — stabilizes intent, never rewrites it.

Adjustments applied:
  1. Filler stripping is verb-gated (only strips if followed by a safe verb)
  2. Synonym mapping is verb-position only (first actionable token)
  3. Tone detection picks dominant tone via priority (urgent > frustrated > polite > casual)
  4. Confidence modifier applied AFTER semantic parsing (returned as multiplier, not pre-applied)
  5. Dangerous synonym returns explicit message, never steers toward destructive confirmation
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ConversationResult:
    """
    Result of a conversational processing pass.

    Attributes:
        cleaned:              The processed input string.
        was_modified:         True if any change was made to the text.
        tone:                 Dominant detected tone (polite/urgent/frustrated/casual/neutral).
        filler_stripped:      True if a filler phrase was removed.
        synonym_mapped:       True if a safe synonym was replaced.
        clarification_needed: True if a destructive synonym was detected.
        dangerous_synonym:    The raw destructive term found (e.g. "nuke"), or None.
        confidence_modifier:  Multiply semantic confidence by this after parsing (1.0 or 0.95).
        indirect_phrasing:    True if filler stripped OR modal verbs detected (for Phase 7).
    """
    cleaned: str
    was_modified: bool
    tone: str = "neutral"
    filler_stripped: bool = False
    synonym_mapped: bool = False
    clarification_needed: bool = False
    dangerous_synonym: Optional[str] = None
    confidence_modifier: float = 1.0
    indirect_phrasing: bool = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Safe action verbs — filler is only stripped when followed by one of these.
# This prevents stripping real semantic content like "can you believe this".
_SAFE_VERBS: frozenset = frozenset({
    "create", "open", "launch", "write", "close", "rename",
    "make", "start", "boot", "shut", "read", "list", "show",
    "find", "search", "move", "copy", "run", "execute", "save",
    "load", "print", "get", "set", "new", "clear", "help",
})

# Filler phrases — ordered longest-first to avoid partial matches.
# Only stripped when the next token is a safe verb.
_FILLER_PHRASES: List[str] = [
    "i would like to",
    "would you mind",
    "i want to",
    "i wanna",
    "could you",
    "can you",
    "please",
    "pls",
    "hey",
    "yo",
    "bro",
    "buddy",
]

# Pre-compiled filler patterns: each matches filler at start of string,
# followed by a safe verb (captured so we can verify it).
# Pattern: ^<filler>\s+(?=<safe_verb_boundary>)
_SAFE_VERB_PATTERN = r'(?:' + '|'.join(re.escape(v) for v in sorted(_SAFE_VERBS, key=len, reverse=True)) + r')\b'
_FILLER_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(
            r'^' + re.escape(phrase) + r'\s+(?=' + _SAFE_VERB_PATTERN + r')',
            re.IGNORECASE
        ),
        phrase
    )
    for phrase in _FILLER_PHRASES
]

# Modal verbs that signal indirect phrasing (for indirect_phrasing flag).
_MODAL_VERBS: frozenset = frozenset({"would", "could", "might", "should", "may"})

# Safe synonym map — verb-position only (first actionable token).
# Maps casual/informal verbs to canonical safe commands.
# Destructive synonyms are NOT included here — they go to DESTRUCTIVE_SYNONYMS.
_SAFE_SYNONYM_MAP: dict = {
    "make":     "create",
    "start":    "launch",
    "open up":  "open",
    "spin up":  "create",
    "boot":     "launch",
    "shut":     "close",
}

# Destructive synonyms — never auto-mapped, always trigger clarification.
_DESTRUCTIVE_SYNONYMS: frozenset = frozenset({
    "wipe", "erase", "destroy", "kill", "purge", "nuke",
    "obliterate", "annihilate", "trash", "zap",
})

# Tone keyword sets — priority: urgent > frustrated > polite > casual > neutral
_TONE_KEYWORDS: dict = {
    "urgent":     frozenset({"asap", "urgent", "now", "immediately", "hurry", "quick", "fast", "rush"}),
    "frustrated": frozenset({"ugh", "again", "still", "broken", "why", "useless", "argh", "seriously", "wtf"}),
    "polite":     frozenset({"please", "thank", "kindly", "appreciate", "thanks", "sorry", "excuse"}),
    "casual":     frozenset({"hey", "yo", "bro", "buddy", "wanna", "gonna", "lemme", "gimme"}),
}
_TONE_PRIORITY: List[str] = ["urgent", "frustrated", "polite", "casual"]


# ---------------------------------------------------------------------------
# ConversationLayer
# ---------------------------------------------------------------------------

class ConversationLayer:
    """
    Phase 6I: Pre-pipeline conversational softening.

    Strips filler, maps safe synonyms, detects tone, and flags
    indirect phrasing — without ever modifying filenames, quoted
    strings, or destructive intent.
    """

    def process(self, text: str) -> ConversationResult:
        """
        Run conversational processing on *text*.

        Returns a ConversationResult. The caller is responsible for
        applying confidence_modifier AFTER semantic parsing.
        """
        original = text
        filler_stripped = False
        synonym_mapped = False
        clarification_needed = False
        dangerous_synonym: Optional[str] = None

        # ── Step 0: Extract quoted strings ──────────────────────────────────
        placeholders: List[str] = []
        _QUOTE_RE = re.compile(r'(["\'])(?:(?!\1).)*\1')

        def _extract(m: re.Match) -> str:
            idx = len(placeholders)
            placeholders.append(m.group(0))
            return f"\x00Q{idx}\x00"

        text = _QUOTE_RE.sub(_extract, text)

        # ── Step 1: Filler phrase stripping (verb-gated, beginning only) ────
        # Only strip if the next token after the filler is a safe verb.
        stripped_text = text
        for pattern, phrase in _FILLER_PATTERNS:
            m = pattern.match(stripped_text.lstrip())
            if m:
                stripped_text = stripped_text.lstrip()[m.end():].lstrip()
                filler_stripped = True
                break  # Only strip one filler phrase

        if filler_stripped:
            text = stripped_text

        # ── Step 2: Safe synonym mapping (verb-position only) ───────────────
        # Only map if the synonym is the FIRST actionable token in the string.
        # Check two-word synonyms first (e.g. "open up"), then single-word.
        words = text.split()
        if words:
            # Check two-word prefix first
            two_word = " ".join(words[:2]).lower() if len(words) >= 2 else ""
            one_word = words[0].lower()

            if two_word in _SAFE_SYNONYM_MAP:
                canonical = _SAFE_SYNONYM_MAP[two_word]
                text = canonical + " " + " ".join(words[2:])
                synonym_mapped = True
            elif one_word in _SAFE_SYNONYM_MAP:
                canonical = _SAFE_SYNONYM_MAP[one_word]
                text = canonical + (" " + " ".join(words[1:]) if len(words) > 1 else "")
                synonym_mapped = True
            elif one_word in _DESTRUCTIVE_SYNONYMS:
                # Destructive synonym detected — do NOT map, flag for clarification
                clarification_needed = True
                dangerous_synonym = one_word

        # ── Step 3: Tone detection (dominant tone, priority order) ───────────
        # Scan all tokens (lowercased) against tone keyword sets.
        # Pick the highest-priority tone that has at least one match.
        all_lower_tokens = set(re.findall(r'\b\w+\b', original.lower()))
        tone = "neutral"
        for t in _TONE_PRIORITY:
            if all_lower_tokens & _TONE_KEYWORDS[t]:
                tone = t
                break

        # ── Step 4: Indirect phrasing detection ─────────────────────────────
        # Triggered if filler was stripped OR modal verbs appear in original.
        modal_found = bool(all_lower_tokens & _MODAL_VERBS)
        indirect_phrasing = filler_stripped or modal_found

        # ── Step 5: Confidence modifier ─────────────────────────────────────
        # Reduce confidence slightly for indirect/ambiguous phrasing.
        # Applied AFTER semantic parsing by the pipeline — returned as multiplier.
        confidence_modifier = 0.95 if indirect_phrasing else 1.0

        # ── Step 6: Re-insert quoted strings ────────────────────────────────
        for idx, quoted in enumerate(placeholders):
            text = text.replace(f"\x00Q{idx}\x00", quoted)

        was_modified = (text != original) or filler_stripped or synonym_mapped

        return ConversationResult(
            cleaned=text,
            was_modified=was_modified,
            tone=tone,
            filler_stripped=filler_stripped,
            synonym_mapped=synonym_mapped,
            clarification_needed=clarification_needed,
            dangerous_synonym=dangerous_synonym,
            confidence_modifier=confidence_modifier,
            indirect_phrasing=indirect_phrasing,
        )

    def soften_response(self, response_text: str, emotion_result: Dict[str, Any]) -> str:
        """
        Adjusts response tone if the user is frustrated or angry.
        """
        if not emotion_result.get("requires_softening"):
            return response_text
            
        emotion = emotion_result.get("emotion")
        intensity = emotion_result.get("intensity", 0.0)
        
        # Simple prefix based on emotion
        if emotion == "angry":
            prefix = "I understand you're upset. " if intensity > 0.7 else "Apologies for the trouble. "
        elif emotion == "frustrated":
            prefix = "I see this is frustrating. Let's get this right. " if intensity > 0.5 else "I'll help you with that. "
        else:
            prefix = ""
            
        return prefix + response_text
