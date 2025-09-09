from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import DateTime
import enum
import uuid

from app.core.database import Base


class PermissionLevel(str, enum.Enum):
    VIEW = "view"
    CHAT = "chat"
    EDIT = "edit"


class CustomBot(Base):
    __tablename__ = "custom_bots"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    model_name = Column(String, nullable=False, default="gpt-4")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    share_uuid = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="custom_bots")
    permissions = relationship("BotPermission", back_populates="bot", cascade="all, delete-orphan")
    tools = relationship("BotTool", back_populates="bot", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="bot", cascade="all, delete-orphan")


class BotPermission(Base):
    __tablename__ = "bot_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("custom_bots.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission_level = Column(Enum(PermissionLevel), nullable=False, default=PermissionLevel.VIEW)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bot = relationship("CustomBot", back_populates="permissions")
    user = relationship("User", back_populates="bot_permissions")


class BotTool(Base):
    __tablename__ = "bot_tools"
    
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("custom_bots.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    tool_config_json = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bot = relationship("CustomBot", back_populates="tools")