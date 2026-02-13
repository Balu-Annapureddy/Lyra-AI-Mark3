"""
Workflow Manager - Phase 2B
Records, manages, and executes workflows
Integrates with SystemStateManager for recording
"""

import uuid
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from lyra.memory.workflow_store import WorkflowStore, Workflow, WorkflowStep
from lyra.reasoning.command_schema import Command
from lyra.core.system_state import SystemStateManager
from lyra.core.logger import get_logger


class WorkflowManager:
    """
    Manages workflow recording, storage, and execution
    Integrates with centralized state manager
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.store = WorkflowStore()
        self.state_manager = SystemStateManager()
        
        # Callback for executing commands
        self.execute_command_callback: Optional[Callable[[Command], Any]] = None
    
    def set_execute_callback(self, callback: Callable[[Command], Any]):
        """
        Set callback for executing commands
        
        Args:
            callback: Function that executes a command
        """
        self.execute_command_callback = callback
    
    def start_recording(self):
        """Start recording a workflow"""
        self.state_manager.start_workflow_recording()
        self.logger.info("Started workflow recording")
    
    def stop_recording(self, name: str, description: str = "", tags: List[str] = None) -> Optional[Workflow]:
        """
        Stop recording and save workflow
        
        Args:
            name: Workflow name
            description: Workflow description
            tags: Optional tags
        
        Returns:
            Created workflow or None if no steps recorded
        """
        steps_commands = self.state_manager.stop_workflow_recording()
        
        if not steps_commands:
            self.logger.warning("No steps recorded in workflow")
            return None
        
        # Create workflow steps
        steps = []
        for i, command in enumerate(steps_commands):
            step = WorkflowStep(
                step_id=str(uuid.uuid4()),
                command=command,
                order=i,
                description=f"Step {i+1}: {command.intent}"
            )
            steps.append(step)
        
        # Create workflow
        workflow = Workflow(
            workflow_id=str(uuid.uuid4()),
            name=name,
            description=description or f"Workflow with {len(steps)} steps",
            steps=steps,
            tags=tags or [],
            metadata={
                "recorded_at": datetime.now().isoformat(),
                "step_count": len(steps)
            }
        )
        
        # Save workflow
        if self.store.save_workflow(workflow):
            self.logger.info(f"Saved workflow: {name} ({len(steps)} steps)")
            return workflow
        else:
            self.logger.error(f"Failed to save workflow: {name}")
            return None
    
    def is_recording(self) -> bool:
        """Check if currently recording a workflow"""
        return self.state_manager.is_recording_workflow()
    
    def record_step(self, command: Command):
        """
        Record a step in the current workflow
        
        Args:
            command: Command to record
        """
        self.state_manager.record_workflow_step(command)
    
    def execute_workflow(self, workflow_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a workflow
        
        Args:
            workflow_id: Workflow ID to execute
            parameters: Optional parameters to override
        
        Returns:
            Execution result
        """
        workflow = self.store.load_workflow(workflow_id)
        
        if not workflow:
            return {
                "success": False,
                "error": f"Workflow not found: {workflow_id}"
            }
        
        if not self.execute_command_callback:
            return {
                "success": False,
                "error": "No execution callback set"
            }
        
        self.logger.info(f"Executing workflow: {workflow.name}")
        
        results = []
        failed_steps = []
        
        # Execute each step
        for step in sorted(workflow.steps, key=lambda s: s.order):
            try:
                self.logger.info(f"Executing step {step.order + 1}: {step.description}")
                
                # Apply parameters if provided
                command = step.command
                if parameters:
                    # Merge parameters (simplified for now)
                    if hasattr(command, 'params'):
                        command.params.update(parameters)
                
                # Execute command
                result = self.execute_command_callback(command)
                
                results.append({
                    "step": step.order,
                    "description": step.description,
                    "success": True,
                    "result": result
                })
            
            except Exception as e:
                self.logger.error(f"Step {step.order + 1} failed: {e}")
                failed_steps.append(step.order)
                results.append({
                    "step": step.order,
                    "description": step.description,
                    "success": False,
                    "error": str(e)
                })
                
                # Stop on first failure
                break
        
        success = len(failed_steps) == 0
        
        return {
            "success": success,
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "total_steps": len(workflow.steps),
            "executed_steps": len(results),
            "failed_steps": failed_steps,
            "results": results
        }
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows"""
        return self.store.list_workflows()
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID"""
        return self.store.load_workflow(workflow_id)
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow"""
        return self.store.delete_workflow(workflow_id)
    
    def update_workflow(self, workflow: Workflow) -> bool:
        """Update existing workflow"""
        # Create new version
        new_workflow = self.store.create_version(workflow)
        return self.store.save_workflow(new_workflow)
    
    def search_workflows(self, query: str) -> List[Dict[str, Any]]:
        """Search workflows"""
        return self.store.search_workflows(query)
    
    def get_workflow_details(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed workflow information
        
        Args:
            workflow_id: Workflow ID
        
        Returns:
            Workflow details or None
        """
        workflow = self.store.load_workflow(workflow_id)
        
        if not workflow:
            return None
        
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "version": workflow.version,
            "steps": [
                {
                    "order": step.order,
                    "description": step.description,
                    "parameters": step.parameters
                }
                for step in sorted(workflow.steps, key=lambda s: s.order)
            ],
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
            "tags": workflow.tags,
            "metadata": workflow.metadata
        }
