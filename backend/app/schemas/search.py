from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from enum import Enum


class SearchType(str, Enum):
    ALL = "all"
    MESSAGES = "messages"
    SESSIONS = "sessions"


class SearchFilters(BaseModel):
    session_id: Optional[int] = None
    bot_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    role_filter: Optional[str] = None


class MessageSearchResult(BaseModel):
    id: int
    session_id: int
    session_title: str
    content: str
    role: str
    timestamp: datetime
    token_count: Optional[int] = None
    match_snippet: Optional[str] = None
    
    class Config:
        from_attributes = True


class SessionSearchResult(BaseModel):
    id: int
    title: str
    bot_id: Optional[int] = None
    message_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    match_snippet: Optional[str] = None
    
    class Config:
        from_attributes = True


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    search_type: SearchType = SearchType.ALL
    filters: Optional[SearchFilters] = None
    use_fulltext: bool = False
    match_whole_words: bool = False
    case_sensitive: bool = False
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)


class SearchResult(BaseModel):
    query: str
    search_type: str
    messages: List[MessageSearchResult]
    sessions: List[SessionSearchResult]
    total_messages: int
    total_sessions: int
    skip: int
    limit: int
    search_method: Optional[str] = "ilike"
    
    class Config:
        from_attributes = True


class SearchSuggestion(BaseModel):
    """For autocomplete/suggestions"""
    text: str
    type: str  # "session", "message", "bot"
    relevance_score: Optional[float] = None
    

class SearchStats(BaseModel):
    """Statistics about search results"""
    total_results: int
    results_by_type: dict
    date_range: Optional[dict] = None
    most_relevant_session: Optional[SessionSearchResult] = None