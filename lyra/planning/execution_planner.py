import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from lyra.planning.planning_schema import ExecutionPlan, PlanStep
from lyra.safety.adaptive_risk_scorer import AdaptiveRiskScorer
from lyra.reasoning.confidence_tracker import ConfidenceTracker
from lyra.core.logger import get_logger





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
        requires_confirmation = any(step.step_risk in ["HIGH", "CRITICAL"] for step in steps)
        estimated_duration = len(steps) * 1.0  # Heuristic for Phase 4A
        
        # Calculate plan confidence
        confidence = self._calculate_plan_confidence(steps, context)
        
        plan = ExecutionPlan(
            reasoning_id=str(uuid.uuid4()),
            risk_level=total_risk,
            steps=steps,
            requires_confirmation=requires_confirmation
        )
        plan.freeze()
        
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
            
            step = PlanStep(
                tool_name="write_file",
                validated_input={"path": path, "content": content},
                step_risk="MEDIUM",
                description=f"Write to file {path}"
            )
            steps.append(step)
        
        elif command.intent == "read_file":
            path = command.entities.get("path", "")
            
            step = PlanStep(
                tool_name="read_file",
                validated_input={"path": path},
                step_risk="LOW",
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
            
            step = PlanStep(
                tool_name="open_url",
                validated_input={"url": url},
                step_risk="LOW",
                description=f"Open URL {url}"
            )
            steps.append(step)
        
        elif command.intent == "launch_app":
            app_name = command.entities.get("app_name", "")
            
            step = PlanStep(
                tool_name="launch_app",
                validated_input={"app_name": app_name},
                step_risk="LOW",
                description=f"Launch application {app_name}"
            )
            steps.append(step)
        elif command.intent == "autonomous_goal" or command.intent == "complex_goal":
            # Handled by TaskOrchestrator in Pipeline
            self.logger.info("Autonomous goal detected - transfer to orchestrator.")
            return None
        
        elif command.intent == "delete_file":
            path = command.entities.get("path", "")
            step = PlanStep(
                tool_name="delete_file",
                validated_input={"path": path},
                step_risk="HIGH",
                description=f"Delete file {path}"
            )
            steps.append(step)
            
        elif command.intent == "install_software":
            package = command.entities.get("package", "unknown")
            step = PlanStep(
                tool_name="install_software",
                validated_input={"package": package},
                step_risk="MEDIUM",
                description=f"Install software: {package}"
            )
            steps.append(step)
            
        elif command.intent == "change_config":
            setting = command.entities.get("setting", "unknown")
            value = command.entities.get("value", "unknown")
            step = PlanStep(
                tool_name="change_config",
                validated_input={"setting": setting, "value": value},
                step_risk="MEDIUM",
                description=f"Change configuration: {setting} to {value}"
            )
            steps.append(step)
            
        else:
            # Unknown intent or no specific mapping
            self.logger.warning(f"No specific plan mapping for intent: {command.intent}")
            # Map it generically if possible or return None
            if command.intent == "unknown":
                return None
        
        # Calculate overall metrics
        total_risk = self._calculate_total_risk(steps)
        requires_confirmation = any(step.step_risk in ["HIGH", "CRITICAL"] for step in steps)
        estimated_duration = len(steps) * 1.0
        
        plan = ExecutionPlan(
            reasoning_id=str(uuid.uuid4()),
            risk_level=total_risk,
            steps=steps,
            requires_confirmation=requires_confirmation
        )
        plan.freeze()
        
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
    
    def _create_step(self, action: Dict[str, Any], step_number: int) -> PlanStep:
        """
        Create execution step from action
        
        Args:
            action: Action dictionary
            step_number: Step number
        
        Returns:
            PlanStep
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
        
        return PlanStep(
            tool_name=tool_required,
            validated_input=parameters,
            step_risk=risk_level,
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
    
    def _calculate_total_risk(self, steps: List[PlanStep]) -> str:
        """Determine overall risk level for the plan."""
        if not steps:
            return "LOW"
        
        risk_hierarchy = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        max_risk = "LOW"
        for step in steps:
            if risk_hierarchy[step.step_risk] > risk_hierarchy[max_risk]:
                max_risk = step.step_risk
        return max_risk
    
    def _calculate_plan_confidence(self, steps: List[PlanStep], 
                                   context: Dict[str, Any]) -> float:
        """Calculate overall plan confidence"""
        if not steps:
            return 0.0
        return 0.9 # Hardened v1.3 simplified for rule-based path
    
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
            "steps": [str(step) for step in plan.steps],
            "risk_level": plan.risk_level,
            "requires_confirmation": plan.requires_confirmation
        }
