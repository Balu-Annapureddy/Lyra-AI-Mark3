"""
Custom exception hierarchy for Lyra AI
Provides specific exceptions for different error scenarios
"""


class LyraException(Exception):
    """Base exception for all Lyra-specific errors"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(LyraException):
    """Raised when configuration is invalid or missing"""
    pass


class IntentDetectionError(LyraException):
    """Raised when intent cannot be detected or is ambiguous"""
    pass


class ExecutionError(LyraException):
    """Raised when task execution fails"""
    pass


class PermissionDeniedError(LyraException):
    """Raised when user denies permission for an action"""
    pass


class MemoryError(LyraException):
    """Raised when memory operations fail"""
    pass


class AutomationError(LyraException):
    """Raised when automation tasks fail"""
    pass


class ValidationError(LyraException):
    """Raised when input validation fails"""
    pass


class SafetyViolationError(LyraException):
    """Raised when an action violates safety constraints"""
    pass
