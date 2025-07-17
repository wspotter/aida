"""
Computer Use Controller
Handles safe computer automation with configurable safety levels.
"""

import os
import json
import logging
import subprocess
import threading
import time
import psutil
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

from utils.config_loader import ConfigLoader
from utils.safety_utils import SafetyValidator


class ComputerController:
    """Safe computer automation with three-tier safety system."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.config = ConfigLoader(config_path).get_config()
        self.computer_config = self.config.get("computer_use", {})
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Safety configuration
        self.safety_level = self.computer_config.get("safety_level", "safer")
        self.require_confirmation = self.computer_config.get("require_confirmation", True)
        self.log_actions = self.computer_config.get("log_actions", True)
        
        # Initialize safety validator
        self.safety_validator = SafetyValidator("configs/safety_rules.json")
        
        # Action logging
        self.action_log = []
        self.max_log_entries = 1000
        
        # User home directory for safe operations
        self.user_home = Path.home()
        self.safe_directories = [
            self.user_home / "Documents",
            self.user_home / "Downloads", 
            self.user_home / "Desktop",
            self.user_home / "Pictures",
            self.user_home / "Music",
            self.user_home / "Videos"
        ]
        
        self.logger.info(f"Computer controller initialized with safety level: {self.safety_level}")
    
    def execute_command(self, command: str, description: str = None) -> Dict[str, Any]:
        """Execute a system command with safety checks."""
        with self._lock:
            try:
                # Validate safety level
                if self.safety_level == "off":
                    return {
                        "success": False,
                        "error": "Computer use is disabled",
                        "safety_level": self.safety_level
                    }
                
                # Validate command safety
                if not self.safety_validator.is_command_safe(command, self.safety_level):
                    return {
                        "success": False,
                        "error": f"Command blocked by safety rules: {command}",
                        "safety_level": self.safety_level
                    }
                
                # Request confirmation if required
                if self.require_confirmation:
                    if not self._request_confirmation(command, description):
                        return {
                            "success": False,
                            "error": "User denied permission",
                            "command": command
                        }
                
                # Log the action
                self._log_action("command", command, description)
                
                # Execute command
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                response = {
                    "success": result.returncode == 0,
                    "command": command,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "timestamp": datetime.now().isoformat()
                }
                
                if not response["success"]:
                    self.logger.warning(f"Command failed: {command} - {result.stderr}")
                
                return response
                
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": "Command timed out",
                    "command": command
                }
            except Exception as e:
                self.logger.error(f"Failed to execute command: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "command": command
                }
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read a file with safety checks."""
        try:
            path = Path(file_path).resolve()
            
            # Safety checks
            if not self._is_path_safe(path, "read"):
                return {
                    "success": False,
                    "error": f"Access denied to path: {path}",
                    "path": str(path)
                }
            
            if not path.exists():
                return {
                    "success": False,
                    "error": "File not found",
                    "path": str(path)
                }
            
            if not path.is_file():
                return {
                    "success": False,
                    "error": "Path is not a file",
                    "path": str(path)
                }
            
            # Request confirmation for sensitive files
            if self.require_confirmation and self._is_sensitive_file(path):
                if not self._request_confirmation(f"read file: {path}"):
                    return {
                        "success": False,
                        "error": "User denied permission",
                        "path": str(path)
                    }
            
            # Log the action
            self._log_action("file_read", str(path))
            
            # Read file
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "path": str(path),
                "size": len(content),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def write_file(self, file_path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """Write to a file with safety checks."""
        try:
            path = Path(file_path).resolve()
            
            # Safety checks
            if not self._is_path_safe(path, "write"):
                return {
                    "success": False,
                    "error": f"Write access denied to path: {path}",
                    "path": str(path)
                }
            
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Request confirmation
            action = "append to" if append else "write to"
            if self.require_confirmation:
                if not self._request_confirmation(f"{action} file: {path}"):
                    return {
                        "success": False,
                        "error": "User denied permission",
                        "path": str(path)
                    }
            
            # Log the action
            self._log_action("file_write", str(path), f"append={append}")
            
            # Write file
            mode = 'a' if append else 'w'
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": str(path),
                "bytes_written": len(content.encode('utf-8')),
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def list_directory(self, directory_path: str) -> Dict[str, Any]:
        """List directory contents with safety checks."""
        try:
            path = Path(directory_path).resolve()
            
            # Safety checks
            if not self._is_path_safe(path, "read"):
                return {
                    "success": False,
                    "error": f"Access denied to directory: {path}",
                    "path": str(path)
                }
            
            if not path.exists():
                return {
                    "success": False,
                    "error": "Directory not found",
                    "path": str(path)
                }
            
            if not path.is_dir():
                return {
                    "success": False,
                    "error": "Path is not a directory",
                    "path": str(path)
                }
            
            # Log the action
            self._log_action("directory_list", str(path))
            
            # List contents
            items = []
            for item in path.iterdir():
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "permissions": oct(stat.st_mode)[-3:]
                    })
                except (OSError, PermissionError):
                    # Skip items we can't access
                    continue
            
            return {
                "success": True,
                "path": str(path),
                "items": items,
                "count": len(items),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list directory {directory_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": directory_path
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        try:
            # Log the action
            self._log_action("system_info", "get_system_info")
            
            # Get system information
            cpu_info = {
                "count": psutil.cpu_count(),
                "usage": psutil.cpu_percent(interval=1),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }
            
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percentage": memory.percent
            }
            
            disk_info = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percentage": (usage.used / usage.total) * 100
                    })
                except PermissionError:
                    continue
            
            return {
                "success": True,
                "system": {
                    "platform": os.name,
                    "cpu": cpu_info,
                    "memory": memory_info,
                    "disk": disk_info,
                    "uptime": time.time() - psutil.boot_time()
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_running_processes(self) -> Dict[str, Any]:
        """Get list of running processes."""
        try:
            # Check safety level
            if self.safety_level == "off":
                return {
                    "success": False,
                    "error": "Computer use is disabled"
                }
            
            # Log the action
            self._log_action("process_list", "get_running_processes")
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return {
                "success": True,
                "processes": processes[:50],  # Top 50 processes
                "total_count": len(processes),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get running processes: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_directory(self, directory_path: str) -> Dict[str, Any]:
        """Create a directory with safety checks."""
        try:
            path = Path(directory_path).resolve()
            
            # Safety checks
            if not self._is_path_safe(path, "write"):
                return {
                    "success": False,
                    "error": f"Access denied to create directory: {path}",
                    "path": str(path)
                }
            
            # Request confirmation
            if self.require_confirmation:
                if not self._request_confirmation(f"create directory: {path}"):
                    return {
                        "success": False,
                        "error": "User denied permission",
                        "path": str(path)
                    }
            
            # Log the action
            self._log_action("directory_create", str(path))
            
            # Create directory
            path.mkdir(parents=True, exist_ok=True)
            
            return {
                "success": True,
                "path": str(path),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create directory {directory_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": directory_path
            }
    
    def copy_file(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        """Copy a file with safety checks."""
        try:
            src = Path(source_path).resolve()
            dst = Path(destination_path).resolve()
            
            # Safety checks
            if not self._is_path_safe(src, "read"):
                return {
                    "success": False,
                    "error": f"Read access denied to source: {src}",
                    "source": str(src)
                }
            
            if not self._is_path_safe(dst, "write"):
                return {
                    "success": False,
                    "error": f"Write access denied to destination: {dst}",
                    "destination": str(dst)
                }
            
            if not src.exists():
                return {
                    "success": False,
                    "error": "Source file not found",
                    "source": str(src)
                }
            
            # Request confirmation
            if self.require_confirmation:
                if not self._request_confirmation(f"copy file from {src} to {dst}"):
                    return {
                        "success": False,
                        "error": "User denied permission",
                        "source": str(src),
                        "destination": str(dst)
                    }
            
            # Log the action
            self._log_action("file_copy", f"{src} -> {dst}")
            
            # Create destination directory if needed
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(src, dst)
            
            return {
                "success": True,
                "source": str(src),
                "destination": str(dst),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to copy file {source_path} to {destination_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": source_path,
                "destination": destination_path
            }
    
    def _is_path_safe(self, path: Path, operation: str) -> bool:
        """Check if a path is safe for the given operation."""
        try:
            # Convert to absolute path
            abs_path = path.resolve()
            
            # Check safety level
            if self.safety_level == "off":
                return False
            elif self.safety_level == "god":
                # God mode allows everything except explicitly blocked paths
                return not self.safety_validator.is_path_blocked(abs_path)
            elif self.safety_level == "safer":
                # Safer mode only allows operations in safe directories
                if operation == "read":
                    # Allow reading from more locations
                    allowed_read_paths = [
                        self.user_home,
                        Path("/tmp"),
                        Path("/var/tmp")
                    ]
                    return any(
                        abs_path.is_relative_to(safe_path) 
                        for safe_path in allowed_read_paths
                    ) and not self.safety_validator.is_path_blocked(abs_path)
                else:
                    # Restrict writing to safe directories only
                    return any(
                        abs_path.is_relative_to(safe_dir) 
                        for safe_dir in self.safe_directories
                    ) and not self.safety_validator.is_path_blocked(abs_path)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Path safety check failed: {e}")
            return False
    
    def _is_sensitive_file(self, path: Path) -> bool:
        """Check if a file is sensitive and requires extra confirmation."""
        sensitive_patterns = [
            ".ssh",
            ".gnupg",
            "password",
            "secret",
            "private",
            "key",
            ".env"
        ]
        
        path_str = str(path).lower()
        return any(pattern in path_str for pattern in sensitive_patterns)
    
    def _request_confirmation(self, action: str, description: str = None) -> bool:
        """Request user confirmation for an action."""
        # In a real implementation, this would show a GUI dialog or prompt
        # For now, we'll log the request and assume confirmation
        message = f"Confirm action: {action}"
        if description:
            message += f" - {description}"
        
        self.logger.info(f"CONFIRMATION REQUESTED: {message}")
        
        # In production, implement actual user confirmation
        # For now, return True to allow actions
        return True
    
    def _log_action(self, action_type: str, details: str, metadata: str = None):
        """Log an action for audit purposes."""
        if not self.log_actions:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "details": details,
            "metadata": metadata,
            "safety_level": self.safety_level
        }
        
        self.action_log.append(log_entry)
        
        # Keep log size manageable
        if len(self.action_log) > self.max_log_entries:
            self.action_log = self.action_log[-self.max_log_entries:]
        
        self.logger.info(f"ACTION: {action_type} - {details}")
    
    def get_action_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent action log entries."""
        return self.action_log[-limit:] if self.action_log else []
    
    def set_safety_level(self, level: str) -> bool:
        """Change the safety level."""
        valid_levels = ["off", "safer", "god"]
        
        if level not in valid_levels:
            self.logger.error(f"Invalid safety level: {level}. Valid: {valid_levels}")
            return False
        
        old_level = self.safety_level
        self.safety_level = level
        
        self._log_action("safety_level_change", f"{old_level} -> {level}")
        self.logger.info(f"Safety level changed from {old_level} to {level}")
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get current controller status."""
        return {
            "safety_level": self.safety_level,
            "require_confirmation": self.require_confirmation,
            "log_actions": self.log_actions,
            "action_log_entries": len(self.action_log),
            "safe_directories": [str(d) for d in self.safe_directories],
            "user_home": str(self.user_home)
        }
