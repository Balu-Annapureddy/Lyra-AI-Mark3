# -*- coding: utf-8 -*-
"""
Semantic Engine orchestrator
Coordinations: Model -> Validation -> Confidence
Entry point for the semantic layer
"""

from typing import Dict, Any, Optional, List
from lyra.core.logger import get_logger
from lyra.semantic.local_model import LocalSemanticModel
from lyra.semantic.schema_validator import SchemaValidator
from lyra.semantic.confidence_engine import ConfidenceEngine

class SemanticEngine:
    """
    Main entry point for semantic intent parsing.
    Orchestrates the local model, validation, and scoring.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.model = LocalSemanticModel()
        self.validator = SchemaValidator()
        self.confidence_engine = ConfidenceEngine()
        self.confidence_threshold = 0.6
        self.logger.info("Semantic Intent Layer initialized")

    def parse_semantic_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Convert natural language to structured intent(s).
        Supports splitting commands like "do A and do B".
        """
        segments = self._split_command(user_input)
        
        parsed_intents = []
        requires_clarification = False
        min_confidence = 1.0
        
        for segment in segments:
            intent = self._process_single_intent(segment)
            parsed_intents.append(intent)
            
            if intent.get("requires_clarification"):
                requires_clarification = True
            
            conf = intent.get("confidence", 0.0)
            if conf < min_confidence:
                min_confidence = conf
                
        # If no valid intents (empty input?), fallback
        if not parsed_intents:
            return self._create_fallback_response()

        return {
            "intents": parsed_intents,
            "confidence": min_confidence,
            "requires_clarification": requires_clarification
        }

    def _split_command(self, text: str) -> List[str]:
        """Split command by 'and then', 'and', 'then'."""
        # Simple split logic - prioritized order
        text = text.lower().strip()
        
        # Limit split to 1 (max 2 parts)
        if " and then " in text:
            return text.split(" and then ", 1)
        if " and " in text:
            return text.split(" and ", 1)
        if " then " in text:
            return text.split(" then ", 1)
            
        return [text]

    def _process_single_intent(self, user_input: str) -> Dict[str, Any]:
        """Process a single segment."""
        try:
            # 1. Generate Raw Output
            raw_intent = self.model.generate_structured_intent(user_input)
            
            # 2. Schema Validation
            validation = self.validator.validate(raw_intent)
            if not validation.valid:
                self.logger.warning(f"Semantic validation failed: {validation.error}")
                return self._create_single_fallback()
                
            validated_intent = validation.data
            
            # 3. Confidence Scoring
            adjusted_confidence = self.confidence_engine.calculate_score(validated_intent)
            validated_intent["confidence"] = adjusted_confidence
            
            # 4. Clarification Check
            if adjusted_confidence < self.confidence_threshold:
                validated_intent["requires_clarification"] = True
                
            return validated_intent
            
        except Exception as e:
            self.logger.error(f"Semantic engine error: {e}")
            return self._create_single_fallback()

    def _create_single_fallback(self) -> Dict[str, Any]:
        """Fallback for a single intent."""
        return {
            "intent": "unknown",
            "parameters": {},
            "confidence": 0.0,
            "requires_clarification": True
        }

    def _create_fallback_response(self) -> Dict[str, Any]:
        """Generate safe fallback response on error (legacy structure wrapper)."""
        single = self._create_single_fallback()
        return {
            "intents": [single],
            "confidence": 0.0,
            "requires_clarification": True
        }
