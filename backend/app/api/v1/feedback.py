from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.chat import ChatMessage
from app.models.feedback import MessageFeedback
from app.schemas.feedback import (
    MessageFeedbackCreate,
    MessageFeedbackUpdate,
    MessageFeedbackRead,
    FeedbackSummary
)

router = APIRouter(prefix="/messages", tags=["feedback"])


@router.post("/{message_id}/feedback", response_model=MessageFeedbackRead)
async def submit_feedback(
    message_id: int,
    feedback: MessageFeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a message.
    
    Rating should be:
    - 1 for thumbs up (positive feedback)
    - -1 for thumbs down (negative feedback)
    """
    # Check if message exists and belongs to user's session
    message = db.query(ChatMessage).filter(
        ChatMessage.id == message_id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify the message belongs to a session owned by the user
    from app.models.chat import ChatSession
    session = db.query(ChatSession).filter(
        ChatSession.id == message.session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to provide feedback for this message"
        )
    
    # Check if feedback already exists
    existing_feedback = db.query(MessageFeedback).filter(
        MessageFeedback.message_id == message_id
    ).first()
    
    if existing_feedback:
        # Update existing feedback
        existing_feedback.rating = feedback.rating
        if feedback.comment is not None:
            existing_feedback.comment = feedback.comment
        db.commit()
        db.refresh(existing_feedback)
        return existing_feedback
    
    # Create new feedback
    new_feedback = MessageFeedback(
        message_id=message_id,
        user_id=current_user.id,
        rating=feedback.rating,
        comment=feedback.comment
    )
    
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    
    return new_feedback


@router.patch("/{message_id}/feedback", response_model=MessageFeedbackRead)
async def update_feedback(
    message_id: int,
    feedback: MessageFeedbackUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update existing feedback for a message.
    """
    # Get existing feedback
    existing_feedback = db.query(MessageFeedback).filter(
        MessageFeedback.message_id == message_id,
        MessageFeedback.user_id == current_user.id
    ).first()
    
    if not existing_feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found for this message"
        )
    
    # Update fields
    if feedback.rating is not None:
        existing_feedback.rating = feedback.rating
    if feedback.comment is not None:
        existing_feedback.comment = feedback.comment
    
    db.commit()
    db.refresh(existing_feedback)
    
    return existing_feedback


@router.delete("/{message_id}/feedback")
async def delete_feedback(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete feedback for a message.
    """
    feedback = db.query(MessageFeedback).filter(
        MessageFeedback.message_id == message_id,
        MessageFeedback.user_id == current_user.id
    ).first()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found for this message"
        )
    
    db.delete(feedback)
    db.commit()
    
    return {"detail": "Feedback deleted successfully"}


@router.get("/feedback/summary", response_model=FeedbackSummary)
async def get_feedback_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get feedback summary for the current user's messages.
    """
    from sqlalchemy import func
    from app.models.chat import ChatSession
    
    # Get all feedback for user's messages
    feedback_query = db.query(MessageFeedback).join(
        ChatMessage, MessageFeedback.message_id == ChatMessage.id
    ).join(
        ChatSession, ChatMessage.session_id == ChatSession.id
    ).filter(
        ChatSession.user_id == current_user.id
    )
    
    total_feedback = feedback_query.count()
    positive_count = feedback_query.filter(MessageFeedback.rating == 1).count()
    negative_count = feedback_query.filter(MessageFeedback.rating == -1).count()
    
    # Get recent feedback
    recent_feedback = feedback_query.order_by(
        MessageFeedback.created_at.desc()
    ).limit(10).all()
    
    positive_percentage = (positive_count / total_feedback * 100) if total_feedback > 0 else 0
    negative_percentage = (negative_count / total_feedback * 100) if total_feedback > 0 else 0
    
    return FeedbackSummary(
        total_feedback=total_feedback,
        positive_count=positive_count,
        negative_count=negative_count,
        positive_percentage=round(positive_percentage, 2),
        negative_percentage=round(negative_percentage, 2),
        recent_feedback=recent_feedback
    )