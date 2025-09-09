from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    custom_bots = relationship("CustomBot", back_populates="owner", cascade="all, delete-orphan")
    bot_permissions = relationship("BotPermission", back_populates="user", cascade="all, delete-orphan")
    token_usage_logs = relationship("TokenUsageLog", back_populates="user", cascade="all, delete-orphan")
    message_feedbacks = relationship("MessageFeedback", back_populates="user", cascade="all, delete-orphan")