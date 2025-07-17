
"""
Command handler for processing user commands and generating responses.
"""

import json
import logging
import math
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from   utils.config_loader import ConfigLoader


class CommandHandler:
    """Handle various user commands and generate appropriate responses."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.config = ConfigLoader(config_path).get_config()
        self.logger = logging.getLogger(__name__)
        
        # Load knowledge base
        self.knowledge_base = self._load_knowledge_base()
        
        # Command statistics
        self.command_stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "command_types": {}
        }
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load local knowledge base."""
        try:
            kb_path = Path("knowledge/knowledge_base.json")
            if kb_path.exists():
                with open(kb_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.logger.warning("Knowledge base not found")
                return {}
        except Exception as e:
            self.logger.error(f"Failed to load knowledge base: {e}")
            return {}
    
    def handle_command(self, nlp_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a command based on NLP processing result."""
        try:
            self.command_stats["total_commands"] += 1
            
            intent = nlp_result.get("intent", "unknown")
            text = nlp_result.get("original_text", "")
            entities = nlp_result.get("extracted_entities", {})
            
            # Track command type
            if intent not in self.command_stats["command_types"]:
                self.command_stats["command_types"][intent] = 0
            self.command_stats["command_types"][intent] += 1
            
            # Route to appropriate handler
            if intent == "greeting":
                response = self._handle_greeting(text)
            elif intent == "goodbye":
                response = self._handle_goodbye(text)
            elif intent == "math":
                response = self._handle_math(text, entities)
            elif intent == "time_date":
                response = self._handle_time_date(text)
            elif intent == "system_info":
                response = self._handle_system_info(text)
            elif intent == "file_operation":
                response = self._handle_file_operation(text, entities)
            elif intent == "weather":
                response = self._handle_weather(text)
            elif intent == "help":
                response = self._handle_help(text)
            elif intent == "question":
                response = self._handle_question(text, nlp_result)
            else:
                response = self._handle_general(text, nlp_result)
            
            # Update statistics
            if response.get("success", True):
                self.command_stats["successful_commands"] += 1
            else:
                self.command_stats["failed_commands"] += 1
            
            return response
            
        except Exception as e:
            self.logger.error(f"Command handling failed: {e}")
            self.command_stats["failed_commands"] += 1
            return {
                "response": "I'm sorry, I encountered an error processing your request.",
                "success": False,
                "error": str(e)
            }
    
    def _handle_greeting(self, text: str) -> Dict[str, Any]:
        """Handle greeting commands."""
        greetings = self.knowledge_base.get("general_knowledge", {}).get("greetings", [
            "Hello! How can I help you today?",
            "Hi there! What can I do for you?",
            "Good day! I'm ready to assist you."
        ])
        
        # Time-based greetings
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            time_greeting = "Good morning!"
        elif 12 <= current_hour < 17:
            time_greeting = "Good afternoon!"
        elif 17 <= current_hour < 21:
            time_greeting = "Good evening!"
        else:
            time_greeting = "Good night!"
        
        import random
        response = f"{time_greeting} {random.choice(greetings)}"
        
        return {
            "response": response,
            "success": True,
            "action": "greeting"
        }
    
    def _handle_goodbye(self, text: str) -> Dict[str, Any]:
        """Handle goodbye commands."""
        goodbyes = [
            "Goodbye! Have a great day!",
            "See you later! Take care!",
            "Farewell! It was nice talking with you.",
            "Bye! Feel free to ask me anything anytime."
        ]
        
        import random
        return {
            "response": random.choice(goodbyes),
            "success": True,
            "action": "goodbye"
        }
    
    def _handle_math(self, text: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle mathematical calculations."""
        try:
            # Extract mathematical expression
            math_expr = self._extract_math_expression(text)
            
            if not math_expr:
                return {
                    "response": "I couldn't find a mathematical expression in your request. Please try something like '2 + 2' or 'square root of 16'.",
                    "success": False
                }
            
            # Calculate result
            result = self._calculate_expression(math_expr)
            
            if result is not None:
                return {
                    "response": f"The result is {result}",
                    "success": True,
                    "action": "calculation",
                    "expression": math_expr,
                    "result": result
                }
            else:
                return {
                    "response": "I couldn't calculate that expression. Please check the syntax.",
                    "success": False
                }
                
        except Exception as e:
            return {
                "response": f"Calculation error: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    def _handle_time_date(self, text: str) -> Dict[str, Any]:
        """Handle time and date queries."""
        now = datetime.now()
        
        if any(word in text.lower() for word in ["time", "clock"]):
            time_str = now.strftime("%I:%M %p")
            response = f"The current time is {time_str}"
        elif any(word in text.lower() for word in ["date", "today"]):
            date_str = now.strftime("%A, %B %d, %Y")
            response = f"Today is {date_str}"
        else:
            datetime_str = now.strftime("%I:%M %p on %A, %B %d, %Y")
            response = f"It's currently {datetime_str}"
        
        return {
            "response": response,
            "success": True,
            "action": "time_date",
            "timestamp": now.isoformat()
        }
    
    def _handle_system_info(self, text: str) -> Dict[str, Any]:
        """Handle system information queries."""
        try:
            import psutil
            
            if "memory" in text.lower() or "ram" in text.lower():
                memory = psutil.virtual_memory()
                response = f"Memory usage: {memory.percent}% ({memory.used // (1024**3)} GB used of {memory.total // (1024**3)} GB total)"
            elif "cpu" in text.lower() or "processor" in text.lower():
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                response = f"CPU usage: {cpu_percent}% ({cpu_count} cores)"
            elif "disk" in text.lower() or "storage" in text.lower():
                disk = psutil.disk_usage('/')
                response = f"Disk usage: {disk.percent}% ({disk.used // (1024**3)} GB used of {disk.total // (1024**3)} GB total)"
            else:
                # General system info
                memory = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=1)
                disk = psutil.disk_usage('/')
                
                response = (f"System Status:\n"
                           f"CPU: {cpu_percent}%\n"
                           f"Memory: {memory.percent}%\n"
                           f"Disk: {disk.percent}%")
            
            return {
                "response": response,
                "success": True,
                "action": "system_info"
            }
            
        except ImportError:
            return {
                "response": "System information is not available (psutil not installed).",
                "success": False
            }
        except Exception as e:
            return {
                "response": f"Error getting system information: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    def _handle_file_operation(self, text: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file operation requests."""
        # This is a simplified handler - actual file operations should go through ComputerController
        file_paths = entities.get("file_path", [])
        
        if "list" in text.lower() or "show" in text.lower():
            try:
                current_dir = os.getcwd()
                files = os.listdir(current_dir)
                file_list = "\n".join(files[:10])  # Show first 10 files
                
                response = f"Files in current directory ({current_dir}):\n{file_list}"
                if len(files) > 10:
                    response += f"\n... and {len(files) - 10} more files"
                
                return {
                    "response": response,
                    "success": True,
                    "action": "file_list",
                    "directory": current_dir,
                    "file_count": len(files)
                }
            except Exception as e:
                return {
                    "response": f"Error listing files: {str(e)}",
                    "success": False,
                    "error": str(e)
                }
        else:
            return {
                "response": "File operations require computer use permissions. Please enable computer use and try again.",
                "success": False,
                "requires_computer_use": True
            }
    
    def _handle_weather(self, text: str) -> Dict[str, Any]:
        """Handle weather queries (offline fallback)."""
        # Since this is offline, provide a fallback response
        return {
            "response": "I don't have access to current weather data in offline mode. You can check your local weather app or website for current conditions.",
            "success": True,
            "action": "weather_fallback",
            "note": "Offline mode - no real weather data available"
        }
    
    def _handle_help(self, text: str) -> Dict[str, Any]:
        """Handle help requests."""
        capabilities = self.knowledge_base.get("general_knowledge", {}).get("capabilities", [
            "I can help with calculations, file operations, system information, and general conversation.",
            "I have access to local knowledge and can remember our conversations.",
            "I can control your computer safely with your permission."
        ])
        
        help_text = "Here's what I can help you with:\n\n"
        help_text += "• Math calculations (e.g., 'calculate 2 + 2')\n"
        help_text += "• Time and date ('what time is it?')\n"
        help_text += "• System information ('show memory usage')\n"
        help_text += "• File operations ('list files')\n"
        help_text += "• General conversation and questions\n"
        help_text += "• Computer control (with safety permissions)\n\n"
        help_text += "Just speak naturally and I'll do my best to help!"
        
        return {
            "response": help_text,
            "success": True,
            "action": "help"
        }
    
    def _handle_question(self, text: str, nlp_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general questions."""
        keywords = nlp_result.get("keywords", [])
        
        # Try to find relevant information in knowledge base
        response = self._search_knowledge_base(keywords)
        
        if response:
            return {
                "response": response,
                "success": True,
                "action": "knowledge_query",
                "keywords": keywords
            }
        else:
            return {
                "response": "I don't have specific information about that. Could you rephrase your question or ask about something else?",
                "success": True,
                "action": "unknown_question",
                "keywords": keywords
            }
    
    def _handle_general(self, text: str, nlp_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general statements and conversation."""
        sentiment = nlp_result.get("sentiment", {})
        polarity = sentiment.get("polarity", 0)
        
        # Respond based on sentiment
        if polarity > 0.1:
            responses = [
                "That sounds positive! I'm glad to hear that.",
                "That's great! Is there anything I can help you with?",
                "Wonderful! How can I assist you today?"
            ]
        elif polarity < -0.1:
            responses = [
                "I'm sorry to hear that. Is there anything I can do to help?",
                "That doesn't sound good. How can I assist you?",
                "I understand. Let me know if there's anything I can help with."
            ]
        else:
            responses = [
                "I see. Is there anything specific you'd like to know or do?",
                "Interesting. How can I help you today?",
                "I understand. What would you like to do next?"
            ]
        
        import random
        return {
            "response": random.choice(responses),
            "success": True,
            "action": "general_conversation",
            "sentiment": sentiment
        }
    
    def _extract_math_expression(self, text: str) -> Optional[str]:
        """Extract mathematical expression from text."""
        # Look for mathematical expressions
        patterns = [
            r"(\d+\.?\d*\s*[\+\-\*\/\%\^]\s*\d+\.?\d*)",
            r"(square root of \d+\.?\d*)",
            r"(\d+\.?\d* factorial)",
            r"(\d+\.?\d* percent of \d+\.?\d*)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Look for word-based math
        text_lower = text.lower()
        if "plus" in text_lower or "add" in text_lower:
            numbers = re.findall(r"\d+\.?\d*", text)
            if len(numbers) >= 2:
                return f"{numbers[0]} + {numbers[1]}"
        elif "minus" in text_lower or "subtract" in text_lower:
            numbers = re.findall(r"\d+\.?\d*", text)
            if len(numbers) >= 2:
                return f"{numbers[0]} - {numbers[1]}"
        elif "times" in text_lower or "multiply" in text_lower:
            numbers = re.findall(r"\d+\.?\d*", text)
            if len(numbers) >= 2:
                return f"{numbers[0]} * {numbers[1]}"
        elif "divided" in text_lower:
            numbers = re.findall(r"\d+\.?\d*", text)
            if len(numbers) >= 2:
                return f"{numbers[0]} / {numbers[1]}"
        
        return None
    
    def _calculate_expression(self, expression: str) -> Optional[float]:
        """Calculate mathematical expression safely."""
        try:
            # Handle special functions
            if "square root" in expression.lower():
                number = re.search(r"(\d+\.?\d*)", expression)
                if number:
                    return math.sqrt(float(number.group(1)))
            
            if "factorial" in expression.lower():
                number = re.search(r"(\d+)", expression)
                if number:
                    return math.factorial(int(number.group(1)))
            
            if "percent of" in expression.lower():
                numbers = re.findall(r"(\d+\.?\d*)", expression)
                if len(numbers) >= 2:
                    return (float(numbers[0]) / 100) * float(numbers[1])
            
            # Handle basic arithmetic
            # Replace common operators
            expression = expression.replace("^", "**")  # Power operator
            
            # Validate expression contains only safe characters
            if re.match(r"^[\d\+\-\*\/\%\.\(\)\s\*]+$", expression):
                result = eval(expression)
                return float(result)
            
        except Exception as e:
            self.logger.error(f"Calculation error: {e}")
        
        return None
    
    def _search_knowledge_base(self, keywords: List[str]) -> Optional[str]:
        """Search knowledge base for relevant information."""
        if not keywords or not self.knowledge_base:
            return None
        
        # Simple keyword matching in knowledge base
        for section_name, section_data in self.knowledge_base.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if any(keyword.lower() in key.lower() for keyword in keywords):
                        if isinstance(value, list):
                            import random
                            return random.choice(value)
                        elif isinstance(value, str):
                            return value
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get command handler statistics."""
        return self.command_stats.copy()
    
    def reset_stats(self):
        """Reset command statistics."""
        self.command_stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "command_types": {}
        }
