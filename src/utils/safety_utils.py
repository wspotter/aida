
"""
Safety utilities for computer use validation.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List


class SafetyValidator:
    """Validate commands and paths for safety."""
    
    def __init__(self, safety_rules_path: str):
        self.safety_rules_path = Path(safety_rules_path)
        self.safety_rules = {}
        self.logger = logging.getLogger(__name__)
        self._load_safety_rules()
    
    def _load_safety_rules(self):
        """Load safety rules from file."""
        try:
            if self.safety_rules_path.exists():
                with open(self.safety_rules_path, 'r', encoding='utf-8') as f:
                    self.safety_rules = json.load(f)
                self.logger.info("Safety rules loaded successfully")
            else:
                self.logger.warning(f"Safety rules file not found: {self.safety_rules_path}")
                self._create_default_rules()
        except Exception as e:
            self.logger.error(f"Failed to load safety rules: {e}")
            self._create_default_rules()
    
    def _create_default_rules(self):
        """Create default safety rules."""
        self.safety_rules = {
            "safety_levels": {
                "off": {"allowed_actions": []},
                "safer": {"allowed_actions": ["file_read", "file_write_user_dir", "system_info"]},
                "god": {"allowed_actions": ["*"]}
            },
            "blocked_commands": [
                "rm -rf /",
                "dd if=/dev/zero",
                ":(){ :|:& };:",
                "chmod -R 777 /",
                "mkfs",
                "fdisk"
            ],
            "sensitive_paths": [
                "/etc/passwd",
                "/etc/shadow",
                "/etc/sudoers",
                "/boot",
                "/sys",
                "/proc"
            ]
        }
    
    def is_command_safe(self, command: str, safety_level: str) -> bool:
        """Check if a command is safe for the given safety level."""
        try:
            # Check blocked commands
            blocked_commands = self.safety_rules.get("blocked_commands", [])
            for blocked in blocked_commands:
                if blocked.lower() in command.lower():
                    return False
            
            # Check safety level permissions
            safety_levels = self.safety_rules.get("safety_levels", {})
            level_config = safety_levels.get(safety_level, {})
            allowed_actions = level_config.get("allowed_actions", [])
            
            if safety_level == "off":
                return False
            elif safety_level == "god":
                return True  # God mode allows everything except explicitly blocked
            elif safety_level == "safer":
                # Check if command matches allowed patterns
                safe_patterns = [
                    r'^ls\s',
                    r'^cat\s',
                    r'^head\s',
                    r'^tail\s',
                    r'^grep\s',
                    r'^find\s.*-name',
                    r'^ps\s',
                    r'^df\s',
                    r'^free\s',
                    r'^uptime',
                    r'^date',
                    r'^whoami',
                    r'^pwd'
                ]
                
                return any(re.match(pattern, command.strip()) for pattern in safe_patterns)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Command safety check failed: {e}")
            return False
    
    def is_path_blocked(self, path: Path) -> bool:
        """Check if a path is explicitly blocked."""
        try:
            sensitive_paths = self.safety_rules.get("sensitive_paths", [])
            path_str = str(path)
            
            for sensitive in sensitive_paths:
                if path_str.startswith(sensitive):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Path safety check failed: {e}")
            return True  # Err on the side of caution
