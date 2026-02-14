"""
Voice Personality Layer - Phase 3C
Consistent, professional voice personality for Lyra
Tone filtering, emoji stripping, SSML support
"""

import re
from typing import Dict, Any, Optional
from lyra.core.logger import get_logger


# Lyra's personality profile
LYRA_PERSONALITY = {
    "tone": "calm, analytical, supportive, direct",
    "pacing": "moderate with strategic pauses",
    "formality": "professional but approachable",
    "verbosity": "concise, minimal fluff",
    "preferred_voice": "female",
    "speech_rate": 175,  # Words per minute
    "pause_before_important": 0.5  # Seconds
}


class VoicePersonality:
    """
    Enforces consistent voice personality for Lyra
    Lightweight implementation focused on tone and clarity
    """
    
    def __init__(self, use_ssml: bool = False):
        self.logger = get_logger(__name__)
        self.use_ssml = use_ssml
        self.personality = LYRA_PERSONALITY
    
    def format_response(self, text: str, response_type: str = "general") -> str:
        """
        Format response according to personality
        
        Args:
            text: Raw response text
            response_type: Type of response (general, warning, error, suggestion, confirmation)
        
        Returns:
            Formatted text
        """
        # Strip emojis
        text = self._strip_emojis(text)
        
        # Clean excessive punctuation
        text = self._clean_punctuation(text)
        
        # Apply tone filtering
        text = self._apply_tone_filter(text, response_type)
        
        # Add SSML pauses if enabled
        if self.use_ssml:
            text = self._add_ssml_pauses(text, response_type)
        
        return text
    
    def _strip_emojis(self, text: str) -> str:
        """Remove all emojis from text"""
        # Unicode emoji pattern
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub('', text)
    
    def _clean_punctuation(self, text: str) -> str:
        """Clean excessive punctuation"""
        # Multiple exclamation marks -> single period
        text = re.sub(r'!+', '.', text)
        
        # Multiple question marks -> single question mark
        text = re.sub(r'\?{2,}', '?', text)
        
        # Multiple periods -> single period
        text = re.sub(r'\.{2,}', '.', text)
        
        # Remove excessive spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _apply_tone_filter(self, text: str, response_type: str) -> str:
        """
        Apply tone filtering based on response type
        Replaces overly casual or excited language
        """
        # Casual -> Professional replacements
        casual_to_professional = {
            r'\bawesome\b': 'excellent',
            r'\bgreat\b': 'good',
            r'\bcool\b': 'understood',
            r'\byeah\b': 'yes',
            r'\bnope\b': 'no',
            r'\bokay\b': 'understood',
            r'\bOK\b': 'Understood',
            r'\bsure thing\b': 'understood',
            r'\bno worries\b': 'understood',
            r'\bno problem\b': 'understood'
        }
        
        for pattern, replacement in casual_to_professional.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Remove filler words
        fillers = [r'\blike\b', r'\bkinda\b', r'\bsorta\b', r'\bbasically\b', r'\bactually\b']
        for filler in fillers:
            text = re.sub(filler, '', text, flags=re.IGNORECASE)
        
        # Clean up extra spaces after removals
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _add_ssml_pauses(self, text: str, response_type: str) -> str:
        """
        Add SSML pause tags for important statements
        Only if SSML is enabled
        """
        if response_type == "warning":
            # Add pause before warning
            text = f'<break time="{self.personality["pause_before_important"]}s"/>{text}'
        
        elif response_type == "error":
            # Add pause before error
            text = f'<break time="{self.personality["pause_before_important"]}s"/>{text}'
        
        return text
    
    # Response Templates
    
    def format_confirmation(self, action: str) -> str:
        """Format confirmation message"""
        text = f"Understood. {action}."
        return self.format_response(text, "confirmation")
    
    def format_suggestion(self, suggestion: str, confidence: float = 0.0) -> str:
        """Format suggestion message"""
        if confidence > 0.8:
            text = f"Based on your pattern, I suggest {suggestion}."
        elif confidence > 0.6:
            text = f"You may want to consider {suggestion}."
        else:
            text = f"Suggestion: {suggestion}."
        
        return self.format_response(text, "suggestion")
    
    def format_warning(self, risk_description: str) -> str:
        """Format warning message"""
        text = f"Caution: {risk_description}. Proceed?"
        return self.format_response(text, "warning")
    
    def format_error(self, error: str, recovery_suggestion: Optional[str] = None) -> str:
        """Format error message"""
        if recovery_suggestion:
            text = f"Error encountered: {error}. {recovery_suggestion}."
        else:
            text = f"Error encountered: {error}."
        
        return self.format_response(text, "error")
    
    def format_low_confidence(self, aspect: str) -> str:
        """Format low confidence message"""
        text = f"I'm uncertain about {aspect}. Please clarify."
        return self.format_response(text, "general")
    
    def format_rejection_acknowledgment(self, suggestion_type: str) -> str:
        """Format rejection acknowledgment"""
        text = f"Understood. I'll adjust future suggestions."
        return self.format_response(text, "confirmation")
    
    def format_adaptive_notification(self, change_description: str) -> str:
        """Format adaptive change notification"""
        text = f"Note: {change_description}."
        return self.format_response(text, "general")
    
    def get_voice_settings(self) -> Dict[str, Any]:
        """
        Get TTS voice settings
        
        Returns:
            Voice configuration dictionary
        """
        return {
            "gender": "female",
            "rate": self.personality["speech_rate"],
            "volume": 0.9,
            "pitch": 1.0
        }


# Convenience functions for common use cases

def format_suggestion_response(suggestion_text: str, confidence: float = 0.0,
                               use_ssml: bool = False) -> str:
    """Format a suggestion with personality"""
    vp = VoicePersonality(use_ssml=use_ssml)
    return vp.format_suggestion(suggestion_text, confidence)


def format_risk_warning(risk_description: str, use_ssml: bool = False) -> str:
    """Format a risk warning with personality"""
    vp = VoicePersonality(use_ssml=use_ssml)
    return vp.format_warning(risk_description)


def format_confidence_message(aspect: str, confidence: float,
                              use_ssml: bool = False) -> str:
    """Format a confidence message with personality"""
    vp = VoicePersonality(use_ssml=use_ssml)
    
    if confidence >= 0.9:
        return vp.format_response("High confidence. Proceeding.", "general")
    elif confidence >= 0.7:
        return vp.format_response("Moderate confidence. Proceeding with caution.", "general")
    elif confidence >= 0.5:
        return vp.format_response("Low confidence. Please verify.", "general")
    else:
        return vp.format_low_confidence(aspect)
