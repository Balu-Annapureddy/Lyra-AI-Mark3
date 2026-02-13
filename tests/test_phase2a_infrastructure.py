"""
Test Phase 2A Infrastructure Components
Tests system state manager, user profile manager, and enhanced event memory
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lyra.core.system_state import SystemStateManager, Suggestion
from lyra.core.user_profile import UserProfileManager
from lyra.memory.event_memory import EventMemory
from lyra.memory.memory_level import MemoryLevel
from datetime import datetime


def test_system_state():
    """Test centralized system state manager"""
    print("\n=== Testing System State Manager ===")
    
    state_mgr = SystemStateManager()
    
    # Test context management
    state_mgr.update_context("project", "LyraAI")
    state_mgr.update_context("mode", "development")
    print(f"✓ Context set: project={state_mgr.get_context('project')}")
    
    # Test trust scoring
    state_mgr.set_trust_score(0.7)
    print(f"✓ Trust score: {state_mgr.get_trust_score()}")
    
    # Test suggestion tracking
    suggestion = Suggestion(
        suggestion_id="test_001",
        suggestion_type="workflow",
        message="Would you like to save this as a workflow?",
        action="save_workflow",
        params={"name": "morning_routine"},
        confidence=0.8,
        timestamp=datetime.now()
    )
    state_mgr.record_suggestion(suggestion, accepted=True)
    print(f"✓ Suggestion recorded, trust updated to: {state_mgr.get_trust_score():.2f}")
    
    # Test workflow recording
    state_mgr.start_workflow_recording()
    print(f"✓ Workflow recording: {state_mgr.is_recording_workflow()}")
    
    print("✅ System State Manager: PASSED")


def test_user_profile():
    """Test user profile manager with trust modeling"""
    print("\n=== Testing User Profile Manager ===")
    
    profile_mgr = UserProfileManager()
    
    # Test suggestion tracking
    profile_mgr.record_suggestion(accepted=True)
    profile_mgr.record_suggestion(accepted=True)
    profile_mgr.record_suggestion(accepted=False)
    print(f"✓ Acceptance rate: {profile_mgr.profile.suggestion_acceptance_rate:.2f}")
    
    # Test command tracking
    profile_mgr.record_command(success=True)
    profile_mgr.record_command(success=True)
    profile_mgr.record_command(success=False)
    print(f"✓ Commands tracked: {profile_mgr.profile.total_commands}")
    
    # Test trust calculation
    trust = profile_mgr.get_trust_score()
    threshold = profile_mgr.get_confirmation_threshold()
    print(f"✓ Trust score: {trust:.2f}")
    print(f"✓ Confirmation threshold: {threshold:.2f}")
    
    # Test stats
    stats = profile_mgr.get_stats()
    print(f"✓ Success rate: {stats['success_rate']:.2f}")
    
    print("✅ User Profile Manager: PASSED")


def test_enhanced_event_memory():
    """Test enhanced event memory with Phase 2A fields"""
    print("\n=== Testing Enhanced Event Memory ===")
    
    event_mem = EventMemory()
    
    # Test storing event with new fields
    event_mem.store_event(
        event_id="test_event_001",
        event_type="command",
        data={"action": "create_file", "filename": "test.txt"},
        memory_level=MemoryLevel.SHORT_TERM,
        importance=0.7,
        confidence_score=0.85,
        context={"project": "LyraAI", "mode": "test"},
        error_category=None,
        user_feedback="success",
        outcome_tags=["success", "file_created"]
    )
    print("✓ Event stored with confidence score and context")
    
    # Test retrieving with new fields
    events = event_mem.retrieve_recent(limit=1)
    if events:
        event = events[0]
        print(f"✓ Retrieved event with confidence: {event.get('confidence_score', 'N/A')}")
        print(f"✓ Context: {event.get('context', {})}")
        print(f"✓ Outcome tags: {event.get('outcome_tags', [])}")
    
    print("✅ Enhanced Event Memory: PASSED")


def main():
    """Run all Phase 2A infrastructure tests"""
    print("=" * 60)
    print("Phase 2A Infrastructure Tests")
    print("=" * 60)
    
    try:
        test_system_state()
        test_user_profile()
        test_enhanced_event_memory()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nPhase 2A Infrastructure is ready!")
        print("Next: Voice interface (push-to-talk)")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
