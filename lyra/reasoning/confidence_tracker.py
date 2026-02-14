"""
Confidence Tracker - Phase 3A
Explicit confidence tracking for all operations
Tracks intent, execution, and risk confidence
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from lyra.core.logger import get_logger


@dataclass
class ConfidenceReport:
    """Comprehensive confidence report"""
    intent_confidence: float  # 0.0-1.0: How sure are we about user intent?
    execution_confidence: float  # 0.0-1.0: How likely is execution to succeed?
    risk_confidence: float  # 0.0-1.0: How accurate is our risk assessment?
    overall_confidence: float  # 0.0-1.0: Weighted average
    confidence_factors: Dict[str, float]  # Breakdown of contributing factors
    timestamp: str
    
    def should_proceed(self, threshold: float = 0.7) -> bool:
        """Check if overall confidence meets threshold"""
        return self.overall_confidence >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ConfidenceTracker:
    """
    Tracks confidence for all operations
    Provides explicit uncertainty quantification
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Confidence weights
        self.intent_weight = 0.4
        self.execution_weight = 0.35
        self.risk_weight = 0.25
    
    def calculate_intent_confidence(self, 
                                    pattern_match_score: float = 0.0,
                                    nlp_confidence: float = 0.0,
                                    context_relevance: float = 0.0,
                                    historical_similarity: float = 0.0) -> float:
        """
        Calculate intent confidence from multiple factors
        
        Args:
            pattern_match_score: How well input matches known patterns (0-1)
            nlp_confidence: NLP model confidence (0-1, or 0 if no NLP)
            context_relevance: How relevant is current context (0-1)
            historical_similarity: Similarity to past successful intents (0-1)
        
        Returns:
            Intent confidence (0-1)
        """
        # Normalize inputs (default to 0.5 if not provided)
        pattern = pattern_match_score if pattern_match_score > 0 else 0.5
        nlp = nlp_confidence if nlp_confidence > 0 else 0.5
        context = context_relevance if context_relevance > 0 else 0.5
        history = historical_similarity if historical_similarity > 0 else 0.5
        
        # Weighted average
        confidence = (
            0.3 * pattern +
            0.3 * nlp +
            0.2 * context +
            0.2 * history
        )
        
        return min(1.0, max(0.0, confidence))
    
    def calculate_execution_confidence(self,
                                       historical_success_rate: float = 0.0,
                                       resource_availability: float = 1.0,
                                       dependency_status: float = 1.0,
                                       similar_command_success: float = 0.0) -> float:
        """
        Calculate execution confidence
        
        Args:
            historical_success_rate: Success rate for this command type (0-1)
            resource_availability: Are required resources available? (0-1)
            dependency_status: Are dependencies satisfied? (0-1)
            similar_command_success: Success rate of similar commands (0-1)
        
        Returns:
            Execution confidence (0-1)
        """
        # Normalize inputs
        history = historical_success_rate if historical_success_rate > 0 else 0.7  # Optimistic default
        resources = resource_availability
        deps = dependency_status
        similar = similar_command_success if similar_command_success > 0 else 0.7
        
        # Weighted average
        confidence = (
            0.4 * history +
            0.3 * resources +
            0.2 * deps +
            0.1 * similar
        )
        
        return min(1.0, max(0.0, confidence))
    
    def calculate_risk_confidence(self,
                                  risk_assessment_certainty: float = 0.0,
                                  historical_risk_accuracy: float = 0.0,
                                  context_completeness: float = 0.0) -> float:
        """
        Calculate risk confidence (how sure are we about the risk assessment?)
        
        Args:
            risk_assessment_certainty: Certainty of risk scorer (0-1)
            historical_risk_accuracy: How accurate have past assessments been? (0-1)
            context_completeness: Do we have complete context? (0-1)
        
        Returns:
            Risk confidence (0-1)
        """
        # Normalize inputs
        certainty = risk_assessment_certainty if risk_assessment_certainty > 0 else 0.6
        accuracy = historical_risk_accuracy if historical_risk_accuracy > 0 else 0.7
        context = context_completeness if context_completeness > 0 else 0.5
        
        # Weighted average
        confidence = (
            0.5 * certainty +
            0.3 * accuracy +
            0.2 * context
        )
        
        return min(1.0, max(0.0, confidence))
    
    def create_report(self,
                     intent_factors: Dict[str, float] = None,
                     execution_factors: Dict[str, float] = None,
                     risk_factors: Dict[str, float] = None) -> ConfidenceReport:
        """
        Create comprehensive confidence report
        
        Args:
            intent_factors: Factors for intent confidence
            execution_factors: Factors for execution confidence
            risk_factors: Factors for risk confidence
        
        Returns:
            ConfidenceReport
        """
        intent_factors = intent_factors or {}
        execution_factors = execution_factors or {}
        risk_factors = risk_factors or {}
        
        # Calculate individual confidences
        intent_conf = self.calculate_intent_confidence(**intent_factors)
        exec_conf = self.calculate_execution_confidence(**execution_factors)
        risk_conf = self.calculate_risk_confidence(**risk_factors)
        
        # Calculate overall confidence (weighted average)
        overall = (
            self.intent_weight * intent_conf +
            self.execution_weight * exec_conf +
            self.risk_weight * risk_conf
        )
        
        # Build factor breakdown
        all_factors = {
            "intent": intent_conf,
            "execution": exec_conf,
            "risk": risk_conf,
            **{f"intent_{k}": v for k, v in intent_factors.items()},
            **{f"execution_{k}": v for k, v in execution_factors.items()},
            **{f"risk_{k}": v for k, v in risk_factors.items()}
        }
        
        return ConfidenceReport(
            intent_confidence=intent_conf,
            execution_confidence=exec_conf,
            risk_confidence=risk_conf,
            overall_confidence=overall,
            confidence_factors=all_factors,
            timestamp=datetime.now().isoformat()
        )
    
    def get_confidence_message(self, report: ConfidenceReport) -> str:
        """
        Generate human-readable confidence message
        
        Args:
            report: Confidence report
        
        Returns:
            Message string
        """
        overall = report.overall_confidence
        
        if overall >= 0.9:
            return "High confidence. Proceeding."
        elif overall >= 0.7:
            return "Moderate confidence. Proceeding with caution."
        elif overall >= 0.5:
            return "Low confidence. Please verify."
        else:
            return "Very low confidence. Clarification needed."
    
    def identify_weak_factors(self, report: ConfidenceReport, 
                             threshold: float = 0.6) -> List[str]:
        """
        Identify factors contributing to low confidence
        
        Args:
            report: Confidence report
            threshold: Threshold for "weak" factors
        
        Returns:
            List of weak factor names
        """
        weak = []
        
        if report.intent_confidence < threshold:
            weak.append("intent")
        if report.execution_confidence < threshold:
            weak.append("execution")
        if report.risk_confidence < threshold:
            weak.append("risk")
        
        return weak
