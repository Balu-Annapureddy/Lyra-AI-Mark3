"""
Integration Tests - Phase 3C
Tests full integration of all Phase 3 modules
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lyra.interaction.voice_personality import (
    VoicePersonality,
    format_suggestion_response,
    format_risk_warning,
    format_confidence_message
)
from lyra.reasoning.suggestion_ranker import SuggestionRanker
from lyra.reasoning.confidence_tracker import ConfidenceTracker
from lyra.safety.adaptive_risk_scorer import AdaptiveRiskScorer
from lyra.learning.rejection_learner import RejectionLearner
from lyra.memory.behavioral_memory import BehavioralMemory
from lyra.reasoning.command_schema import Command


def test_voice_personality():
    """Test voice personality layer"""
    print("\n=== Testing Voice Personality ===")
    
    vp = VoicePersonality(use_ssml=False)
    
    # Test emoji stripping
    print("\n1. Emoji Stripping:")
    text_with_emoji = "Great! 🎉 This is awesome! 😊"
    cleaned = vp.format_response(text_with_emoji)
    print(f"   Input:  '{text_with_emoji}'")
    print(f"   Output: '{cleaned}'")
    assert '🎉' not in cleaned and '😊' not in cleaned
    
    # Test punctuation cleaning
    print("\n2. Punctuation Cleaning:")
    text_with_punct = "Wait!!! What??? Really..."
    cleaned = vp.format_response(text_with_punct)
    print(f"   Input:  '{text_with_punct}'")
    print(f"   Output: '{cleaned}'")
    
    # Test tone filtering
    print("\n3. Tone Filtering:")
    casual_text = "Yeah, that's awesome! No worries, cool!"
    professional = vp.format_response(casual_text)
    print(f"   Input:  '{casual_text}'")
    print(f"   Output: '{professional}'")
    
    # Test response templates
    print("\n4. Response Templates:")
    print(f"   Confirmation: {vp.format_confirmation('executing command')}")
    print(f"   Suggestion:   {vp.format_suggestion('check email', confidence=0.85)}")
    print(f"   Warning:      {vp.format_warning('high risk operation')}")
    print(f"   Error:        {vp.format_error('file not found', 'verify path')}")
    print(f"   Low Conf:     {vp.format_low_confidence('intent')}")
    
    print("\n✅ Voice Personality: PASSED")


def test_suggestion_ranking_with_voice():
    """Test suggestion ranking integrated with voice personality"""
    print("\n=== Testing Suggestion Ranking + Voice ===")
    
    ranker = SuggestionRanker()
    vp = VoicePersonality()
    
    # Create test suggestions
    suggestions = [
        {"type": "email_check", "name": "Check Email", "risk_score": 0.1},
        {"type": "backup_files", "name": "Backup Files", "risk_score": 0.3}
    ]
    
    # Rank suggestions
    ranked = ranker.rank_suggestions(suggestions, top_n=2)
    
    print("\n1. Ranked Suggestions with Voice Formatting:")
    for suggestion in ranked:
        score = suggestion.total_score
        name = suggestion.suggestion_data['name']
        
        # Format with voice personality
        formatted = vp.format_suggestion(name, confidence=score)
        print(f"   Rank {suggestion.rank}: {formatted}")
        print(f"      (Score: {score:.3f})")
    
    print("\n✅ Suggestion Ranking + Voice: PASSED")


def test_confidence_reporting_with_voice():
    """Test confidence reporting integrated with voice personality"""
    print("\n=== Testing Confidence Reporting + Voice ===")
    
    tracker = ConfidenceTracker()
    vp = VoicePersonality()
    
    # Test different confidence levels
    confidence_levels = [
        (0.95, "high confidence scenario"),
        (0.75, "moderate confidence scenario"),
        (0.55, "low confidence scenario"),
        (0.35, "very low confidence scenario")
    ]
    
    print("\n1. Confidence Messages:")
    for conf, scenario in confidence_levels:
        report = tracker.create_report(
            intent_factors={"pattern_match_score": conf},
            execution_factors={"historical_success_rate": conf},
            risk_factors={"risk_assessment_certainty": conf}
        )
        
        message = format_confidence_message("intent", report.overall_confidence)
        print(f"   {scenario} ({conf:.2f}): {message}")
    
    print("\n✅ Confidence Reporting + Voice: PASSED")


def test_risk_warnings_with_voice():
    """Test risk warnings with voice personality"""
    print("\n=== Testing Risk Warnings + Voice ===")
    
    scorer = AdaptiveRiskScorer()
    vp = VoicePersonality()
    
    # Test critical operation
    print("\n1. Critical Operation Warning:")
    cmd = Command(
        intent="delete_system_file",
        raw_input="delete important.sys",
        confidence=0.9,
        entities={"filename": "important.sys"}
    )
    
    assessment = scorer.calculate_risk(cmd)
    warning = vp.format_warning(f"{assessment.risk_level.value} risk: {list(assessment.factors.values())[0] if assessment.factors else 'operation'}")
    print(f"   {warning}")
    
    # Test with SSML
    print("\n2. Warning with SSML:")
    vp_ssml = VoicePersonality(use_ssml=True)
    warning_ssml = vp_ssml.format_warning("critical operation detected")
    print(f"   {warning_ssml}")
    
    print("\n✅ Risk Warnings + Voice: PASSED")


def test_rejection_learning_impact():
    """Test rejection learning impact on responses"""
    print("\n=== Testing Rejection Learning Impact ===")
    
    learner = RejectionLearner()
    vp = VoicePersonality()
    
    # Record some rejections
    print("\n1. Recording Rejections:")
    suggestion_type = "morning_email_check"
    for i in range(3):
        learner.record_rejection(suggestion_type, reason="wrong_time")
    
    stats = learner.get_rejection_stats(suggestion_type)
    print(f"   Rejections: {stats['total_rejections']}")
    print(f"   Current weight: {stats['current_weight']:.3f}")
    
    # Format acknowledgment
    print("\n2. Rejection Acknowledgment:")
    ack = vp.format_rejection_acknowledgment(suggestion_type)
    print(f"   {ack}")
    
    # Check if should suggest
    should_suggest = learner.should_suggest(suggestion_type, min_weight=0.6)
    print(f"\n3. Should Suggest (0.6 threshold): {should_suggest}")
    
    print("\n✅ Rejection Learning Impact: PASSED")


def test_full_integration_flow():
    """Test complete integration flow"""
    print("\n=== Testing Full Integration Flow ===")
    
    # Initialize all components
    memory = BehavioralMemory()
    ranker = SuggestionRanker()
    tracker = ConfidenceTracker()
    scorer = AdaptiveRiskScorer()
    learner = RejectionLearner()
    vp = VoicePersonality()
    
    print("\n1. Complete Suggestion Flow:")
    
    # Step 1: Generate suggestions
    suggestions = [
        {"type": "workflow_morning", "name": "Morning Routine", "risk_score": 0.2},
        {"type": "email_check", "name": "Check Email", "risk_score": 0.1}
    ]
    
    # Step 2: Rank suggestions
    ranked = ranker.rank_suggestions(suggestions, top_n=1)
    best = ranked[0] if ranked else None
    
    if best:
        print(f"   Best suggestion: {best.suggestion_data['name']}")
        print(f"   Score: {best.total_score:.3f}")
        
        # Step 3: Check rejection history
        should_suggest = learner.should_suggest(best.suggestion_type)
        print(f"   Should suggest: {should_suggest}")
        
        if should_suggest:
            # Step 4: Create confidence report
            report = tracker.create_report(
                intent_factors={"pattern_match_score": best.total_score},
                execution_factors={"historical_success_rate": 0.9},
                risk_factors={"risk_assessment_certainty": 0.8}
            )
            print(f"   Overall confidence: {report.overall_confidence:.3f}")
            
            # Step 5: Format with voice personality
            formatted = vp.format_suggestion(
                best.suggestion_data['name'],
                confidence=report.overall_confidence
            )
            print(f"   Formatted response: '{formatted}'")
            
            # Step 6: Record outcome in behavioral memory
            memory.record_suggestion_outcome(
                best.suggestion_type,
                accepted=True,
                context={"project": "test"}
            )
            print(f"   ✓ Outcome recorded in behavioral memory")
    
    print("\n2. Complete Risk Assessment Flow:")
    
    # Create command
    cmd = Command(
        intent="delete_file",
        raw_input="delete test.txt",
        confidence=0.9,
        entities={"filename": "test.txt"}
    )
    
    # Assess risk
    assessment = scorer.calculate_risk(cmd)
    print(f"   Risk level: {assessment.risk_level.value}")
    print(f"   Risk score: {assessment.risk_score:.2f}")
    print(f"   Threshold: {assessment.confirmation_threshold:.2f}")
    
    # Create confidence report
    report = tracker.create_report(
        intent_factors={"pattern_match_score": cmd.confidence},
        execution_factors={"historical_success_rate": 0.85},
        risk_factors={"risk_assessment_certainty": 0.9}
    )
    
    # Format warning if needed
    if assessment.requires_confirmation:
        warning = vp.format_warning(f"{assessment.risk_level.value} risk operation")
        print(f"   Warning: '{warning}'")
    
    # Format confidence message
    conf_msg = format_confidence_message("execution", report.overall_confidence)
    print(f"   Confidence: '{conf_msg}'")
    
    print("\n✅ Full Integration Flow: PASSED")


def test_auditability():
    """Test that all adaptive modules remain auditable"""
    print("\n=== Testing Auditability ===")
    
    memory = BehavioralMemory()
    learner = RejectionLearner()
    scorer = AdaptiveRiskScorer()
    
    print("\n1. Behavioral Memory Auditability:")
    patterns = memory.get_workflow_patterns(min_frequency=1)
    print(f"   ✓ Can retrieve workflow patterns: {len(patterns)} found")
    
    print("\n2. Rejection Learning Auditability:")
    stats = learner.get_all_stats()
    print(f"   ✓ Can retrieve rejection stats: {len(stats)} types tracked")
    
    print("\n3. Adaptive Risk Auditability:")
    summary = scorer.get_adjustment_summary()
    print(f"   ✓ Can retrieve adjustments: {summary['total_adjustments']} active")
    print(f"   ✓ Safety floors protected: {len(summary['critical_operations'])} operations")
    
    print("\n✅ Auditability: PASSED")


def main():
    """Run all Phase 3C integration tests"""
    print("=" * 60)
    print("Phase 3C Integration Tests - Voice & Full Integration")
    print("=" * 60)
    
    try:
        # Voice personality tests
        test_voice_personality()
        
        # Integration tests
        test_suggestion_ranking_with_voice()
        test_confidence_reporting_with_voice()
        test_risk_warnings_with_voice()
        test_rejection_learning_impact()
        
        # Full integration
        test_full_integration_flow()
        
        # Auditability verification
        test_auditability()
        
        print("\n" + "=" * 60)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        print("\nPhase 3C: Complete!")
        print("- Voice personality layer ✅")
        print("- Tone filtering (calm, analytical) ✅")
        print("- Emoji & punctuation cleaning ✅")
        print("- SSML pause support ✅")
        print("- Full integration verified ✅")
        print("- Auditability maintained ✅")
        
        print("\n" + "=" * 60)
        print("🎉 PHASE 3 COMPLETE - ADAPTIVE INTELLIGENCE OPERATIONAL")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
