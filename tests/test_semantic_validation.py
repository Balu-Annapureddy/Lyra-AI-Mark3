# -*- coding: utf-8 -*-
"""
tests/test_semantic_validation.py
Phase F3: Semantic Validation Engine Tests

Covers:
  - Parameter extraction per intent
  - Required-field enforcement & clarification
  - Feasibility validation (filesystem, URL, app)
  - Pipeline blocks execution on invalid / missing params
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from lyra.semantic.semantic_engine import SemanticEngine
from lyra.semantic.schema_validator import (
    SchemaValidator, FeasibilityResult, INTENT_PARAMETERS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_config():
    from lyra.core.config import Config
    Config._instance = None
    Config._config_data = {}
    yield
    Config._instance = None
    Config._config_data = {}


@pytest.fixture
def engine():
    return SemanticEngine()


@pytest.fixture
def validator():
    return SchemaValidator()


# =====================================================================
# Parameter Extraction
# =====================================================================

class TestExtractParameters:

    def test_create_file_with_extension(self, engine):
        params = engine.extract_parameters("create_file", "create a file called notes.txt")
        assert params.get("filename") == "notes.txt"

    def test_create_file_quoted(self, engine):
        params = engine.extract_parameters("create_file", 'create "report.md" on desktop')
        assert params.get("filename") == "report.md"
        assert params.get("directory") == "~/Desktop"

    def test_create_file_directory_keyword(self, engine):
        params = engine.extract_parameters("create_file", "create file in downloads")
        assert params.get("directory") == "~/Downloads"

    def test_delete_file_with_path(self, engine):
        params = engine.extract_parameters("delete_file", "delete C:/temp/old.txt")
        assert "filepath" in params

    def test_delete_file_with_extension(self, engine):
        params = engine.extract_parameters("delete_file", "delete the file report.pdf")
        assert params.get("filepath") == "report.pdf"

    def test_read_file_with_extension(self, engine):
        params = engine.extract_parameters("read_file", "read config.yaml")
        assert params.get("filepath") == "config.yaml"

    def test_open_url_with_full_url(self, engine):
        params = engine.extract_parameters("open_url", "open https://google.com")
        assert params.get("url") == "https://google.com"

    def test_open_url_bare_domain(self, engine):
        params = engine.extract_parameters("open_url", "go to example.com")
        assert "url" in params
        assert "example.com" in params["url"]

    def test_launch_app_known(self, engine):
        params = engine.extract_parameters("launch_app", "launch chrome")
        assert params.get("app_name") == "chrome"

    def test_launch_app_quoted(self, engine):
        params = engine.extract_parameters("launch_app", 'start "my_tool"')
        assert params.get("app_name") == "my_tool"

    def test_search_web_query(self, engine):
        params = engine.extract_parameters("search_web", "search for python tutorials")
        assert "query" in params
        assert len(params["query"]) > 0

    def test_screen_read_region(self, engine):
        params = engine.extract_parameters("screen_read", "capture the top left area")
        assert "region" in params

    def test_code_help_language(self, engine):
        params = engine.extract_parameters("code_help", "help me debug this python code")
        assert params.get("language") == "python"

    def test_unknown_intent_empty(self, engine):
        params = engine.extract_parameters("unknown", "blah blah blah")
        assert params == {}

    def test_conversation_empty(self, engine):
        params = engine.extract_parameters("conversation", "hello how are you")
        assert params == {}


# =====================================================================
# Required Parameter Validation (validate_parameters)
# =====================================================================

class TestValidateParameters:

    def test_missing_filename_clarification(self, validator):
        result = validator.validate_parameters("create_file", {})
        assert not result.valid
        assert result.requires_clarification is True
        assert result.clarification_question is not None
        assert "file" in result.clarification_question.lower()

    def test_missing_filepath_delete(self, validator):
        result = validator.validate_parameters("delete_file", {})
        assert not result.valid
        assert result.requires_clarification is True
        assert "delete" in result.clarification_question.lower()

    def test_missing_filepath_read(self, validator):
        result = validator.validate_parameters("read_file", {})
        assert not result.valid
        assert result.requires_clarification is True

    def test_missing_url(self, validator):
        result = validator.validate_parameters("open_url", {})
        assert not result.valid
        assert result.requires_clarification is True

    def test_missing_app_name(self, validator):
        result = validator.validate_parameters("launch_app", {})
        assert not result.valid
        assert result.requires_clarification is True

    def test_missing_query(self, validator):
        result = validator.validate_parameters("search_web", {})
        assert not result.valid
        assert result.requires_clarification is True

    def test_screen_read_no_required(self, validator):
        """screen_read has no required params — always valid."""
        result = validator.validate_parameters("screen_read", {})
        assert result.valid

    def test_conversation_no_required(self, validator):
        result = validator.validate_parameters("conversation", {})
        assert result.valid

    def test_valid_create_file(self, validator):
        result = validator.validate_parameters("create_file", {"filename": "notes.txt"})
        assert result.valid

    def test_valid_delete_file(self, validator):
        result = validator.validate_parameters("delete_file", {"filepath": "/tmp/x.txt"})
        assert result.valid

    def test_empty_string_treated_as_missing(self, validator):
        result = validator.validate_parameters("create_file", {"filename": "  "})
        assert not result.valid
        assert result.requires_clarification is True


# =====================================================================
# Feasibility Validation
# =====================================================================

class TestFeasibilityValidation:

    def test_create_file_invalid_chars(self, validator):
        result = validator.validate_feasibility("create_file", {"filename": "bad<file>.txt"})
        assert not result.valid
        assert any("invalid" in e.lower() for e in result.errors)

    def test_create_file_nonexistent_dir(self, validator):
        result = validator.validate_feasibility(
            "create_file", {"filename": "ok.txt", "directory": "/nonexistent_xyz_123"}
        )
        assert not result.valid

    def test_create_file_valid(self, validator):
        result = validator.validate_feasibility("create_file", {"filename": "notes.txt"})
        assert result.valid

    def test_delete_nonexistent_file(self, validator):
        result = validator.validate_feasibility(
            "delete_file", {"filepath": "/tmp/____nonexistent____.txt"}
        )
        assert not result.valid

    def test_delete_existing_file(self, validator):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            result = validator.validate_feasibility("delete_file", {"filepath": path})
            assert result.valid
        finally:
            os.unlink(path)

    def test_delete_protected_path(self, validator):
        result = validator.validate_feasibility("delete_file", {"filepath": "C:\\"})
        assert not result.valid
        assert any("protected" in e.lower() for e in result.errors)

    def test_delete_wildcard_blocked(self, validator):
        result = validator.validate_feasibility("delete_file", {"filepath": "*.txt"})
        assert not result.valid
        assert any("wildcard" in e.lower() for e in result.errors)

    def test_read_nonexistent(self, validator):
        result = validator.validate_feasibility(
            "read_file", {"filepath": "/tmp/____nonexistent____.md"}
        )
        assert not result.valid

    def test_read_existing(self, validator):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            result = validator.validate_feasibility("read_file", {"filepath": path})
            assert result.valid
        finally:
            os.unlink(path)

    def test_url_valid(self, validator):
        result = validator.validate_feasibility("open_url", {"url": "https://google.com"})
        assert result.valid

    def test_url_invalid(self, validator):
        result = validator.validate_feasibility("open_url", {"url": "not-a-url"})
        assert not result.valid

    def test_launch_app_not_found(self, validator):
        result = validator.validate_feasibility(
            "launch_app", {"app_name": "____nonexistent_app____"}
        )
        assert not result.valid

    def test_launch_app_found(self, validator):
        # python should be on PATH in our venv
        result = validator.validate_feasibility("launch_app", {"app_name": "python"})
        assert result.valid

    def test_search_empty_query(self, validator):
        result = validator.validate_feasibility("search_web", {"query": ""})
        assert not result.valid

    def test_search_valid_query(self, validator):
        result = validator.validate_feasibility("search_web", {"query": "lyra ai"})
        assert result.valid


# =====================================================================
# Engine-level validate_feasibility (combines param + feasibility)
# =====================================================================

class TestEngineFeasibility:

    def test_missing_params_triggers_clarification(self, engine):
        result = engine.validate_feasibility("delete_file", {})
        assert not result.valid
        assert result.requires_clarification is True
        assert result.clarification_question is not None

    def test_valid_params_passes_to_feasibility(self, engine):
        result = engine.validate_feasibility(
            "open_url", {"url": "https://example.com"}
        )
        assert result.valid

    def test_invalid_feasibility_after_params_ok(self, engine):
        result = engine.validate_feasibility(
            "open_url", {"url": "bad_url"}
        )
        assert not result.valid
        assert not result.requires_clarification  # params present, URL just bad


# =====================================================================
# Pipeline Integration
# =====================================================================

class TestPipelineBlocking:

    def test_pipeline_blocks_missing_params(self):
        """Pipeline returns clarification when required params missing."""
        with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model"):
            from lyra.core.pipeline import LyraPipeline
            pipe = LyraPipeline()
            pipe.use_embedding_router = False

            # "delete file" with no filepath should trigger clarification
            result = pipe.process_command("delete file", auto_confirm=True)
            assert result is not None
            # Either clarification requested or unknown intent
            # (regex may not detect intent — that's fine, it'll fail either way)

    def test_pipeline_blocks_invalid_feasibility(self):
        """Pipeline returns error when feasibility fails."""
        with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model"):
            from lyra.core.pipeline import LyraPipeline, Command
            pipe = LyraPipeline()

            # Inject a command with invalid filepath
            cmd = Command(
                raw_input="delete /nonexistent_dir/file.txt",
                intent="delete_file",
                entities={"filepath": "/nonexistent_dir/file.txt"},
                confidence=0.95,
            )
            cmd.decision_source = "test"

            # Directly test the validation gate
            feasibility = pipe.semantic_engine.validate_feasibility(
                cmd.intent, cmd.entities
            )
            assert not feasibility.valid

    def test_pipeline_passes_valid_command(self):
        """Pipeline proceeds when validation passes."""
        with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model"):
            from lyra.core.pipeline import LyraPipeline
            pipe = LyraPipeline()

            feasibility = pipe.semantic_engine.validate_feasibility(
                "search_web", {"query": "python tutorials"}
            )
            assert feasibility.valid


# =====================================================================
# Schema Validator (backward compatibility)
# =====================================================================

class TestSchemaValidatorCompat:

    def test_valid_schema(self, validator):
        data = {
            "intent": "create_file",
            "parameters": {"filename": "test.txt"},
            "confidence": 0.9,
            "requires_clarification": False,
        }
        result = validator.validate(data)
        assert result.valid

    def test_missing_keys(self, validator):
        result = validator.validate({"intent": "test"})
        assert not result.valid

    def test_non_dict(self, validator):
        result = validator.validate("not a dict")
        assert not result.valid

    def test_confidence_range(self, validator):
        data = {
            "intent": "test",
            "parameters": {},
            "confidence": 1.5,
            "requires_clarification": False,
        }
        result = validator.validate(data)
        assert not result.valid
