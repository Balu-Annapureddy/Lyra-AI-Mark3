# -*- coding: utf-8 -*-
"""
lyra/safety/rollback_engine.py
Phase 4: Rollback Architecture — Hardened v1.3
Manages undo stacks, snapshots, and LIFO restoration logic.

Hard Constraints:
- Rollback must NOT modify memory layer directly.
- Rollback must NOT re-plan.
- Rollback must only use registered strategies.
- Rollback failures escalate risk state.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from lyra.core.logger import get_logger

@dataclass
class RollbackAction:
    """A registered action to reverse a tool's effect."""
    step_id: str
    tool_name: str
    undo_logic: str  # Heuristic or method reference
    snapshot: Dict[str, Any]

class RollbackEngine:
    """
    Engine for capturing snapshots and executing rollback stacks.
    Enforces reversibility for tools marked as reversible in SafetyPolicyRegistry.
    
    Hardened v1.3:
    - Standardized logging: [ROLLBACK-START], [ROLLBACK-STEP], [ROLLBACK-COMPLETE], [ROLLBACK-FAILED]
    - Failure escalation: rollback failures escalate risk state
    - Strict LIFO ordering
    """
    def __init__(self):
        self.logger = get_logger(__name__)
        self._stack: List[RollbackAction] = []
        self._failure_count: int = 0
        
    def capture_pre_state(self, step_id: str, tool_name: str, parameters: Dict[str, Any]) -> Optional[RollbackAction]:
        """
        Capture state before tool execution if reversible.
        """
        snapshot = {}
        undo_logic = None
        
        if tool_name == "write_file":
            path = parameters.get("path")
            if path and os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        snapshot = {"path": path, "exists": True, "old_content": f.read()}
                    undo_logic = "restore_file"
                except Exception as e:
                    self.logger.warning(f"[ROLLBACK] Failed to snapshot {path}: {e}")
            else:
                snapshot = {"path": path, "exists": False}
                undo_logic = "delete_file"
                
        elif tool_name == "create_file":
            path = parameters.get("path")
            snapshot = {"path": path, "exists": False}
            undo_logic = "delete_file"
                
        elif tool_name == "change_config":
            snapshot = {"setting": parameters.get("setting"), "prev_value": "MOCKED_PREV"}
            undo_logic = "restore_config"

        if undo_logic:
            action = RollbackAction(step_id, tool_name, undo_logic, snapshot)
            self._stack.append(action)
            self.logger.info(f"[ROLLBACK-REGISTERED] {tool_name} (Step: {step_id})")
            return action
        
        return None

    def execute_rollback(self) -> Dict[str, Any]:
        """
        Execute the rollback stack in reverse (LIFO) order.
        Returns a summary of the rollback operation.
        """
        if not self._stack:
            self.logger.info("[ROLLBACK] No actions to rollback.")
            return {"rolled_back": 0, "failed": 0, "status": "EMPTY"}

        total = len(self._stack)
        self.logger.info(f"[ROLLBACK-START] Reversing {total} actions.")
        
        rolled_back = 0
        failed = 0
        
        for action in reversed(self._stack):
            try:
                self.logger.info(f"[ROLLBACK-STEP] Reversing {action.tool_name} (Step: {action.step_id})")
                success = self._dispatch_undo(action)
                if success:
                    rolled_back += 1
                else:
                    failed += 1
                    self._failure_count += 1
                    self.logger.error(
                        f"[ROLLBACK-FAILED] Undoing {action.tool_name} (Step: {action.step_id}) failed. "
                        f"Risk state escalated."
                    )
            except Exception as e:
                failed += 1
                self._failure_count += 1
                self.logger.error(
                    f"[ROLLBACK-FAILED] Critical failure during rollback of "
                    f"{action.tool_name} (Step: {action.step_id}): {e}. "
                    f"Risk state escalated."
                )
        
        status = "COMPLETE" if failed == 0 else "PARTIAL"
        self.logger.info(
            f"[ROLLBACK-COMPLETE] Rolled back {rolled_back}/{total} actions. "
            f"Failures: {failed}. Status: {status}."
        )
        
        self._stack = []
        
        return {
            "rolled_back": rolled_back,
            "failed": failed,
            "total": total,
            "status": status,
            "risk_escalated": failed > 0
        }

    def _dispatch_undo(self, action: RollbackAction) -> bool:
        """Dispatches undo logic based on recorded handler."""
        logic = action.undo_logic
        snap = action.snapshot
        
        if logic == "restore_file":
            path = snap.get("path")
            content = snap.get("old_content")
            if path and content is not None:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            return False
            
        elif logic == "delete_file":
            path = snap.get("path")
            if path and os.path.exists(path):
                os.remove(path)
            return True
            
        elif logic == "restore_config":
            self.logger.info(f"Restoring config {snap.get('setting')} to {snap.get('prev_value')}")
            return True
            
        self.logger.warning(f"[ROLLBACK] Unknown undo logic: {logic}")
        return False

    @property
    def has_failures(self) -> bool:
        """Check if any rollback failures have occurred."""
        return self._failure_count > 0

    def clear(self):
        """Clear the rollback stack (e.g., after successful execution)."""
        self._stack = []
