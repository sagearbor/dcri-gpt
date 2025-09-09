from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.usage import UsageSummary, ModelUsageStats
from app.services.usage_tracking import UsageTrackingService

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/summary", response_model=UsageSummary)
async def get_usage_summary(
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage summary for the current user.
    
    Returns aggregated usage data including:
    - Total tokens and cost
    - Today's usage
    - This month's usage
    - Usage breakdown by model
    """
    return UsageTrackingService.get_user_usage_summary(
        db=db,
        user_id=current_user.id,
        days=days
    )


@router.get("/models", response_model=List[ModelUsageStats])
async def get_model_usage_stats(
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed usage statistics by model for the current user.
    
    Returns stats for each model including:
    - Total tokens and cost
    - Usage count
    - Average tokens per use
    - Percentage of total usage
    """
    return UsageTrackingService.get_model_usage_stats(
        db=db,
        user_id=current_user.id,
        days=days
    )


@router.get("/history")
async def get_usage_history(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed usage history for the current user.
    
    Returns a paginated list of all token usage logs.
    """
    from app.models.usage import TokenUsageLog
    
    logs = db.query(TokenUsageLog).filter(
        TokenUsageLog.user_id == current_user.id
    ).order_by(
        TokenUsageLog.timestamp.desc()
    ).offset(offset).limit(limit).all()
    
    total = db.query(TokenUsageLog).filter(
        TokenUsageLog.user_id == current_user.id
    ).count()
    
    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "model_name": log.model_name,
                "prompt_tokens": log.prompt_tokens,
                "completion_tokens": log.completion_tokens,
                "total_tokens": log.total_tokens,
                "cost": log.cost,
                "timestamp": log.timestamp,
                "session_id": log.session_id,
                "bot_id": log.bot_id
            }
            for log in logs
        ]
    }