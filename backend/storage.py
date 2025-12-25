"""
Simple JSON-based storage for conversations.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import uuid
from .models import Conversation, ConversationMessage
from .config import CONVERSATIONS_DIR


class ConversationStorage:
    """Simple file-based storage for conversations."""

    def __init__(self, storage_dir: str = CONVERSATIONS_DIR):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _get_file_path(self, conversation_id: str) -> str:
        """Get file path for a conversation."""
        return os.path.join(self.storage_dir, f"{conversation_id}.json")

    def create_conversation(self) -> Conversation:
        """Create a new conversation."""
        conversation_id = str(uuid.uuid4())
        now = datetime.utcnow()

        conversation = Conversation(
            id=conversation_id,
            created_at=now,
            updated_at=now,
            messages=[]
        )

        self._save_conversation(conversation)
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        file_path = self._get_file_path(conversation_id)

        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r') as f:
            data = json.load(f)
            return Conversation(**data)

    def list_conversations(self) -> List[Conversation]:
        """List all conversations."""
        conversations = []

        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                conversation_id = filename[:-5]  # Remove .json
                conversation = self.get_conversation(conversation_id)
                if conversation:
                    conversations.append(conversation)

        # Sort by updated_at descending
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return conversations

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: Optional[str] = None,
        mode: Optional[str] = None,
        data: Optional[Dict] = None
    ) -> Optional[Conversation]:
        """Add a message to a conversation."""
        conversation = self.get_conversation(conversation_id)

        if not conversation:
            return None

        message = ConversationMessage(
            role=role,
            content=content,
            mode=mode,
            data=data,
            timestamp=datetime.utcnow()
        )

        conversation.messages.append(message)
        conversation.updated_at = datetime.utcnow()

        self._save_conversation(conversation)
        return conversation

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        file_path = self._get_file_path(conversation_id)

        if os.path.exists(file_path):
            os.remove(file_path)
            return True

        return False

    def _save_conversation(self, conversation: Conversation):
        """Save conversation to disk."""
        file_path = self._get_file_path(conversation.id)

        # Convert to dict for JSON serialization
        data = conversation.model_dump(mode='json')

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)


# Global storage instance
storage = ConversationStorage()
