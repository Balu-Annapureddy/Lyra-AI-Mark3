"""
Rollback Manager - Phase 4C
Manages opt-in snapshots and rollback for reversible operations
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from lyra.planning.planning_schema import PlanStep
from lyra.core.logger import get_logger


@dataclass
class RollbackSnapshot:
    """Snapshot for rollback"""
    step_id: str
    tool_name: str
    snapshot_data: Dict[str, Any]
    timestamp: str


class RollbackManager:
    """
    Manages rollback for reversible tools
    Opt-in via tool metadata: reversible=True
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.snapshots: Dict[str, RollbackSnapshot] = {}
        
        # Snapshot storage
        self.snapshot_dir = Path(__file__).parent.parent.parent / "data" / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    def create_snapshot(self, step: PlanStep) -> Optional[RollbackSnapshot]:
        """
        Create snapshot for reversible step
        Only if tool is reversible
        
        Args:
            step: Execution step
        
        Returns:
            Snapshot if created, None if not reversible
        """
        # Check if step is reversible
        if not step.reversible:
            self.logger.debug(f"Step {step.step_id} not reversible, skipping snapshot")
            return None
        
        # Create snapshot based on tool
        snapshot_data = None
        
        if step.tool_name == "write_file":
            snapshot_data = self._snapshot_write_file(step)
        elif step.tool_name == "launch_app":
            snapshot_data = self._snapshot_launch_app(step)
        # Add more tools as needed
        
        if snapshot_data is None:
            self.logger.debug(f"No snapshot handler for {step.tool_name}")
            return None
        
        # Create snapshot
        snapshot = RollbackSnapshot(
            step_id=step.step_id,
            tool_name=step.tool_name,
            snapshot_data=snapshot_data,
            timestamp=datetime.now().isoformat()
        )
        
        # Store snapshot
        self.snapshots[step.step_id] = snapshot
        self._save_snapshot(snapshot)
        
        self.logger.info(f"Created snapshot for {step.step_id}")
        
        return snapshot
    
    def _snapshot_write_file(self, step: PlanStep) -> Dict[str, Any]:
        """Create snapshot for write_file operation"""
        path = step.validated_input.get("path")
        if not path:
            return {}
        
        # Check if file exists
        if os.path.exists(path):
            # Read current content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
                
                return {
                    "path": path,
                    "existed": True,
                    "old_content": old_content
                }
            except Exception as e:
                self.logger.warning(f"Could not read file for snapshot: {e}")
                return {
                    "path": path,
                    "existed": True,
                    "old_content": None
                }
        else:
            # File doesn't exist, will be created
            return {
                "path": path,
                "existed": False,
                "old_content": None
            }
    
    def _snapshot_launch_app(self, step: PlanStep) -> Dict[str, Any]:
        """Create snapshot for launch_app operation"""
        # For now, just record app name
        # Future: store process ID for kill capability
        return {
            "app_name": step.validated_input.get("app_name"),
            "process_id": None  # Future enhancement
        }
    
    def rollback_step(self, step_id: str) -> bool:
        """
        Rollback a single step
        
        Args:
            step_id: Step ID to rollback
        
        Returns:
            True if rolled back successfully
        """
        if step_id not in self.snapshots:
            self.logger.warning(f"No snapshot for {step_id}")
            return False
        
        snapshot = self.snapshots[step_id]
        
        try:
            if snapshot.tool_name == "write_file":
                return self._rollback_write_file(snapshot)
            elif snapshot.tool_name == "launch_app":
                return self._rollback_launch_app(snapshot)
            else:
                self.logger.warning(f"No rollback handler for {snapshot.tool_name}")
                return False
        
        except Exception as e:
            self.logger.error(f"Rollback failed for {step_id}: {e}")
            return False
    
    def _rollback_write_file(self, snapshot: RollbackSnapshot) -> bool:
        """Rollback write_file operation"""
        data = snapshot.snapshot_data
        path = data.get("path")
        
        if not path:
            return False
        
        if data.get("existed"):
            # Restore old content
            old_content = data.get("old_content")
            if old_content is not None:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(old_content)
                self.logger.info(f"Restored file: {path}")
                return True
            else:
                self.logger.warning(f"Cannot restore file (no content): {path}")
                return False
        else:
            # Delete created file
            if os.path.exists(path):
                os.remove(path)
                self.logger.info(f"Deleted created file: {path}")
                return True
            else:
                self.logger.warning(f"File already deleted: {path}")
                return True
    
    def _rollback_launch_app(self, snapshot: RollbackSnapshot) -> bool:
        """Rollback launch_app operation"""
        # For now, just log
        # Future: kill process if PID stored
        self.logger.info(f"Rollback launch_app: {snapshot.snapshot_data.get('app_name')}")
        return True
    
    def rollback_plan(self, plan_id: str, step_ids: List[str]) -> int:
        """
        Rollback multiple steps in reverse order
        
        Args:
            plan_id: Plan ID
            step_ids: List of step IDs to rollback
        
        Returns:
            Number of steps rolled back
        """
        rolled_back = 0
        
        # Rollback in reverse order
        for step_id in reversed(step_ids):
            if self.rollback_step(step_id):
                rolled_back += 1
        
        self.logger.info(f"Rolled back {rolled_back}/{len(step_ids)} steps for plan {plan_id}")
        
        return rolled_back
    
    def _save_snapshot(self, snapshot: RollbackSnapshot):
        """Save snapshot to disk"""
        try:
            snapshot_file = self.snapshot_dir / f"{snapshot.step_id}.json"
            with open(snapshot_file, 'w') as f:
                json.dump(asdict(snapshot), f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save snapshot: {e}")
    
    def clear_snapshots(self, plan_id: str = None):
        """Clear snapshots for a plan or all"""
        if plan_id:
            # Clear specific plan snapshots
            to_remove = [sid for sid in self.snapshots if sid.startswith(plan_id)]
            for sid in to_remove:
                del self.snapshots[sid]
        else:
            # Clear all
            self.snapshots.clear()
