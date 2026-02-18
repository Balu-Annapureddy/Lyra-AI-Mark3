# -*- coding: utf-8 -*-
"""
tests/test_phase6h_normalization.py
Phase 6H: Unit tests for NormalizationEngine and pipeline integration.
"""

import unittest
from unittest.mock import MagicMock, patch

from lyra.context.normalization_engine import (
    NormalizationEngine,
    NormalizationResult,
    DESTRUCTIVE_KEYWORDS,
    SAFE_KEYWORDS,
    TYPO_MAP,
)


class TestNormalizationEngineWhitespace(unittest.TestCase):
    """Step 1: Whitespace normalization."""

    def setUp(self):
        self.engine = NormalizationEngine()

    def test_leading_trailing_stripped(self):
        r = self.engine.normalize("  create file  ")
        self.assertEqual(r.normalized, "create file")
        self.assertTrue(r.was_modified)

    def test_internal_spaces_collapsed(self):
        r = self.engine.normalize("create    file   notes.txt")
        self.assertEqual(r.normalized, "create file notes.txt")
        self.assertTrue(r.was_modified)

    def test_tabs_collapsed(self):
        r = self.engine.normalize("create\t\tfile\tnotes.txt")
        self.assertEqual(r.normalized, "create file notes.txt")
        self.assertTrue(r.was_modified)

    def test_clean_input_unchanged(self):
        r = self.engine.normalize("create file notes.txt")
        self.assertEqual(r.normalized, "create file notes.txt")
        self.assertFalse(r.was_modified)


class TestNormalizationEngineRepeatedChars(unittest.TestCase):
    """Step 2: Repeated alphabetic character compression."""

    def setUp(self):
        self.engine = NormalizationEngine()

    def test_triple_letter_compressed(self):
        r = self.engine.normalize("pleaaase help")
        self.assertEqual(r.normalized, "pleaase help")
        self.assertTrue(r.was_modified)

    def test_many_repeated_compressed_to_two(self):
        r = self.engine.normalize("heeeeelp")
        # Compression gives "heelp", then safe keyword step corrects to "help"
        self.assertIn(r.normalized, ("heelp", "help"))
        self.assertTrue(r.was_modified)

    def test_digits_not_compressed(self):
        """Version numbers and numeric sequences must be untouched."""
        r = self.engine.normalize("version 1.0000.txt")
        # digits inside the path token are skipped entirely
        self.assertIn("1.0000.txt", r.normalized)

    def test_double_letters_untouched(self):
        """Two consecutive identical letters are fine (e.g. 'feel', 'tool')."""
        r = self.engine.normalize("feel free")
        self.assertEqual(r.normalized, "feel free")
        self.assertFalse(r.was_modified)


class TestNormalizationEngineConnectors(unittest.TestCase):
    """Step 3: Connector normalization."""

    def setUp(self):
        self.engine = NormalizationEngine()

    def test_andthen_split(self):
        r = self.engine.normalize("create file andthen launch app")
        self.assertIn("and then", r.normalized)
        self.assertTrue(r.was_modified)

    def test_n_then_normalised(self):
        r = self.engine.normalize("open file n then close it")
        self.assertIn("and then", r.normalized)
        self.assertTrue(r.was_modified)


class TestNormalizationEngineTypoDictionary(unittest.TestCase):
    """Step 4: Typo dictionary substitution."""

    def setUp(self):
        self.engine = NormalizationEngine()

    def test_teh_corrected(self):
        r = self.engine.normalize("teh file")
        self.assertEqual(r.normalized, "the file")
        self.assertTrue(r.was_modified)

    def test_opne_corrected(self):
        r = self.engine.normalize("opne the folder")
        self.assertEqual(r.normalized, "open the folder")
        self.assertTrue(r.was_modified)

    def test_creat_corrected(self):
        r = self.engine.normalize("creat a file")
        self.assertEqual(r.normalized, "create a file")
        self.assertTrue(r.was_modified)

    def test_unknown_word_unchanged(self):
        r = self.engine.normalize("xyzzy the file")
        self.assertIn("xyzzy", r.normalized)


class TestNormalizationEngineSafeKeywords(unittest.TestCase):
    """Step 5: Safe keyword edit-distance correction."""

    def setUp(self):
        self.engine = NormalizationEngine()

    def test_cretae_corrected_to_create(self):
        r = self.engine.normalize("cretae file test.txt")
        self.assertIn("create", r.normalized)
        self.assertTrue(r.was_modified)

    def test_launc_corrected_to_launch(self):
        r = self.engine.normalize("launc the app")
        self.assertIn("launch", r.normalized)
        self.assertTrue(r.was_modified)

    def test_safe_keyword_exact_unchanged(self):
        r = self.engine.normalize("create file notes.txt")
        self.assertEqual(r.normalized, "create file notes.txt")
        self.assertFalse(r.was_modified)


class TestNormalizationEngineDestructiveGuard(unittest.TestCase):
    """Destructive keyword guard — never auto-correct near dangerous words."""

    def setUp(self):
        self.engine = NormalizationEngine()

    def test_deleet_not_corrected(self):
        """'deleet' is in DESTRUCTIVE_NEAR_MISS — must NOT be auto-corrected."""
        r = self.engine.normalize("deleet file notes.txt")
        self.assertIsNotNone(r.dangerous_token_detected)
        self.assertEqual(r.dangerous_token_detected, "delete")
        # The normalized text must NOT contain the corrected word
        self.assertNotIn("delete", r.normalized)

    def test_remov_not_corrected(self):
        r = self.engine.normalize("remov the folder")
        self.assertIsNotNone(r.dangerous_token_detected)
        self.assertEqual(r.dangerous_token_detected, "remove")

    def test_wipe_exact_unchanged(self):
        """Exact destructive keyword typed correctly — pass through untouched."""
        r = self.engine.normalize("wipe the disk")
        self.assertIsNone(r.dangerous_token_detected)
        self.assertIn("wipe", r.normalized)

    def test_delete_exact_unchanged(self):
        r = self.engine.normalize("delete file notes.txt")
        self.assertIsNone(r.dangerous_token_detected)
        self.assertIn("delete", r.normalized)

    def test_all_destructive_keywords_pass_through(self):
        """Every exact destructive keyword must pass through without flagging."""
        for kw in DESTRUCTIVE_KEYWORDS:
            with self.subTest(keyword=kw):
                r = self.engine.normalize(f"{kw} something")
                self.assertIsNone(
                    r.dangerous_token_detected,
                    f"Exact keyword '{kw}' should not trigger dangerous_token_detected"
                )


class TestNormalizationEngineQuotedStrings(unittest.TestCase):
    """Quoted strings must be left completely untouched."""

    def setUp(self):
        self.engine = NormalizationEngine()

    def test_quoted_typo_untouched(self):
        """Typos inside quotes must NOT be corrected."""
        r = self.engine.normalize('create "my teh file.txt"')
        self.assertIn('"my teh file.txt"', r.normalized)

    def test_quoted_repeated_chars_untouched(self):
        r = self.engine.normalize('open "pleaaase.txt"')
        self.assertIn('"pleaaase.txt"', r.normalized)

    def test_single_quoted_untouched(self):
        r = self.engine.normalize("create 'teh notes.txt'")
        self.assertIn("'teh notes.txt'", r.normalized)

    def test_outer_typo_corrected_quoted_preserved(self):
        """Typos outside quotes corrected; quoted section preserved."""
        r = self.engine.normalize('opne "my teh file.txt"')
        self.assertIn("open", r.normalized)
        self.assertIn('"my teh file.txt"', r.normalized)


class TestNormalizationEnginePathTokens(unittest.TestCase):
    """Tokens containing '.' or '/' must be skipped."""

    def setUp(self):
        self.engine = NormalizationEngine()

    def test_filename_extension_untouched(self):
        r = self.engine.normalize("create notes.txt")
        self.assertIn("notes.txt", r.normalized)

    def test_path_untouched(self):
        r = self.engine.normalize("open /home/user/docs")
        self.assertIn("/home/user/docs", r.normalized)

    def test_version_number_untouched(self):
        r = self.engine.normalize("install v1.0000.pkg")
        self.assertIn("v1.0000.pkg", r.normalized)


class TestNormalizationResultDataclass(unittest.TestCase):
    """NormalizationResult fields are populated correctly."""

    def setUp(self):
        self.engine = NormalizationEngine()

    def test_modification_count_increments(self):
        r = self.engine.normalize("teh opne fiel")
        self.assertGreater(r.modification_count, 0)

    def test_delta_non_empty_on_change(self):
        r = self.engine.normalize("teh file")
        self.assertNotEqual(r.delta, "no changes")

    def test_delta_no_changes(self):
        r = self.engine.normalize("create file notes.txt")
        self.assertEqual(r.delta, "no changes")

    def test_dangerous_token_none_on_clean_input(self):
        r = self.engine.normalize("create file notes.txt")
        self.assertIsNone(r.dangerous_token_detected)


class TestPipelineNormalizationIntegration(unittest.TestCase):
    """Integration tests: NormalizationEngine wired into LyraPipeline."""

    def setUp(self):
        from lyra.core.pipeline import LyraPipeline
        self.pipeline = LyraPipeline()

        # Mock all downstream components so we isolate normalization behaviour
        self.pipeline.semantic_engine = MagicMock()
        self.pipeline.semantic_engine.parse_semantic_intent.return_value = {
            "intents": [{"intent": "create_file", "parameters": {"filename": "test.txt"}, "confidence": 0.9}]
        }
        self.pipeline.refinement_engine = MagicMock()
        self.pipeline.refinement_engine.refine_intent.return_value = None
        self.pipeline.clarification_manager = MagicMock()
        self.pipeline.clarification_manager.has_pending.return_value = False
        self.pipeline.planner = MagicMock()
        self.pipeline.planner.create_plan_from_command.return_value = MagicMock(
            requires_confirmation=False
        )
        self.pipeline.gateway = MagicMock()
        self.pipeline.gateway.execute_plan.return_value = MagicMock(
            success=True, results=[], total_duration=0.05
        )

    def test_normalization_applied_counter_increments(self):
        """normalization_applied increments when input is modified."""
        before = self.pipeline.metrics.counters["normalization_applied"]
        # 'opne' is in TYPO_MAP → corrected to 'open' → was_modified=True
        self.pipeline.process_command("opne file test.txt", auto_confirm=True)
        after = self.pipeline.metrics.counters["normalization_applied"]
        self.assertEqual(after, before + 1)

    def test_normalization_applied_not_incremented_on_clean_input(self):
        """normalization_applied does NOT increment when input needs no changes."""
        before = self.pipeline.metrics.counters["normalization_applied"]
        self.pipeline.process_command("create file test.txt", auto_confirm=True)
        after = self.pipeline.metrics.counters["normalization_applied"]
        self.assertEqual(after, before)

    def test_dangerous_token_returns_clarification(self):
        """A near-destructive typo returns an explicit clarification message."""
        result = self.pipeline.process_command("delet file notes.txt", auto_confirm=True)
        self.assertFalse(result.success)
        self.assertIn("delete", result.output)
        self.assertIn("Destructive commands must be typed explicitly", result.output)

    def test_dangerous_token_does_not_increment_normalization_applied(self):
        """normalization_applied must NOT increment when dangerous token detected."""
        before = self.pipeline.metrics.counters["normalization_applied"]
        self.pipeline.process_command("delet file notes.txt", auto_confirm=True)
        after = self.pipeline.metrics.counters["normalization_applied"]
        self.assertEqual(after, before)

    def test_introspection_bypasses_normalization(self):
        """Introspection commands (metrics, status) are never normalised."""
        # 'metrics' must return the metrics report, not trigger normalization
        result = self.pipeline.process_command("metrics")
        self.assertTrue(result.success)
        self.assertIn("Lyra Internal Metrics", result.output)
        # normalization_applied must be 0 (introspection bypassed it)
        self.assertEqual(self.pipeline.metrics.counters["normalization_applied"], 0)

    def test_metrics_report_includes_normalization_applied(self):
        """The metrics report must include the normalization_applied line."""
        result = self.pipeline.process_command("metrics")
        self.assertIn("Normalization Applied", result.output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
