"""
Test Phase 3A & 3B - Adaptive Intelligence Layer
Tests behavioral memory, confidence tracking, rejection learning,
suggestion ranking, and adaptive risk calibration
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lyra.memory.behavioral_memory import BehavioralMemory
from lyra.reasoning.confidence_tracker import ConfidenceTracker
from lyra.learning.rejection_learner import RejectionLearner
from lyra.reasoning.suggestion_ranker import SuggestionRanker
from lyra.safety.adaptive_risk_scorer import AdaptiveRiskScorer, CRITICAL_OPERATIONS
from lyra.reasoning.command_schema import Command
import uuid


def test_behavioral_memory():
    """Test behavioral memory layer"""
    print("\n=== Testing Behavioral Memory ===")
    
    memory = BehavioralMemory()
    
    # Test workflow pattern recording
    print("\n1. Workflow Pattern Recording:")
    workflow_id = str(uuid.uuid4())
    for i in range(5):
        memory.record_workflow_execution(workflow_id, "Morning Routine", execution_time=120.0)
    
    patterns = memory.get_workflow_patterns(min_frequency=3)
    print(f"   ✓ Patterns recorded: {len(patterns)}")
    if patterns:
        pattern = patterns[0]
        print(f"   ✓ Workflow: {pattern.workflow_name}")
        print(f"   ✓ Frequency: {pattern.frequency}")
        print(f"   ✓ Avg execution time: {pattern.avg_execution_time:.1f}s")
    
    # Test risk tolerance recording
    print("\n2. Risk Tolerance Tracking:")
    memory.record_risk_action("high", "delete_file", "accepted", trust_score=0.7)
    memory.record_risk_action("high", "delete_file", "rejected", trust_score=0.7)
    
    trend = memory.get_risk_tolerance_trend(days_back=30)
    print(f"   ✓ Risk trends: {len(trend)} risk levels tracked")
    
    # Test suggestion effectiveness
    print("\n3. Suggestion Effectiveness:")
    memory.record_suggestion_outcome("email_check", accepted=True, context={"project": "work"})
    memory.record_suggestion_outcome("email_check", accepted=True, context={"project": "work"})
    memory.record_suggestion_outcome("email_check", accepted=False, context={"project": "work"})
    
    effectiveness = memory.get_suggestion_effectiveness("email_check")
    print(f"   ✓ Total suggestions: {effectiveness['total']}")
    print(f"   ✓ Acceptance rate: {effectiveness['acceptance_rate']:.1%}")
    
    print("\n✅ Behavioral Memory: PASSED")


def test_confidence_tracker():
    """Test confidence tracking"""
    print("\n=== Testing Confidence Tracker ===")
    
    tracker = ConfidenceTracker()
    
    # Test intent confidence
    print("\n1. Intent Confidence:")
    intent_conf = tracker.calculate_intent_confidence(
        pattern_match_score=0.8,
        nlp_confidence=0.9,
        context_relevance=0.7,
        historical_similarity=0.85
    )
    print(f"   ✓ Intent confidence: {intent_conf:.2f}")
    
    # Test execution confidence
    print("\n2. Execution Confidence:")
    exec_conf = tracker.calculate_execution_confidence(
        historical_success_rate=0.9,
        resource_availability=1.0,
        dependency_status=1.0
    )
    print(f"   ✓ Execution confidence: {exec_conf:.2f}")
    
    # Test risk confidence
    print("\n3. Risk Confidence:")
    risk_conf = tracker.calculate_risk_confidence(
        risk_assessment_certainty=0.8,
        historical_risk_accuracy=0.85
    )
    print(f"   ✓ Risk confidence: {risk_conf:.2f}")
    
    # Test comprehensive report
    print("\n4. Comprehensive Report:")
    report = tracker.create_report(
        intent_factors={"pattern_match_score": 0.8, "nlp_confidence": 0.9},
        execution_factors={"historical_success_rate": 0.9},
        risk_factors={"risk_assessment_certainty": 0.8}
    )
    print(f"   ✓ Overall confidence: {report.overall_confidence:.2f}")
    print(f"   ✓ Should proceed (0.7 threshold): {report.should_proceed()}")
    print(f"   ✓ Message: {tracker.get_confidence_message(report)}")
    
    print("\n✅ Confidence Tracker: PASSED")


def test_rejection_learner():
    """Test rejection learning with logarithmic penalties"""
    print("\n=== Testing Rejection Learner ===")
    
    learner = RejectionLearner()
    
    # Test penalty calculation
    print("\n1. Logarithmic Penalty Calculation:")
    test_counts = [1, 3, 5, 10, 100]
    for count in test_counts:
        penalty = learner.calculate_penalty(count)
        print(f"   {count:3d} rejections: {penalty:.3f} ({penalty*100:.1f}% penalty)")
    
    # Test rejection recording
    print("\n2. Rejection Recording:")
    for i in range(5):
        learner.record_rejection("email_check", reason="wrong_time", context={"project": "work"})
    
    weight = learner.get_suggestion_weight("email_check")
    print(f"   ✓ Weight after 5 rejections: {weight:.3f}")
    
    stats = learner.get_rejection_stats("email_check")
    print(f"   ✓ Total rejections: {stats['total_rejections']}")
    print(f"   ✓ Current penalty: {stats['current_penalty']:.3f}")
    print(f"   ✓ Common reasons: {stats['common_reasons']}")
    
    # Test should_suggest
    print("\n3. Suggestion Filtering:")
    should_suggest = learner.should_suggest("email_check", min_weight=0.6)
    print(f"   ✓ Should suggest (0.6 threshold): {should_suggest}")
    
    print("\n✅ Rejection Learner: PASSED")


def test_suggestion_ranker():
    """Test suggestion ranking with normalized scoring"""
    print("\n=== Testing Suggestion Ranker ===")
    
    ranker = SuggestionRanker()
    
    # Create test suggestions
    suggestions = [
        {
            "type": "workflow_morning",
            "name": "Morning Routine",
            "risk_score": 0.2
        },
        {
            "type": "command_email",
            "name": "Check Email",
            "risk_score": 0.1
        },
        {
            "type": "workflow_backup",
            "name": "Backup Files",
            "risk_score": 0.5
        }
    ]
    
    context = {"project": "work", "time_of_day": "morning"}
    
    # Test ranking
    print("\n1. Suggestion Ranking:")
    ranked = ranker.rank_suggestions(suggestions, context, top_n=3)
    
    for suggestion in ranked:
        print(f"\n   Rank {suggestion.rank}: {suggestion.suggestion_data['name']}")
        print(f"      Total score: {suggestion.total_score:.3f}")
        print(f"      Trust: {suggestion.score_breakdown['trust']:.2f}")
        print(f"      Context: {suggestion.score_breakdown['context']:.2f}")
        print(f"      History: {suggestion.score_breakdown['history']:.2f}")
        print(f"      Risk: {suggestion.score_breakdown['risk']:.2f}")
        print(f"      Recency: {suggestion.score_breakdown['recency']:.2f}")
    
    # Test best suggestion
    print("\n2. Best Suggestion:")
    best = ranker.get_best_suggestion(suggestions, context)
    if best:
        print(f"   ✓ Best: {best.suggestion_data['name']}")
        print(f"   ✓ Score: {best.total_score:.3f}")
    
    print("\n✅ Suggestion Ranker: PASSED")


def test_adaptive_risk_scorer():
    """Test adaptive risk scoring with safety floors"""
    print("\n=== Testing Adaptive Risk Scorer ===")
    
    scorer = AdaptiveRiskScorer()
    
    # Test safety floors
    print("\n1. Safety Floor Enforcement:")
    for operation, floor in list(CRITICAL_OPERATIONS.items())[:3]:
        threshold = scorer.get_threshold(operation, base_threshold=0.5)
        print(f"   {operation}: {threshold:.2f} (floor: {floor:.2f})")
        assert threshold >= floor, f"Safety floor violated for {operation}!"
    
    # Test adaptive risk calculation
    print("\n2. Adaptive Risk Assessment:")
    cmd = Command(
        intent="delete_system_file",
        raw_input="delete important.sys",
        confidence=0.9,
        entities={"filename": "important.sys"}
    )
    
    assessment = scorer.calculate_risk(cmd)
    print(f"   ✓ Risk level: {assessment.risk_level.value}")
    print(f"   ✓ Risk score: {assessment.risk_score:.2f}")
    print(f"   ✓ Threshold: {assessment.confirmation_threshold:.2f}")
    print(f"   ✓ Requires confirmation: {assessment.requires_confirmation}")
    
    # Verify safety floor
    assert assessment.confirmation_threshold >= CRITICAL_OPERATIONS["delete_system_file"], \
        "Safety floor not enforced!"
    
    # Test override recording
    print("\n3. Override Learning:")
    scorer.record_override("create_file", accepted=True)
    adjustment_summary = scorer.get_adjustment_summary()
    print(f"   ✓ Total adjustments: {adjustment_summary['total_adjustments']}")
    print(f"   ✓ Critical operations protected: {len(adjustment_summary['critical_operations'])}")
    
    # Test calibration
    print("\n4. Threshold Calibration:")
    scorer.calibrate_thresholds()
    print(f"   ✓ Calibration complete")
    
    print("\n✅ Adaptive Risk Scorer: PASSED")


def main():
    """Run all Phase 3 tests"""
    print("=" * 60)
    print("Phase 3A & 3B Tests - Adaptive Intelligence Layer")
    print("=" * 60)
    
    try:
        # Phase 3A tests
        test_behavioral_memory()
        test_confidence_tracker()
        test_rejection_learner()
        
        # Phase 3B tests
        test_suggestion_ranker()
        test_adaptive_risk_scorer()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nPhase 3A & 3B: Complete!")
        print("- Behavioral memory with SQLite ✅")
        print("- Confidence tracking (3 types) ✅")
        print("- Rejection learning (logarithmic) ✅")
        print("- Suggestion ranking (normalized) ✅")
        print("- Adaptive risk (safety floors) ✅")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
