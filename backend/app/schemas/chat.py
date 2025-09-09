from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[int] = None
    bot_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: Literal["user", "assistant", "system"]
    content: str
    token_count: Optional[int] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True


class ChatSessionBase(BaseModel):
    title: Optional[str] = None
    bot_id: Optional[int] = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionRead(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSessionRead):
    messages: List[ChatMessageResponse] = []


class StreamingChatResponse(BaseModel):
    session_id: int
    message_id: Optional[int] = None
    content: str
    is_complete: bool = False
    token_usage: Optional[dict] = None