"""
Preference Store
Manages user preferences and behavioral patterns
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from lyra.core.logger import get_logger
from lyra.core.exceptions import MemoryError


class PreferenceStore:
    """
    User preference storage with JSON backend
    Supports hierarchical preferences and defaults
    """
    
    def __init__(self, preferences_file: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if preferences_file is None:
            project_root = Path(__file__).parent.parent.parent
            preferences_file = str(project_root / "data" / "user_preferences.json")
        
        self.preferences_file = preferences_file
        Path(preferences_file).parent.mkdir(parents=True, exist_ok=True)
        
        self.preferences: Dict[str, Any] = self._load_preferences()
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load preferences from file"""
        try:
            if Path(self.preferences_file).exists():
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                    self.logger.info("Loaded user preferences")
                    return prefs
            else:
                self.logger.info("No existing preferences, using defaults")
                return self._get_default_preferences()
        
        except json.JSONDecodeError as e:
            raise MemoryError(f"Invalid preferences file: {e}")
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default preferences"""
        return {
            "interface": {
                "default_mode": "text",
                "voice_enabled": False,
                "language": "en"
            },
            "automation": {
                "auto_confirm_safe_actions": False,
                "dry_run_by_default": True
            },
            "personalization": {
                "name": "",
                "timezone": "UTC"
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get preference value using dot notation
        
        Args:
            key_path: Dot-separated path (e.g., 'interface.voice_enabled')
            default: Default value if not found
        
        Returns:
            Preference value or default
        """
        keys = key_path.split('.')
        value = self.preferences
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """
        Set preference value using dot notation
        
        Args:
            key_path: Dot-separated path
            value: Value to set
        """
        keys = key_path.split('.')
        prefs = self.preferences
        
        for key in keys[:-1]:
            if key not in prefs:
                prefs[key] = {}
            prefs = prefs[key]
        
        prefs[keys[-1]] = value
        self._save_preferences()
        self.logger.info(f"Set preference: {key_path} = {value}")
    
    def _save_preferences(self):
        """Save preferences to file"""
        try:
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=2)
        
        except Exception as e:
            raise MemoryError(f"Failed to save preferences: {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all preferences"""
        return self.preferences.copy()
    
    def reset_to_defaults(self):
        """Reset all preferences to defaults"""
        self.preferences = self._get_default_preferences()
        self._save_preferences()
        self.logger.info("Reset preferences to defaults")
