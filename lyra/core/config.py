"""
Configuration management for Lyra AI
Handles loading, validation, and access to configuration settings
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from lyra.core.exceptions import ConfigurationError


class Config:
    """
    Centralized configuration management
    Supports YAML configuration files with environment-specific overrides
    """
    
    _instance = None
    _config_data: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._load_default_config()
    
    def _load_default_config(self):
        """Load default configuration"""
        project_root = Path(__file__).parent.parent.parent
        default_config_path = project_root / "config" / "default_config.yaml"
        
        if default_config_path.exists():
            self.load_from_file(str(default_config_path))
        else:
            # Set minimal defaults if config file doesn't exist
            self._config_data = self._get_minimal_defaults()
    
    def _get_minimal_defaults(self) -> Dict[str, Any]:
        """Get minimal default configuration"""
        return {
            "lyra": {
                "name": "Lyra",
                "version": "0.1.0",
                "mode": "development"
            },
            "interaction": {
                "default_interface": "text",
                "voice_enabled": False,
                "language": "en"
            },
            "safety": {
                "require_confirmation": True,
                "permission_level": "strict",
                "log_all_actions": True
            },
            "memory": {
                "database_path": "data/lyra_memory.db",
                "max_event_history": 10000,
                "summarization_threshold": 1000
            },
            "automation": {
                "pc_control_enabled": True,
                "phone_control_enabled": False,
                "dry_run_mode": True
            },
            "logging": {
                "level": "INFO",
                "file_path": "data/logs/lyra.log",
                "console_output": True
            }
        }
    
    def load_from_file(self, config_path: str):
        """
        Load configuration from YAML file
        
        Args:
            config_path: Path to YAML configuration file
        
        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    self._config_data.update(loaded_config)
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Dot-separated path (e.g., 'safety.permission_level')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key_path: Dot-separated path (e.g., 'safety.permission_level')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config_data
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save_to_file(self, config_path: str):
        """
        Save current configuration to YAML file
        
        Args:
            config_path: Path to save configuration
        """
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration dictionary"""
        return self._config_data.copy()
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if valid, raises ConfigurationError otherwise
        """
        required_sections = ['lyra', 'interaction', 'safety', 'memory', 'automation', 'logging']
        
        for section in required_sections:
            if section not in self._config_data:
                raise ConfigurationError(f"Missing required configuration section: {section}")
        
        return True
