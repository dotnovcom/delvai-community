from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=256)
    interaction_type: Literal["text", "voice", "video"] = "text"


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    interaction_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content_type: str
    content: str
    tokens_used: int
    ai_engine: Optional[str] = None
    metadata: Optional[dict[str, Any]] = Field(None, validation_alias="metadata_")
    my_feedback: Optional[Literal["like", "dislike"]] = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class TranscriptRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)
    title: Optional[str] = Field(None, max_length=256)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    content_type: Literal["text", "image", "file"] = "text"
    image_url: Optional[str] = None
    file_name: Optional[str] = None
    file_url: Optional[str] = None
    deep_think: bool = True
    online_search: bool = True


class FeedbackRequest(BaseModel):
    vote: Literal["like", "dislike", "none"]


class RegenerateRequest(BaseModel):
    deep_think: bool = False
    online_search: bool = False


class FeedbackRequest(BaseModel):
    vote: Literal["like", "dislike", "none"]


class RegenerateRequest(BaseModel):
    deep_think: bool = False
    online_search: bool = False


class ChatStreamRequest(BaseModel):
    conversation_id: int
    content: str = Field(..., min_length=1, max_length=10000)
    content_type: Literal["text", "image", "file"] = "text"
    image_url: Optional[str] = None
    file_name: Optional[str] = None
    file_url: Optional[str] = None
