# -*- coding: utf-8 -*-
"""
Semantic Schema Validator
Phase F3: Enhanced with per-intent parameter definitions and feasibility checks.
Enforces strict structure on intent outputs.
Rejects malformed data immediately.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from lyra.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of schema validation"""
    valid: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class FeasibilityResult:
    """Result of feasibility validation (Phase F3)."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    requires_clarification: bool = False
    clarification_question: Optional[str] = None


# ---------------------------------------------------------------------------
# Per-intent parameter definitions
# ---------------------------------------------------------------------------

INTENT_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "create_file": {
        "required": ["filename"],
        "optional": ["directory", "content"],
        "clarification": "What should I name the new file?",
    },
    "delete_file": {
        "required": ["filepath"],
        "optional": [],
        "clarification": "Which file would you like me to delete?",
    },
    "read_file": {
        "required": ["filepath"],
        "optional": [],
        "clarification": "Which file would you like me to read?",
    },
    "open_url": {
        "required": ["url"],
        "optional": [],
        "clarification": "Which URL should I open?",
    },
    "launch_app": {
        "required": ["app_name"],
        "optional": [],
        "clarification": "Which application should I launch?",
    },
    "search_web": {
        "required": ["query"],
        "optional": [],
        "clarification": "What would you like me to search for?",
    },
    "screen_read": {
        "required": [],
        "optional": ["region"],
        "clarification": None,
    },
    "code_help": {
        "required": [],
        "optional": ["code_snippet", "language", "error_message"],
        "clarification": None,
    },
    "conversation": {
        "required": [],
        "optional": [],
        "clarification": None,
    },
    "unknown": {
        "required": [],
        "optional": [],
        "clarification": None,
    },
}

# Characters forbidden in filenames (Windows + POSIX union)
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Protected paths that must never be deleted
_PROTECTED_PATHS = {
    "/", "C:\\", "C:/", "/root", "/home", "/etc", "/usr", "/bin",
    "/var", "/sys", "/proc", "/boot",
}
_PROTECTED_PREFIXES = (
    "C:\\Windows", "C:\\Program Files", "C:\\System",
    "/usr/", "/etc/", "/bin/", "/sbin/", "/var/", "/sys/", "/proc/",
)


class SchemaValidator:
    """
    Strict validator for semantic intent outputs.
    Ensures downstream components always get clean data.

    Phase F3 additions:
        - validate_parameters(): per-intent required field enforcement
        - validate_feasibility(): filesystem / URL / app existence checks
    """

    REQUIRED_KEYS = {"intent", "parameters", "confidence", "requires_clarification"}

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a raw intent dictionary against strict schema.

        Args:
            data: Raw dictionary from local model

        Returns:
            ValidationResult with cleaned data or error
        """
        if not isinstance(data, dict):
            return ValidationResult(False, error="Output must be a dictionary")

        # 1. Check for missing keys
        missing = self.REQUIRED_KEYS - data.keys()
        if missing:
            return ValidationResult(False, error=f"Missing required keys: {missing}")

        # 2. Check for extra keys (Strictness)
        extra = data.keys() - self.REQUIRED_KEYS
        if extra:
            return ValidationResult(False, error=f"Unknown keys found: {extra}")

        # 3. Type validation
        if not isinstance(data["intent"], str):
            return ValidationResult(False, error="Field 'intent' must be a string")

        if not isinstance(data["parameters"], dict):
            return ValidationResult(False, error="Field 'parameters' must be a dictionary")

        if not isinstance(data["confidence"], (int, float)):
             return ValidationResult(False, error="Field 'confidence' must be specific float")

        if not isinstance(data["requires_clarification"], bool):
            return ValidationResult(False, error="Field 'requires_clarification' must be a boolean")

        # 4. Value range validation
        confidence = float(data["confidence"])
        if not (0.0 <= confidence <= 1.0):
            return ValidationResult(False, error="Confidence must be between 0.0 and 1.0")

        # 5. Semantic validity (basic)
        if not data["intent"].strip():
            return ValidationResult(False, error="Intent string cannot be empty")

        # Return validated data (cast types if needed)
        cleaned_data = {
            "intent": data["intent"].strip(),
            "parameters": data["parameters"],
            "confidence": confidence,
            "requires_clarification": data["requires_clarification"]
        }

        return ValidationResult(True, data=cleaned_data)

    # ------------------------------------------------------------------
    # Phase F3: Parameter validation
    # ------------------------------------------------------------------

    def validate_parameters(self, intent: str, params: Dict[str, Any]) -> FeasibilityResult:
        """
        Check that all required parameters for the given intent are present.

        Returns FeasibilityResult with clarification question if missing.
        """
        spec = INTENT_PARAMETERS.get(intent)
        if spec is None:
            # Unknown intent — nothing to validate
            return FeasibilityResult(valid=True)

        missing = [
            key for key in spec["required"]
            if key not in params or not str(params[key]).strip()
        ]

        if missing:
            question = spec.get("clarification") or (
                f"I need more information: {', '.join(missing)}"
            )
            return FeasibilityResult(
                valid=False,
                errors=[f"Missing required parameter(s): {', '.join(missing)}"],
                requires_clarification=True,
                clarification_question=question,
            )

        return FeasibilityResult(valid=True)

    # ------------------------------------------------------------------
    # Phase F3: Feasibility validation
    # ------------------------------------------------------------------

    def validate_feasibility(self, intent: str, params: Dict[str, Any]) -> FeasibilityResult:
        """
        Verify that the command can actually be executed.

        Checks filesystem existence, URL format, app availability, etc.
        Never assumes defaults for missing required parameters.
        """
        handler = _FEASIBILITY_HANDLERS.get(intent)
        if handler is None:
            return FeasibilityResult(valid=True)
        return handler(params)


# ======================================================================
# Feasibility handlers (module-level, stateless)
# ======================================================================

def _validate_create_file(params: Dict[str, Any]) -> FeasibilityResult:
    filename = params.get("filename", "")
    directory = params.get("directory", "")
    errors: List[str] = []

    # Filename character check
    if _INVALID_FILENAME_CHARS.search(filename):
        errors.append(
            f"Filename '{filename}' contains invalid characters."
        )

    # Directory existence
    if directory and not os.path.isdir(directory):
        errors.append(f"Directory '{directory}' does not exist.")

    return FeasibilityResult(valid=len(errors) == 0, errors=errors)


def _validate_delete_file(params: Dict[str, Any]) -> FeasibilityResult:
    filepath = params.get("filepath", "")
    errors: List[str] = []

    # Protect system paths
    abs_path = os.path.abspath(filepath) if filepath else ""
    normalised = abs_path.replace("\\", "/")

    if abs_path in _PROTECTED_PATHS or normalised in _PROTECTED_PATHS:
        errors.append("Cannot delete protected system path.")
        return FeasibilityResult(valid=False, errors=errors)

    for prefix in _PROTECTED_PREFIXES:
        if normalised.startswith(prefix.replace("\\", "/")):
            errors.append(
                f"Cannot delete files inside protected directory '{prefix}'."
            )
            return FeasibilityResult(valid=False, errors=errors)

    # Wildcard check
    if "*" in filepath or "?" in filepath:
        errors.append("Wildcard deletes are not allowed.")
        return FeasibilityResult(valid=False, errors=errors)

    # Existence check
    if not os.path.exists(filepath):
        errors.append(f"File '{filepath}' does not exist.")

    return FeasibilityResult(valid=len(errors) == 0, errors=errors)


def _validate_read_file(params: Dict[str, Any]) -> FeasibilityResult:
    filepath = params.get("filepath", "")
    errors: List[str] = []

    if not os.path.exists(filepath):
        errors.append(f"File '{filepath}' does not exist.")

    return FeasibilityResult(valid=len(errors) == 0, errors=errors)


def _validate_open_url(params: Dict[str, Any]) -> FeasibilityResult:
    url = params.get("url", "")
    errors: List[str] = []

    url_pattern = re.compile(
        r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE
    )
    if not url_pattern.match(url):
        errors.append(f"'{url}' is not a valid URL (must start with http:// or https://).")

    return FeasibilityResult(valid=len(errors) == 0, errors=errors)


def _validate_launch_app(params: Dict[str, Any]) -> FeasibilityResult:
    app_name = params.get("app_name", "")
    errors: List[str] = []

    # Try shutil.which (works for executables on PATH)
    if shutil.which(app_name) is None:
        errors.append(f"Application '{app_name}' not found on system PATH.")

    return FeasibilityResult(valid=len(errors) == 0, errors=errors)


def _validate_search_web(params: Dict[str, Any]) -> FeasibilityResult:
    query = params.get("query", "")
    errors: List[str] = []

    if not query.strip():
        errors.append("Search query cannot be empty.")

    return FeasibilityResult(valid=len(errors) == 0, errors=errors)


_FEASIBILITY_HANDLERS = {
    "create_file": _validate_create_file,
    "delete_file": _validate_delete_file,
    "read_file": _validate_read_file,
    "open_url": _validate_open_url,
    "launch_app": _validate_launch_app,
    "search_web": _validate_search_web,
}
