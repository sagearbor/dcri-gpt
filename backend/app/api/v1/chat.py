import json
import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.models.bot import CustomBot, BotPermission, PermissionLevel
from app.models.usage import TokenUsageLog
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionRead,
    ChatSessionWithMessages
)
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)
router = APIRouter()


def generate_session_title(first_message: str) -> str:
    words = first_message.split()[:8]
    title = " ".join(words)
    if len(first_message) > len(title):
        title += "..."
    return title


def check_bot_access(bot: CustomBot, user: User, db: Session) -> bool:
    """Check if user has access to use a bot for chatting"""
    # Owner has all permissions
    if bot.user_id == user.id:
        return True
    
    # Public bots are accessible to all
    if bot.is_public:
        return True
    
    # Check explicit permissions (need at least CHAT permission)
    permission = db.query(BotPermission).filter(
        BotPermission.bot_id == bot.id,
        BotPermission.user_id == user.id
    ).first()
    
    if permission and permission.permission_level in [PermissionLevel.CHAT, PermissionLevel.EDIT]:
        return True
    
    return False


async def save_message_to_db(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    token_count: Optional[int] = None
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        role=MessageRole(role),
        content=content,
        token_count=token_count
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


async def save_token_usage(
    db: Session,
    user_id: int,
    session_id: int,
    bot_id: Optional[int],
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float
):
    usage_log = TokenUsageLog(
        user_id=user_id,
        session_id=session_id,
        bot_id=bot_id,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost=cost
    )
    db.add(usage_log)
    db.commit()


async def stream_chat_response(
    llm_gateway: LLMGateway,
    messages: List[dict],
    session: ChatSession,
    user_message: str,
    db: Session,
    background_tasks: BackgroundTasks
):
    try:
        full_response = ""
        prompt_tokens = llm_gateway.count_messages_tokens(messages)
        
        async for chunk in llm_gateway.get_streaming_completion(messages):
            full_response += chunk
            response_data = {
                "session_id": session.id,
                "content": chunk,
                "is_complete": False
            }
            yield f"data: {json.dumps(response_data)}\n\n"
        
        completion_tokens = llm_gateway.count_tokens(full_response)
        total_tokens = prompt_tokens + completion_tokens
        cost = llm_gateway.estimate_cost(prompt_tokens, completion_tokens)
        
        background_tasks.add_task(
            save_message_to_db,
            db,
            session.id,
            "user",
            user_message,
            llm_gateway.count_tokens(user_message)
        )
        
        background_tasks.add_task(
            save_message_to_db,
            db,
            session.id,
            "assistant",
            full_response,
            completion_tokens
        )
        
        background_tasks.add_task(
            save_token_usage,
            db,
            session.user_id,
            session.id,
            session.bot_id,
            llm_gateway.model_name,
            prompt_tokens,
            completion_tokens,
            cost
        )
        
        final_response = {
            "session_id": session.id,
            "content": "",
            "is_complete": True,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost": cost
            }
        }
        yield f"data: {json.dumps(final_response)}\n\n"
        
    except Exception as e:
        logger.error(f"Error in stream_chat_response: {e}")
        error_response = {
            "session_id": session.id if session else None,
            "content": f"Error: {str(e)}",
            "is_complete": True,
            "error": True
        }
        yield f"data: {json.dumps(error_response)}\n\n"


@router.post("/chat")
async def chat(
    request: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> StreamingResponse:
    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
    else:
        # If creating a new session with a bot, check access
        if request.bot_id:
            bot = db.query(CustomBot).filter(CustomBot.id == request.bot_id).first()
            if not bot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bot not found"
                )
            
            if not check_bot_access(bot, current_user, db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to use this bot"
                )
        
        session = ChatSession(
            user_id=current_user.id,
            bot_id=request.bot_id,
            title=generate_session_title(request.content)
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    
    model_name = "gpt-4o-mini"
    system_prompt = "You are a helpful AI assistant."
    
    if session.bot_id:
        bot = db.query(CustomBot).filter(CustomBot.id == session.bot_id).first()
        if bot:
            model_name = bot.model_name
            system_prompt = bot.system_prompt
    
    messages = [{"role": "system", "content": system_prompt}]
    
    if request.session_id:
        history = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.timestamp).all()
        
        for msg in history:
            messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
    
    messages.append({"role": "user", "content": request.content})
    
    llm_gateway = LLMGateway(model_name=model_name)
    
    return StreamingResponse(
        stream_chat_response(
            llm_gateway,
            messages,
            session,
            request.content,
            db,
            background_tasks
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sessions", response_model=List[ChatSessionRead])
def get_sessions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    sessions = db.query(
        ChatSession,
        func.count(ChatMessage.id).label("message_count")
    ).outerjoin(
        ChatMessage
    ).filter(
        ChatSession.user_id == current_user.id
    ).group_by(
        ChatSession.id
    ).order_by(
        ChatSession.updated_at.desc().nullslast(),
        ChatSession.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    result = []
    for session, message_count in sessions:
        session_dict = {
            "id": session.id,
            "user_id": session.user_id,
            "title": session.title,
            "bot_id": session.bot_id,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "message_count": message_count or 0
        }
        result.append(session_dict)
    
    return result


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp).all()
    
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "bot_id": session.bot_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": messages,
        "message_count": len(messages)
    }


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    db.delete(session)
    db.commit()