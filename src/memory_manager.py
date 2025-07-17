"""
Advanced Memory Management System
Handles long-term conversation memory with vector embeddings and context-aware retrieval.
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

from  utils.config_loader import ConfigLoader


class MemoryManager:
    """Advanced memory management with vector embeddings and semantic search."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.config = ConfigLoader(config_path).get_config()
        self.memory_config = self.config.get("memory", {})
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(
            self.memory_config.get("embedding_model", "all-MiniLM-L6-v2")
        )
        
        # Initialize ChromaDB
        self._init_database()
        
        # Memory statistics
        self.stats = {
            "total_memories": 0,
            "conversations": 0,
            "last_cleanup": datetime.now()
        }
        
    def _init_database(self):
        """Initialize ChromaDB vector database."""
        try:
            db_path = Path(self.memory_config.get("database_path", "./embeddings/memory.db"))
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Configure ChromaDB
            self.chroma_client = chromadb.PersistentClient(
                path=str(db_path.parent),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collections
            self.conversations_collection = self.chroma_client.get_or_create_collection(
                name="conversations",
                metadata={"description": "User conversations and interactions"}
            )
            
            self.preferences_collection = self.chroma_client.get_or_create_collection(
                name="preferences",
                metadata={"description": "User preferences and learned behaviors"}
            )
            
            self.context_collection = self.chroma_client.get_or_create_collection(
                name="context",
                metadata={"description": "Contextual information and facts"}
            )
            
            self.logger.info("Memory database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def store_conversation(self, user_input: str, assistant_response: str, 
                          context: Dict[str, Any] = None) -> str:
        """Store a conversation exchange in memory."""
        with self._lock:
            try:
                conversation_id = f"conv_{datetime.now().isoformat()}_{hash(user_input) % 10000}"
                
                # Prepare conversation data
                conversation_text = f"User: {user_input}\nAssistant: {assistant_response}"
                
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "user_input": user_input,
                    "assistant_response": assistant_response,
                    "context": json.dumps(context or {}),
                    "type": "conversation"
                }
                
                # Generate embedding
                embedding = self.embedding_model.encode(conversation_text).tolist()
                
                # Store in ChromaDB
                self.conversations_collection.add(
                    embeddings=[embedding],
                    documents=[conversation_text],
                    metadatas=[metadata],
                    ids=[conversation_id]
                )
                
                self.stats["total_memories"] += 1
                self.stats["conversations"] += 1
                
                self.logger.debug(f"Stored conversation: {conversation_id}")
                return conversation_id
                
            except Exception as e:
                self.logger.error(f"Failed to store conversation: {e}")
                return None
    
    def store_preference(self, preference_type: str, preference_data: Dict[str, Any]) -> str:
        """Store user preference or learned behavior."""
        with self._lock:
            try:
                preference_id = f"pref_{preference_type}_{datetime.now().isoformat()}"
                
                # Create searchable text from preference data
                preference_text = f"{preference_type}: {json.dumps(preference_data)}"
                
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "preference_type": preference_type,
                    "data": json.dumps(preference_data),
                    "type": "preference"
                }
                
                # Generate embedding
                embedding = self.embedding_model.encode(preference_text).tolist()
                
                # Store in ChromaDB
                self.preferences_collection.add(
                    embeddings=[embedding],
                    documents=[preference_text],
                    metadatas=[metadata],
                    ids=[preference_id]
                )
                
                self.logger.debug(f"Stored preference: {preference_id}")
                return preference_id
                
            except Exception as e:
                self.logger.error(f"Failed to store preference: {e}")
                return None
    
    def retrieve_similar_conversations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve conversations similar to the query."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search similar conversations
            results = self.conversations_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            similar_conversations = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]
                    
                    # Only include if similarity is above threshold
                    similarity = 1 - distance  # Convert distance to similarity
                    threshold = self.memory_config.get("similarity_threshold", 0.7)
                    
                    if similarity >= threshold:
                        similar_conversations.append({
                            "document": doc,
                            "metadata": metadata,
                            "similarity": similarity,
                            "user_input": metadata.get("user_input", ""),
                            "assistant_response": metadata.get("assistant_response", ""),
                            "timestamp": metadata.get("timestamp", "")
                        })
            
            return similar_conversations
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve similar conversations: {e}")
            return []
    
    def retrieve_preferences(self, preference_type: str = None) -> List[Dict[str, Any]]:
        """Retrieve user preferences, optionally filtered by type."""
        try:
            # Query all preferences or filter by type
            if preference_type:
                # Use metadata filtering
                results = self.preferences_collection.get(
                    where={"preference_type": preference_type},
                    include=["documents", "metadatas"]
                )
            else:
                results = self.preferences_collection.get(
                    include=["documents", "metadatas"]
                )
            
            # Format results
            preferences = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    metadata = results["metadatas"][i]
                    preferences.append({
                        "document": doc,
                        "metadata": metadata,
                        "preference_type": metadata.get("preference_type", ""),
                        "data": json.loads(metadata.get("data", "{}")),
                        "timestamp": metadata.get("timestamp", "")
                    })
            
            return preferences
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve preferences: {e}")
            return []
    
    def get_conversation_context(self, query: str, max_context: int = 3) -> str:
        """Get relevant conversation context for the current query."""
        try:
            similar_conversations = self.retrieve_similar_conversations(query, max_context)
            
            if not similar_conversations:
                return ""
            
            context_parts = []
            for conv in similar_conversations:
                timestamp = conv.get("timestamp", "")
                user_input = conv.get("user_input", "")
                assistant_response = conv.get("assistant_response", "")
                
                context_parts.append(
                    f"Previous conversation ({timestamp}):\n"
                    f"User: {user_input}\n"
                    f"Assistant: {assistant_response}\n"
                )
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation context: {e}")
            return ""
    
    def learn_from_interaction(self, user_input: str, user_feedback: str = None):
        """Learn from user interactions and feedback."""
        try:
            # Analyze user input patterns
            if len(user_input.split()) > 10:  # Long queries
                self.store_preference("query_style", {"prefers_detailed": True})
            
            # Learn from feedback
            if user_feedback:
                if any(word in user_feedback.lower() for word in ["good", "great", "perfect", "thanks"]):
                    self.store_preference("positive_feedback", {"input": user_input, "feedback": user_feedback})
                elif any(word in user_feedback.lower() for word in ["wrong", "bad", "incorrect", "no"]):
                    self.store_preference("negative_feedback", {"input": user_input, "feedback": user_feedback})
            
        except Exception as e:
            self.logger.error(f"Failed to learn from interaction: {e}")
    
    def cleanup_old_memories(self, days_old: int = 30):
        """Clean up old memories to maintain performance."""
        with self._lock:
            try:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                cutoff_iso = cutoff_date.isoformat()
                
                # Get old conversations
                old_conversations = self.conversations_collection.get(
                    where={"timestamp": {"$lt": cutoff_iso}},
                    include=["metadatas"]
                )
                
                if old_conversations["ids"]:
                    # Delete old conversations
                    self.conversations_collection.delete(ids=old_conversations["ids"])
                    self.logger.info(f"Cleaned up {len(old_conversations['ids'])} old conversations")
                
                self.stats["last_cleanup"] = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Failed to cleanup old memories: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        try:
            conv_count = self.conversations_collection.count()
            pref_count = self.preferences_collection.count()
            
            self.stats.update({
                "total_conversations": conv_count,
                "total_preferences": pref_count,
                "database_size": self._get_database_size()
            })
            
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Failed to get memory stats: {e}")
            return self.stats
    
    def _get_database_size(self) -> str:
        """Get database size in human-readable format."""
        try:
            db_path = Path(self.memory_config.get("database_path", "./embeddings/memory.db"))
            if db_path.parent.exists():
                size_bytes = sum(f.stat().st_size for f in db_path.parent.rglob('*') if f.is_file())
                
                # Convert to human-readable format
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size_bytes < 1024.0:
                        return f"{size_bytes:.1f} {unit}"
                    size_bytes /= 1024.0
                return f"{size_bytes:.1f} TB"
            return "0 B"
            
        except Exception as e:
            self.logger.error(f"Failed to get database size: {e}")
            return "Unknown"
    
    def export_memories(self, output_path: str) -> bool:
        """Export memories to JSON file for backup."""
        try:
            # Get all conversations and preferences
            conversations = self.conversations_collection.get(include=["documents", "metadatas"])
            preferences = self.preferences_collection.get(include=["documents", "metadatas"])
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "conversations": {
                    "documents": conversations.get("documents", []),
                    "metadatas": conversations.get("metadatas", [])
                },
                "preferences": {
                    "documents": preferences.get("documents", []),
                    "metadatas": preferences.get("metadatas", [])
                },
                "stats": self.get_memory_stats()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Memories exported to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export memories: {e}")
            return False
    
    def reset_memory(self, confirm: bool = False) -> bool:
        """Reset all memories (use with caution)."""
        if not confirm:
            self.logger.warning("Memory reset requires confirmation")
            return False
        
        with self._lock:
            try:
                # Delete all collections
                self.chroma_client.delete_collection("conversations")
                self.chroma_client.delete_collection("preferences")
                self.chroma_client.delete_collection("context")
                
                # Recreate collections
                self._init_database()
                
                # Reset stats
                self.stats = {
                    "total_memories": 0,
                    "conversations": 0,
                    "last_cleanup": datetime.now()
                }
                
                self.logger.info("Memory system reset successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to reset memory: {e}")
                return False
