# -*- coding: utf-8 -*-
"""
lyra/context/normalization_engine.py
Phase 6H: Robust Input Normalization & Error-Tolerant Understanding Layer

Philosophy: Conservative > Clever.
If unsure → do nothing. Never auto-improve destructive intent.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class NormalizationResult:
    """
    Result of a normalization pass.

    Attributes:
        normalized:              The cleaned input string.
        was_modified:            True if any change was made.
        dangerous_token_detected: The raw token that looked like a destructive
                                  keyword (e.g. "deleet"), or None.
        delta:                   Human-readable summary of changes made.
        modification_count:      Number of individual substitutions applied
                                  (for future adaptive confidence scoring).
    """
    normalized: str
    was_modified: bool
    dangerous_token_detected: Optional[str] = None
    delta: str = ""
    modification_count: int = 0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Words that must NEVER be auto-corrected.
# If a misspelled token is within edit-distance 1 of any of these, we stop
# and ask the user to type the word explicitly.
DESTRUCTIVE_KEYWORDS: frozenset = frozenset({
    "delete", "remove", "format", "wipe", "shutdown",
    "erase", "overwrite", "kill", "terminate", "destroy", "purge",
})

# Safe command keywords that CAN be corrected when edit-distance <= 1.
SAFE_KEYWORDS: frozenset = frozenset({
    "create", "open", "launch", "close", "write", "rename",
    "read", "list", "show", "find", "search", "move", "copy",
    "start", "stop", "run", "execute", "print", "save", "load",
    "help", "exit", "quit", "clear", "new", "make", "get", "set",
})

# Common English words that happen to be edit-distance 1 from a SAFE_KEYWORD
# but are NOT typos. These must never be auto-corrected.
# Examples: "last" (dist 1 from "list"), "fast" (dist 1 from "cast"),
#           "past" (dist 1 from "cast"), "lost" (dist 1 from "list"),
#           "lust" (dist 1 from "list"), "fist" (dist 1 from "list").
COMMON_WORDS_EXCLUSION: frozenset = frozenset({
    # near "list"
    "last", "lost", "lust", "fist", "gist", "mist", "wist",
    # near "show"
    "shot", "shop", "shoe", "shod", "shoo",
    # common question/conversational words that happen to be near commands
    # 'how' is edit-distance 1 from 'show' (s-how vs how)
    "how", "who", "now", "row", "sow", "bow", "cow", "low", "mow", "tow", "vow", "wow",
    # 'what', 'when', 'where', 'why' — near various commands
    "what", "when", "where", "why", "was", "has", "had", "are", "our",
    # near "find"
    "bind", "kind", "mind", "wind", "rind",
    # near "move"
    "love", "dove", "cove", "rove", "wove",
    # near "copy"
    "cozy", "cony",
    # near "stop"
    "step", "stem", "sten", "stow",
    # near "run"
    "gun", "sun", "bun", "fun", "nun", "pun",
    # near "get"
    "got", "gut", "git", "gat",
    # near "set"
    "sat", "sit", "sot", "net", "bet", "jet", "let", "met", "pet", "vet", "wet", "yet",
    # near "new"
    "dew", "few", "hew", "jew", "mew", "sew",
    # near "read"
    "bead", "dead", "head", "lead", "mead", "tread",
    # near "save"
    "cave", "gave", "have", "lave", "nave", "pave", "rave", "wave",
    # near "load"
    "road", "toad", "goad",
    # near "make"
    "bake", "cake", "fake", "lake", "rake", "sake", "take", "wake",
    # near "open"
    "oven",
    # near "quit"
    "guit", "knit", "spit", "slit", "grit", "brit",
    # near "exit"
    "edit",
    # near "print"
    "pint",
    # near "clear"
    "clean", "cleat", "chear",
    # near "start"
    "smart", "stark", "stare", "stars", "starn",
    # near "close"
    "chose", "those",
    # near "write"
    "white", "quite", "kite",
    # near "search"
    "starch",
    # near "rename"
    "rename",  # exact, never a typo of itself
    # near "launch"
    "haunch", "paunch", "raunch",
    # near "execute"
    "executes",
    # near "copy"
    "corp",
})

# Static typo dictionary — exact lowercase word match only.
TYPO_MAP: dict = {
    "teh":    "the",
    "pahse":  "phase",
    "giv":    "give",
    "eme":    "me",
    "plese":  "please",
    "pleese": "please",
    "creat":  "create",
    "cretae": "create",   # common transposition
    "craete": "create",
    "launc":  "launch",
    "opne":   "open",
    "clos":   "close",
    "wrtie":  "write",
    "wriet":  "write",
    "renmae": "rename",
    "renam":  "rename",
    "fiel":   "file",
    "flie":   "file",
    "fodler": "folder",
    "foldr":  "folder",
    "direcotry": "directory",
    "directoy":  "directory",
    "adn":    "and",
    "nad":    "and",
    "thn":    "then",
    "thne":   "then",
    "fo":     "of",
    "ot":     "to",
    "hte":    "the",
    "yuo":    "you",
    "taht":   "that",
    "waht":   "what",
    "whta":   "what",
}

# Connector patterns that improve multi-intent splitting reliability.
# Ordered: longer patterns first to avoid partial matches.
CONNECTOR_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r'\bandthen\b', re.IGNORECASE),  "and then"),
    (re.compile(r'\bn\s+then\b', re.IGNORECASE), "and then"),
    (re.compile(r'\bthen\s+and\b', re.IGNORECASE), "and then"),
]

# Explicit near-miss set for destructive keywords.
# These are common misspellings that are edit-distance > 1 from the keyword
# but are clearly intended as destructive commands.
# Checked BEFORE the Levenshtein loop for reliability.
DESTRUCTIVE_NEAR_MISS: dict = {
    # misspelling -> canonical destructive keyword
    "deleet":    "delete",
    "delet":     "delete",
    "del":       "delete",
    "deleete":   "delete",
    "remov":     "remove",
    "remvoe":    "remove",
    "remov":     "remove",
    "rmove":     "remove",
    "foramt":    "format",
    "fromat":    "format",
    "wiipe":     "wipe",
    "wip":       "wipe",
    "shutdwon":  "shutdown",
    "shutdonw":  "shutdown",
    "shutdwn":   "shutdown",
    "eras":      "erase",
    "erease":    "erase",
    "overwrit":  "overwrite",
    "overwrite": "overwrite",  # exact — already in DESTRUCTIVE_KEYWORDS
    "kil":       "kill",
    "terminat":  "terminate",
    "destory":   "destroy",
    "destry":    "destroy",
    "purg":      "purge",
}

# Regex: repeated alphabetic characters (3+) → compress to 2.
# Deliberately excludes digits so "v1.0000.txt" is untouched.
_REPEATED_ALPHA_RE = re.compile(r'([a-zA-Z])\1{2,}')

# Regex: quoted string extraction placeholder.
_QUOTE_RE = re.compile(r'(["\'])(?:(?!\1).)*\1')


# ---------------------------------------------------------------------------
# Levenshtein distance (simple iterative, no external deps)
# ---------------------------------------------------------------------------

def _levenshtein(a: str, b: str) -> int:
    """Compute edit distance between two strings."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    # Use two rows to save memory
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(
                curr[j - 1] + 1,       # insertion
                prev[j] + 1,           # deletion
                prev[j - 1] + cost,    # substitution
            )
        prev = curr
    return prev[lb]


# ---------------------------------------------------------------------------
# Token-level helpers
# ---------------------------------------------------------------------------

def _is_path_token(token: str) -> bool:
    """Return True if the token looks like a filename, path, or version."""
    return '.' in token or '/' in token or '\\' in token


def _is_digit_token(token: str) -> bool:
    """Return True if the token is purely numeric."""
    return token.replace('.', '').replace('-', '').isdigit()


def _should_skip_token(token: str) -> bool:
    """Return True if this token must be left completely untouched."""
    return _is_path_token(token) or _is_digit_token(token) or not token


# ---------------------------------------------------------------------------
# NormalizationEngine
# ---------------------------------------------------------------------------

class NormalizationEngine:
    """
    Phase 6H: Pre-pipeline input normalization.

    Applies a conservative set of transforms to improve intent detection
    without ever guessing at destructive intent or modifying filenames.
    """

    def normalize(self, raw_input: str) -> NormalizationResult:
        """
        Run all normalization transforms on *raw_input*.

        Returns a NormalizationResult describing what changed (if anything).
        """
        original = raw_input
        changes: List[str] = []
        mod_count = 0

        # ── Step 0: Extract quoted strings ──────────────────────────────────
        # Replace quoted sections with placeholders so they are never touched.
        placeholders: List[str] = []

        def _extract_quote(m: re.Match) -> str:
            idx = len(placeholders)
            placeholders.append(m.group(0))
            return f"\x00QUOTE{idx}\x00"

        text = _QUOTE_RE.sub(_extract_quote, raw_input)

        # ── Step 1: Whitespace normalization ────────────────────────────────
        collapsed = re.sub(r'\s+', ' ', text).strip()
        if collapsed != text:
            changes.append("whitespace collapsed")
            mod_count += 1
        text = collapsed

        # ── Step 2: Repeated alphabetic character compression ───────────────
        # Only compresses [a-zA-Z] runs; digits/symbols untouched.
        compressed = _REPEATED_ALPHA_RE.sub(r'\1\1', text)
        if compressed != text:
            changes.append("repeated chars compressed")
            mod_count += 1
        text = compressed

        # ── Step 3: Connector normalization ─────────────────────────────────
        for pattern, replacement in CONNECTOR_PATTERNS:
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                changes.append(f"connector normalised → '{replacement}'")
                mod_count += 1
            text = new_text

        # ── Steps 4 & 5: Token-level transforms ─────────────────────────────
        # We work token-by-token so we can apply exclusion rules precisely.
        tokens = text.split(' ')
        new_tokens: List[str] = []
        dangerous_token: Optional[str] = None

        for token in tokens:
            # Skip placeholders (quoted content)
            if token.startswith('\x00QUOTE') and token.endswith('\x00'):
                new_tokens.append(token)
                continue

            # Skip path/digit tokens
            if _should_skip_token(token):
                new_tokens.append(token)
                continue

            lower = token.lower()

            # ── Destructive keyword guard ────────────────────────────────
            # If the token is already a destructive keyword, leave it alone.
            if lower in DESTRUCTIVE_KEYWORDS:
                new_tokens.append(token)
                continue

            # Check explicit near-miss dictionary first (catches edit-distance
            # > 1 misspellings that are still clearly destructive intent).
            if lower in DESTRUCTIVE_NEAR_MISS:
                dangerous_token = DESTRUCTIVE_NEAR_MISS[lower]
                new_tokens = tokens  # restore original tokens
                break

            # Then check edit-distance 1 from any destructive keyword.
            for dk in DESTRUCTIVE_KEYWORDS:
                if _levenshtein(lower, dk) <= 1:
                    dangerous_token = dk
                    break

            if dangerous_token:
                # Abort token-level processing entirely.
                new_tokens = tokens  # restore original tokens
                break

            # ── Step 4: Typo dictionary ──────────────────────────────────
            if lower in TYPO_MAP:
                corrected = TYPO_MAP[lower]
                changes.append(f"typo '{token}' → '{corrected}'")
                mod_count += 1
                new_tokens.append(corrected)
                continue

            # ── Step 5: Safe keyword edit-distance correction ────────────
            # Skip if the token is a common English word that happens to be
            # edit-distance 1 from a safe keyword (false positive guard).
            if lower in COMMON_WORDS_EXCLUSION:
                new_tokens.append(token)
                continue

            best_match: Optional[str] = None
            for kw in SAFE_KEYWORDS:
                if _levenshtein(lower, kw) <= 1 and lower != kw:
                    # Prefer the shortest edit (greedy first-match is fine
                    # since SAFE_KEYWORDS are all distinct enough).
                    best_match = kw
                    break

            if best_match:
                changes.append(f"keyword '{token}' → '{best_match}'")
                mod_count += 1
                new_tokens.append(best_match)
                continue

            new_tokens.append(token)

        if not dangerous_token:
            text = ' '.join(new_tokens)

        # ── Step 6: Re-insert quoted strings ────────────────────────────────
        for idx, quoted in enumerate(placeholders):
            text = text.replace(f"\x00QUOTE{idx}\x00", quoted)

        # ── Build result ─────────────────────────────────────────────────────
        was_modified = (text != original)
        delta = "; ".join(changes) if changes else "no changes"

        return NormalizationResult(
            normalized=text,
            was_modified=was_modified,
            dangerous_token_detected=dangerous_token,
            delta=delta,
            modification_count=mod_count,
        )
