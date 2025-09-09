from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PermissionLevel(str, Enum):
    VIEW = "view"
    CHAT = "chat"
    EDIT = "edit"


class BotToolConfig(BaseModel):
    tool_name: str
    tool_config_json: Optional[dict] = None
    is_enabled: bool = True


class BotBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=1)
    model_name: str = Field(default="gpt-4")
    is_public: bool = False


class BotCreate(BotBase):
    tools: Optional[List[BotToolConfig]] = None


class BotUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    model_name: Optional[str] = None
    is_public: Optional[bool] = None
    tools: Optional[List[BotToolConfig]] = None


class BotPermissionBase(BaseModel):
    user_id: int
    permission_level: PermissionLevel = PermissionLevel.VIEW


class BotPermissionCreate(BotPermissionBase):
    pass


class BotPermissionRead(BotPermissionBase):
    id: int
    bot_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class BotToolRead(BaseModel):
    id: int
    tool_name: str
    tool_config_json: Optional[dict] = None
    is_enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class BotRead(BotBase):
    id: int
    user_id: int
    share_uuid: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[BotPermissionRead] = []
    tools: List[BotToolRead] = []
    
    class Config:
        from_attributes = True


class BotShareRequest(BaseModel):
    user_email: str = Field(..., description="Email of user to share with")
    permission_level: PermissionLevel = PermissionLevel.VIEW


class BotShareResponse(BaseModel):
    message: str
    permission: BotPermissionRead


class BotPublicToggleResponse(BaseModel):
    is_public: bool
    share_url: Optional[str] = None
    message: str