# -*- coding: utf-8 -*-
"""
tests/test_phase6i_conversation_layer.py
Phase 6I: Unit tests for ConversationLayer and pipeline integration.
"""

import unittest
from unittest.mock import MagicMock

from lyra.context.conversation_layer import (
    ConversationLayer,
    ConversationResult,
    _DESTRUCTIVE_SYNONYMS,
    _SAFE_SYNONYM_MAP,
    _FILLER_PHRASES,
)


class TestFillerStripping(unittest.TestCase):
    """Filler phrase stripping — verb-gated, beginning-only."""

    def setUp(self):
        self.layer = ConversationLayer()

    def test_can_you_stripped_before_verb(self):
        r = self.layer.process("can you create a file")
        self.assertTrue(r.filler_stripped)
        self.assertTrue(r.cleaned.startswith("create"))

    def test_please_stripped_before_verb(self):
        r = self.layer.process("please open the folder")
        self.assertTrue(r.filler_stripped)
        self.assertTrue(r.cleaned.startswith("open"))

    def test_could_you_stripped_before_verb(self):
        r = self.layer.process("could you launch the app")
        self.assertTrue(r.filler_stripped)
        self.assertTrue(r.cleaned.startswith("launch"))

    def test_i_want_to_stripped(self):
        r = self.layer.process("i want to write a file")
        self.assertTrue(r.filler_stripped)
        self.assertTrue(r.cleaned.startswith("write"))

    def test_i_would_like_to_stripped(self):
        r = self.layer.process("i would like to close the app")
        self.assertTrue(r.filler_stripped)
        self.assertTrue(r.cleaned.startswith("close"))

    def test_hey_stripped_before_verb(self):
        r = self.layer.process("hey create a new file")
        self.assertTrue(r.filler_stripped)
        self.assertTrue(r.cleaned.startswith("create"))

    def test_filler_NOT_stripped_without_safe_verb(self):
        """'can you believe this' — no safe verb follows, must NOT strip."""
        r = self.layer.process("can you believe this")
        self.assertFalse(r.filler_stripped)
        self.assertIn("can you", r.cleaned)

    def test_filler_NOT_stripped_in_middle(self):
        """Filler in the middle of a sentence must not be removed."""
        r = self.layer.process("create a file please")
        self.assertFalse(r.filler_stripped)
        self.assertIn("please", r.cleaned)

    def test_only_one_filler_stripped(self):
        """Only the first matching filler is stripped.
        'hey please create' → 'hey' is followed by 'please' (not a safe verb),
        so verb-gate blocks it. 'please create' → 'please' IS followed by 'create'.
        Use a case where the first filler IS verb-gated correctly.
        """
        # 'hey' is followed by 'create' (safe verb) → strips
        r = self.layer.process("hey create a file please")
        self.assertTrue(r.filler_stripped)
        self.assertTrue(r.cleaned.startswith("create"))
        # 'please' at the end is NOT stripped (not at beginning)
        self.assertIn("please", r.cleaned)

    def test_filler_not_stripped_when_next_token_not_safe_verb(self):
        """Verb-gate: 'please' followed by 'can' (not a safe verb) is NOT stripped.
        'can you' is not at the start of the string either, so nothing is stripped.
        This verifies the verb-gate prevents false stripping of real semantic content."""
        r = self.layer.process("please can you create a file")
        # 'please' → next token 'can' is NOT a safe verb → verb-gate blocks stripping
        # 'can you' → not at start of string (preceded by 'please') → not matched
        # Result: filler_stripped=False (correct — no filler was stripped)
        self.assertFalse(r.filler_stripped)
        self.assertIn("please", r.cleaned)


    def test_pls_stripped(self):
        r = self.layer.process("pls open the folder")
        self.assertTrue(r.filler_stripped)


class TestSafeSynonymMapping(unittest.TestCase):
    """Safe synonym mapping — verb-position only (first token)."""

    def setUp(self):
        self.layer = ConversationLayer()

    def test_make_mapped_to_create(self):
        r = self.layer.process("make a file called notes.txt")
        self.assertTrue(r.synonym_mapped)
        self.assertTrue(r.cleaned.startswith("create"))

    def test_start_mapped_to_launch(self):
        r = self.layer.process("start the application")
        self.assertTrue(r.synonym_mapped)
        self.assertTrue(r.cleaned.startswith("launch"))

    def test_open_up_mapped_to_open(self):
        r = self.layer.process("open up the folder")
        self.assertTrue(r.synonym_mapped)
        self.assertTrue(r.cleaned.startswith("open"))

    def test_spin_up_mapped_to_create(self):
        r = self.layer.process("spin up a new project")
        self.assertTrue(r.synonym_mapped)
        self.assertTrue(r.cleaned.startswith("create"))

    def test_boot_mapped_to_launch(self):
        r = self.layer.process("boot the server")
        self.assertTrue(r.synonym_mapped)
        self.assertTrue(r.cleaned.startswith("launch"))

    def test_shut_mapped_to_close(self):
        r = self.layer.process("shut the window")
        self.assertTrue(r.synonym_mapped)
        self.assertTrue(r.cleaned.startswith("close"))

    def test_synonym_NOT_mapped_in_middle(self):
        """'make' in the middle of a sentence must NOT be mapped."""
        r = self.layer.process("create a file and make it better")
        self.assertFalse(r.synonym_mapped)
        self.assertIn("make", r.cleaned)

    def test_exact_safe_verb_unchanged(self):
        """Exact safe verbs are not re-mapped."""
        r = self.layer.process("create a file")
        self.assertFalse(r.synonym_mapped)
        self.assertEqual(r.cleaned, "create a file")


class TestDestructiveSynonymGuard(unittest.TestCase):
    """Destructive synonyms must NEVER be auto-mapped — trigger clarification."""

    def setUp(self):
        self.layer = ConversationLayer()

    def test_nuke_triggers_clarification(self):
        r = self.layer.process("nuke the folder")
        self.assertTrue(r.clarification_needed)
        self.assertEqual(r.dangerous_synonym, "nuke")
        self.assertFalse(r.synonym_mapped)

    def test_wipe_triggers_clarification(self):
        r = self.layer.process("wipe the disk")
        self.assertTrue(r.clarification_needed)
        self.assertEqual(r.dangerous_synonym, "wipe")

    def test_erase_triggers_clarification(self):
        r = self.layer.process("erase everything")
        self.assertTrue(r.clarification_needed)
        self.assertEqual(r.dangerous_synonym, "erase")

    def test_kill_triggers_clarification(self):
        r = self.layer.process("kill the process")
        self.assertTrue(r.clarification_needed)
        self.assertEqual(r.dangerous_synonym, "kill")

    def test_purge_triggers_clarification(self):
        r = self.layer.process("purge the cache")
        self.assertTrue(r.clarification_needed)
        self.assertEqual(r.dangerous_synonym, "purge")

    def test_destroy_triggers_clarification(self):
        r = self.layer.process("destroy the config")
        self.assertTrue(r.clarification_needed)
        self.assertEqual(r.dangerous_synonym, "destroy")

    def test_all_destructive_synonyms_flagged(self):
        """Every destructive synonym must trigger clarification."""
        for term in _DESTRUCTIVE_SYNONYMS:
            with self.subTest(term=term):
                r = self.layer.process(f"{term} the target")
                self.assertTrue(
                    r.clarification_needed,
                    f"'{term}' should trigger clarification"
                )

    def test_destructive_in_middle_not_flagged(self):
        """Destructive synonym in the middle of a sentence is not at verb-position."""
        # 'wipe' is not the first token here — safe verb 'create' is first
        r = self.layer.process("create a wipe-clean template")
        self.assertFalse(r.clarification_needed)


class TestToneDetection(unittest.TestCase):
    """Tone detection — dominant tone, priority order."""

    def setUp(self):
        self.layer = ConversationLayer()

    def test_polite_tone(self):
        r = self.layer.process("please create a file")
        self.assertEqual(r.tone, "polite")

    def test_urgent_tone(self):
        r = self.layer.process("create the file asap")
        self.assertEqual(r.tone, "urgent")

    def test_frustrated_tone(self):
        r = self.layer.process("why is this still broken")
        self.assertEqual(r.tone, "frustrated")

    def test_casual_tone(self):
        r = self.layer.process("yo create a file bro")
        self.assertEqual(r.tone, "casual")

    def test_neutral_tone(self):
        r = self.layer.process("create file notes.txt")
        self.assertEqual(r.tone, "neutral")

    def test_urgent_beats_polite(self):
        """urgent > polite in priority."""
        r = self.layer.process("please hurry asap")
        self.assertEqual(r.tone, "urgent")

    def test_frustrated_beats_polite(self):
        """frustrated > polite in priority."""
        r = self.layer.process("why is this broken please")
        self.assertEqual(r.tone, "frustrated")

    def test_urgent_beats_frustrated(self):
        """urgent > frustrated in priority."""
        r = self.layer.process("ugh do this immediately")
        self.assertEqual(r.tone, "urgent")

    def test_tone_detected_only_once(self):
        """Multiple tone markers → single dominant tone, not double-counted."""
        r = self.layer.process("please thank you asap hurry")
        # urgent wins
        self.assertEqual(r.tone, "urgent")


class TestConfidenceShaping(unittest.TestCase):
    """Confidence modifier — returned as multiplier, applied post-semantic."""

    def setUp(self):
        self.layer = ConversationLayer()

    def test_modifier_reduced_when_filler_stripped(self):
        r = self.layer.process("can you create a file")
        self.assertEqual(r.confidence_modifier, 0.95)

    def test_modifier_reduced_when_modal_verb(self):
        r = self.layer.process("could you create a file")
        # 'could' is a modal verb → indirect_phrasing=True
        self.assertEqual(r.confidence_modifier, 0.95)

    def test_modifier_unchanged_for_direct_command(self):
        r = self.layer.process("create file notes.txt")
        self.assertEqual(r.confidence_modifier, 1.0)

    def test_indirect_phrasing_flag_set_on_filler(self):
        r = self.layer.process("please open the folder")
        self.assertTrue(r.indirect_phrasing)

    def test_indirect_phrasing_flag_set_on_modal(self):
        r = self.layer.process("would you run the script")
        self.assertTrue(r.indirect_phrasing)

    def test_indirect_phrasing_false_for_direct(self):
        r = self.layer.process("run the script")
        self.assertFalse(r.indirect_phrasing)


class TestQuotedStringPreservation(unittest.TestCase):
    """Quoted strings must be completely untouched."""

    def setUp(self):
        self.layer = ConversationLayer()

    def test_quoted_content_preserved(self):
        r = self.layer.process('create "my make file.txt"')
        self.assertIn('"my make file.txt"', r.cleaned)

    def test_filler_outside_quotes_stripped_quoted_preserved(self):
        r = self.layer.process('please create "my make file.txt"')
        self.assertTrue(r.filler_stripped)
        self.assertIn('"my make file.txt"', r.cleaned)

    def test_single_quoted_preserved(self):
        r = self.layer.process("make 'spin up config.txt'")
        # synonym mapped (make→create at position 0)
        self.assertIn("'spin up config.txt'", r.cleaned)

    def test_destructive_synonym_in_quotes_not_flagged(self):
        """'nuke' inside quotes is not at verb-position — not flagged."""
        r = self.layer.process('create "nuke template.txt"')
        self.assertFalse(r.clarification_needed)


class TestPathTokenPreservation(unittest.TestCase):
    """File paths and filenames must not be corrupted."""

    def setUp(self):
        self.layer = ConversationLayer()

    def test_filename_preserved(self):
        r = self.layer.process("create notes.txt")
        self.assertIn("notes.txt", r.cleaned)

    def test_path_preserved(self):
        r = self.layer.process("open /home/user/docs")
        self.assertIn("/home/user/docs", r.cleaned)


class TestWasModifiedFlag(unittest.TestCase):
    """was_modified reflects actual changes."""

    def setUp(self):
        self.layer = ConversationLayer()

    def test_modified_on_filler_strip(self):
        r = self.layer.process("please create a file")
        self.assertTrue(r.was_modified)

    def test_modified_on_synonym_map(self):
        r = self.layer.process("make a file")
        self.assertTrue(r.was_modified)

    def test_not_modified_on_clean_input(self):
        r = self.layer.process("create file notes.txt")
        self.assertFalse(r.was_modified)


class TestPipelineConversationIntegration(unittest.TestCase):
    """Integration tests: ConversationLayer wired into LyraPipeline."""

    def setUp(self):
        from lyra.core.pipeline import LyraPipeline
        self.pipeline = LyraPipeline()

        # Mock downstream components
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

    def test_conversation_adjustments_increments_on_filler(self):
        before = self.pipeline.metrics.counters["conversation_adjustments"]
        self.pipeline.process_command("please create file test.txt", auto_confirm=True)
        after = self.pipeline.metrics.counters["conversation_adjustments"]
        self.assertEqual(after, before + 1)

    def test_conversation_adjustments_increments_on_synonym(self):
        before = self.pipeline.metrics.counters["conversation_adjustments"]
        self.pipeline.process_command("make file test.txt", auto_confirm=True)
        after = self.pipeline.metrics.counters["conversation_adjustments"]
        self.assertEqual(after, before + 1)

    def test_conversation_adjustments_not_incremented_on_clean(self):
        before = self.pipeline.metrics.counters["conversation_adjustments"]
        self.pipeline.process_command("create file test.txt", auto_confirm=True)
        after = self.pipeline.metrics.counters["conversation_adjustments"]
        self.assertEqual(after, before)

    def test_tone_detected_increments_on_polite(self):
        before = self.pipeline.metrics.counters["tone_detected"]
        self.pipeline.process_command("please create file test.txt", auto_confirm=True)
        after = self.pipeline.metrics.counters["tone_detected"]
        self.assertEqual(after, before + 1)

    def test_tone_detected_not_incremented_on_neutral(self):
        before = self.pipeline.metrics.counters["tone_detected"]
        self.pipeline.process_command("create file test.txt", auto_confirm=True)
        after = self.pipeline.metrics.counters["tone_detected"]
        self.assertEqual(after, before)

    def test_destructive_synonym_returns_explicit_message(self):
        result = self.pipeline.process_command("nuke the folder", auto_confirm=True)
        self.assertFalse(result.success)
        self.assertIn("nuke", result.output)
        self.assertIn("destructive", result.output.lower())
        self.assertIn("explicit supported command", result.output)

    def test_destructive_synonym_not_increments_conversation_adjustments(self):
        before = self.pipeline.metrics.counters["conversation_adjustments"]
        self.pipeline.process_command("nuke the folder", auto_confirm=True)
        after = self.pipeline.metrics.counters["conversation_adjustments"]
        self.assertEqual(after, before)

    def test_introspection_bypasses_conversation_layer(self):
        """'metrics' command must bypass ConversationLayer entirely."""
        result = self.pipeline.process_command("metrics")
        self.assertTrue(result.success)
        self.assertIn("Lyra Internal Metrics", result.output)
        self.assertIn("Conv. Adjustments", result.output)
        self.assertIn("Tone Detected", result.output)

    def test_metrics_report_includes_new_counters(self):
        result = self.pipeline.process_command("metrics")
        self.assertIn("Conv. Adjustments", result.output)
        self.assertIn("Tone Detected", result.output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
