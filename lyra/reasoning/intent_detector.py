"""
Intent Detection System
Classifies user input into actionable intents with confidence scoring
"""

import re
from typing import Dict, List, Tuple, Optional
from lyra.reasoning.command_schema import Command, RiskLevel
from lyra.core.logger import get_logger
from lyra.core.exceptions import IntentDetectionError


logger = get_logger(__name__)


class IntentPattern:
    """Represents an intent with matching patterns and metadata"""
    
    def __init__(self, intent_name: str, patterns: List[str], risk_level: RiskLevel,
                 entity_extractors: Optional[Dict[str, str]] = None):
        self.intent_name = intent_name
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.risk_level = risk_level
        self.entity_extractors = entity_extractors or {}


class IntentDetector:
    """
    Intent classification and entity extraction
    Extensible pattern-based system with confidence scoring
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.intent_registry: List[IntentPattern] = []
        self._register_default_intents()
    
    def _register_default_intents(self):
        """Register default intent patterns"""
        
        # System information intents (SAFE)
        self.register_intent(
            "get_time",
            [r"what time is it", r"current time", r"tell me the time"],
            RiskLevel.SAFE
        )
        
        self.register_intent(
            "get_date",
            [r"what.*date", r"today.*date", r"current date"],
            RiskLevel.SAFE
        )
        
        # File operations (MEDIUM to HIGH)
        self.register_intent(
            "create_file",
            [r"create.*file", r"make.*file", r"new file"],
            RiskLevel.MEDIUM,
            {"filename": r"(?:named?|called)\s+([^\s]+)"}
        )
        
        self.register_intent(
            "delete_file",
            [r"delete.*file", r"remove.*file"],
            RiskLevel.HIGH,
            {"filename": r"(?:file|named?|called)\s+([^\s]+)"}
        )
        
        self.register_intent(
            "open_file",
            [r"open.*file", r"show.*file"],
            RiskLevel.LOW,
            {"filename": r"(?:file|named?|called)\s+([^\s]+)"}
        )
        
        # Application control (LOW)
        self.register_intent(
            "open_application",
            [r"open\s+(\w+)", r"launch\s+(\w+)", r"start\s+(\w+)"],
            RiskLevel.LOW,
            {"app_name": r"(?:open|launch|start)\s+(\w+)"}
        )
        
        self.register_intent(
            "close_application",
            [r"close\s+(\w+)", r"quit\s+(\w+)", r"exit\s+(\w+)"],
            RiskLevel.MEDIUM,
            {"app_name": r"(?:close|quit|exit)\s+(\w+)"}
        )
        
        # System control (CRITICAL)
        self.register_intent(
            "shutdown_system",
            [r"shutdown", r"turn off.*computer", r"power off"],
            RiskLevel.CRITICAL
        )
        
        self.register_intent(
            "restart_system",
            [r"restart", r"reboot"],
            RiskLevel.CRITICAL
        )
        
        # Search and information (SAFE)
        self.register_intent(
            "search_files",
            [r"search.*for", r"find.*file", r"locate.*file"],
            RiskLevel.SAFE,
            {"query": r"(?:for|file)\s+(.+)"}
        )
        
        # General conversation (SAFE)
        self.register_intent(
            "greeting",
            [r"^hi$", r"^hello$", r"^hey$", r"good morning", r"good evening"],
            RiskLevel.SAFE
        )
        
        self.register_intent(
            "help",
            [r"help", r"what can you do", r"capabilities"],
            RiskLevel.SAFE
        )
    
    def register_intent(self, intent_name: str, patterns: List[str], 
                       risk_level: RiskLevel, entity_extractors: Optional[Dict[str, str]] = None):
        """
        Register a new intent pattern
        
        Args:
            intent_name: Name of the intent
            patterns: List of regex patterns to match
            risk_level: Risk level for this intent
            entity_extractors: Optional dict of entity_name -> regex pattern
        """
        intent_pattern = IntentPattern(intent_name, patterns, risk_level, entity_extractors)
        self.intent_registry.append(intent_pattern)
        self.logger.debug(f"Registered intent: {intent_name}")
    
    def detect_intent(self, user_input: str) -> Command:
        """
        Detect intent from user input and create Command object
        
        Args:
            user_input: Raw user input text
        
        Returns:
            Command object with detected intent and entities
        
        Raises:
            IntentDetectionError: If no intent can be detected
        """
        user_input = user_input.strip()
        
        if not user_input:
            raise IntentDetectionError("Empty input provided")
        
        # Try to match against registered intents
        best_match = None
        best_confidence = 0.0
        
        for intent_pattern in self.intent_registry:
            for pattern in intent_pattern.patterns:
                match = pattern.search(user_input)
                if match:
                    # Calculate confidence based on match quality
                    match_length = len(match.group(0))
                    input_length = len(user_input)
                    confidence = match_length / input_length
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (intent_pattern, match)
        
        if not best_match:
            # No intent matched
            command = Command(
                raw_input=user_input,
                intent="unknown",
                confidence=0.0,
                risk_level=RiskLevel.SAFE
            )
            self.logger.warning(f"No intent detected for: {user_input}")
            return command
        
        intent_pattern, match = best_match
        
        # Extract entities
        entities = self._extract_entities(user_input, intent_pattern.entity_extractors)
        
        # Create command
        command = Command(
            raw_input=user_input,
            intent=intent_pattern.intent_name,
            entities=entities,
            confidence=best_confidence,
            risk_level=intent_pattern.risk_level,
            requires_confirmation=intent_pattern.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        
        self.logger.info(f"Detected intent: {command.intent} (confidence: {command.confidence:.2%})")
        return command
    
    def _extract_entities(self, text: str, extractors: Dict[str, str]) -> Dict[str, str]:
        """
        Extract entities from text using regex patterns
        
        Args:
            text: Input text
            extractors: Dict of entity_name -> regex pattern
        
        Returns:
            Dict of extracted entities
        """
        entities = {}
        
        for entity_name, pattern in extractors.items():
            regex = re.compile(pattern, re.IGNORECASE)
            match = regex.search(text)
            if match:
                entities[entity_name] = match.group(1) if match.groups() else match.group(0)
        
        return entities
    
    def get_registered_intents(self) -> List[str]:
        """Get list of all registered intent names"""
        return [intent.intent_name for intent in self.intent_registry]
