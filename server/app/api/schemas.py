from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SessionCreateRequest(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=80)


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    # Number of context passages (each a hit plus its neighbouring chunks).
    top_k: int = Field(default=5, ge=1, le=20)


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    abstained: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SendMessageResponse(BaseModel):
    session_id: UUID
    user_message: MessageResponse
    assistant_message: MessageResponse
    retrieval_query: str | None = None
    needs_clarification: bool = False
