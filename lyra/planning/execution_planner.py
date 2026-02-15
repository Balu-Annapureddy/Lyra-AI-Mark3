"""
Execution Planner - Phase 4A
Decomposes complex requests into structured execution plans
No direct OS access - plans only
"""

import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from lyra.safety.adaptive_risk_scorer import AdaptiveRiskScorer
from lyra.reasoning.confidence_tracker import ConfidenceTracker
from lyra.core.logger import get_logger


@dataclass
class ExecutionStep:
    """Single step in an execution plan"""
    step_id: str
    step_number: int
    action_type: str  # e.g., "file_read", "file_write", "command_run"
    tool_required: str  # Tool name from registry
    parameters: Dict[str, Any]
    risk_level: str  # LOW, MEDIUM, HIGH
    requires_confirmation: bool
    depends_on: List[str]  # Step IDs this depends on
    reversible: bool
    estimated_duration: float  # seconds
    description: str  # Human-readable description


@dataclass
class ExecutionPlan:
    """Complete execution plan for a request"""
    plan_id: str
    request: str  # Original user request
    steps: List[ExecutionStep]
    total_risk_score: float
    requires_confirmation: bool
    created_at: str
    estimated_total_duration: float
    confidence_score: float  # Overall plan confidence


class ExecutionPlanner:
    """
    Generates structured execution plans from user requests
    NO direct execution - planning only
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.risk_scorer = AdaptiveRiskScorer()
        self.confidence_tracker = ConfidenceTracker()
    
    def create_plan(self, request: str, context: Dict[str, Any] = None) -> ExecutionPlan:
        """
        Create execution plan from user request
        
        Args:
            request: User request string
            context: Optional context
        
        Returns:
            ExecutionPlan
        """
        context = context or {}
        
        # Parse request and identify actions
        actions = self._parse_request(request)
        
        # Generate steps
        steps = []
        for i, action in enumerate(actions, 1):
            step = self._create_step(action, i)
            steps.append(step)
        
        # Calculate overall metrics
        total_risk = self._calculate_total_risk(steps)
        requires_confirmation = any(step.requires_confirmation for step in steps)
        estimated_duration = sum(step.estimated_duration for step in steps)
        
        # Calculate plan confidence
        confidence = self._calculate_plan_confidence(steps, context)
        
        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            request=request,
            steps=steps,
            total_risk_score=total_risk,
            requires_confirmation=requires_confirmation,
            created_at=datetime.now().isoformat(),
            estimated_total_duration=estimated_duration,
            confidence_score=confidence
        )
        
        self.logger.info(f"Plan created: {plan.plan_id} with {len(steps)} steps")
        return plan
    
    def create_plan_from_command(self, command) -> ExecutionPlan:
        """
        Create execution plan from Command object
        Phase 5A: Intent-to-plan mapping
        
        Args:
            command: Command object from IntentDetector
        
        Returns:
            ExecutionPlan
        """
        steps = []
        
        # Map intent to execution steps
        if command.intent == "write_file":
            # Extract path and content from entities
            path = command.entities.get("path", "")
            content = command.entities.get("content", "")
            
            # If not in entities, try to extract from raw input
            if not path or not content:
                import re
                match = re.search(r'file\s+(\S+)\s+with content\s+["\'](.+)["\']', command.raw_input)
                if match:
                    path = match.group(1)
                    content = match.group(2)
            
            step = ExecutionStep(
                step_id=str(uuid.uuid4()),
                step_number=1,
                action_type="file_write",
                tool_required="write_file",
                parameters={"path": path, "content": content},
                risk_level="MEDIUM",
                requires_confirmation=True,
                depends_on=[],
                reversible=True,
                estimated_duration=0.5,
                description=f"Write to file {path}"
            )
            steps.append(step)
        
        elif command.intent == "read_file":
            path = command.entities.get("path", "")
            
            step = ExecutionStep(
                step_id=str(uuid.uuid4()),
                step_number=1,
                action_type="file_read",
                tool_required="read_file",
                parameters={"path": path},
                risk_level="LOW",
                requires_confirmation=False,
                depends_on=[],
                reversible=False,
                estimated_duration=0.2,
                description=f"Read file {path}"
            )
            steps.append(step)
        
        elif command.intent == "open_url":
            url = command.entities.get("url", "")
            
            # Ensure URL has protocol
            if url and not url.startswith(("http://", "https://")):
                if url.startswith("www."):
                    url = "https://" + url
                else:
                    url = "https://" + url
            
            step = ExecutionStep(
                step_id=str(uuid.uuid4()),
                step_number=1,
                action_type="app_launcher",
                tool_required="open_url",
                parameters={"url": url},
                risk_level="LOW",
                requires_confirmation=False,
                depends_on=[],
                reversible=False,
                estimated_duration=1.0,
                description=f"Open URL {url}"
            )
            steps.append(step)
        
        elif command.intent == "launch_app":
            app_name = command.entities.get("app_name", "")
            
            step = ExecutionStep(
                step_id=str(uuid.uuid4()),
                step_number=1,
                action_type="app_launcher",
                tool_required="launch_app",
                parameters={"app_name": app_name},
                risk_level="LOW",
                requires_confirmation=False,
                depends_on=[],
                reversible=False,
                estimated_duration=1.5,
                description=f"Launch application {app_name}"
            )
            steps.append(step)
        
        else:
            # Unknown intent
            self.logger.warning(f"No plan mapping for intent: {command.intent}")
            return None
        
        # Calculate overall metrics
        total_risk = self._calculate_total_risk(steps)
        requires_confirmation = any(step.requires_confirmation for step in steps)
        estimated_duration = sum(step.estimated_duration for step in steps)
        
        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            request=command.raw_input,
            steps=steps,
            total_risk_score=total_risk,
            requires_confirmation=requires_confirmation,
            created_at=datetime.now().isoformat(),
            estimated_total_duration=estimated_duration,
            confidence_score=command.confidence
        )
        
        self.logger.info(f"Plan created from command: {plan.plan_id}, intent={command.intent}")
        return plan

    
    def _parse_request(self, request: str) -> List[Dict[str, Any]]:
        """
        Parse request into action list
        Simple heuristic-based parsing for Phase 4A
        
        Args:
            request: User request
        
        Returns:
            List of action dictionaries
        """
        request_lower = request.lower()
        actions = []
        
        # File operations
        if "read" in request_lower and "file" in request_lower:
            actions.append({
                "type": "file_read",
                "tool": "read_file",
                "description": "Read file contents"
            })
        
        if "write" in request_lower and "file" in request_lower:
            actions.append({
                "type": "file_write",
                "tool": "write_file",
                "description": "Write to file"
            })
        
        if ("delete" in request_lower or "remove" in request_lower) and "file" in request_lower:
            actions.append({
                "type": "file_delete",
                "tool": "delete_file",
                "description": "Delete file"
            })
        
        # Command operations
        if "run" in request_lower or "execute" in request_lower:
            actions.append({
                "type": "command_run",
                "tool": "run_command",
                "description": "Execute command"
            })
        
        # System operations
        if "system" in request_lower and "info" in request_lower:
            actions.append({
                "type": "system_info",
                "tool": "get_system_info",
                "description": "Get system information"
            })
        
        # Default: treat as general command
        if not actions:
            actions.append({
                "type": "general",
                "tool": "general_action",
                "description": "General action"
            })
        
        return actions
    
    def _create_step(self, action: Dict[str, Any], step_number: int) -> ExecutionStep:
        """
        Create execution step from action
        
        Args:
            action: Action dictionary
            step_number: Step number
        
        Returns:
            ExecutionStep
        """
        action_type = action["type"]
        tool_required = action["tool"]
        
        # Determine risk level based on action type
        risk_level = self._determine_risk_level(action_type)
        
        # Determine if confirmation required
        requires_confirmation = risk_level in ["MEDIUM", "HIGH"]
        
        # Determine if reversible
        reversible = action_type in ["file_read", "system_info"]
        
        # Estimate duration
        estimated_duration = self._estimate_duration(action_type)
        
        # Create basic parameters (stub values for Phase 4A)
        parameters = {}
        if action_type in ["file_read", "file_write", "file_delete"]:
            parameters["path"] = "placeholder.txt"  # Will be filled by user
        if action_type == "file_write":
            parameters["content"] = ""  # Will be filled by user
        if action_type == "command_run":
            parameters["command"] = ""  # Will be filled by user
        
        return ExecutionStep(
            step_id=str(uuid.uuid4()),
            step_number=step_number,
            action_type=action_type,
            tool_required=tool_required,
            parameters=parameters,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            depends_on=[],  # No dependencies in simple planner
            reversible=reversible,
            estimated_duration=estimated_duration,
            description=action["description"]
        )
    
    def _determine_risk_level(self, action_type: str) -> str:
        """Determine risk level for action type"""
        high_risk = ["file_delete", "command_run", "system_modify"]
        medium_risk = ["file_write", "file_create", "config_modify"]
        
        if action_type in high_risk:
            return "HIGH"
        elif action_type in medium_risk:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _estimate_duration(self, action_type: str) -> float:
        """Estimate duration for action type (seconds)"""
        duration_map = {
            "file_read": 0.5,
            "file_write": 1.0,
            "file_delete": 0.5,
            "command_run": 2.0,
            "system_info": 0.3,
            "general": 1.0
        }
        return duration_map.get(action_type, 1.0)
    
    def _calculate_total_risk(self, steps: List[ExecutionStep]) -> float:
        """
        Calculate total risk score for plan
        Uses risk multiplication like workflow engine
        """
        if not steps:
            return 0.0
        
        # Map risk levels to scores
        risk_map = {"LOW": 0.2, "MEDIUM": 0.5, "HIGH": 0.8}
        
        # Multiply risks (compound risk)
        total_risk = 1.0
        for step in steps:
            step_risk = risk_map.get(step.risk_level, 0.5)
            total_risk *= (1.0 - step_risk)
        
        # Invert to get final risk
        final_risk = 1.0 - total_risk
        
        return min(1.0, final_risk)
    
    def _calculate_plan_confidence(self, steps: List[ExecutionStep], 
                                   context: Dict[str, Any]) -> float:
        """Calculate overall plan confidence"""
        if not steps:
            return 0.0
        
        # Simple confidence based on:
        # - Number of steps (fewer = higher confidence)
        # - Risk levels (lower = higher confidence)
        # - Reversibility (more reversible = higher confidence)
        
        step_count_factor = max(0.5, 1.0 - (len(steps) * 0.1))
        
        reversible_count = sum(1 for step in steps if step.reversible)
        reversibility_factor = reversible_count / len(steps) if steps else 0.0
        
        high_risk_count = sum(1 for step in steps if step.risk_level == "HIGH")
        risk_factor = max(0.3, 1.0 - (high_risk_count * 0.2))
        
        confidence = (
            0.4 * step_count_factor +
            0.3 * reversibility_factor +
            0.3 * risk_factor
        )
        
        return min(1.0, max(0.0, confidence))
    
    def validate_plan(self, plan: ExecutionPlan) -> bool:
        """
        Validate plan completeness
        
        Args:
            plan: Execution plan
        
        Returns:
            True if valid
        """
        if not plan.steps:
            self.logger.warning("Plan has no steps")
            return False
        
        # Check all steps have required fields
        for step in plan.steps:
            if not step.tool_required:
                self.logger.warning(f"Step {step.step_id} missing tool")
                return False
            
            if not step.action_type:
                self.logger.warning(f"Step {step.step_id} missing action type")
                return False
        
        return True
    
    def to_dict(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Convert plan to dictionary for logging"""
        return {
            "plan_id": plan.plan_id,
            "request": plan.request,
            "steps": [asdict(step) for step in plan.steps],
            "total_risk_score": plan.total_risk_score,
            "requires_confirmation": plan.requires_confirmation,
            "created_at": plan.created_at,
            "estimated_total_duration": plan.estimated_total_duration,
            "confidence_score": plan.confidence_score
        }
