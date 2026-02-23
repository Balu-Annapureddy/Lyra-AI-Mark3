# -*- coding: utf-8 -*-
"""
lyra/context/language_mirror.py
Phase F7: Multilingual Support Layer

Lightweight language detection and response mirroring.
Prioritizes English (en), Telugu (te), and Hindi (hi).
Secondary support for Spanish (es), French (fr), German (de).
"""

import json
from typing import Dict, Any, Optional, List
from langdetect import detect, detect_langs, DetectorFactory
from lyra.core.logger import get_logger

# Ensure consistent results from langdetect
DetectorFactory.seed = 0

logger = get_logger(__name__)

class LanguageMirror:
    """
    Handles language detection and response mirroring.
    Uses dictionary-based mirroring for system messages to avoid heavy translation models.
    """

    # Primary Languages
    PRIMARY_LANGS = {"en", "te", "hi"}
    # Secondary Languages
    SECONDARY_LANGS = {"es", "fr", "de"}

    # System Phrase Dictionary
    # Keys are English canonical phrases. Values are dicts mapping lang code to translation.
    SYSTEM_PHRASES = {
        "Which file would you like me to delete?": {
            "te": "మీరు ఏ ఫైల్‌ను తొలగించాలనుకుంటున్నారు?",
            "hi": "आप कौन सी फ़ाइल हटाना चाहते हैं?",
            "es": "¿Qué archivo le gustaría que elimine?",
            "fr": "Quel fichier voudriez-vous que je supprime ?",
            "de": "Welche Datei möchten Sie löschen?"
        },
        "Are you sure?": {
            "te": "మీరు ఖచ్చితంగా ఉన్నారా?",
            "hi": "क्या आप सुनिश्चित हैं?",
            "es": "¿Está seguro?",
            "fr": "Êtes-vous sûr ?",
            "de": "Sind Sie sicher?"
        },
        "I couldn't understand that.": {
            "te": "నాకు అది అర్థం కాలేదు.",
            "hi": "मैं उसे समझ नहीं सका।",
            "es": "No pude entender eso.",
            "fr": "Je n'ai pas pu comprendre cela.",
            "de": "Das konnte ich nicht verstehen."
        },
        "That sounds frustrating.": {
            "te": "అది నిరాశపరిచేలా ఉంది.",
            "hi": "यह निराशाजनक लगता है।",
            "es": "Eso suena frustrante.",
            "fr": "Cela semble frustrant.",
            "de": "Das klingt frustrierend."
        },
        "Operation completed successfully.": {
            "te": "ఆపరేషన్ విజయవంతంగా పూర్తయింది.",
            "hi": "ऑपरेशन सफलतापूर्वक पूरा हुआ।",
            "es": "Operación completada con éxito.",
            "fr": "Opération terminée avec succès.",
            "de": "Vorgang erfolgreich abgeschlossen."
        },
        "Please confirm.": {
            "te": "దయచేసి ధృవీకరించండి.",
            "hi": "कृपया पुष्टि करें।",
            "es": "Por favor confirme.",
            "fr": "Veuillez confirmer.",
            "de": "Bitte bestätigen."
        },
        "Unknown command.": {
            "te": "తెలియని ఆదేశం.",
            "hi": "अज्ञात आदेश।",
            "es": "Comando desconocido.",
            "fr": "Commande inconnue.",
            "de": "Unbekannter Befehl."
        },
        "Could not understand command": {
            "te": "ఆదేశాన్ని అర్థం చేసుకోలేకపోయాను",
            "hi": "आदेश समझ में नहीं आया",
            "es": "No se pudo entender el comando",
            "fr": "Impossible de comprendre la commande",
            "de": "Befehl konnte nicht verstanden werden"
        },
        "I understood you want to unknown, but I need more details. Can you be more specific?": {
            "te": "మీరు అమాయకమైనది చేయాలనుకుంటున్నారని నేను అర్థం చేసుకున్నాను, కానీ నాకు మరిన్ని వివరాలు కావాలి. మీరు మరింత నిర్దిష్టంగా చెప్పగలరా?",
            "hi": "मुझे समझ आया कि आप अज्ञात करना चाहते हैं, लेकिन मुझे और विवरण चाहिए। क्या आप अधिक विशिष्ट हो सकते हैं?",
            "es": "Entendí que quieres desconocido, pero necesito más detalles. ¿Puedes ser más específico?",
            "fr": "J'ai compris que vous vouliez inconnu, mais j'ai besoin de plus de détails. Pouvez-vous être plus précis ?",
            "de": "Ich habe verstanden, dass Sie unbekannt möchten, aber ich benötige weitere Details. Können Sie genauer sein?"
        }
    }

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detects the language of the given text.
        Returns ISO code (e.g., 'en', 'te', 'hi').
        """
        if not text or len(text.strip()) < 3:
            return "en" # Default to English for very short/empty input
            
        try:
            # Get top predictions
            langs = detect_langs(text)
            # Find the most likely support language
            for l in langs:
                if l.lang in LanguageMirror.PRIMARY_LANGS or l.lang in LanguageMirror.SECONDARY_LANGS:
                    # Confidence threshold check
                    if l.prob > 0.5:
                        return l.lang
            
            # Fallback to top if no primary/secondary match specifically
            primary_code = langs[0].lang if langs else "en"
            return primary_code
        except Exception as e:
            logger.debug(f"Language detection failed for '{text}': {e}")
            return "en"

    @staticmethod
    def mirror_response(text: str, target_language: str) -> str:
        """
        Mirrors system phrases into the target language using the dictionary.
        Returns the original text if no mapping is found.
        """
        if target_language == "en" or not text:
            return text

        # Check for direct matches in the dictionary
        # We also check if the text contains a standard phrase as a substring for flexible matching
        for phrase, translations in LanguageMirror.SYSTEM_PHRASES.items():
            if phrase in text and target_language in translations:
                # Replace the English phrase with the translation
                return text.replace(phrase, translations[target_language])
                
        return text

    @staticmethod
    def store_preference(language: str, session_memory: Any):
        """
        Stores language preference in session memory if threshold is reached.
        This is typically called by session_memory.py itself.
        """
        if hasattr(session_memory, 'update_language_preference'):
            session_memory.update_language_preference(language)
