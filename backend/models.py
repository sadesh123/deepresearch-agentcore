"""
Pydantic models for API request/response.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ResearchRequest(BaseModel):
    """Request model for research questions."""
    question: str = Field(..., min_length=10, max_length=1000, description="Research question")
    mode: str = Field(..., description="Mode: 'council' or 'dxo'")


class CouncilResponse(BaseModel):
    """Response model for Council deliberation."""
    question: str
    stage1: List[Dict[str, Any]]
    stage2: List[Dict[str, Any]]
    stage3: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DxOResponse(BaseModel):
    """Response model for DxO research."""
    question: str
    workflow: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationMessage(BaseModel):
    """Single message in a conversation."""
    role: str  # 'user' or 'assistant'
    content: Optional[str] = None
    mode: Optional[str] = None  # 'council' or 'dxo'
    data: Optional[Dict[str, Any]] = None  # Full response data
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    """Conversation model."""
    id: str
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessage] = []


class ConversationCreate(BaseModel):
    """Request to create a new conversation."""
    initial_message: Optional[str] = None


class ConversationList(BaseModel):
    """List of conversations."""
    conversations: List[Conversation]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    aws_region: str
    bedrock_model: str
