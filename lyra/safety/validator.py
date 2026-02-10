"""
Input Validator
Validates and sanitizes user input for safety
"""

import re
from pathlib import Path
from typing import Dict, Any, List
from lyra.core.logger import get_logger
from lyra.core.exceptions import ValidationError, SafetyViolationError


class InputValidator:
    """
    Validates user input and command parameters
    Detects dangerous patterns and sanitizes input
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Dangerous patterns to detect
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",           # Recursive delete root
            r"format\s+c:",            # Format C drive
            r"del\s+/[fs]\s+\*",       # Force delete all
            r"shutdown\s+-[hpr]",      # Immediate shutdown (caught separately)
        ]
    
    def validate_command_input(self, user_input: str) -> bool:
        """
        Validate user input for dangerous patterns
        
        Args:
            user_input: Raw user input
        
        Returns:
            True if valid
        
        Raises:
            SafetyViolationError: If dangerous pattern detected
        """
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                raise SafetyViolationError(
                    f"Dangerous pattern detected in input",
                    {"pattern": pattern, "input": user_input}
                )
        
        return True
    
    def validate_filename(self, filename: str) -> bool:
        """
        Validate filename for safety
        
        Args:
            filename: Filename to validate
        
        Returns:
            True if valid
        
        Raises:
            ValidationError: If filename invalid
        """
        # Check length
        if not filename or len(filename) > 255:
            raise ValidationError("Invalid filename length")
        
        # Check for invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, filename):
            raise ValidationError(
                "Filename contains invalid characters",
                {"filename": filename}
            )
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 
                         'COM4', 'LPT1', 'LPT2', 'LPT3']
        if filename.upper() in reserved_names:
            raise ValidationError(
                "Filename is a reserved system name",
                {"filename": filename}
            )
        
        return True
    
    def validate_path(self, path: str, must_exist: bool = False) -> bool:
        """
        Validate file path for safety
        
        Args:
            path: File path to validate
            must_exist: Whether path must exist
        
        Returns:
            True if valid
        
        Raises:
            ValidationError: If path invalid
        """
        try:
            path_obj = Path(path)
            
            # Check if path exists (if required)
            if must_exist and not path_obj.exists():
                raise ValidationError(
                    "Path does not exist",
                    {"path": path}
                )
            
            # Check for path traversal attempts
            if ".." in path:
                raise SafetyViolationError(
                    "Path traversal attempt detected",
                    {"path": path}
                )
            
            return True
        
        except Exception as e:
            raise ValidationError(f"Invalid path: {e}")
    
    def sanitize_input(self, user_input: str) -> str:
        """
        Sanitize user input
        
        Args:
            user_input: Raw input
        
        Returns:
            Sanitized input
        """
        # Remove leading/trailing whitespace
        sanitized = user_input.strip()
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Limit length
        max_length = 1000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            self.logger.warning(f"Input truncated to {max_length} characters")
        
        return sanitized
    
    def validate_command_parameters(self, params: Dict[str, Any]) -> bool:
        """
        Validate command parameters
        
        Args:
            params: Parameters dictionary
        
        Returns:
            True if valid
        """
        # Validate filenames
        if 'filename' in params:
            self.validate_filename(params['filename'])
        
        # Validate paths
        if 'filepath' in params:
            self.validate_path(params['filepath'])
        
        if 'directory' in params:
            self.validate_path(params['directory'])
        
        return True
