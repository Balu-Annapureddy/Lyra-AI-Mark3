"""
Lyra AI Operating System - Core Package
A local-first, modular personal AI assistant
"""

__version__ = "0.1.0"
__author__ = "Your Name"

from lyra.core.config import Config
from lyra.core.logger import get_logger
from lyra.core.state_manager import LyraState, StateManager

__all__ = [
    "Config",
    "get_logger",
    "LyraState",
    "StateManager",
]
