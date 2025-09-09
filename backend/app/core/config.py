from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import json


class Settings(BaseSettings):
    # Application
    APP_NAME: str = Field(default="DCRI GPT", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment (development, staging, production)")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./dcri_gpt.db", description="Database connection URL")
    
    # Security
    JWT_SECRET_KEY: str = Field(..., description="Secret key for JWT encoding")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRATION_MINUTES: int = Field(default=1440, description="JWT token expiration in minutes")
    
    # OpenAI/Azure OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    AZURE_OPENAI_API_KEY: Optional[str] = Field(default=None, description="Azure OpenAI API key")
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(default=None, description="Azure OpenAI endpoint")
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = Field(default=None, description="Azure OpenAI deployment name")
    AZURE_OPENAI_API_VERSION: str = Field(default="2023-12-01-preview", description="Azure OpenAI API version")
    
    # Azure Key Vault
    AZURE_KEY_VAULT_URL: Optional[str] = Field(default=None, description="Azure Key Vault URL")
    AZURE_CLIENT_ID: Optional[str] = Field(default=None, description="Azure client ID")
    AZURE_CLIENT_SECRET: Optional[str] = Field(default=None, description="Azure client secret")
    AZURE_TENANT_ID: Optional[str] = Field(default=None, description="Azure tenant ID")
    
    # Vector Store
    CHROMA_PERSIST_DIRECTORY: str = Field(default="./chroma_db", description="ChromaDB persistence directory")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:5173", "http://localhost:3000"], description="CORS allowed origins")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # SharePoint Integration
    SHAREPOINT_CLIENT_ID: Optional[str] = Field(default=None, description="SharePoint client ID")
    SHAREPOINT_CLIENT_SECRET: Optional[str] = Field(default=None, description="SharePoint client secret")
    SHAREPOINT_TENANT_ID: Optional[str] = Field(default=None, description="SharePoint tenant ID")
    
    # Box Integration
    BOX_CLIENT_ID: Optional[str] = Field(default=None, description="Box client ID")
    BOX_CLIENT_SECRET: Optional[str] = Field(default=None, description="Box client secret")
    BOX_ENTERPRISE_ID: Optional[str] = Field(default=None, description="Box enterprise ID")
    
    # SQL Server
    SQL_CONNECTION_STRING: Optional[str] = Field(default=None, description="SQL Server connection string")
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v
    
    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v):
        if v == "your-secret-key-change-this-in-production":
            raise ValueError("Please set a secure JWT_SECRET_KEY in your .env file")
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY should be at least 32 characters long")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()