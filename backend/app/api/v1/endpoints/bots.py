from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.bot import CustomBot, BotPermission, BotTool, PermissionLevel
from app.schemas.bot import (
    BotCreate, BotRead, BotUpdate, 
    BotShareRequest, BotShareResponse,
    BotPublicToggleResponse, BotPermissionCreate,
    BotToolConfig
)

router = APIRouter()


def check_bot_permission(
    bot: CustomBot,
    user: User,
    required_permission: PermissionLevel = PermissionLevel.VIEW
) -> bool:
    """Check if user has required permission for a bot"""
    # Owner has all permissions
    if bot.user_id == user.id:
        return True
    
    # Check if bot is public and user needs only VIEW permission
    if bot.is_public and required_permission == PermissionLevel.VIEW:
        return True
    
    # Check explicit permissions
    for perm in bot.permissions:
        if perm.user_id == user.id:
            # Check permission hierarchy: EDIT > CHAT > VIEW
            if required_permission == PermissionLevel.VIEW:
                return True
            elif required_permission == PermissionLevel.CHAT:
                return perm.permission_level in [PermissionLevel.CHAT, PermissionLevel.EDIT]
            elif required_permission == PermissionLevel.EDIT:
                return perm.permission_level == PermissionLevel.EDIT
    
    return False


@router.get("/", response_model=List[BotRead])
async def list_bots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    include_shared: bool = True,
    include_public: bool = True
):
    """List all bots accessible to the current user"""
    query = db.query(CustomBot).options(
        joinedload(CustomBot.permissions),
        joinedload(CustomBot.tools)
    )
    
    bots = []
    
    # Get user's own bots
    user_bots = query.filter(CustomBot.user_id == current_user.id).all()
    bots.extend(user_bots)
    
    if include_shared:
        # Get bots shared with the user
        shared_bots = query.join(BotPermission).filter(
            BotPermission.user_id == current_user.id
        ).all()
        bots.extend(shared_bots)
    
    if include_public:
        # Get public bots (excluding ones already in the list)
        bot_ids = [bot.id for bot in bots]
        public_bots = query.filter(
            CustomBot.is_public == True,
            ~CustomBot.id.in_(bot_ids) if bot_ids else True
        ).all()
        bots.extend(public_bots)
    
    return bots


@router.post("/", response_model=BotRead, status_code=status.HTTP_201_CREATED)
async def create_bot(
    bot: BotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new custom bot"""
    # Create the bot
    db_bot = CustomBot(
        name=bot.name,
        description=bot.description,
        system_prompt=bot.system_prompt,
        model_name=bot.model_name,
        is_public=bot.is_public,
        user_id=current_user.id,
        share_uuid=str(uuid.uuid4())
    )
    db.add(db_bot)
    db.flush()  # Get the bot ID
    
    # Add tools if provided
    if bot.tools:
        for tool_config in bot.tools:
            db_tool = BotTool(
                bot_id=db_bot.id,
                tool_name=tool_config.tool_name,
                tool_config_json=tool_config.tool_config_json,
                is_enabled=tool_config.is_enabled
            )
            db.add(db_tool)
    
    db.commit()
    db.refresh(db_bot)
    
    # Load relationships
    db_bot = db.query(CustomBot).options(
        joinedload(CustomBot.permissions),
        joinedload(CustomBot.tools)
    ).filter(CustomBot.id == db_bot.id).first()
    
    return db_bot


@router.get("/{bot_id}", response_model=BotRead)
async def get_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific bot by ID"""
    bot = db.query(CustomBot).options(
        joinedload(CustomBot.permissions),
        joinedload(CustomBot.tools)
    ).filter(CustomBot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Check if user has permission to view this bot
    if not check_bot_permission(bot, current_user, PermissionLevel.VIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this bot"
        )
    
    return bot


@router.get("/share/{share_uuid}", response_model=BotRead)
async def get_bot_by_share_uuid(
    share_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a bot by its share UUID (for public sharing)"""
    bot = db.query(CustomBot).options(
        joinedload(CustomBot.permissions),
        joinedload(CustomBot.tools)
    ).filter(CustomBot.share_uuid == share_uuid).first()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    if not bot.is_public and bot.user_id != current_user.id:
        # Check if user has explicit permission
        if not check_bot_permission(bot, current_user, PermissionLevel.VIEW):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This bot is not publicly shared"
            )
    
    return bot


@router.put("/{bot_id}", response_model=BotRead)
async def update_bot(
    bot_id: int,
    bot_update: BotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a bot (owner or EDIT permission required)"""
    bot = db.query(CustomBot).filter(CustomBot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Check if user has permission to edit this bot
    if bot.user_id != current_user.id:
        if not check_bot_permission(bot, current_user, PermissionLevel.EDIT):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this bot"
            )
    
    # Update bot fields
    update_data = bot_update.dict(exclude_unset=True, exclude={'tools'})
    for field, value in update_data.items():
        setattr(bot, field, value)
    
    # Update tools if provided
    if bot_update.tools is not None:
        # Remove existing tools
        db.query(BotTool).filter(BotTool.bot_id == bot_id).delete()
        
        # Add new tools
        for tool_config in bot_update.tools:
            db_tool = BotTool(
                bot_id=bot_id,
                tool_name=tool_config.tool_name,
                tool_config_json=tool_config.tool_config_json,
                is_enabled=tool_config.is_enabled
            )
            db.add(db_tool)
    
    db.commit()
    db.refresh(bot)
    
    # Load relationships
    bot = db.query(CustomBot).options(
        joinedload(CustomBot.permissions),
        joinedload(CustomBot.tools)
    ).filter(CustomBot.id == bot_id).first()
    
    return bot


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a bot (owner only)"""
    bot = db.query(CustomBot).filter(CustomBot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Only owner can delete
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the bot owner can delete it"
        )
    
    db.delete(bot)
    db.commit()


@router.post("/{bot_id}/share", response_model=BotShareResponse)
async def share_bot(
    bot_id: int,
    share_request: BotShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Share a bot with another user (owner only)"""
    bot = db.query(CustomBot).filter(CustomBot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Only owner can share
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the bot owner can share it"
        )
    
    # Find the user to share with
    target_user = db.query(User).filter(User.email == share_request.user_email).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if permission already exists
    existing_perm = db.query(BotPermission).filter(
        BotPermission.bot_id == bot_id,
        BotPermission.user_id == target_user.id
    ).first()
    
    if existing_perm:
        # Update existing permission
        existing_perm.permission_level = share_request.permission_level
        db.commit()
        db.refresh(existing_perm)
        permission = existing_perm
        message = f"Updated permission for {share_request.user_email}"
    else:
        # Create new permission
        permission = BotPermission(
            bot_id=bot_id,
            user_id=target_user.id,
            permission_level=share_request.permission_level
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)
        message = f"Bot shared with {share_request.user_email}"
    
    return BotShareResponse(
        message=message,
        permission=permission
    )


@router.delete("/{bot_id}/share/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unshare_bot(
    bot_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a user's permission to access a bot (owner only)"""
    bot = db.query(CustomBot).filter(CustomBot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Only owner can unshare
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the bot owner can manage sharing"
        )
    
    # Find and delete the permission
    permission = db.query(BotPermission).filter(
        BotPermission.bot_id == bot_id,
        BotPermission.user_id == user_id
    ).first()
    
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    db.delete(permission)
    db.commit()


@router.patch("/{bot_id}/public", response_model=BotPublicToggleResponse)
async def toggle_bot_public(
    bot_id: int,
    is_public: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle a bot's public status and generate share link (owner only)"""
    bot = db.query(CustomBot).filter(CustomBot.id == bot_id).first()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found"
        )
    
    # Only owner can change public status
    if bot.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the bot owner can change public status"
        )
    
    bot.is_public = is_public
    
    # Regenerate share UUID if making public
    if is_public and not bot.share_uuid:
        bot.share_uuid = str(uuid.uuid4())
    
    db.commit()
    db.refresh(bot)
    
    share_url = None
    if is_public:
        # In production, this would be the actual domain
        base_url = "http://localhost:5173"  # Frontend URL
        share_url = f"{base_url}/bot/share/{bot.share_uuid}"
    
    return BotPublicToggleResponse(
        is_public=bot.is_public,
        share_url=share_url,
        message=f"Bot is now {'public' if is_public else 'private'}"
    )