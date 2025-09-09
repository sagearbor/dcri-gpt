from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import logging

from app.models.usage import TokenUsageLog
from app.models.user import User
from app.schemas.usage import TokenUsageCreate, UsageSummary, ModelUsageStats

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """Service for tracking and analyzing token usage."""
    
    @staticmethod
    async def log_usage(
        db: Session,
        user_id: int,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        session_id: Optional[int] = None,
        bot_id: Optional[int] = None
    ) -> TokenUsageLog:
        """
        Log token usage to the database.
        
        Args:
            db: Database session
            user_id: ID of the user
            model_name: Name of the model used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            cost: Calculated cost
            session_id: Optional chat session ID
            bot_id: Optional bot ID
            
        Returns:
            Created TokenUsageLog instance
        """
        try:
            usage_log = TokenUsageLog(
                user_id=user_id,
                bot_id=bot_id,
                session_id=session_id,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=cost
            )
            
            db.add(usage_log)
            db.commit()
            db.refresh(usage_log)
            
            logger.info(f"Logged usage for user {user_id}: {prompt_tokens + completion_tokens} tokens, ${cost}")
            return usage_log
            
        except Exception as e:
            logger.error(f"Error logging usage: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def get_user_usage_summary(
        db: Session,
        user_id: int,
        days: int = 30
    ) -> UsageSummary:
        """
        Get usage summary for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            days: Number of days to look back (default 30)
            
        Returns:
            UsageSummary with aggregated data
        """
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Total usage
        total_usage = db.query(
            func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
            func.sum(TokenUsageLog.cost).label("total_cost"),
            func.count(func.distinct(TokenUsageLog.session_id)).label("total_sessions")
        ).filter(
            and_(
                TokenUsageLog.user_id == user_id,
                TokenUsageLog.timestamp >= start_date
            )
        ).first()
        
        # Today's usage
        today_usage = db.query(
            func.sum(TokenUsageLog.total_tokens).label("tokens_today"),
            func.sum(TokenUsageLog.cost).label("cost_today")
        ).filter(
            and_(
                TokenUsageLog.user_id == user_id,
                TokenUsageLog.timestamp >= today_start
            )
        ).first()
        
        # This month's usage
        month_usage = db.query(
            func.sum(TokenUsageLog.total_tokens).label("tokens_this_month"),
            func.sum(TokenUsageLog.cost).label("cost_this_month")
        ).filter(
            and_(
                TokenUsageLog.user_id == user_id,
                TokenUsageLog.timestamp >= month_start
            )
        ).first()
        
        # Usage by model
        model_usage = db.query(
            TokenUsageLog.model_name,
            func.sum(TokenUsageLog.total_tokens).label("tokens"),
            func.sum(TokenUsageLog.cost).label("cost")
        ).filter(
            and_(
                TokenUsageLog.user_id == user_id,
                TokenUsageLog.timestamp >= start_date
            )
        ).group_by(TokenUsageLog.model_name).all()
        
        by_model = {}
        for model in model_usage:
            by_model[model.model_name] = {
                "tokens": float(model.tokens or 0),
                "cost": float(model.cost or 0)
            }
        
        return UsageSummary(
            total_tokens=int(total_usage.total_tokens or 0),
            total_cost=float(total_usage.total_cost or 0),
            total_sessions=int(total_usage.total_sessions or 0),
            tokens_today=int(today_usage.tokens_today or 0),
            cost_today=float(today_usage.cost_today or 0),
            tokens_this_month=int(month_usage.tokens_this_month or 0),
            cost_this_month=float(month_usage.cost_this_month or 0),
            by_model=by_model
        )
    
    @staticmethod
    def get_system_usage_overview(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get system-wide usage overview (admin only).
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            Dictionary with system-wide usage statistics
        """
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        # Total system usage
        total_usage = db.query(
            func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
            func.sum(TokenUsageLog.cost).label("total_cost"),
            func.count(func.distinct(TokenUsageLog.user_id)).label("active_users"),
            func.count(func.distinct(TokenUsageLog.session_id)).label("total_sessions")
        ).filter(
            TokenUsageLog.timestamp >= start_date
        ).first()
        
        # Top users by usage
        top_users = db.query(
            User.email,
            func.sum(TokenUsageLog.total_tokens).label("tokens"),
            func.sum(TokenUsageLog.cost).label("cost")
        ).join(
            User, User.id == TokenUsageLog.user_id
        ).filter(
            TokenUsageLog.timestamp >= start_date
        ).group_by(
            User.id, User.email
        ).order_by(
            func.sum(TokenUsageLog.cost).desc()
        ).limit(10).all()
        
        # Usage by model
        model_usage = db.query(
            TokenUsageLog.model_name,
            func.sum(TokenUsageLog.total_tokens).label("tokens"),
            func.sum(TokenUsageLog.cost).label("cost"),
            func.count(TokenUsageLog.id).label("count")
        ).filter(
            TokenUsageLog.timestamp >= start_date
        ).group_by(
            TokenUsageLog.model_name
        ).all()
        
        # Daily usage trend
        daily_usage = db.query(
            func.date(TokenUsageLog.timestamp).label("date"),
            func.sum(TokenUsageLog.total_tokens).label("tokens"),
            func.sum(TokenUsageLog.cost).label("cost")
        ).filter(
            TokenUsageLog.timestamp >= start_date
        ).group_by(
            func.date(TokenUsageLog.timestamp)
        ).order_by(
            func.date(TokenUsageLog.timestamp)
        ).all()
        
        return {
            "total_tokens": int(total_usage.total_tokens or 0),
            "total_cost": float(total_usage.total_cost or 0),
            "active_users": int(total_usage.active_users or 0),
            "total_sessions": int(total_usage.total_sessions or 0),
            "top_users": [
                {
                    "email": user.email,
                    "tokens": int(user.tokens),
                    "cost": float(user.cost)
                }
                for user in top_users
            ],
            "model_usage": [
                {
                    "model": model.model_name,
                    "tokens": int(model.tokens),
                    "cost": float(model.cost),
                    "count": int(model.count)
                }
                for model in model_usage
            ],
            "daily_trend": [
                {
                    "date": day.date.isoformat(),
                    "tokens": int(day.tokens),
                    "cost": float(day.cost)
                }
                for day in daily_usage
            ]
        }
    
    @staticmethod
    def get_model_usage_stats(
        db: Session,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> List[ModelUsageStats]:
        """
        Get detailed usage statistics by model.
        
        Args:
            db: Database session
            user_id: Optional user ID for user-specific stats
            days: Number of days to look back
            
        Returns:
            List of ModelUsageStats
        """
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        query = db.query(
            TokenUsageLog.model_name,
            func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
            func.sum(TokenUsageLog.cost).label("total_cost"),
            func.count(TokenUsageLog.id).label("usage_count"),
            func.avg(TokenUsageLog.total_tokens).label("avg_tokens")
        ).filter(
            TokenUsageLog.timestamp >= start_date
        )
        
        if user_id:
            query = query.filter(TokenUsageLog.user_id == user_id)
        
        model_stats = query.group_by(TokenUsageLog.model_name).all()
        
        # Calculate total for percentage
        total_tokens = sum(stat.total_tokens for stat in model_stats)
        
        results = []
        for stat in model_stats:
            percentage = (stat.total_tokens / total_tokens * 100) if total_tokens > 0 else 0
            results.append(
                ModelUsageStats(
                    model_name=stat.model_name,
                    total_tokens=int(stat.total_tokens),
                    total_cost=float(stat.total_cost),
                    usage_count=int(stat.usage_count),
                    average_tokens=float(stat.avg_tokens),
                    percentage_of_total=round(percentage, 2)
                )
            )
        
        return results