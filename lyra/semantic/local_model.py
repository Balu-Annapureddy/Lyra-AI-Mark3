# -*- coding: utf-8 -*-
"""
Local Semantic Model
Rule-based simulation of an LLM behavior
Placeholders structure for future quantized model drop-in
"""

from typing import Dict, Any
import re

class LocalSemanticModel:
    """
    Simulates a local LLM for intent extraction.
    Currently uses regex/rules to 'generate' the JSON structure.
    This allows architecture testing without model weight dependencies.
    """
    
    def generate_structured_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Simulate LLM generation of structured intent
        
        Args:
            user_input: Natural language text
            
        Returns:
            Dictionary matching the strict schema
        """
        text = user_input.lower().strip()
        
        # Default fallback (Unknown)
        response = {
            "intent": "unknown",
            "parameters": {},
            "confidence": 0.0,
            "requires_clarification": True
        }

        # --- Rule-Based Simulation (Mocking the LLM) ---
        
        # 1. File Creation (Write)
        # Strict check: requires "create", "make", "write" AND "file"
        if ("create" in text or "make" in text or "write" in text) and "file" in text:
            # simple extraction (Phase 6A: handled "named" keyword, avoid common words)
            # Look for explicit "named X" first
            name_match = re.search(r"named\s+([^\s]+)", text)
            if name_match:
                path = name_match.group(1)
            else:
                # If no "named", try to find file X, but avoid "and", "with"
                match = re.search(r"file\s+(?!and\b|with\b)([^\s]+)", text)
                path = match.group(1) if match else "untitled.txt"
            
            content_match = re.search(r"content\s+[\"'](.+)[\"']", text)
            if content_match:
                content = content_match.group(1)
            else:
                # Try natural language extraction "write X in it", "include text X"
                # Look for "include text", "write", "with content" followed by anything until end or "in it"
                nl_match = re.search(r"(?:include|write|content)\s+(?:the\s+)?(?:text\s+)?(.+?)(?:\s+in\s+it)?$", text)
                content = nl_match.group(1) if nl_match else ""
            
            response = {
                "intent": "write_file",
                "parameters": {
                    "path": path,
                    "content": content
                },
                "confidence": 0.85 if content else 0.6,
                "requires_clarification": False
            }

        # 2. Open URL
        elif "open" in text and ("http" in text or ".com" in text or "google" in text):
            url = ""
            if "http" in text:
                url_match = re.search(r"(https?://\S+)", text)
                if url_match: url = url_match.group(1)
            elif "google" in text:
                url = "https://google.com"
            else:
                url_match = re.search(r"([a-z0-9.-]+\.com)", text)
                if url_match: url = f"https://{url_match.group(1)}"
            
            response = {
                "intent": "open_url",
                "parameters": {"url": url},
                "confidence": 0.9,
                "requires_clarification": False
            }
            
        # 3. Read File (Open/Read)
        elif ("open" in text or "read" in text) and "file" in text and "http" not in text:
            match = re.search(r"file\s+(?:named\s+)?([^\s]+)", text)
            path = match.group(1) if match else "untitled.txt"
            
            response = {
                "intent": "read_file",
                "parameters": {"path": path},
                "confidence": 0.85,
                "requires_clarification": False
            }

        # 4. Launch App
        elif "launch" in text or "start" in text or "open" in text:
             # If we got here, it's not a URL (block 2) and not a file (block 3)
             app_match = re.search(r"(?:launch|start|open)\s+(\w+)", text)
             app = app_match.group(1) if app_match else ""
             
             # Filter out common non-apps
             if app in ["file", "the", "it", "url", "website"]:
                 # Likely a partial match for something else
                 pass
             else:
                 response = {
                    "intent": "launch_app",
                    "parameters": {"app_name": app},
                    "confidence": 0.8,
                    "requires_clarification": False
                 }

        # 5. Ambiguous / Clarification trigger
        elif "do the thing" in text or text == "file":
             response = {
                "intent": "unknown",
                "parameters": {},
                "confidence": 0.3,
                "requires_clarification": True
            }
            
        return response
