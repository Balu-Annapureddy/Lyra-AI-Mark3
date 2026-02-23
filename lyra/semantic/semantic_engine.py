# -*- coding: utf-8 -*-
"""
Semantic Engine orchestrator
Phase F3: Enhanced with parameter extraction and feasibility validation.
Coordinations: Model -> Validation -> Confidence -> Parameter Extraction
Entry point for the semantic layer.
"""

import re
from typing import Dict, Any, Optional, List
from lyra.core.logger import get_logger
from lyra.semantic.local_model import LocalSemanticModel
from lyra.semantic.schema_validator import SchemaValidator, FeasibilityResult
from lyra.semantic.confidence_engine import ConfidenceEngine

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for parameter extraction (deterministic, no LLM)
# ---------------------------------------------------------------------------

# Filename patterns — matches quoted filenames or bare words with extensions
_FILENAME_RE = re.compile(
    r'''(?:["']([^"']+)["'])'''                       # quoted: "foo.txt"
    r'''|(\b[\w\-]+\.(?:txt|py|md|json|yaml|yml'''    # bare extension match
    r'''|csv|log|html|css|js|ts|xml|ini|cfg'''
    r'''|pdf|docx?|xlsx?|pptx?|jpg|png|gif|svg'''
    r'''|sh|bat|ps1|rb|java|c|cpp|h|rs|go)\b)''',
    re.IGNORECASE,
)

# URL pattern
_URL_RE = re.compile(
    r'(https?://[^\s,;"\'>]+)',
    re.IGNORECASE,
)

# Directory keywords
_DIR_KEYWORDS = {
    "desktop":   "~/Desktop",
    "downloads": "~/Downloads",
    "documents": "~/Documents",
    "home":      "~",
}

# Filepath-style pattern: requires a path separator after prefix
_FILEPATH_RE = re.compile(
    r'''((?:[A-Za-z]:[/\\]|~[/\\]|\.[/\\]|\.\.)[^\s,;]+)'''
)

# Quoted string extraction (for general text parameters)
_QUOTED_RE = re.compile(r'''["']([^"']+)["']''')

# App name patterns — common apps and executables
_COMMON_APPS = {
    "notepad", "calculator", "calc", "chrome", "firefox", "edge",
    "spotify", "vscode", "code", "terminal", "cmd", "powershell",
    "explorer", "vlc", "teams", "slack", "discord", "obs",
    "gimp", "paint", "word", "excel", "outlook",
}


class SemanticEngine:
    """
    Main entry point for semantic intent parsing.
    Orchestrates the local model, validation, and scoring.

    Phase F3: Adds extract_parameters() and validate_feasibility().
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        self.model = LocalSemanticModel()
        self.validator = SchemaValidator()
        self.confidence_engine = ConfidenceEngine()
        self.confidence_threshold = 0.6
        self.logger.info("Semantic Intent Layer initialized")

    def parse_semantic_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Convert natural language to structured intent(s).
        Supports splitting commands like "do A and do B".
        """
        segments = self._split_command(user_input)

        parsed_intents = []
        requires_clarification = False
        min_confidence = 1.0

        for segment in segments:
            intent = self._process_single_intent(segment)
            parsed_intents.append(intent)

            if intent.get("requires_clarification"):
                requires_clarification = True

            conf = intent.get("confidence", 0.0)
            if conf < min_confidence:
                min_confidence = conf

        # If no valid intents (empty input?), fallback
        if not parsed_intents:
            return self._create_fallback_response()

        return {
            "intents": parsed_intents,
            "confidence": min_confidence,
            "requires_clarification": requires_clarification
        }

    def _split_command(self, text: str) -> List[str]:
        """Split command by 'and then', 'and', 'then'."""
        text = text.lower().strip()

        if " and then " in text:
            return text.split(" and then ", 1)
        if " and " in text:
            return text.split(" and ", 1)
        if " then " in text:
            return text.split(" then ", 1)

        return [text]

    def _process_single_intent(self, user_input: str) -> Dict[str, Any]:
        """Process a single segment."""
        try:
            # 1. Generate Raw Output
            raw_intent = self.model.generate_structured_intent(user_input)

            # 2. Schema Validation
            validation = self.validator.validate(raw_intent)
            if not validation.valid:
                self.logger.warning(f"Semantic validation failed: {validation.error}")
                return self._create_single_fallback()

            validated_intent = validation.data

            # 3. Confidence Scoring
            adjusted_confidence = self.confidence_engine.calculate_score(validated_intent)
            validated_intent["confidence"] = adjusted_confidence

            # 4. Clarification Check
            if adjusted_confidence < self.confidence_threshold:
                validated_intent["requires_clarification"] = True

            return validated_intent

        except Exception as e:
            self.logger.error(f"Semantic engine error: {e}")
            return self._create_single_fallback()

    # ------------------------------------------------------------------
    # Phase F3: Parameter Extraction
    # ------------------------------------------------------------------

    def extract_parameters(self, intent: str, text: str) -> Dict[str, Any]:
        """
        Extract structured parameters from user text for the given intent.

        Uses regex patterns, path detection, quoted strings, and
        directory keyword resolution. No LLM or embedding usage.

        Args:
            intent: Classified intent string
            text:   Raw (or normalised) user text

        Returns:
            Dictionary of extracted parameters.
        """
        handler = _PARAM_EXTRACTORS.get(intent)
        if handler is None:
            return {}
        return handler(text)

    # ------------------------------------------------------------------
    # Phase F3: Feasibility Validation (delegates to SchemaValidator)
    # ------------------------------------------------------------------

    def validate_feasibility(self, intent: str, params: Dict[str, Any]) -> FeasibilityResult:
        """
        Validate that the command is feasible.

        First checks required parameters, then filesystem / URL / app feasibility.
        """
        # 1. Check required parameters are present
        param_result = self.validator.validate_parameters(intent, params)
        if not param_result.valid:
            return param_result

        # 2. Check filesystem / URL / app feasibility
        return self.validator.validate_feasibility(intent, params)

    # ------------------------------------------------------------------
    # Fallbacks
    # ------------------------------------------------------------------

    def _create_single_fallback(self) -> Dict[str, Any]:
        """Fallback for a single intent."""
        return {
            "intent": "unknown",
            "parameters": {},
            "confidence": 0.0,
            "requires_clarification": True
        }

    def _create_fallback_response(self) -> Dict[str, Any]:
        """Generate safe fallback response on error (legacy structure wrapper)."""
        single = self._create_single_fallback()
        return {
            "intents": [single],
            "confidence": 0.0,
            "requires_clarification": True
        }


# ======================================================================
# Parameter extraction handlers (module-level, stateless)
# ======================================================================

def _extract_create_file(text: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    # Try filename
    m = _FILENAME_RE.search(text)
    if m:
        params["filename"] = m.group(1) or m.group(2)

    # Try directory keyword
    text_lower = text.lower()
    for keyword, path in _DIR_KEYWORDS.items():
        if keyword in text_lower:
            params["directory"] = path
            break

    # Try explicit path
    if "directory" not in params:
        pm = _FILEPATH_RE.search(text)
        if pm:
            candidate = pm.group(1)
            # Don't assign filepath as directory if it looks like a filename
            if "." not in candidate.split("/")[-1].split("\\")[-1]:
                params["directory"] = candidate

    # Try quoted content
    quoted = _QUOTED_RE.findall(text)
    if quoted:
        # If filename not found yet, first quoted string is filename
        if "filename" not in params:
            params["filename"] = quoted[0]
        # If we have more quoted strings, treat second as content
        if len(quoted) > 1 and "content" not in params:
            params["content"] = quoted[1]

    return params


def _extract_delete_file(text: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    # Try filename with extension first
    m = _FILENAME_RE.search(text)
    if m:
        params["filepath"] = m.group(1) or m.group(2)
        return params

    # Try explicit path
    pm = _FILEPATH_RE.search(text)
    if pm:
        params["filepath"] = pm.group(1)
        return params

    # Try quoted string
    quoted = _QUOTED_RE.findall(text)
    if quoted:
        params["filepath"] = quoted[0]

    return params


def _extract_read_file(text: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    # Try filename with extension first
    m = _FILENAME_RE.search(text)
    if m:
        params["filepath"] = m.group(1) or m.group(2)
        return params

    # Try explicit path
    pm = _FILEPATH_RE.search(text)
    if pm:
        params["filepath"] = pm.group(1)
        return params

    # Try quoted string
    quoted = _QUOTED_RE.findall(text)
    if quoted:
        params["filepath"] = quoted[0]

    return params


def _extract_open_url(text: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    # Try URL
    m = _URL_RE.search(text)
    if m:
        params["url"] = m.group(1)
        return params

    # Try quoted string that looks like a domain
    quoted = _QUOTED_RE.findall(text)
    for q in quoted:
        if "." in q and " " not in q:
            params["url"] = q if q.startswith("http") else f"https://{q}"
            return params

    # Try bare domain (simple heuristic)
    domain_re = re.compile(r'\b([\w\-]+\.(?:com|org|net|io|dev|edu|gov|co)\b[^\s]*)', re.I)
    dm = domain_re.search(text)
    if dm:
        params["url"] = f"https://{dm.group(1)}"

    return params


def _extract_launch_app(text: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    text_lower = text.lower()

    # Check for known apps
    for app in _COMMON_APPS:
        if app in text_lower:
            params["app_name"] = app
            return params

    # Try quoted string
    quoted = _QUOTED_RE.findall(text)
    if quoted:
        params["app_name"] = quoted[0]
        return params

    # Heuristic: last word after "open/launch/start/run"
    trigger = re.search(r'\b(?:open|launch|start|run)\s+(?:the\s+)?(\w+)', text_lower)
    if trigger:
        params["app_name"] = trigger.group(1)

    return params


def _extract_search_web(text: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    # Strip the action prefix to get the query
    stripped = re.sub(
        r'^(?:search\s+(?:for|about|the\s+web\s+for)?'
        r'|look\s+up\s+(?:on\s+the\s+internet\s+)?'
        r'|find\s+(?:information\s+)?(?:about|on)?'
        r'|google\s+(?:this\s+for\s+me)?)\s*',
        '', text, flags=re.I,
    ).strip()

    if stripped:
        params["query"] = stripped

    # Fallback: use the whole text
    if "query" not in params and text.strip():
        params["query"] = text.strip()

    return params


def _extract_screen_read(text: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    # Optional region parsing (e.g., "top left", "bottom right")
    region_pattern = re.compile(
        r'\b(top|bottom|left|right|center|full|entire)\b', re.I
    )
    regions = region_pattern.findall(text.lower())
    if regions:
        params["region"] = " ".join(regions)

    return params


def _extract_code_help(text: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    # Try code block or quoted snippet
    code_block = re.search(r'```(.+?)```', text, re.DOTALL)
    if code_block:
        params["code_snippet"] = code_block.group(1).strip()
    else:
        quoted = _QUOTED_RE.findall(text)
        if quoted:
            params["code_snippet"] = quoted[0]

    # Try language detection
    langs = {"python", "javascript", "java", "c++", "c#", "ruby",
             "go", "rust", "typescript", "html", "css", "sql", "bash"}
    text_lower = text.lower()
    for lang in langs:
        if lang in text_lower:
            params["language"] = lang
            break

    return params


_PARAM_EXTRACTORS = {
    "create_file": _extract_create_file,
    "delete_file": _extract_delete_file,
    "read_file":   _extract_read_file,
    "open_url":    _extract_open_url,
    "launch_app":  _extract_launch_app,
    "search_web":  _extract_search_web,
    "screen_read": _extract_screen_read,
    "code_help":   _extract_code_help,
}
