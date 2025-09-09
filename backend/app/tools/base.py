from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolExecutionError(Exception):
    pass


class Tool(ABC):
    def __init__(self, name: str, description: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> ToolResult:
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query or command to execute"
                    }
                },
                "required": ["query"]
            }
        }
    
    def format_for_langchain(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "func": self.execute,
            "return_direct": False
        }