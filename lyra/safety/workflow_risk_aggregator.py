"""
Workflow Risk Aggregator - Phase 2B Critical Component
Aggregates risk across workflow steps
Workflows multiply risk, not average it
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from lyra.memory.workflow_store import Workflow
from lyra.core.logger import get_logger


@dataclass
class RiskScore:
    """Risk assessment result"""
    level: str  # low, medium, high, critical
    score: float  # 0.0-1.0
    factors: Dict[str, Any]
    requires_confirmation: bool
    reason: str = ""


class WorkflowRiskAggregator:
    """
    Aggregates risk across workflow steps
    Workflows are riskier than individual commands
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Risk thresholds
        self.thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8,
            "critical": 0.95
        }
        
        # Base confirmation threshold for workflows
        self.workflow_confirmation_threshold = 0.5  # Lower than single commands
    
    def calculate_workflow_risk(self, workflow: Workflow, user_trust_score: float = 0.5) -> RiskScore:
        """
        Aggregate risk across all workflow steps
        
        Args:
            workflow: Workflow to assess
            user_trust_score: User's trust score (0.0-1.0)
        
        Returns:
            Aggregated risk score
        """
        if not workflow.steps:
            return RiskScore(
                level="low",
                score=0.0,
                factors={},
                requires_confirmation=False,
                reason="Empty workflow"
            )
        
        # Calculate risk for each step
        step_risks = []
        for step in workflow.steps:
            step_risk = self._calculate_step_risk(step)
            step_risks.append(step_risk)
        
        # Aggregate risks (workflows multiply risk, not average)
        cumulative_risk = self._aggregate_risks(step_risks)
        
        # Add workflow complexity penalty
        complexity_penalty = min(0.2, len(workflow.steps) / 50)  # Max 0.2 for 10+ steps
        cumulative_risk = min(1.0, cumulative_risk + complexity_penalty)
        
        # Adjust for user trust
        # Low trust = higher perceived risk
        trust_adjustment = (1.0 - user_trust_score) * 0.1
        final_risk = min(1.0, cumulative_risk + trust_adjustment)
        
        # Determine risk level
        risk_level = self._get_risk_level(final_risk)
        
        # Determine if confirmation required
        requires_confirmation = final_risk > self.workflow_confirmation_threshold
        
        # Build factors
        factors = {
            "workflow_complexity": len(workflow.steps),
            "max_step_risk": max(step_risks),
            "avg_step_risk": sum(step_risks) / len(step_risks),
            "complexity_penalty": complexity_penalty,
            "trust_adjustment": trust_adjustment,
            "user_trust_score": user_trust_score
        }
        
        reason = self._build_reason(workflow, final_risk, factors)
        
        return RiskScore(
            level=risk_level,
            score=final_risk,
            factors=factors,
            requires_confirmation=requires_confirmation,
            reason=reason
        )
    
    def _calculate_step_risk(self, step) -> float:
        """
        Calculate risk for a single step
        Simplified for Phase 2B (will integrate with full RiskScorer in Phase 2C)
        
        Args:
            step: Workflow step
        
        Returns:
            Risk score (0.0-1.0)
        """
        # Base risk from command type (simplified)
        command = step.command
        
        # Check if command is a dict (from storage) or Command object
        if isinstance(command, dict):
            intent = command.get("intent", "")
        else:
            intent = getattr(command, "intent", "")
        
        # Risk mapping (simplified)
        high_risk_intents = ["delete", "shutdown", "restart", "install", "uninstall"]
        medium_risk_intents = ["create", "modify", "move", "rename"]
        
        if any(risk in intent.lower() for risk in high_risk_intents):
            return 0.8
        elif any(risk in intent.lower() for risk in medium_risk_intents):
            return 0.5
        else:
            return 0.3
    
    def _aggregate_risks(self, risks: List[float]) -> float:
        """
        Aggregate risks using max + weighted average
        Workflows multiply risk, not average it
        
        Args:
            risks: List of risk scores
        
        Returns:
            Aggregated risk score
        """
        if not risks:
            return 0.0
        
        max_risk = max(risks)
        avg_risk = sum(risks) / len(risks)
        
        # Workflows are riskier: 60% max risk + 40% average + 10% base
        # This ensures workflows are always riskier than individual commands
        aggregated = min(1.0, max_risk * 0.6 + avg_risk * 0.4 + 0.1)
        
        return aggregated
    
    def _get_risk_level(self, score: float) -> str:
        """Get risk level from score"""
        if score >= self.thresholds["critical"]:
            return "critical"
        elif score >= self.thresholds["high"]:
            return "high"
        elif score >= self.thresholds["medium"]:
            return "medium"
        else:
            return "low"
    
    def _build_reason(self, workflow: Workflow, risk_score: float, factors: Dict[str, Any]) -> str:
        """Build human-readable reason for risk assessment"""
        level = self._get_risk_level(risk_score)
        
        reasons = []
        
        if factors["workflow_complexity"] > 5:
            reasons.append(f"Complex workflow ({factors['workflow_complexity']} steps)")
        
        if factors["max_step_risk"] > 0.7:
            reasons.append("Contains high-risk operations")
        
        if factors["user_trust_score"] < 0.4:
            reasons.append("Low user trust score")
        
        if not reasons:
            reasons.append("Standard workflow execution")
        
        return f"{level.upper()} risk: {', '.join(reasons)}"
    
    def requires_confirmation(self, workflow: Workflow, user_trust_score: float = 0.5) -> bool:
        """
        Quick check if workflow requires confirmation
        
        Args:
            workflow: Workflow to check
            user_trust_score: User's trust score
        
        Returns:
            True if confirmation required
        """
        risk = self.calculate_workflow_risk(workflow, user_trust_score)
        return risk.requires_confirmation
