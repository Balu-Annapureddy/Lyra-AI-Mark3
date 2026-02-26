# -*- coding: utf-8 -*-
"""
lyra/memory/memory_context_builder.py
Phase 2: Context Injection Layer v1.1
Selects and summarizes relevant memory for ReasoningRequests.
"""

from typing import List, Dict, Any, Optional
from lyra.memory.memory_manager import MemoryManager
from lyra.memory.memory_schema import MemoryEntry, MemoryType
from lyra.core.logger import get_logger

class MemoryContextBuilder:
    """
    Responsibilities:
    - Select relevant STM + LTM entries.
    - Summarize into bounded context (max 500 tokens / 25% window).
    - Enforce No Raw Logs policy.
    """
    
    MAX_INJECTION_TOKENS = 500
    CONTEXT_WINDOW_PERCENT = 0.25

    def __init__(self, memory_manager: MemoryManager):
        self.logger = get_logger(__name__)
        self.memory_manager = memory_manager

    def build_context(self, user_input: str, 
                     context_window_size: int = 2048,
                     max_tokens_limit: Optional[int] = None,
                     trace_id: str = "") -> str:
        """
        Builds a summarized string of relevant memories with dynamic budgeting.
        """
        # 1. Fetch relevant memories
        preferences = self.memory_manager.query_memory(
            {"memory_type": MemoryType.USER_PREFERENCE}, 
            trace_id=trace_id
        )
        procedures = self.memory_manager.query_memory(
            {"memory_type": MemoryType.LEARNED_PROCEDURE},
            trace_id=trace_id
        )
        recent_history = self.memory_manager.query_memory(
            {"memory_type": MemoryType.TASK_HISTORY},
            trace_id=trace_id
        )[-3:]
        
        all_relevant = preferences + procedures + recent_history
        
        if not all_relevant:
            return ""

        # 2. Dynamic Budgeting (Phase 2.2)
        # Budget is min(500 tokens, 25% of window, and optional provider limit)
        token_budget = min(self.MAX_INJECTION_TOKENS, int(self.CONTEXT_WINDOW_PERCENT * context_window_size))
        if max_tokens_limit:
            token_budget = min(token_budget, max_tokens_limit)
        
        # Approximate char limit (4 chars per token)
        char_limit = token_budget * 4
        
        context_parts = ["[MEMORY CONTEXT]"]
        current_chars = 0
        
        for entry in all_relevant:
            # Enforce "No Raw Logs" - summarize content
            summary = self._summarize_entry(entry)
            entry_str = f"- {entry.memory_type.value}: {summary}\n"
            
            if current_chars + len(entry_str) > char_limit:
                self.logger.info(f"[MEMORY-CONTEXT] Budget of {token_budget} tokens reached ({current_chars} chars)")
                break
                
            context_parts.append(entry_str)
            current_chars += len(entry_str)
            
        self.logger.info(f"[MEMORY-CONTEXT] [Trace: {trace_id}] Built context with {len(context_parts)-1} entries ({current_chars} chars)")
        return "\n".join(context_parts)

    def _summarize_entry(self, entry: MemoryEntry) -> str:
        """Simple summarizer to prevent raw log injection."""
        content = entry.content
        if entry.memory_type == MemoryType.USER_PREFERENCE:
            return f"User prefers {content.get('key', 'unknown')} as {content.get('value', 'unknown')}"
        elif entry.memory_type == MemoryType.LEARNED_PROCEDURE:
            return f"Learned process for {content.get('task', 'task')}: {content.get('summary', 'validated steps')}"
        elif entry.memory_type == MemoryType.TASK_HISTORY:
            return f"Past action: {content.get('intent', 'unknown')} ({'success' if content.get('success') else 'failure'})"
        
        return str(content)[:100] # Fallback truncation
