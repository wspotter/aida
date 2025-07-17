
"""
File operations plugin for safe file management.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List


class FilePlugin:
    """File operations plugin with safety checks."""
    
    def __init__(self, computer_controller=None):
        self.logger = logging.getLogger(__name__)
        self.computer_controller = computer_controller
        
        # Safe directories for file operations
        self.safe_directories = [
            Path.home() / "Documents",
            Path.home() / "Downloads",
            Path.home() / "Desktop",
            Path.home() / "Pictures"
        ]
    
    def can_handle(self, text: str) -> bool:
        """Check if this plugin can handle the given text."""
        file_indicators = [
            'file', 'folder', 'directory', 'document',
            'open', 'read', 'write', 'create', 'delete',
            'copy', 'move', 'list', 'show files'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in file_indicators)
    
    def process(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process file operation request."""
        try:
            text_lower = text.lower()
            
            if 'list' in text_lower or 'show files' in text_lower:
                return self._list_files(text)
            elif 'create' in text_lower:
                return self._create_file(text)
            elif 'read' in text_lower or 'open' in text_lower:
                return self._read_file(text)
            elif 'write' in text_lower:
                return self._write_file(text)
            else:
                return {
                    "success": False,
                    "response": "I'm not sure what file operation you want to perform."
                }
                
        except Exception as e:
            self.logger.error(f"File plugin error: {e}")
            return {
                "success": False,
                "response": f"File operation error: {str(e)}"
            }
    
    def _list_files(self, text: str) -> Dict[str, Any]:
        """List files in a directory."""
        try:
            # Default to current directory
            directory = Path.cwd()
            
            # Try to extract directory from text
            if 'documents' in text.lower():
                directory = Path.home() / "Documents"
            elif 'downloads' in text.lower():
                directory = Path.home() / "Downloads"
            elif 'desktop' in text.lower():
                directory = Path.home() / "Desktop"
            
            if not directory.exists():
                return {
                    "success": False,
                    "response": f"Directory {directory} does not exist."
                }
            
            # List files
            files = []
            for item in directory.iterdir():
                if item.is_file():
                    files.append(item.name)
            
            if files:
                file_list = ", ".join(files[:10])  # Show first 10 files
                response = f"Files in {directory.name}: {file_list}"
                if len(files) > 10:
                    response += f" and {len(files) - 10} more files"
            else:
                response = f"No files found in {directory.name}"
            
            return {
                "success": True,
                "response": response,
                "files": files,
                "directory": str(directory)
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Error listing files: {str(e)}"
            }
    
    def _create_file(self, text: str) -> Dict[str, Any]:
        """Create a new file."""
        if not self.computer_controller:
            return {
                "success": False,
                "response": "File creation requires computer use permissions."
            }
        
        # This would use the computer controller for safe file creation
        return {
            "success": False,
            "response": "File creation is not yet implemented in this plugin."
        }
    
    def _read_file(self, text: str) -> Dict[str, Any]:
        """Read a file."""
        if not self.computer_controller:
            return {
                "success": False,
                "response": "File reading requires computer use permissions."
            }
        
        # This would use the computer controller for safe file reading
        return {
            "success": False,
            "response": "File reading is not yet implemented in this plugin."
        }
    
    def _write_file(self, text: str) -> Dict[str, Any]:
        """Write to a file."""
        if not self.computer_controller:
            return {
                "success": False,
                "response": "File writing requires computer use permissions."
            }
        
        # This would use the computer controller for safe file writing
        return {
            "success": False,
            "response": "File writing is not yet implemented in this plugin."
        }
