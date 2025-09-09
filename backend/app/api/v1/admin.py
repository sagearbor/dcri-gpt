from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.feedback import MessageFeedback
from app.services.usage_tracking import UsageTrackingService

router = APIRouter(prefix="/admin", tags=["admin"])


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check if current user is admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@router.get("/usage/overview")
async def get_system_usage_overview(
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get system-wide usage overview (admin only).
    
    Returns:
    - Total tokens and cost across all users
    - Number of active users
    - Top users by usage
    - Usage breakdown by model
    - Daily usage trend
    """
    return UsageTrackingService.get_system_usage_overview(db=db, days=days)


@router.get("/users")
async def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    List all users in the system (admin only).
    
    Returns paginated list of users with their details.
    """
    from sqlalchemy import func
    from app.models.chat import ChatSession
    from app.models.usage import TokenUsageLog
    
    users = db.query(
        User,
        func.count(func.distinct(ChatSession.id)).label("session_count"),
        func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
        func.sum(TokenUsageLog.cost).label("total_cost")
    ).outerjoin(
        ChatSession, User.id == ChatSession.user_id
    ).outerjoin(
        TokenUsageLog, User.id == TokenUsageLog.user_id
    ).group_by(
        User.id
    ).offset(skip).limit(limit).all()
    
    result = []
    for user, session_count, total_tokens, total_cost in users:
        result.append({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "session_count": session_count or 0,
            "total_tokens": int(total_tokens or 0),
            "total_cost": float(total_cost or 0)
        })
    
    return result


@router.get("/feedback")
async def get_all_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    rating_filter: int = Query(None, description="Filter by rating (1 or -1)"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    View all user-submitted feedback (admin only).
    
    Returns paginated list of feedback with associated message and user info.
    """
    from app.models.chat import ChatMessage, ChatSession
    
    query = db.query(
        MessageFeedback,
        ChatMessage,
        User,
        ChatSession
    ).join(
        ChatMessage, MessageFeedback.message_id == ChatMessage.id
    ).join(
        User, MessageFeedback.user_id == User.id
    ).join(
        ChatSession, ChatMessage.session_id == ChatSession.id
    )
    
    if rating_filter:
        query = query.filter(MessageFeedback.rating == rating_filter)
    
    total = query.count()
    
    feedback_items = query.order_by(
        MessageFeedback.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    result = []
    for feedback, message, user, session in feedback_items:
        result.append({
            "id": feedback.id,
            "rating": feedback.rating,
            "comment": feedback.comment,
            "created_at": feedback.created_at,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username
            },
            "message": {
                "id": message.id,
                "content": message.content[:200] + "..." if len(message.content) > 200 else message.content,
                "role": message.role.value,
                "timestamp": message.timestamp
            },
            "session": {
                "id": session.id,
                "title": session.title
            }
        })
    
    # Calculate feedback statistics
    positive_count = db.query(MessageFeedback).filter(MessageFeedback.rating == 1).count()
    negative_count = db.query(MessageFeedback).filter(MessageFeedback.rating == -1).count()
    total_feedback = positive_count + negative_count
    
    return {
        "total": total,
        "items": result,
        "statistics": {
            "total_feedback": total_feedback,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "positive_percentage": round((positive_count / total_feedback * 100) if total_feedback > 0 else 0, 2),
            "negative_percentage": round((negative_count / total_feedback * 100) if total_feedback > 0 else 0, 2)
        }
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Enable or disable a user account (admin only).
    """
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own admin status"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "message": f"User {'activated' if is_active else 'deactivated'} successfully"
    }


@router.get("/stats/summary")
async def get_platform_statistics(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get high-level platform statistics (admin only).
    """
    from sqlalchemy import func
    from app.models.chat import ChatSession, ChatMessage
    from app.models.bot import CustomBot
    from app.models.usage import TokenUsageLog
    
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    total_sessions = db.query(func.count(ChatSession.id)).scalar()
    total_messages = db.query(func.count(ChatMessage.id)).scalar()
    total_bots = db.query(func.count(CustomBot.id)).scalar()
    public_bots = db.query(func.count(CustomBot.id)).filter(CustomBot.is_public == True).scalar()
    
    usage_stats = db.query(
        func.sum(TokenUsageLog.total_tokens),
        func.sum(TokenUsageLog.cost),
        func.count(func.distinct(TokenUsageLog.model_name))
    ).first()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users
        },
        "chat": {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_messages_per_session": round(total_messages / total_sessions if total_sessions > 0 else 0, 2)
        },
        "bots": {
            "total": total_bots,
            "public": public_bots,
            "private": total_bots - public_bots
        },
        "usage": {
            "total_tokens": int(usage_stats[0] or 0),
            "total_cost": float(usage_stats[1] or 0),
            "models_used": int(usage_stats[2] or 0)
        }
    }