from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class MessageFeedbackCreate(BaseModel):
    rating: int = Field(..., description="1 for thumbs up, -1 for thumbs down")
    comment: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v not in [-1, 1]:
            raise ValueError('Rating must be 1 (thumbs up) or -1 (thumbs down)')
        return v


class MessageFeedbackUpdate(BaseModel):
    rating: Optional[int] = Field(None, description="1 for thumbs up, -1 for thumbs down")
    comment: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v is not None and v not in [-1, 1]:
            raise ValueError('Rating must be 1 (thumbs up) or -1 (thumbs down)')
        return v


class MessageFeedbackRead(BaseModel):
    id: int
    message_id: int
    user_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackSummary(BaseModel):
    total_feedback: int
    positive_count: int
    negative_count: int
    positive_percentage: float
    negative_percentage: float
    recent_feedback: list[MessageFeedbackRead]