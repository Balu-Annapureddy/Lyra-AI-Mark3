# -*- coding: utf-8 -*-
"""
tests/test_embedding_router.py
Phase F2: Embedding Intent Router Tests

Strategy:
  - For classification tests, directly inject orthogonal per-intent embeddings
    into router._intent_embeddings (no fake encoder needed for training phrases).
  - FakeModel only needs to handle the single user-input encode() call.
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np


# ---------------------------------------------------------------------------
# Orthogonal intent vectors (8-dim, one-hot per intent)
# ---------------------------------------------------------------------------

INTENT_VEC = {
    "create_file": np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32),
    "delete_file": np.array([0, 1, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32),
    "read_file":   np.array([0, 0, 1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32),
    "open_url":    np.array([0, 0, 0, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32),
    "launch_app":  np.array([0, 0, 0, 0, 1, 0, 0, 0, 0, 0], dtype=np.float32),
    "search_web":  np.array([0, 0, 0, 0, 0, 1, 0, 0, 0, 0], dtype=np.float32),
    "screen_read": np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0], dtype=np.float32),
    "code_help":   np.array([0, 0, 0, 0, 0, 0, 0, 1, 0, 0], dtype=np.float32),
    "conversation":np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 0], dtype=np.float32),
}

# Garbage vector points in a unique dimension (dim-9) with zero cosine
# similarity against every real intent vector.
_GARBAGE = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 1], dtype=np.float32)


def _build_fake_embeddings():
    """Build intent_embeddings dict: each intent gets 3 copies of its vector."""
    return {
        intent: np.stack([vec.copy() for _ in range(3)])
        for intent, vec in INTENT_VEC.items()
    }


# Map: keyword in user text → vector to return from encode()
_KEYWORD_TO_VEC = {
    "create":    INTENT_VEC["create_file"],
    "make":      INTENT_VEC["create_file"],
    "delete":    INTENT_VEC["delete_file"],
    "remove":    INTENT_VEC["delete_file"],
    "read":      INTENT_VEC["read_file"],
    "open":      INTENT_VEC["open_url"],
    "launch":    INTENT_VEC["launch_app"],
    "start":     INTENT_VEC["launch_app"],
    "search":    INTENT_VEC["search_web"],
    "find":      INTENT_VEC["search_web"],
    "screen":    INTENT_VEC["screen_read"],
    "code":      INTENT_VEC["code_help"],
    "debug":     INTENT_VEC["code_help"],
    "hello":     INTENT_VEC["conversation"],
    "hey":       INTENT_VEC["conversation"],
    "hi ":       INTENT_VEC["conversation"],  # trailing space to avoid "this"
}


class FakeModel:
    """Encodes user-input text by keyword matching into intent vectors."""

    def encode(self, texts, convert_to_tensor=False):
        results = []
        for text in texts:
            tl = text.lower()
            matched = False
            for kw, vec in _KEYWORD_TO_VEC.items():
                if kw in tl:
                    results.append(vec.copy())
                    matched = True
                    break
            if not matched:
                results.append(_GARBAGE.copy())
        return np.array(results, dtype=np.float32)


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
def router():
    """Router with FakeModel and pre-injected orthogonal embeddings."""
    with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model"):
        from lyra.semantic.intent_router import EmbeddingIntentRouter
        r = EmbeddingIntentRouter()
        r._model = FakeModel()
        r._loaded = True
        r._intent_embeddings = _build_fake_embeddings()
        yield r
        if r._unload_timer is not None:
            r._unload_timer.cancel()


@pytest.fixture
def unloaded_router():
    with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model"):
        from lyra.semantic.intent_router import EmbeddingIntentRouter
        r = EmbeddingIntentRouter()
        r._loaded = False
        r._model = None
        yield r


# ---------------------------------------------------------------------------
# Tests — Data Loading
# ---------------------------------------------------------------------------

class TestIntentPhrases:

    def test_phrases_loaded(self, router):
        assert len(router._intent_phrases) > 0
        assert "create_file" in router._intent_phrases

    def test_all_intents_present(self, router):
        for name in ["create_file", "delete_file", "read_file", "open_url",
                      "launch_app", "search_web", "screen_read", "code_help",
                      "conversation", "unknown"]:
            assert name in router.get_supported_intents()

    def test_unknown_excluded_from_embeddings(self, router):
        # We built embeddings manually, but the production code also excludes it
        with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model"):
            from lyra.semantic.intent_router import EmbeddingIntentRouter
            r = EmbeddingIntentRouter()
            r._model = FakeModel()
            r._loaded = True
            r._compute_intent_embeddings()
            assert "unknown" not in r._intent_embeddings


# ---------------------------------------------------------------------------
# Tests — Classification
# ---------------------------------------------------------------------------

class TestClassification:

    def test_result_keys(self, router):
        result = router.classify("create a new file")
        assert set(result.keys()) == {"intent", "confidence", "requires_escalation", "method"}

    def test_method_is_embedding(self, router):
        assert router.classify("create a file")["method"] == "embedding"

    @pytest.mark.parametrize("text,expected", [
        ("create a new document", "create_file"),
        ("make a file called notes", "create_file"),
        ("delete the old report", "delete_file"),
        ("remove this file", "delete_file"),
        ("read the notes file", "read_file"),
        ("open the website", "open_url"),
        ("launch the calculator", "launch_app"),
        ("start the terminal", "launch_app"),
        ("search for python tutorials", "search_web"),
        ("find information about AI", "search_web"),
        ("screen capture please", "screen_read"),
        ("debug this python script", "code_help"),
        ("hello there", "conversation"),
    ])
    def test_intent_detection(self, router, text, expected):
        result = router.classify(text)
        assert result["intent"] == expected, f"'{text}' -> expected {expected}, got {result['intent']}"


# ---------------------------------------------------------------------------
# Tests — Thresholds
# ---------------------------------------------------------------------------

class TestThresholds:

    def test_high_confidence_no_escalation(self, router):
        result = router.classify("create a new file")
        # Cos-sim between identical vectors = 1.0 → above threshold
        assert result["confidence"] >= router._confidence_threshold
        assert result["requires_escalation"] is False

    def test_garbage_input_is_unknown(self, router):
        result = router.classify("xyzzy foobar flurble")
        assert result["intent"] == "unknown"
        assert result["requires_escalation"] is True

    def test_mid_confidence_gives_escalation(self, router):
        router._confidence_threshold = 1.1  # Unreachable
        router._mid_confidence_threshold = 0.01
        result = router.classify("create a new file")
        assert result["requires_escalation"] is True
        assert result["intent"] != "unknown"

    def test_below_all_thresholds_gives_unknown(self, router):
        router._confidence_threshold = 1.1
        router._mid_confidence_threshold = 1.1
        result = router.classify("create a new file")
        assert result["intent"] == "unknown"
        assert result["requires_escalation"] is True


# ---------------------------------------------------------------------------
# Tests — Lifecycle
# ---------------------------------------------------------------------------

class TestModelLifecycle:

    def test_lazy_load_triggered(self):
        with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model") as ml:
            from lyra.semantic.intent_router import EmbeddingIntentRouter
            r = EmbeddingIntentRouter()
            assert not r._loaded
            r.classify("hello")
            ml.assert_called_once()

    def test_is_loaded(self, router, unloaded_router):
        assert router.is_loaded() is True
        assert unloaded_router.is_loaded() is False

    def test_unload(self, router):
        router._unload_model()
        assert not router._loaded
        assert router._model is None
        assert router._intent_embeddings == {}

    def test_timer_scheduled(self, router):
        router._unload_after_seconds = 9999
        router.classify("create something")
        assert router._unload_timer is not None
        router._unload_timer.cancel()


# ---------------------------------------------------------------------------
# Tests — Safety & Fallback
# ---------------------------------------------------------------------------

class TestSafetyGuards:

    def test_unloaded_returns_unknown(self, unloaded_router):
        result = unloaded_router.classify("create a file")
        assert result["intent"] == "unknown"
        assert result["requires_escalation"] is True

    def test_fallback_structure(self, router):
        assert router._fallback_result() == {
            "intent": "unknown", "confidence": 0.0,
            "requires_escalation": True, "method": "embedding_fallback",
        }

    def test_encode_error_returns_fallback(self, router):
        router._model.encode = MagicMock(side_effect=RuntimeError("boom"))
        result = router.classify("create a file")
        assert result["intent"] == "unknown"


# ---------------------------------------------------------------------------
# Tests — Pipeline Integration
# ---------------------------------------------------------------------------

class TestPipelineIntegration:

    def test_pipeline_has_router(self):
        with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model"):
            from lyra.core.pipeline import LyraPipeline
            pipe = LyraPipeline()
            assert hasattr(pipe, "embedding_router")
            assert pipe.use_embedding_router is True

    def test_disable_embedding_flag(self):
        with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model"):
            from lyra.core.pipeline import LyraPipeline
            pipe = LyraPipeline()
            pipe.use_embedding_router = False
            result = pipe.process_command("create file test.txt", auto_confirm=True)
            assert result is not None

    def test_regex_fallback(self):
        with patch("lyra.semantic.intent_router.EmbeddingIntentRouter._load_model"):
            with patch("lyra.semantic.intent_router.EmbeddingIntentRouter.classify",
                       return_value={"intent": "unknown", "confidence": 0.0,
                                     "requires_escalation": True, "method": "embedding_fallback"}):
                from lyra.core.pipeline import LyraPipeline
                pipe = LyraPipeline()
                result = pipe.process_command("create file hello.txt", auto_confirm=True)
                assert result is not None
