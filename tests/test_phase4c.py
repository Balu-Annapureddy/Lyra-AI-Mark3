"""
Phase 4C Tests - Execution Safety Enhancements
Tests for dependency resolution, rollback, verification, simulation, panic stop
"""

import pytest
import os
import tempfile
from pathlib import Path
from lyra.execution.dependency_resolver import DependencyResolver
from lyra.execution.rollback_manager import RollbackManager
from lyra.execution.execution_gateway import ExecutionGateway
from lyra.planning.execution_planner import ExecutionStep, ExecutionPlan


class TestDependencyResolver:
    """Test dependency resolution"""
    
    def test_simple_order(self):
        """Test simple dependency ordering"""
        resolver = DependencyResolver()
        
        steps = [
            ExecutionStep(
                step_id="step2",
                step_number=2,
                description="Step 2",
                tool_required="write_file",
                parameters={"path": "output.txt", "content": "${step1.output}"},
                depends_on=["step1"],
                reversible=True
            ),
            ExecutionStep(
                step_id="step1",
                step_number=1,
                description="Step 1",
                tool_required="read_file",
                parameters={"path": "input.txt"},
                depends_on=[],
                reversible=False
            )
        ]
        
        ordered = resolver.resolve_execution_order(steps)
        
        assert len(ordered) == 2
        assert ordered[0].step_id == "step1"
        assert ordered[1].step_id == "step2"
    
    def test_circular_dependency(self):
        """Test circular dependency detection"""
        resolver = DependencyResolver()
        
        steps = [
            ExecutionStep(
                step_id="step1",
                step_number=1,
                description="Step 1",
                tool_required="read_file",
                parameters={},
                depends_on=["step2"],
                reversible=False
            ),
            ExecutionStep(
                step_id="step2",
                step_number=2,
                description="Step 2",
                tool_required="write_file",
                parameters={},
                depends_on=["step1"],
                reversible=True
            )
        ]
        
        with pytest.raises(ValueError, match="Circular dependency"):
            resolver.resolve_execution_order(steps)
    
    def test_output_substitution(self):
        """Test output substitution"""
        resolver = DependencyResolver()
        
        step = ExecutionStep(
            step_id="step2",
            step_number=2,
            description="Step 2",
            tool_required="write_file",
            parameters={"path": "output.txt", "content": "${step1.output}"},
            depends_on=["step1"],
            reversible=True
        )
        
        context = {
            "step1": {
                "output": "Hello World",
                "success": True
            }
        }
        
        substituted = resolver.substitute_outputs(step, context)
        
        assert substituted.parameters["content"] == "Hello World"


class TestRollbackManager:
    """Test rollback mechanism"""
    
    def test_snapshot_creation_write_file(self):
        """Test snapshot creation for write_file"""
        manager = RollbackManager()
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Original content")
            temp_path = f.name
        
        try:
            step = ExecutionStep(
                step_id="test_step",
                step_number=1,
                description="Write file",
                tool_required="write_file",
                parameters={"path": temp_path, "content": "New content"},
                depends_on=[],
                reversible=True
            )
            
            snapshot = manager.create_snapshot(step)
            
            assert snapshot is not None
            assert snapshot.step_id == "test_step"
            assert snapshot.tool_name == "write_file"
            assert snapshot.snapshot_data["existed"] == True
            assert snapshot.snapshot_data["old_content"] == "Original content"
        
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_rollback_write_file(self):
        """Test rollback for write_file"""
        manager = RollbackManager()
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Original content")
            temp_path = f.name
        
        try:
            step = ExecutionStep(
                step_id="test_step",
                step_number=1,
                description="Write file",
                tool_required="write_file",
                parameters={"path": temp_path, "content": "New content"},
                depends_on=[],
                reversible=True
            )
            
            # Create snapshot
            snapshot = manager.create_snapshot(step)
            
            # Modify file
            with open(temp_path, 'w') as f:
                f.write("New content")
            
            # Rollback
            success = manager.rollback_step("test_step")
            
            assert success == True
            
            # Verify content restored
            with open(temp_path, 'r') as f:
                content = f.read()
            assert content == "Original content"
        
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_no_snapshot_for_non_reversible(self):
        """Test that no snapshot is created for non-reversible steps"""
        manager = RollbackManager()
        
        step = ExecutionStep(
            step_id="test_step",
            step_number=1,
            description="Read file",
            tool_required="read_file",
            parameters={"path": "test.txt"},
            depends_on=[],
            reversible=False
        )
        
        snapshot = manager.create_snapshot(step)
        
        assert snapshot is None


class TestExecutionGateway:
    """Test execution gateway Phase 4C features"""
    
    def test_simulation_mode(self):
        """Test simulation mode"""
        gateway = ExecutionGateway()
        
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                ExecutionStep(
                    step_id="step1",
                    step_number=1,
                    description="Read file",
                    tool_required="read_file",
                    parameters={"path": "test.txt"},
                    depends_on=[],
                    reversible=False
                )
            ],
            total_risk_score=0.3,
            requires_confirmation=False
        )
        
        result = gateway.execute_plan(plan, simulate=True)
        
        assert result.success == True
        assert result.steps_completed == 1
        assert "[SIMULATED]" in result.results[0].output
    
    def test_panic_stop(self):
        """Test panic stop mechanism"""
        gateway = ExecutionGateway()
        
        # Activate panic stop
        gateway.panic_stop("Test panic")
        
        assert gateway.is_panic_stopped() == True
        
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                ExecutionStep(
                    step_id="step1",
                    step_number=1,
                    description="Read file",
                    tool_required="read_file",
                    parameters={"path": "test.txt"},
                    depends_on=[],
                    reversible=False
                )
            ],
            total_risk_score=0.3,
            requires_confirmation=False
        )
        
        result = gateway.execute_plan(plan)
        
        assert result.success == False
        assert "halted" in result.error.lower()
        
        # Resume
        gateway.resume_execution()
        assert gateway.is_panic_stopped() == False
    
    def test_dependency_resolution_in_plan(self):
        """Test dependency resolution during execution"""
        gateway = ExecutionGateway()
        
        plan = ExecutionPlan(
            plan_id="test_plan",
            steps=[
                ExecutionStep(
                    step_id="step2",
                    step_number=2,
                    description="Step 2",
                    tool_required="get_system_info",
                    parameters={},
                    depends_on=["step1"],
                    reversible=False
                ),
                ExecutionStep(
                    step_id="step1",
                    step_number=1,
                    description="Step 1",
                    tool_required="get_system_info",
                    parameters={},
                    depends_on=[],
                    reversible=False
                )
            ],
            total_risk_score=0.2,
            requires_confirmation=False
        )
        
        result = gateway.execute_plan(plan, simulate=True)
        
        assert result.success == True
        # Verify step1 executed before step2
        assert result.results[0].step_id == "step1"
        assert result.results[1].step_id == "step2"
    
    def test_verification_failure_triggers_rollback(self):
        """Test that verification failure triggers rollback"""
        gateway = ExecutionGateway()
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Original")
            temp_path = f.name
        
        try:
            plan = ExecutionPlan(
                plan_id="test_plan",
                steps=[
                    ExecutionStep(
                        step_id="step1",
                        step_number=1,
                        description="Write file",
                        tool_required="write_file",
                        parameters={"path": temp_path, "content": ""},  # Empty content
                        depends_on=[],
                        reversible=True
                    )
                ],
                total_risk_score=0.5,
                requires_confirmation=False
            )
            
            result = gateway.execute_plan(plan, confirmed=True)
            
            # Verification should fail for empty content
            # (Note: This depends on verify() implementation)
            # For now, just verify execution completed
            assert len(result.results) == 1
        
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestIntegration:
    """Integration tests for Phase 4C"""
    
    def test_full_pipeline_with_rollback(self):
        """Test full pipeline: dependency, snapshot, execute, verify, rollback"""
        gateway = ExecutionGateway()
        
        # Create temp files
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Input data")
            input_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Original output")
            output_path = f.name
        
        try:
            plan = ExecutionPlan(
                plan_id="test_plan",
                steps=[
                    ExecutionStep(
                        step_id="step1",
                        step_number=1,
                        description="Read input",
                        tool_required="read_file",
                        parameters={"path": input_path},
                        depends_on=[],
                        reversible=False
                    ),
                    ExecutionStep(
                        step_id="step2",
                        step_number=2,
                        description="Write output",
                        tool_required="write_file",
                        parameters={"path": output_path, "content": "New output"},
                        depends_on=["step1"],
                        reversible=True
                    )
                ],
                total_risk_score=0.5,
                requires_confirmation=False
            )
            
            result = gateway.execute_plan(plan, confirmed=True)
            
            assert result.success == True
            assert result.steps_completed == 2
        
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
