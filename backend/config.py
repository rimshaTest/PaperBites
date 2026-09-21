# config.py
import os
import json
from typing import Any, Dict, Optional
import logging

from dotenv import load_dotenv

# Loads backend/.env (gitignored) into the process environment, if present, before any
# environment variable is read below - lets secrets (Mongo connection string, API keys) live
# outside the committed config.json instead of in plaintext. A missing .env is not an error;
# load_dotenv() is a no-op in that case and config.json's own values are used as-is.
load_dotenv()

class Config:
    """
    Configuration manager with defaults, file loading and environment variables.
    """
    
    DEFAULT_CONFIG = {
        "api": {
            "email": "user@example.com",  # For Unpaywall API
            "pexels_key": "",  # For paper card thumbnail images (paper/latest.py)
            "semantic_scholar_key": "",  # Optional - raises Semantic Scholar's low anonymous rate limit
            "gemini_key": "",  # For card description summarization (paper/summarize.py)
            "gemini_requests_per_minute": 5  # Free tier default for gemini-2.5-flash; raise if on a paid plan
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
                    logging.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logging.error(f"Error loading config file: {e}")
    
    def load_env(self) -> None:
        """Override configuration with environment variables (including a gitignored .env file
        loaded by load_dotenv() above). Runs after load_file(), so these win over config.json -
        the intended way to supply secrets without committing them."""
        # Secrets - keep these out of config.json; set them in backend/.env instead (see
        # .env.example)
        if os.getenv("PAPERBITES_MONGODB_URI"):
            self.set("storage.mongodb.connection_string", os.getenv("PAPERBITES_MONGODB_URI"))
        if os.getenv("PAPERBITES_MONGODB_DB"):
            self.set("storage.mongodb.database_name", os.getenv("PAPERBITES_MONGODB_DB"))
        if os.getenv("PAPERBITES_PEXELS_KEY"):
            self.set("api.pexels_key", os.getenv("PAPERBITES_PEXELS_KEY"))
        if os.getenv("PAPERBITES_SEMANTIC_SCHOLAR_KEY"):
            self.set("api.semantic_scholar_key", os.getenv("PAPERBITES_SEMANTIC_SCHOLAR_KEY"))
        if os.getenv("PAPERBITES_GEMINI_KEY"):
            self.set("api.gemini_key", os.getenv("PAPERBITES_GEMINI_KEY"))
        if os.getenv("PAPERBITES_GEMINI_RPM"):
            self.set("api.gemini_requests_per_minute", int(os.getenv("PAPERBITES_GEMINI_RPM")))
        if os.getenv("PAPERBITES_EMAIL"):
            self.set("api.email", os.getenv("PAPERBITES_EMAIL"))

        # OCR configuration
        if os.getenv("TESSERACT_CMD"):
            self.set("paths.tesseract_cmd", os.getenv("TESSERACT_CMD"))

        # Output directories
        if os.getenv("PAPERBITES_TEMP_DIR"):
            self.set("paths.temp_dir", os.getenv("PAPERBITES_TEMP_DIR"))

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
            logging.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logging.error(f"Error saving config: {e}")
    
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