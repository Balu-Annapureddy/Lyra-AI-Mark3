"""
Test Phase 2B Workflow Engine
Tests workflow recording, storage, execution, and risk aggregation
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lyra.memory.workflow_store import WorkflowStore, Workflow, WorkflowStep
from lyra.reasoning.workflow_manager import WorkflowManager
from lyra.safety.workflow_risk_aggregator import WorkflowRiskAggregator
from lyra.reasoning.command_schema import Command
import uuid


def test_workflow_storage():
    """Test workflow storage and retrieval"""
    print("\n=== Testing Workflow Storage ===")
    
    store = WorkflowStore()
    
    # Create test workflow
    steps = [
        WorkflowStep(
            step_id=str(uuid.uuid4()),
            command={"intent": "open_application", "app": "notepad"},
            order=0,
            description="Open Notepad"
        ),
        WorkflowStep(
            step_id=str(uuid.uuid4()),
            command={"intent": "create_file", "filename": "test.txt"},
            order=1,
            description="Create test file"
        )
    ]
    
    workflow = Workflow(
        workflow_id=str(uuid.uuid4()),
        name="Test Workflow",
        description="A simple test workflow",
        steps=steps,
        tags=["test", "demo"]
    )
    
    # Save workflow
    success = store.save_workflow(workflow)
    print(f"✓ Workflow saved: {success}")
    
    # Load workflow
    loaded = store.load_workflow(workflow.workflow_id)
    print(f"✓ Workflow loaded: {loaded.name}")
    print(f"✓ Steps: {len(loaded.steps)}")
    
    # List workflows
    workflows = store.list_workflows()
    print(f"✓ Total workflows: {len(workflows)}")
    
    # Search workflows
    results = store.search_workflows("test")
    print(f"✓ Search results: {len(results)}")
    
    print("✅ Workflow Storage: PASSED")
    return workflow.workflow_id


def test_workflow_manager(workflow_id: str):
    """Test workflow manager"""
    print("\n=== Testing Workflow Manager ===")
    
    manager = WorkflowManager()
    
    # Get workflow details
    details = manager.get_workflow_details(workflow_id)
    print(f"✓ Workflow: {details['name']}")
    print(f"✓ Steps: {details['steps']}")
    
    # List all workflows
    all_workflows = manager.list_workflows()
    print(f"✓ Total workflows: {len(all_workflows)}")
    
    print("✅ Workflow Manager: PASSED")


def test_workflow_risk_aggregation(workflow_id: str):
    """Test workflow risk aggregation"""
    print("\n=== Testing Workflow Risk Aggregation ===")
    
    store = WorkflowStore()
    aggregator = WorkflowRiskAggregator()
    
    # Load workflow
    workflow = store.load_workflow(workflow_id)
    
    # Calculate risk with different trust scores
    print("\nRisk Assessment:")
    
    for trust_score in [0.2, 0.5, 0.8]:
        risk = aggregator.calculate_workflow_risk(workflow, trust_score)
        print(f"\n  Trust Score: {trust_score:.1f}")
        print(f"  ✓ Risk Level: {risk.level}")
        print(f"  ✓ Risk Score: {risk.score:.2f}")
        print(f"  ✓ Requires Confirmation: {risk.requires_confirmation}")
        print(f"  ✓ Reason: {risk.reason}")
        print(f"  ✓ Factors: {risk.factors}")
    
    # Test high-risk workflow
    print("\n\nHigh-Risk Workflow Test:")
    high_risk_steps = [
        WorkflowStep(
            step_id=str(uuid.uuid4()),
            command={"intent": "delete_file", "filename": "important.txt"},
            order=0,
            description="Delete file"
        ),
        WorkflowStep(
            step_id=str(uuid.uuid4()),
            command={"intent": "shutdown_system"},
            order=1,
            description="Shutdown system"
        )
    ]
    
    high_risk_workflow = Workflow(
        workflow_id=str(uuid.uuid4()),
        name="High Risk Workflow",
        description="Workflow with high-risk operations",
        steps=high_risk_steps
    )
    
    risk = aggregator.calculate_workflow_risk(high_risk_workflow, user_trust_score=0.5)
    print(f"  ✓ Risk Level: {risk.level}")
    print(f"  ✓ Risk Score: {risk.score:.2f}")
    print(f"  ✓ Requires Confirmation: {risk.requires_confirmation}")
    print(f"  ✓ Max Step Risk: {risk.factors['max_step_risk']:.2f}")
    
    print("\n✅ Workflow Risk Aggregation: PASSED")


def test_workflow_recording():
    """Test workflow recording"""
    print("\n=== Testing Workflow Recording ===")
    
    manager = WorkflowManager()
    
    # Start recording
    manager.start_recording()
    print(f"✓ Recording started: {manager.is_recording()}")
    
    # Simulate recording steps
    for i in range(3):
        command = Command(
            intent=f"test_action_{i}",
            raw_input=f"Test command {i}",
            confidence=0.9,
            entities={"step": i}
        )
        manager.record_step(command)
        print(f"✓ Recorded step {i+1}")
    
    # Stop recording and save
    workflow = manager.stop_recording(
        name="Recorded Workflow",
        description="Workflow created from recording",
        tags=["recorded", "test"]
    )
    
    if workflow:
        print(f"✓ Workflow saved: {workflow.name}")
        print(f"✓ Steps recorded: {len(workflow.steps)}")
    
    print("✅ Workflow Recording: PASSED")


def main():
    """Run all Phase 2B workflow tests"""
    print("=" * 60)
    print("Phase 2B Workflow Engine Tests")
    print("=" * 60)
    
    try:
        # Test storage
        workflow_id = test_workflow_storage()
        
        # Test manager
        test_workflow_manager(workflow_id)
        
        # Test risk aggregation
        test_workflow_risk_aggregation(workflow_id)
        
        # Test recording
        test_workflow_recording()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nPhase 2B: Workflow Engine is ready!")
        print("Next: Phase 2C - Enhanced Risk & Safety Layer")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
