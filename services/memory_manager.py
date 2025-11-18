"""Memory manager for persistent conversation history."""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


class MemoryManager:
    """Manages conversation history and persistence."""
    
    def __init__(self, memory_path: str = "~/.lolo/memory.json", max_conversations: int = 50):
        """
        Initialize the memory manager.
        
        Args:
            memory_path: Path to the memory file (default: ~/.lolo/memory.json)
            max_conversations: Maximum number of conversations to store (default: 50)
        """
        self.memory_path = Path(memory_path).expanduser()
        self.max_conversations = max_conversations
        
        # Create memory directory if it doesn't exist
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_memory(self) -> Dict[str, Any]:
        """
        Load conversation memory from file.
        
        Returns:
            Dictionary containing conversation history and metadata
        """
        if not self.memory_path.exists():
            return {
                "conversations": [],
                "total_conversations": 0,
                "total_cost": 0.0,
                "last_updated": None
            }
        
        try:
            with open(self.memory_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # If file is corrupted, return empty memory
            print(f"Warning: Could not load memory file: {e}")
            return {
                "conversations": [],
                "total_conversations": 0,
                "total_cost": 0.0,
                "last_updated": None
            }
    
    def save_memory(self, memory: Dict[str, Any]) -> None:
        """
        Save conversation memory to file.
        
        Args:
            memory: Dictionary containing conversation history and metadata
        """
        memory["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.memory_path, 'w') as f:
                json.dump(memory, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save memory file: {e}")
    
    def add_conversation(self, memory: Dict[str, Any], conversation: Dict[str, Any]) -> None:
        """
        Add new conversation to memory.
        
        Args:
            memory: Dictionary containing conversation history
            conversation: New conversation to add
        """
        memory["conversations"].append(conversation)
        memory["total_conversations"] += 1
        memory["total_cost"] += conversation.get("cost", 0.0)
        
        # Cleanup old conversations if limit exceeded
        if len(memory["conversations"]) > self.max_conversations:
            memory["conversations"] = memory["conversations"][-self.max_conversations:]
        
        self.save_memory(memory)
    
    def clear_memory(self) -> None:
        """Clear all conversation history by deleting the memory file."""
        if self.memory_path.exists():
            try:
                self.memory_path.unlink()
            except IOError as e:
                print(f"Warning: Could not delete memory file: {e}")
    
    def get_context_messages(self, memory: Dict[str, Any], limit: int = 10) -> List[Dict[str, str]]:
        """
        Get recent conversations for context.
        
        Args:
            memory: Dictionary containing conversation history
            limit: Maximum number of conversations to include (default: 10)
        
        Returns:
            List of message dictionaries for API context
        """
        messages = []
        
        # Get last N conversations
        recent_conversations = memory["conversations"][-limit:]
        
        for conv in recent_conversations:
            # Add user question
            messages.append({
                "role": "user",
                "content": conv["question"]
            })
            
            # Add assistant response
            messages.append({
                "role": "assistant",
                "content": conv["response"]
            })
        
        return messages
