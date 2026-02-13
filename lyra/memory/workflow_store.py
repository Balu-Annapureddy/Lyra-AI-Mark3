"""
Workflow Storage - Phase 2B
Stores workflows as JSON with versioning
Supports parameterization and metadata tracking
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from lyra.reasoning.command_schema import Command
from lyra.core.logger import get_logger


@dataclass
class WorkflowStep:
    """Single step in a workflow"""
    step_id: str
    command: Command
    order: int
    description: Optional[str] = None
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "step_id": self.step_id,
            "command": self.command.to_dict() if hasattr(self.command, 'to_dict') else str(self.command),
            "order": self.order,
            "description": self.description,
            "parameters": self.parameters
        }


@dataclass
class Workflow:
    """Workflow definition with versioning"""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    version: int = 1
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = None
    parameters: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        if self.tags is None:
            self.tags = []
        if self.parameters is None:
            self.parameters = {}
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "parameters": self.parameters,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """Create workflow from dictionary"""
        # Reconstruct steps
        steps = []
        for step_data in data.get("steps", []):
            # For now, store command as dict
            step = WorkflowStep(
                step_id=step_data["step_id"],
                command=step_data["command"],  # Will be reconstructed on execution
                order=step_data["order"],
                description=step_data.get("description"),
                parameters=step_data.get("parameters", {})
            )
            steps.append(step)
        
        return cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            description=data["description"],
            steps=steps,
            version=data.get("version", 1),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            tags=data.get("tags", []),
            parameters=data.get("parameters", {}),
            metadata=data.get("metadata", {})
        )


class WorkflowStore:
    """
    Workflow storage with JSON backend and versioning
    Stores workflows in individual JSON files
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if storage_path is None:
            project_root = Path(__file__).parent.parent.parent
            storage_path = str(project_root / "data" / "workflows")
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Workflow storage initialized at: {self.storage_path}")
    
    def save_workflow(self, workflow: Workflow) -> bool:
        """
        Save workflow to storage
        
        Args:
            workflow: Workflow to save
        
        Returns:
            True if successful
        """
        try:
            workflow.updated_at = datetime.now().isoformat()
            
            # Save to JSON file
            file_path = self.storage_path / f"{workflow.workflow_id}.json"
            with open(file_path, 'w') as f:
                json.dump(workflow.to_dict(), f, indent=2)
            
            self.logger.info(f"Saved workflow: {workflow.name} (v{workflow.version})")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to save workflow: {e}")
            return False
    
    def load_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        Load workflow from storage
        
        Args:
            workflow_id: Workflow ID
        
        Returns:
            Workflow or None if not found
        """
        try:
            file_path = self.storage_path / f"{workflow_id}.json"
            
            if not file_path.exists():
                self.logger.warning(f"Workflow not found: {workflow_id}")
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            workflow = Workflow.from_dict(data)
            self.logger.info(f"Loaded workflow: {workflow.name} (v{workflow.version})")
            return workflow
        
        except Exception as e:
            self.logger.error(f"Failed to load workflow: {e}")
            return None
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all workflows
        
        Returns:
            List of workflow metadata
        """
        workflows = []
        
        try:
            for file_path in self.storage_path.glob("*.json"):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                workflows.append({
                    "workflow_id": data["workflow_id"],
                    "name": data["name"],
                    "description": data["description"],
                    "version": data.get("version", 1),
                    "steps": len(data.get("steps", [])),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "tags": data.get("tags", [])
                })
            
            return workflows
        
        except Exception as e:
            self.logger.error(f"Failed to list workflows: {e}")
            return []
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete workflow
        
        Args:
            workflow_id: Workflow ID
        
        Returns:
            True if successful
        """
        try:
            file_path = self.storage_path / f"{workflow_id}.json"
            
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"Deleted workflow: {workflow_id}")
                return True
            else:
                self.logger.warning(f"Workflow not found: {workflow_id}")
                return False
        
        except Exception as e:
            self.logger.error(f"Failed to delete workflow: {e}")
            return False
    
    def create_version(self, workflow: Workflow) -> Workflow:
        """
        Create a new version of a workflow
        
        Args:
            workflow: Workflow to version
        
        Returns:
            New workflow with incremented version
        """
        new_workflow = Workflow(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            description=workflow.description,
            steps=workflow.steps.copy(),
            version=workflow.version + 1,
            created_at=workflow.created_at,
            updated_at=datetime.now().isoformat(),
            tags=workflow.tags.copy(),
            parameters=workflow.parameters.copy(),
            metadata=workflow.metadata.copy()
        )
        
        return new_workflow
    
    def search_workflows(self, query: str) -> List[Dict[str, Any]]:
        """
        Search workflows by name or tags
        
        Args:
            query: Search query
        
        Returns:
            List of matching workflows
        """
        all_workflows = self.list_workflows()
        query_lower = query.lower()
        
        matching = []
        for wf in all_workflows:
            if (query_lower in wf["name"].lower() or 
                query_lower in wf["description"].lower() or
                any(query_lower in tag.lower() for tag in wf["tags"])):
                matching.append(wf)
        
        return matching
