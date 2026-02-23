# -*- coding: utf-8 -*-
"""
lyra/semantic/intent_router.py
Phase F2: Embedding Intent Router

Semantic intent classification using sentence-transformers.
Lazy-loaded, resource-aware, CPU-only.
Falls back gracefully if model cannot load.
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from lyra.core.config import Config
from lyra.core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingIntentRouter:
    """
    Embedding-based intent classifier using sentence-transformers.

    - Lazy-loaded: model loads on first classify() call
    - Auto-unloads after configurable idle timeout
    - CPU-only, < 500MB RAM target
    - Returns structured classification result
    - Falls back to unknown if model unavailable
    """

    def __init__(self, config: Optional[Config] = None):
        self._config = config or Config()

        # Config values
        self._model_name: str = self._config.get(
            "embedding.model", "all-MiniLM-L6-v2"
        )
        self._lazy_load: bool = self._config.get("embedding.lazy_load", True)
        self._confidence_threshold: float = self._config.get(
            "embedding.confidence_threshold", 0.75
        )
        self._mid_confidence_threshold: float = self._config.get(
            "embedding.mid_confidence_threshold", 0.5
        )
        self._unload_after_seconds: int = self._config.get(
            "embedding.unload_after_seconds", 120
        )
        self._cache_embeddings: bool = self._config.get(
            "embedding.cache_embeddings", True
        )
        self._device: str = self._config.get("embedding.device", "cpu")

        # Resource guard
        self._warn_threshold_gb: float = self._config.get(
            "resource_monitor.warn_threshold_gb", 3.5
        )

        # Internal state
        self._model = None
        self._intent_embeddings: Dict[str, Any] = {}
        self._intent_phrases: Dict[str, List[str]] = {}
        self._last_used: float = 0.0
        self._lock = threading.Lock()
        self._unload_timer: Optional[threading.Timer] = None
        self._loaded = False

        # Load intent phrases from data file
        self._load_intent_phrases()

        logger.info(
            "EmbeddingIntentRouter initialized (model=%s, lazy=%s)",
            self._model_name,
            self._lazy_load,
        )

    # ------------------------------------------------------------------
    # Intent phrase loading (lightweight, always runs)
    # ------------------------------------------------------------------

    def _load_intent_phrases(self):
        """Load intent training phrases from data/intent_embeddings.json."""
        project_root = Path(__file__).parent.parent.parent
        data_path = project_root / "data" / "intent_embeddings.json"

        if not data_path.exists():
            logger.warning("Intent phrases file not found: %s", data_path)
            self._intent_phrases = {}
            return

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                self._intent_phrases = json.load(f)
            logger.info(
                "Loaded intent phrases for %d intents", len(self._intent_phrases)
            )
        except Exception as e:
            logger.error("Failed to load intent phrases: %s", e)
            self._intent_phrases = {}

    # ------------------------------------------------------------------
    # Model lifecycle (lazy load / unload)
    # ------------------------------------------------------------------

    def _check_ram_available(self) -> bool:
        """Return True if enough RAM is available to load the model."""
        try:
            import psutil

            mem = psutil.virtual_memory()
            available_gb = mem.available / (1024 ** 3)
            if available_gb < self._warn_threshold_gb:
                logger.warning(
                    "Low RAM (%.1f GB free < %.1f GB threshold). "
                    "Skipping embedding model load.",
                    available_gb,
                    self._warn_threshold_gb,
                )
                return False
            return True
        except ImportError:
            # psutil not installed — optimistic
            return True

    def _load_model(self):
        """Load the sentence-transformer model and precompute embeddings."""
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return

            if not self._check_ram_available():
                return

            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model: %s ...", self._model_name)
                start = time.perf_counter()

                self._model = SentenceTransformer(
                    self._model_name, device=self._device
                )

                elapsed = time.perf_counter() - start
                logger.info("Embedding model loaded in %.2f s", elapsed)

                # Precompute intent embeddings
                self._compute_intent_embeddings()
                self._loaded = True
                self._last_used = time.monotonic()

            except Exception as e:
                logger.error("Failed to load embedding model: %s", e)
                self._model = None
                self._loaded = False

    def _unload_model(self):
        """Release model and embeddings to free RAM."""
        with self._lock:
            if not self._loaded:
                return

            logger.info("Unloading embedding model to free RAM")
            self._model = None
            self._intent_embeddings = {}
            self._loaded = False

            # Cancel any pending unload timer
            if self._unload_timer is not None:
                self._unload_timer.cancel()
                self._unload_timer = None

    def _schedule_unload(self):
        """Schedule model unload after idle timeout."""
        if self._unload_timer is not None:
            self._unload_timer.cancel()

        self._unload_timer = threading.Timer(
            self._unload_after_seconds, self._unload_model
        )
        self._unload_timer.daemon = True
        self._unload_timer.start()

    def _compute_intent_embeddings(self):
        """Precompute embeddings for all intent training phrases."""
        if self._model is None or not self._intent_phrases:
            return

        logger.info("Precomputing intent embeddings...")
        start = time.perf_counter()

        for intent, phrases in self._intent_phrases.items():
            if not phrases:
                continue
            # Skip "unknown" — it's a fallback category, not a match target
            if intent == "unknown":
                continue
            embeddings = self._model.encode(phrases, convert_to_tensor=False)
            self._intent_embeddings[intent] = embeddings

        elapsed = time.perf_counter() - start
        logger.info(
            "Precomputed embeddings for %d intents in %.2f s",
            len(self._intent_embeddings),
            elapsed,
        )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify user input into an intent using embedding similarity.

        Args:
            text: Raw user input (post-normalization)

        Returns:
            {
                "intent": str,
                "confidence": float,
                "requires_escalation": bool,
                "method": "embedding"
            }
        """
        # Ensure model is loaded
        if not self._loaded:
            self._load_model()

        # If model still not loaded (RAM guard or import error) → unknown
        if not self._loaded or self._model is None:
            return self._fallback_result()

        try:
            self._last_used = time.monotonic()

            # Encode user input
            input_embedding = self._model.encode(
                [text], convert_to_tensor=False
            )[0]

            # Find best matching intent via cosine similarity
            best_intent = "unknown"
            best_score = 0.0

            for intent, phrase_embeddings in self._intent_embeddings.items():
                similarities = self._cosine_similarity(
                    input_embedding, phrase_embeddings
                )
                max_sim = float(max(similarities))

                if max_sim > best_score:
                    best_score = max_sim
                    best_intent = intent

            # Apply thresholds
            requires_escalation = False

            if best_score >= self._confidence_threshold:
                requires_escalation = False
            elif best_score >= self._mid_confidence_threshold:
                requires_escalation = True
            else:
                best_intent = "unknown"
                requires_escalation = True

            # Schedule idle unload
            self._schedule_unload()

            return {
                "intent": best_intent,
                "confidence": round(best_score, 4),
                "requires_escalation": requires_escalation,
                "method": "embedding",
            }

        except Exception as e:
            logger.error("Embedding classification failed: %s", e)
            return self._fallback_result()

    def _cosine_similarity(self, vec, matrix) -> List[float]:
        """Compute cosine similarity between a vector and each row of a matrix."""
        import numpy as np

        vec = np.array(vec, dtype=np.float32)
        matrix = np.array(matrix, dtype=np.float32)

        # Normalize
        vec_norm = vec / (np.linalg.norm(vec) + 1e-10)
        matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
        matrix_normed = matrix / matrix_norms

        similarities = matrix_normed @ vec_norm
        return similarities.tolist()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fallback_result(self) -> Dict[str, Any]:
        """Return a safe unknown result when model is unavailable."""
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "requires_escalation": True,
            "method": "embedding_fallback",
        }

    def is_loaded(self) -> bool:
        """Check if the embedding model is currently loaded."""
        return self._loaded

    def get_supported_intents(self) -> List[str]:
        """Return list of supported intent names."""
        return list(self._intent_phrases.keys())
