from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func, text
from typing import List, Optional, Any
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.models.bot import CustomBot
from app.schemas.search import (
    SearchQuery,
    SearchResult,
    MessageSearchResult,
    SessionSearchResult,
    SearchFilters
)

router = APIRouter()


@router.get("/search", response_model=SearchResult)
async def search_chat_history(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    search_type: str = Query("all", regex="^(all|messages|sessions)$", description="Type of search"),
    session_id: Optional[int] = Query(None, description="Filter by specific session"),
    bot_id: Optional[int] = Query(None, description="Filter by specific bot"),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Search through chat history with various filters.
    
    - **q**: Search query (searches in message content and session titles)
    - **search_type**: Type of search (all, messages, sessions)
    - **session_id**: Filter by specific session
    - **bot_id**: Filter by specific bot
    - **date_from/date_to**: Date range filters
    - **skip/limit**: Pagination
    """
    
    search_pattern = f"%{q}%"
    
    # Initialize results
    message_results = []
    session_results = []
    
    # Search in messages if requested
    if search_type in ["all", "messages"]:
        messages_query = db.query(ChatMessage).join(
            ChatSession, ChatMessage.session_id == ChatSession.id
        ).filter(
            ChatSession.user_id == current_user.id,
            ChatMessage.content.ilike(search_pattern)
        )
        
        # Apply filters
        if session_id:
            messages_query = messages_query.filter(ChatMessage.session_id == session_id)
        
        if bot_id:
            messages_query = messages_query.filter(ChatSession.bot_id == bot_id)
        
        if date_from:
            messages_query = messages_query.filter(ChatMessage.timestamp >= date_from)
        
        if date_to:
            messages_query = messages_query.filter(ChatMessage.timestamp <= date_to)
        
        # Execute query with pagination
        messages = messages_query.order_by(
            ChatMessage.timestamp.desc()
        ).offset(skip).limit(limit).all()
        
        # Format message results
        for msg in messages:
            session = db.query(ChatSession).filter(ChatSession.id == msg.session_id).first()
            message_results.append({
                "id": msg.id,
                "session_id": msg.session_id,
                "session_title": session.title if session else "Unknown Session",
                "content": msg.content,
                "role": msg.role.value,
                "timestamp": msg.timestamp,
                "match_snippet": _get_match_snippet(msg.content, q)
            })
    
    # Search in session titles if requested
    if search_type in ["all", "sessions"]:
        sessions_query = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id,
            ChatSession.title.ilike(search_pattern)
        )
        
        # Apply filters
        if bot_id:
            sessions_query = sessions_query.filter(ChatSession.bot_id == bot_id)
        
        if date_from:
            sessions_query = sessions_query.filter(ChatSession.created_at >= date_from)
        
        if date_to:
            sessions_query = sessions_query.filter(ChatSession.created_at <= date_to)
        
        # Execute query with pagination
        sessions = sessions_query.order_by(
            ChatSession.updated_at.desc().nullslast(),
            ChatSession.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        # Format session results
        for session in sessions:
            message_count = db.query(func.count(ChatMessage.id)).filter(
                ChatMessage.session_id == session.id
            ).scalar()
            
            last_message = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.timestamp.desc()).first()
            
            session_results.append({
                "id": session.id,
                "title": session.title,
                "bot_id": session.bot_id,
                "message_count": message_count or 0,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "last_message_at": last_message.timestamp if last_message else None,
                "match_snippet": _get_match_snippet(session.title, q)
            })
    
    # Get total counts for pagination
    total_messages = 0
    total_sessions = 0
    
    if search_type in ["all", "messages"]:
        total_messages = db.query(func.count(ChatMessage.id)).join(
            ChatSession, ChatMessage.session_id == ChatSession.id
        ).filter(
            ChatSession.user_id == current_user.id,
            ChatMessage.content.ilike(search_pattern)
        ).scalar() or 0
    
    if search_type in ["all", "sessions"]:
        total_sessions = db.query(func.count(ChatSession.id)).filter(
            ChatSession.user_id == current_user.id,
            ChatSession.title.ilike(search_pattern)
        ).scalar() or 0
    
    return {
        "query": q,
        "search_type": search_type,
        "messages": message_results,
        "sessions": session_results,
        "total_messages": total_messages,
        "total_sessions": total_sessions,
        "skip": skip,
        "limit": limit
    }


@router.get("/sessions/{session_id}/messages", response_model=List[MessageSearchResult])
async def get_session_messages(
    session_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role_filter: Optional[str] = Query(None, regex="^(user|assistant|system)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get paginated messages for a specific session.
    
    - **session_id**: ID of the session
    - **skip/limit**: Pagination
    - **role_filter**: Filter by message role (user, assistant, system)
    """
    
    # Verify session belongs to user
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    # Build query
    query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
    
    if role_filter:
        query = query.filter(ChatMessage.role == MessageRole(role_filter))
    
    # Get total count
    total_count = query.count()
    
    # Get messages with pagination
    messages = query.order_by(
        ChatMessage.timestamp
    ).offset(skip).limit(limit).all()
    
    # Format results
    results = []
    for msg in messages:
        results.append({
            "id": msg.id,
            "session_id": msg.session_id,
            "session_title": session.title,
            "content": msg.content,
            "role": msg.role.value,
            "timestamp": msg.timestamp,
            "token_count": msg.token_count
        })
    
    return results


@router.get("/advanced-search", response_model=SearchResult)
async def advanced_search(
    q: str = Query(..., min_length=1, max_length=500),
    use_fulltext: bool = Query(False, description="Use full-text search (PostgreSQL only)"),
    match_whole_words: bool = Query(False, description="Match whole words only"),
    case_sensitive: bool = Query(False, description="Case-sensitive search"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Advanced search with full-text capabilities (PostgreSQL/Azure SQL).
    Falls back to ILIKE for SQLite.
    """
    
    # Check database type
    db_url = str(db.bind.url)
    is_postgres = "postgresql" in db_url or "postgres" in db_url
    is_mssql = "mssql" in db_url or "sqlserver" in db_url
    
    message_results = []
    session_results = []
    
    if use_fulltext and is_postgres:
        # PostgreSQL full-text search
        # Create search vector
        search_query = func.plainto_tsquery('english', q)
        
        # Search messages
        messages = db.query(ChatMessage).join(
            ChatSession, ChatMessage.session_id == ChatSession.id
        ).filter(
            ChatSession.user_id == current_user.id,
            func.to_tsvector('english', ChatMessage.content).match(search_query)
        ).order_by(
            func.ts_rank(func.to_tsvector('english', ChatMessage.content), search_query).desc()
        ).offset(skip).limit(limit).all()
        
        # Search sessions
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id,
            func.to_tsvector('english', ChatSession.title).match(search_query)
        ).order_by(
            func.ts_rank(func.to_tsvector('english', ChatSession.title), search_query).desc()
        ).offset(skip).limit(limit).all()
        
    elif use_fulltext and is_mssql:
        # SQL Server full-text search
        # Note: Requires full-text catalog to be set up
        messages = db.query(ChatMessage).join(
            ChatSession, ChatMessage.session_id == ChatSession.id
        ).filter(
            ChatSession.user_id == current_user.id,
            text(f"CONTAINS(content, :query)")
        ).params(query=q).offset(skip).limit(limit).all()
        
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id,
            text(f"CONTAINS(title, :query)")
        ).params(query=q).offset(skip).limit(limit).all()
        
    else:
        # Fallback to ILIKE for SQLite or when full-text is not requested
        if match_whole_words:
            # Use word boundaries
            search_pattern = f"%\\b{q}\\b%"
        else:
            search_pattern = f"%{q}%"
        
        # Apply case sensitivity
        if case_sensitive:
            messages = db.query(ChatMessage).join(
                ChatSession, ChatMessage.session_id == ChatSession.id
            ).filter(
                ChatSession.user_id == current_user.id,
                ChatMessage.content.like(search_pattern)
            ).offset(skip).limit(limit).all()
            
            sessions = db.query(ChatSession).filter(
                ChatSession.user_id == current_user.id,
                ChatSession.title.like(search_pattern)
            ).offset(skip).limit(limit).all()
        else:
            messages = db.query(ChatMessage).join(
                ChatSession, ChatMessage.session_id == ChatSession.id
            ).filter(
                ChatSession.user_id == current_user.id,
                ChatMessage.content.ilike(search_pattern)
            ).offset(skip).limit(limit).all()
            
            sessions = db.query(ChatSession).filter(
                ChatSession.user_id == current_user.id,
                ChatSession.title.ilike(search_pattern)
            ).offset(skip).limit(limit).all()
    
    # Format results
    for msg in messages:
        session = db.query(ChatSession).filter(ChatSession.id == msg.session_id).first()
        message_results.append({
            "id": msg.id,
            "session_id": msg.session_id,
            "session_title": session.title if session else "Unknown Session",
            "content": msg.content,
            "role": msg.role.value,
            "timestamp": msg.timestamp,
            "match_snippet": _get_match_snippet(msg.content, q)
        })
    
    for session in sessions:
        message_count = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.session_id == session.id
        ).scalar()
        
        session_results.append({
            "id": session.id,
            "title": session.title,
            "bot_id": session.bot_id,
            "message_count": message_count or 0,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "match_snippet": _get_match_snippet(session.title, q)
        })
    
    return {
        "query": q,
        "search_type": "all",
        "messages": message_results,
        "sessions": session_results,
        "total_messages": len(message_results),
        "total_sessions": len(session_results),
        "skip": skip,
        "limit": limit,
        "search_method": "fulltext" if use_fulltext and (is_postgres or is_mssql) else "ilike"
    }


def _get_match_snippet(text: str, query: str, context_length: int = 50) -> str:
    """
    Extract a snippet of text around the matched query.
    """
    if not text or not query:
        return ""
    
    # Find the position of the query (case-insensitive)
    pos = text.lower().find(query.lower())
    
    if pos == -1:
        # If exact match not found, return beginning of text
        return text[:min(len(text), context_length * 2)] + ("..." if len(text) > context_length * 2 else "")
    
    # Calculate start and end positions for snippet
    start = max(0, pos - context_length)
    end = min(len(text), pos + len(query) + context_length)
    
    # Build snippet with ellipsis
    snippet = ""
    if start > 0:
        snippet += "..."
    snippet += text[start:end]
    if end < len(text):
        snippet += "..."
    
    return snippet