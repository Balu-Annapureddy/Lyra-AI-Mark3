# -*- coding: utf-8 -*-
"""
lyra/memory/context_compressor.py
Phase F9: Contextual Memory Compression (Subsystem M)
"""

import re
from typing import List, Dict, Any, Optional
from lyra.core.logger import get_logger

logger = get_logger(__name__)

class ContextCompressor:
    """
    Compresses long conversation history while preserving semantic continuity.
    Prioritizes safety records and recent context.
    """

    # Config defaults (can be overridden by pipeline if needed)
    COMPRESSION_TRIGGER_TURNS = 20
    PRESERVE_RECENT_TURNS = 6

    # Safety keys that trigger automatic preservation
    SAFETY_KEYS = {
        "risk_level": "HIGH",
        "confirmation_required": True,
        "safety_violation": True,
        "execution_log": True
    }

    @staticmethod
    def should_compress(turn_count: int, trigger_threshold: int = 20) -> bool:
        """Check if compression is needed."""
        return turn_count > trigger_threshold

    @staticmethod
    def compress(
        history: List[Dict[str, Any]], 
        model_advisor: Any = None,
        preserve_count: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Compress older turns in history while preserving safety records and recent turns.
        """
        if len(history) <= preserve_count:
            return history

        # 1. Split history into older and recent segments
        if preserve_count > 0:
            recent_segment = history[-preserve_count:]
            older_segment = history[:-preserve_count]
        else:
            recent_segment = []
            older_segment = history

        # 2. Extract safety-critical records from the older segment
        to_compress = []
        safety_records = []

        for entry in older_segment:
            is_safety = False
            for key, val in ContextCompressor.SAFETY_KEYS.items():
                if entry.get(key) == val:
                    is_safety = True
                    break
            
            if is_safety:
                safety_records.append(entry)
            else:
                to_compress.append(entry)

        if not to_compress:
            # Nothing to compress (all older turns were safety records)
            return history

        # 3. Compress the remaining older turns
        summary_content = ""
        # If we have an advisor and it's initialized (or we can initialize it)
        if model_advisor:
            summary_content = ContextCompressor._llm_summarize(to_compress, model_advisor)
        else:
            summary_content = ContextCompressor._rule_summarize(to_compress)

        # 4. Construct new history
        compressed_entry = {
            "role": "system",
            "content": f"[COMPRESSED HISTORY SUMMARY]\n{summary_content}",
            "is_compressed_summary": True
        }

        # New history = Summary + Preserved Safety Records + Recent Turns
        return [compressed_entry] + safety_records + recent_segment

    @staticmethod
    def _llm_summarize(entries: List[Dict[str, Any]], model_advisor: Any) -> str:
        """Use model advisor to generate a concise summary."""
        logger.info("Using LLM for context compression...")
        
        history_text = "\n".join([
            f"{e.get('role', 'unknown')}: {e.get('content', '') or e.get('raw_input', '')}" 
            for e in entries
        ])
        
        prompt = (
            "Summarize the following conversation focusing only on:\n"
            "- User goals\n"
            "- Decisions made\n"
            "- Files referenced\n"
            "- Pending actions\n"
            "Return concise structured summary.\n\n"
            "Conversation:\n"
            f"{history_text}"
        )
        
        try:
            # We use a special mode for compression analysis if available
            # or just a direct generation.
            # For Gemini, we can just call generate_content or a wrapper.
            # In our new advisor, we have an 'analyze' method but for summary we want text.
            # Let's add a 'summarize' method to LLMEscalationAdvisor or use ._gen_model
            if hasattr(model_advisor, 'generate_summary'):
                return model_advisor.generate_summary(prompt)
            
            # Simple fallback: if it's the new advisor, we use its gen_model if initialized
            if hasattr(model_advisor, '_gen_model') and model_advisor._initialize_gemini():
                resp = model_advisor._gen_model.generate_content(prompt)
                return resp.text.strip()
            
            return ContextCompressor._rule_summarize(entries)
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            return ContextCompressor._rule_summarize(entries)

    @staticmethod
    def _rule_summarize(entries: List[Dict[str, Any]]) -> str:
        """Lightweight rule-based summarization (fallback)."""
        logger.info("Using rule-based context compression...")
        
        intents = []
        files = []
        actions = []
        
        for e in entries:
            # Extract intent
            if "intent" in e:
                intents.append(e["intent"])
            
            # Extract files (simple regex)
            content = str(e.get("content", "")) + str(e.get("raw_input", ""))
            found_files = re.findall(r'[a-zA-Z0-9_\-\.]+\.[a-z]{2,4}', content)
            files.extend(found_files)
            
            # Extract success indicators
            if e.get("success"):
                actions.append(f"Completed {e.get('intent', 'task')}")

        # Unique sets
        intents = sorted(list(set(intents)))
        files = sorted(list(set(files)))
        actions = sorted(list(set(actions)))

        summary_parts = []
        if intents:
            summary_parts.append(f"Intents: {', '.join(intents)}")
        if files:
            summary_parts.append(f"Files: {', '.join(files)}")
        if actions:
            summary_parts.append(f"Recent Actions: {' | '.join(actions)}")
            
        if not summary_parts:
            return "Multiple earlier turns compressed. No specific goals or files identified."
            
        return "\n".join(summary_parts)
