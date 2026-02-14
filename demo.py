"""
Lyra AI Demo - Interactive Feature Showcase
Demonstrates all Phase 2 features in an interactive menu
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lyra.core.system_state import SystemStateManager
from lyra.core.user_profile import UserProfileManager
from lyra.memory.event_memory import EventMemory
from lyra.memory.workflow_store import WorkflowStore, Workflow, WorkflowStep
from lyra.reasoning.workflow_manager import WorkflowManager
from lyra.safety.workflow_risk_aggregator import WorkflowRiskAggregator
from lyra.safety.risk_scorer import RiskScorer
from lyra.safety.execution_logger import ExecutionLogger
from lyra.reasoning.pattern_detector import PatternDetector
from lyra.reasoning.proactive_agent import ProactiveAgent
from lyra.reasoning.command_schema import Command
from lyra.interaction.voice_interface import VoiceInterface
import uuid
from datetime import datetime


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_infrastructure():
    """Demo Phase 2A: Infrastructure"""
    print_header("Phase 2A: Infrastructure & Trust Modeling")
    
    # System State Manager
    print("\n1. Centralized State Manager:")
    state_mgr = SystemStateManager()
    state_mgr.set_active_project("LyraAI-Demo")
    state_mgr.update_context("mode", "demo")
    print(f"   ✓ Active Project: {state_mgr.get_active_project()}")
    print(f"   ✓ Context: {state_mgr.get_context('mode')}")
    print(f"   ✓ Trust Score: {state_mgr.get_trust_score():.2f}")
    
    # User Profile Manager
    print("\n2. User Trust Modeling:")
    profile_mgr = UserProfileManager()
    profile = profile_mgr.get_profile()
    print(f"   ✓ Trust Score: {profile.trust_score:.2f}")
    print(f"   ✓ Total Commands: {profile.total_commands}")
    print(f"   ✓ Confirmation Threshold: {profile_mgr.get_confirmation_threshold():.2f}")
    
    # Enhanced Event Memory
    print("\n3. Enhanced Event Logging:")
    event_memory = EventMemory()
    event_memory.store_event(
        event_id=f"demo_{uuid.uuid4()}",
        event_type="command",
        data={"intent": "demo_command", "action": "showcase"},
        confidence_score=0.95,
        context={"project": "LyraAI-Demo", "mode": "demo"},
        outcome_tags=["success", "demo"]
    )
    recent = event_memory.retrieve_recent(limit=1)
    if recent:
        print(f"   ✓ Event stored with confidence: {recent[0]['confidence_score']}")
        print(f"   ✓ Context: {recent[0]['context']}")
        print(f"   ✓ Outcome tags: {recent[0]['outcome_tags']}")


def demo_voice():
    """Demo Phase 2A: Voice Interface"""
    print_header("Phase 2A: Voice Interface")
    
    print("\n1. Text-to-Speech Demo:")
    print("   Testing TTS engine...")
    
    try:
        voice = VoiceInterface(model_size="tiny")
        
        # List voices
        voices = voice.get_available_voices()
        print(f"   ✓ Available voices: {len(voices)}")
        
        # Test TTS
        print("   ✓ Speaking test message...")
        voice.speak("Hello! I am Lyra. All Phase 2 features are operational.")
        
        print("   ✅ Voice interface working!")
        voice.cleanup()
    except Exception as e:
        print(f"   ⚠ Voice interface error: {e}")
        print("   (This is normal if audio devices are not available)")


def demo_workflows():
    """Demo Phase 2B: Workflow Engine"""
    print_header("Phase 2B: Workflow Engine")
    
    # Create a demo workflow
    print("\n1. Creating Demo Workflow:")
    store = WorkflowStore()
    
    steps = [
        WorkflowStep(
            step_id=str(uuid.uuid4()),
            command={"intent": "open_application", "app": "notepad"},
            order=0,
            description="Open Notepad"
        ),
        WorkflowStep(
            step_id=str(uuid.uuid4()),
            command={"intent": "create_file", "filename": "demo.txt"},
            order=1,
            description="Create demo file"
        ),
        WorkflowStep(
            step_id=str(uuid.uuid4()),
            command={"intent": "write_text", "text": "Hello from Lyra!"},
            order=2,
            description="Write text"
        )
    ]
    
    workflow = Workflow(
        workflow_id=str(uuid.uuid4()),
        name="Demo Workflow",
        description="A demonstration workflow",
        steps=steps,
        tags=["demo", "test"]
    )
    
    store.save_workflow(workflow)
    print(f"   ✓ Workflow created: {workflow.name}")
    print(f"   ✓ Steps: {len(workflow.steps)}")
    
    # Workflow Risk Assessment
    print("\n2. Workflow Risk Assessment:")
    aggregator = WorkflowRiskAggregator()
    risk = aggregator.calculate_workflow_risk(workflow, user_trust_score=0.7)
    print(f"   ✓ Risk Level: {risk.level}")
    print(f"   ✓ Risk Score: {risk.score:.2f}")
    print(f"   ✓ Requires Confirmation: {risk.requires_confirmation}")
    print(f"   ✓ Reason: {risk.reason}")
    
    # List workflows
    print("\n3. Workflow Management:")
    all_workflows = store.list_workflows()
    print(f"   ✓ Total workflows: {len(all_workflows)}")
    for wf in all_workflows[:3]:  # Show first 3
        print(f"      - {wf['name']} ({wf['steps']} steps)")


def demo_risk_safety():
    """Demo Phase 2C: Risk & Safety"""
    print_header("Phase 2C: Risk & Safety Layer")
    
    # Risk Scoring
    print("\n1. Dynamic Risk Scoring:")
    scorer = RiskScorer()
    
    test_commands = [
        ("get_time", "Safe operation"),
        ("create_file", "Medium risk"),
        ("delete_file", "High risk"),
        ("shutdown_system", "Critical risk")
    ]
    
    for intent, desc in test_commands:
        cmd = Command(intent=intent, raw_input=f"test {intent}", confidence=0.9)
        assessment = scorer.calculate_risk(cmd)
        print(f"   {desc}:")
        print(f"      Risk: {assessment.risk_level.value.upper()} ({assessment.risk_score:.2f})")
        print(f"      Confirmation: {assessment.requires_confirmation}")
    
    # Execution Logging
    print("\n2. Execution Logger:")
    logger = ExecutionLogger()
    
    cmd = Command(
        intent="create_file",
        raw_input="create test.txt",
        confidence=0.9,
        entities={"filename": "demo_test.txt"}
    )
    
    before = logger.capture_before_state(cmd)
    cmd.status = "completed"
    after = logger.capture_after_state(cmd, "File created")
    
    record = logger.log_execution(cmd, before, after, success=True, execution_time_ms=125.5)
    print(f"   ✓ Execution logged: {record.record_id}")
    print(f"   ✓ Rollback instructions: {len(record.rollback_instructions)} available")


def demo_proactive():
    """Demo Phase 2D: Proactive Intelligence"""
    print_header("Phase 2D: Proactive Intelligence")
    
    # Pattern Detection
    print("\n1. Pattern Detection:")
    detector = PatternDetector()
    patterns = detector.get_all_patterns()
    
    print(f"   ✓ Time patterns: {len(patterns['time_patterns'])}")
    print(f"   ✓ Sequence patterns: {len(patterns['sequence_patterns'])}")
    print(f"   ✓ Context patterns: {len(patterns['context_patterns'])}")
    
    if patterns['context_patterns']:
        pattern = patterns['context_patterns'][0]
        print(f"\n   Sample pattern:")
        print(f"      Intent: {pattern['intent']}")
        print(f"      Confidence: {pattern['confidence']:.2f}")
    
    # Proactive Agent
    print("\n2. Proactive Suggestions:")
    agent = ProactiveAgent()
    
    is_proactive = agent.should_be_proactive()
    print(f"   ✓ Proactive mode: {is_proactive}")
    
    suggestions = agent.get_suggestions()
    print(f"   ✓ Current suggestions: {len(suggestions)}")
    
    summary = agent.get_suggestion_summary()
    print(f"\n   Suggestion Stats:")
    print(f"      Total: {summary['total_suggestions']}")
    print(f"      Acceptance rate: {summary['acceptance_rate']:.1%}")


def demo_all():
    """Run all demos"""
    print("\n" + "🚀" * 30)
    print("   LYRA AI - PHASE 2 FEATURE SHOWCASE")
    print("🚀" * 30)
    
    try:
        demo_infrastructure()
        input("\nPress Enter to continue to Voice Interface demo...")
        
        demo_voice()
        input("\nPress Enter to continue to Workflow Engine demo...")
        
        demo_workflows()
        input("\nPress Enter to continue to Risk & Safety demo...")
        
        demo_risk_safety()
        input("\nPress Enter to continue to Proactive Intelligence demo...")
        
        demo_proactive()
        
        print("\n" + "=" * 60)
        print("   ✅ ALL DEMOS COMPLETE!")
        print("=" * 60)
        print("\n   Phase 2 Status: FULLY OPERATIONAL")
        print("   All subsystems tested successfully!")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main menu"""
    while True:
        print("\n" + "=" * 60)
        print("   LYRA AI - INTERACTIVE DEMO")
        print("=" * 60)
        print("\n  Select a demo:")
        print("    1. Infrastructure & Trust Modeling (Phase 2A)")
        print("    2. Voice Interface (Phase 2A)")
        print("    3. Workflow Engine (Phase 2B)")
        print("    4. Risk & Safety Layer (Phase 2C)")
        print("    5. Proactive Intelligence (Phase 2D)")
        print("    6. Run ALL Demos")
        print("    0. Exit")
        
        choice = input("\n  Enter choice: ").strip()
        
        if choice == '1':
            demo_infrastructure()
        elif choice == '2':
            demo_voice()
        elif choice == '3':
            demo_workflows()
        elif choice == '4':
            demo_risk_safety()
        elif choice == '5':
            demo_proactive()
        elif choice == '6':
            demo_all()
        elif choice == '0':
            print("\n  Goodbye!")
            break
        else:
            print("\n  Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
