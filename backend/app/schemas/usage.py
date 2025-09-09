from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List


class TokenUsageCreate(BaseModel):
    user_id: int
    bot_id: Optional[int] = None
    session_id: Optional[int] = None
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: Optional[float] = None


class TokenUsageRead(BaseModel):
    id: int
    user_id: int
    bot_id: Optional[int] = None
    session_id: Optional[int] = None
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: Optional[float] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class UsageSummary(BaseModel):
    total_tokens: int
    total_cost: float
    total_sessions: int
    tokens_today: int
    cost_today: float
    tokens_this_month: int
    cost_this_month: float
    by_model: Dict[str, Dict[str, float]]  # model_name -> {tokens, cost}


class UsageByPeriod(BaseModel):
    period: str  # 'day', 'week', 'month'
    start_date: datetime
    end_date: datetime
    total_tokens: int
    total_cost: float
    sessions_count: int
    average_tokens_per_session: float


class ModelUsageStats(BaseModel):
    model_name: str
    total_tokens: int
    total_cost: float
    usage_count: int
    average_tokens: float
    percentage_of_total: float