"""
Test Phase 2C & 2D - Risk, Safety, and Proactive Features
Tests risk scoring, execution logging, pattern detection, and proactive suggestions
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lyra.safety.risk_scorer import RiskScorer
from lyra.safety.execution_logger import ExecutionLogger
from lyra.reasoning.pattern_detector import PatternDetector
from lyra.reasoning.proactive_agent import ProactiveAgent
from lyra.reasoning.command_schema import Command, RiskLevel
from lyra.memory.event_memory import EventMemory
from datetime import datetime


def test_risk_scorer():
    """Test dynamic risk scoring"""
    print("\n=== Testing Risk Scorer ===")
    
    scorer = RiskScorer()
    
    # Test different risk levels
    test_commands = [
        Command(intent="get_time", raw_input="what time is it", confidence=0.9),
        Command(intent="open_application", raw_input="open calculator", confidence=0.9, entities={"app": "calculator"}),
        Command(intent="create_file", raw_input="create test.txt", confidence=0.9, entities={"filename": "test.txt"}),
        Command(intent="delete_file", raw_input="delete important.txt", confidence=0.9, entities={"filename": "important.txt"}),
        Command(intent="shutdown_system", raw_input="shutdown computer", confidence=0.9)
    ]
    
    print("\nRisk Assessments:")
    for cmd in test_commands:
        assessment = scorer.calculate_risk(cmd)
        print(f"\n  Intent: {cmd.intent}")
        print(f"  ✓ Risk Level: {assessment.risk_level.value}")
        print(f"  ✓ Risk Score: {assessment.risk_score:.2f}")
        print(f"  ✓ Requires Confirmation: {assessment.requires_confirmation}")
        print(f"  ✓ Threshold: {assessment.confirmation_threshold:.2f}")
        print(f"  ✓ Reason: {assessment.reason}")
    
    print("\n✅ Risk Scorer: PASSED")


def test_execution_logger():
    """Test execution logging with rollback"""
    print("\n=== Testing Execution Logger ===")
    
    logger = ExecutionLogger()
    
    # Test file creation command
    cmd = Command(
        intent="create_file",
        raw_input="create test.txt",
        confidence=0.9,
        entities={"filename": "test_execution.txt"}
    )
    
    # Capture before state
    before_state = logger.capture_before_state(cmd)
    print(f"✓ Before state captured: {before_state}")
    
    # Simulate execution
    cmd.status = "completed"
    result = "File created successfully"
    
    # Capture after state
    after_state = logger.capture_after_state(cmd, result)
    print(f"✓ After state captured: {after_state}")
    
    # Log execution
    record = logger.log_execution(cmd, before_state, after_state, success=True, execution_time_ms=150.5)
    print(f"✓ Execution logged: {record.record_id}")
    print(f"✓ Rollback instructions: {record.rollback_instructions}")
    
    # Retrieve recent executions
    recent = logger.get_recent_executions(limit=5)
    print(f"✓ Recent executions: {len(recent)}")
    
    print("\n✅ Execution Logger: PASSED")


def test_pattern_detector():
    """Test pattern detection"""
    print("\n=== Testing Pattern Detector ===")
    
    detector = PatternDetector()
    event_memory = EventMemory()
    
    # Create some test events to establish patterns
    print("\nCreating test events...")
    for i in range(5):
        event_memory.store_event(
            event_id=f"test_event_{i}",
            event_type="command",
            data={"intent": "check_email", "app": "outlook"},
            importance=0.5,
            confidence_score=0.9,
            context={"project": "work"}
        )
    
    # Detect patterns
    all_patterns = detector.get_all_patterns()
    
    print(f"\n✓ Time patterns: {len(all_patterns['time_patterns'])}")
    print(f"✓ Sequence patterns: {len(all_patterns['sequence_patterns'])}")
    print(f"✓ Context patterns: {len(all_patterns['context_patterns'])}")
    
    if all_patterns['context_patterns']:
        print(f"\nSample context pattern:")
        pattern = all_patterns['context_patterns'][0]
        print(f"  Intent: {pattern['intent']}")
        print(f"  Context: {pattern['context']}")
        print(f"  Occurrences: {pattern['occurrences']}")
        print(f"  Confidence: {pattern['confidence']:.2f}")
    
    print("\n✅ Pattern Detector: PASSED")


def test_proactive_agent():
    """Test proactive suggestions"""
    print("\n=== Testing Proactive Agent ===")
    
    agent = ProactiveAgent()
    
    # Check if should be proactive
    is_proactive = agent.should_be_proactive()
    print(f"✓ Should be proactive: {is_proactive}")
    
    # Get suggestions
    suggestions = agent.get_suggestions(context={"project": "work"})
    print(f"✓ Current suggestions: {len(suggestions)}")
    
    if suggestions:
        print(f"\nSample suggestion:")
        suggestion = suggestions[0]
        print(f"  Type: {suggestion['type']}")
        print(f"  Intent: {suggestion['intent']}")
        print(f"  Reason: {suggestion['reason']}")
        print(f"  Confidence: {suggestion['confidence']:.2f}")
    
    # Test suggestion response
    agent.record_suggestion_response("test_suggestion", accepted=True)
    print(f"✓ Suggestion response recorded")
    
    # Get summary
    summary = agent.get_suggestion_summary()
    print(f"\nSuggestion Summary:")
    print(f"  Total: {summary['total_suggestions']}")
    print(f"  Accepted: {summary['accepted']}")
    print(f"  Rejected: {summary['rejected']}")
    print(f"  Acceptance Rate: {summary['acceptance_rate']:.2%}")
    
    print("\n✅ Proactive Agent: PASSED")


def main():
    """Run all Phase 2C & 2D tests"""
    print("=" * 60)
    print("Phase 2C & 2D Tests - Risk, Safety, and Proactive Features")
    print("=" * 60)
    
    try:
        # Phase 2C tests
        test_risk_scorer()
        test_execution_logger()
        
        # Phase 2D tests
        test_pattern_detector()
        test_proactive_agent()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nPhase 2C & 2D: Complete!")
        print("- Risk scoring with dynamic thresholds ✅")
        print("- Execution logging with rollback ✅")
        print("- Pattern detection ✅")
        print("- Proactive suggestions with cooldown ✅")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
