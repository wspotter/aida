
"""
Configuration loader utility.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """Load and manage configuration files."""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = {}
        self.logger = logging.getLogger(__name__)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                self.logger.warning(f"Configuration file not found: {self.config_path}")
                self.config = {}
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = {}
    
    def get_config(self) -> Dict[str, Any]:
        """Get the full configuration."""
        return self.config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def reload(self):
        """Reload configuration from file."""
        self._load_config()
