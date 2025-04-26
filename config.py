# config.py
import os
import json
from typing import Any, Dict, Optional

class Config:
    """
    Configuration manager with defaults, file loading and environment variables.
    """
    
    DEFAULT_CONFIG = {
        "api": {
            "pexels_key": "",
            "email": "user@example.com"  # For Unpaywall API
        },
        "video": {
            "formats": {
                "tiktok": {"width": 1080, "height": 1920},
                "instagram": {"width": 1080, "height": 1080},
                "youtube": {"width": 1920, "height": 1080}
            },
            "default_format": "tiktok",
            "fps": 30,
            "quality": "medium"
        },
        "paper": {
            "max_papers": 3,
            "summarizer": {
                "model": "facebook/bart-large-cnn",
                "max_length": 100,
                "min_length": 30
            }
        },
        "paths": {
            "temp_dir": "temp_assets",
            "output_dir": "videos",
            "tesseract_cmd": ""
        }
    }
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_file()
        self.load_env()
    
    def load_file(self) -> None:
        """Load configuration from JSON file if it exists."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    self._deep_update(self.config, loaded_config)
            except Exception as e:
                print(f"Error loading config file: {e}")
    
    def load_env(self) -> None:
        """Override configuration with environment variables."""
        # Handle specific known environment variables
        if os.getenv("PEXELS_API_KEY"):
            self.set("api.pexels_key", os.getenv("PEXELS_API_KEY"))
            
        # Map TESSERACT_CMD to config
        if os.getenv("TESSERACT_CMD"):
            self.set("paths.tesseract_cmd", os.getenv("TESSERACT_CMD"))
            
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to configuration value
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        parts = key_path.split('.')
        value = self.config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
                
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to configuration value
            value: Value to set
        """
        parts = key_path.split('.')
        config = self.config
        
        # Navigate to the correct nested dict
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        
        # Set the value
        config[parts[-1]] = value
    
    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _deep_update(self, target: Dict, source: Dict) -> None:
        """
        Recursively update nested dictionaries.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value