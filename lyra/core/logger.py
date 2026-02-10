"""
Structured logging system for Lyra AI
Provides multi-level logging with file and console outputs
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler


class LyraLogger:
    """Custom logger for Lyra with structured output"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None, level: str = "INFO") -> logging.Logger:
        """
        Get or create a logger instance
        
        Args:
            name: Logger name (typically module name)
            log_file: Optional log file path
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(levelname)s | %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger


def get_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Convenience function to get a logger
    
    Args:
        name: Logger name
        log_file: Optional log file path
    
    Returns:
        Configured logger instance
    """
    if log_file is None:
        # Use default log file
        project_root = Path(__file__).parent.parent.parent
        log_file = str(project_root / "data" / "logs" / "lyra.log")
    
    return LyraLogger.get_logger(name, log_file)


class ActionLogger:
    """
    Specialized logger for action audit trail
    Records all actions taken by Lyra for safety and debugging
    """
    
    def __init__(self, log_file: Optional[str] = None):
        if log_file is None:
            project_root = Path(__file__).parent.parent.parent
            log_file = str(project_root / "data" / "logs" / "actions.log")
        
        self.logger = LyraLogger.get_logger("lyra.actions", log_file)
    
    def log_action(self, action_type: str, details: dict, success: bool = True):
        """
        Log an action with details
        
        Args:
            action_type: Type of action (e.g., 'file_operation', 'system_command')
            details: Dictionary with action details
            success: Whether action succeeded
        """
        status = "SUCCESS" if success else "FAILED"
        message = f"[{action_type}] {status} | {details}"
        
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)
