# -*- coding: utf-8 -*-
"""
Semantic Schema Validator
Enforces strict structure on intent outputs
Reject malformed data immediately
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of schema validation"""
    valid: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SchemaValidator:
    """
    Strict validator for semantic intent outputs
    Ensures downstream components always get clean data
    """
    
    REQUIRED_KEYS = {"intent", "parameters", "confidence", "requires_clarification"}
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a raw intent dictionary against strict schema
        
        Args:
            data: Raw dictionary from local model
            
        Returns:
            ValidationResult with cleaned data or error
        """
        if not isinstance(data, dict):
            return ValidationResult(False, error="Output must be a dictionary")
        
        # 1. Check for missing keys
        missing = self.REQUIRED_KEYS - data.keys()
        if missing:
            return ValidationResult(False, error=f"Missing required keys: {missing}")
            
        # 2. Check for extra keys (Strictness)
        extra = data.keys() - self.REQUIRED_KEYS
        if extra:
            return ValidationResult(False, error=f"Unknown keys found: {extra}")
            
        # 3. Type validation
        if not isinstance(data["intent"], str):
            return ValidationResult(False, error="Field 'intent' must be a string")
            
        if not isinstance(data["parameters"], dict):
            return ValidationResult(False, error="Field 'parameters' must be a dictionary")
            
        if not isinstance(data["confidence"], (int, float)):
             return ValidationResult(False, error="Field 'confidence' must be specific float")
             
        if not isinstance(data["requires_clarification"], bool):
            return ValidationResult(False, error="Field 'requires_clarification' must be a boolean")
            
        # 4. Value range validation
        confidence = float(data["confidence"])
        if not (0.0 <= confidence <= 1.0):
            return ValidationResult(False, error="Confidence must be between 0.0 and 1.0")
            
        # 5. Semantic validity (basic)
        if not data["intent"].strip():
            return ValidationResult(False, error="Intent string cannot be empty")

        # Return validated data (cast types if needed)
        cleaned_data = {
            "intent": data["intent"].strip(),
            "parameters": data["parameters"],
            "confidence": confidence,
            "requires_clarification": data["requires_clarification"]
        }
        
        return ValidationResult(True, data=cleaned_data)
