# -*- coding: utf-8 -*-
"""
Confidence Engine
Heuristic scoring for semantic intents
Prevents blind trust in model outputs
"""

from typing import Dict, Any

class ConfidenceEngine:
    """
    Computes confidence scores based on heuristic analysis
    Does not rely solely on the model's self-reported confidence
    """
    
    def calculate_score(self, intent_data: Dict[str, Any]) -> float:
        """
        Compute a realistic confidence score (0.0 - 1.0)
        
        Args:
            intent_data: Validated intent dictionary
            
        Returns:
            Float confidence score
        """
        base_score = intent_data.get("confidence", 0.5)
        
        # 1. Cap maximum confidence (Models are overconfident)
        # Even a perfect match shouldn't be 1.0 unless verified by execution (which we don't do here)
        final_score = min(base_score, 0.95)
        
        intent = intent_data["intent"]
        params = intent_data["parameters"]
        
        # 2. Penalty for generic/unknown intents
        if intent == "unknown" or intent == "generic_interaction":
            final_score = min(final_score, 0.4)
            
        # 3. Parameter completeness check (Heuristic)
        # If intent implies parameters but none exist -> penalize
        if intent in ["write_file", "open_url", "launch_app"]:
            if not params:
                final_score -= 0.3
            elif len(params) == 1 and "" in params.values():
                final_score -= 0.2
        
        # 4. Ambiguity penalty (Short inputs are often ambiguous)
        # This would ideally check the *input* length, 
        # but here we only see the output. We assume the model 
        # lowered confidence for short inputs, but we enforce a floor.
        
        return max(0.0, final_score)
