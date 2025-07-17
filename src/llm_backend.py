"""
LLM Backend Integration
Handles local LLM processing with Ollama and LMStudio support.
"""

import json
import logging
import requests
import threading
import time
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from  utils.config_loader import ConfigLoader


class LLMBackend:
    """Local LLM backend with Ollama and LMStudio support."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.config = ConfigLoader(config_path).get_config()
        self.llm_config = self.config.get("llm", {})
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Backend configuration
        self.backend = self.llm_config.get("backend", "ollama")
        self.ollama_url = self.llm_config.get("ollama_url", "http://localhost:11434")
        self.lmstudio_url = self.llm_config.get("lmstudio_url", "http://localhost:1234")
        self.model = self.llm_config.get("model", "llama2:7b")
        
        # Generation parameters
        self.temperature = self.llm_config.get("temperature", 0.7)
        self.max_tokens = self.llm_config.get("max_tokens", 512)
        self.context_window = self.llm_config.get("context_window", 4096)
        
        # Conversation context
        self.conversation_history = []
        self.max_history_length = 10
        
        # Backend status
        self.backend_status = {
            "ollama": False,
            "lmstudio": False,
            "active_backend": None
        }
        
        # Initialize backend
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize and test the LLM backend."""
        try:
            if self.backend == "ollama":
                self._test_ollama_connection()
            elif self.backend == "lmstudio":
                self._test_lmstudio_connection()
            else:
                self.logger.error(f"Unknown backend: {self.backend}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM backend: {e}")
    
    def _test_ollama_connection(self) -> bool:
        """Test Ollama connection and model availability."""
        try:
            if not OLLAMA_AVAILABLE:
                self.logger.error("Ollama package not available")
                return False
            
            # Test connection
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model["name"] for model in models]
                
                if self.model in model_names:
                    self.backend_status["ollama"] = True
                    self.backend_status["active_backend"] = "ollama"
                    self.logger.info(f"Ollama connected successfully with model: {self.model}")
                    return True
                else:
                    self.logger.warning(f"Model {self.model} not found in Ollama. Available: {model_names}")
                    # Try to pull the model
                    self._pull_ollama_model(self.model)
            else:
                self.logger.error(f"Ollama connection failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ollama connection error: {e}")
        except Exception as e:
            self.logger.error(f"Ollama test failed: {e}")
        
        return False
    
    def _test_lmstudio_connection(self) -> bool:
        """Test LMStudio connection."""
        try:
            response = requests.get(f"{self.lmstudio_url}/v1/models", timeout=5)
            if response.status_code == 200:
                self.backend_status["lmstudio"] = True
                self.backend_status["active_backend"] = "lmstudio"
                self.logger.info("LMStudio connected successfully")
                return True
            else:
                self.logger.error(f"LMStudio connection failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"LMStudio connection error: {e}")
        except Exception as e:
            self.logger.error(f"LMStudio test failed: {e}")
        
        return False
    
    def _pull_ollama_model(self, model_name: str) -> bool:
        """Pull a model in Ollama."""
        try:
            self.logger.info(f"Pulling Ollama model: {model_name}")
            
            if OLLAMA_AVAILABLE:
                # Use ollama package if available
                ollama.pull(model_name)
                self.logger.info(f"Successfully pulled model: {model_name}")
                return True
            else:
                # Fallback to API call
                response = requests.post(
                    f"{self.ollama_url}/api/pull",
                    json={"name": model_name},
                    timeout=300  # 5 minutes timeout for model download
                )
                
                if response.status_code == 200:
                    self.logger.info(f"Successfully pulled model: {model_name}")
                    return True
                
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
        
        return False
    
    def generate_response(self, prompt: str, context: str = None, 
                         system_prompt: str = None) -> str:
        """Generate response from the LLM."""
        with self._lock:
            try:
                # Prepare the full prompt
                full_prompt = self._prepare_prompt(prompt, context, system_prompt)
                
                # Generate response based on active backend
                if self.backend_status["active_backend"] == "ollama":
                    response = self._generate_ollama_response(full_prompt)
                elif self.backend_status["active_backend"] == "lmstudio":
                    response = self._generate_lmstudio_response(full_prompt)
                else:
                    # Try to reconnect or fallback
                    if self._try_reconnect():
                        return self.generate_response(prompt, context, system_prompt)
                    else:
                        response = self._fallback_response(prompt)
                
                # Store in conversation history
                self._update_conversation_history(prompt, response)
                
                return response
                
            except Exception as e:
                self.logger.error(f"Failed to generate response: {e}")
                return self._fallback_response(prompt)
    
    def generate_streaming_response(self, prompt: str, context: str = None,
                                  system_prompt: str = None) -> Generator[str, None, None]:
        """Generate streaming response from the LLM."""
        try:
            full_prompt = self._prepare_prompt(prompt, context, system_prompt)
            
            if self.backend_status["active_backend"] == "ollama":
                yield from self._generate_ollama_streaming(full_prompt)
            elif self.backend_status["active_backend"] == "lmstudio":
                yield from self._generate_lmstudio_streaming(full_prompt)
            else:
                yield self._fallback_response(prompt)
                
        except Exception as e:
            self.logger.error(f"Failed to generate streaming response: {e}")
            yield self._fallback_response(prompt)
    
    def _prepare_prompt(self, prompt: str, context: str = None, 
                       system_prompt: str = None) -> str:
        """Prepare the full prompt with context and system instructions."""
        parts = []
        
        # Add system prompt
        if system_prompt:
            parts.append(f"System: {system_prompt}")
        else:
            parts.append("System: You are a helpful voice assistant. Provide concise, accurate responses.")
        
        # Add context if provided
        if context:
            parts.append(f"Context: {context}")
        
        # Add conversation history (last few exchanges)
        if self.conversation_history:
            parts.append("Recent conversation:")
            for exchange in self.conversation_history[-3:]:  # Last 3 exchanges
                parts.append(f"User: {exchange['user']}")
                parts.append(f"Assistant: {exchange['assistant']}")
        
        # Add current prompt
        parts.append(f"User: {prompt}")
        parts.append("Assistant:")
        
        return "\n".join(parts)
    
    def _generate_ollama_response(self, prompt: str) -> str:
        """Generate response using Ollama."""
        try:
            if OLLAMA_AVAILABLE:
                # Use ollama package
                response = ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    }
                )
                return response["response"].strip()
            else:
                # Use API directly
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens,
                        }
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()["response"].strip()
                else:
                    raise Exception(f"Ollama API error: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Ollama generation failed: {e}")
            raise
    
    def _generate_lmstudio_response(self, prompt: str) -> str:
        """Generate response using LMStudio."""
        try:
            response = requests.post(
                f"{self.lmstudio_url}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                raise Exception(f"LMStudio API error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"LMStudio generation failed: {e}")
            raise
    
    def _generate_ollama_streaming(self, prompt: str) -> Generator[str, None, None]:
        """Generate streaming response using Ollama."""
        try:
            if OLLAMA_AVAILABLE:
                # Use ollama package for streaming
                stream = ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    stream=True,
                    options={
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    }
                )
                
                for chunk in stream:
                    if "response" in chunk:
                        yield chunk["response"]
            else:
                # Use API for streaming
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens,
                        }
                    },
                    stream=True,
                    timeout=30
                )
                
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            self.logger.error(f"Ollama streaming failed: {e}")
            yield self._fallback_response(prompt)
    
    def _generate_lmstudio_streaming(self, prompt: str) -> Generator[str, None, None]:
        """Generate streaming response using LMStudio."""
        try:
            response = requests.post(
                f"{self.lmstudio_url}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "stream": True
                },
                stream=True,
                timeout=30
            )
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if "choices" in data and data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            self.logger.error(f"LMStudio streaming failed: {e}")
            yield self._fallback_response(prompt)
    
    def _update_conversation_history(self, user_input: str, assistant_response: str):
        """Update conversation history."""
        self.conversation_history.append({
            "user": user_input,
            "assistant": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only recent history
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def _try_reconnect(self) -> bool:
        """Try to reconnect to backends."""
        self.logger.info("Attempting to reconnect to LLM backends...")
        
        # Try Ollama first
        if self._test_ollama_connection():
            return True
        
        # Try LMStudio
        if self._test_lmstudio_connection():
            return True
        
        self.logger.error("Failed to connect to any LLM backend")
        return False
    
    def _fallback_response(self, prompt: str) -> str:
        """Generate fallback response when LLM is unavailable."""
        fallback_responses = {
            "greeting": "Hello! I'm having trouble connecting to my language model. How can I help you with basic tasks?",
            "math": "I can help with basic calculations even without my language model.",
            "time": "I can tell you the current time and date.",
            "system": "I can provide system information.",
            "default": "I'm sorry, I'm having trouble connecting to my language model right now. I can still help with basic tasks like math, time, and system information."
        }
        
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["hello", "hi", "hey"]):
            return fallback_responses["greeting"]
        elif any(word in prompt_lower for word in ["calculate", "math", "compute"]):
            return fallback_responses["math"]
        elif any(word in prompt_lower for word in ["time", "date", "clock"]):
            return fallback_responses["time"]
        elif any(word in prompt_lower for word in ["system", "computer", "memory"]):
            return fallback_responses["system"]
        else:
            return fallback_responses["default"]
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        models = []
        
        try:
            if self.backend_status["ollama"]:
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    ollama_models = response.json().get("models", [])
                    models.extend([model["name"] for model in ollama_models])
            
            if self.backend_status["lmstudio"]:
                response = requests.get(f"{self.lmstudio_url}/v1/models", timeout=5)
                if response.status_code == 200:
                    lmstudio_models = response.json().get("data", [])
                    models.extend([model["id"] for model in lmstudio_models])
                    
        except Exception as e:
            self.logger.error(f"Failed to get available models: {e}")
        
        return models
    
    def switch_model(self, model_name: str) -> bool:
        """Switch to a different model."""
        try:
            available_models = self.get_available_models()
            
            if model_name in available_models:
                self.model = model_name
                self.logger.info(f"Switched to model: {model_name}")
                return True
            else:
                self.logger.error(f"Model {model_name} not available. Available: {available_models}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to switch model: {e}")
            return False
    
    def get_backend_status(self) -> Dict[str, Any]:
        """Get current backend status."""
        return {
            "backend_status": self.backend_status,
            "current_model": self.model,
            "available_models": self.get_available_models(),
            "conversation_history_length": len(self.conversation_history),
            "configuration": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "context_window": self.context_window
            }
        }
    
    def clear_conversation_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.logger.info("Conversation history cleared")
    
    def set_generation_parameters(self, temperature: float = None, 
                                max_tokens: int = None) -> bool:
        """Update generation parameters."""
        try:
            if temperature is not None:
                if 0.0 <= temperature <= 2.0:
                    self.temperature = temperature
                else:
                    raise ValueError("Temperature must be between 0.0 and 2.0")
            
            if max_tokens is not None:
                if max_tokens > 0:
                    self.max_tokens = max_tokens
                else:
                    raise ValueError("Max tokens must be positive")
            
            self.logger.info(f"Updated generation parameters: temp={self.temperature}, max_tokens={self.max_tokens}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set generation parameters: {e}")
            return False
