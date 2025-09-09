from typing import Any, Dict, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain_openai import AzureChatOpenAI
from app.tools.base import Tool, ToolResult, ToolExecutionError
from app.services.key_vault import get_key_vault_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class SQLTool(Tool):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="SQL_Query",
            description="Execute natural language queries against SQL databases. Can answer questions about data, generate reports, and analyze trends.",
            config=config
        )
        self.key_vault = get_key_vault_service()
        self.connection_string_alias = config.get("connection_string_alias", "sql_primary") if config else "sql_primary"
        self.read_only = config.get("read_only", True) if config else True
        self.max_results = config.get("max_results", 100) if config else 100
        self.engine: Optional[Engine] = None
        self.sql_agent = None
        self._initialize()
    
    def _initialize(self):
        try:
            connection_string = self.key_vault.get_connection_string(self.connection_string_alias)
            if not connection_string:
                connection_string = settings.SQL_CONNECTION_STRING
            
            if not connection_string:
                logger.warning("No SQL connection string found, SQL Tool will not be available")
                return
            
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )
            
            db = SQLDatabase(self.engine)
            
            llm = AzureChatOpenAI(
                deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                temperature=0
            )
            
            toolkit = SQLDatabaseToolkit(
                db=db,
                llm=llm,
                use_query_checker=True,
                max_rows_per_query=self.max_results
            )
            
            self.sql_agent = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                verbose=True,
                agent_type="openai-functions",
                handle_parsing_errors=True,
                max_iterations=3
            )
            
            logger.info(f"SQL Tool initialized with connection alias: {self.connection_string_alias}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQL Tool: {e}")
            self.engine = None
            self.sql_agent = None
    
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> ToolResult:
        if not self.sql_agent:
            return ToolResult(
                success=False,
                error="SQL Tool is not properly configured. Please check database connection settings."
            )
        
        try:
            if self.read_only and self._is_write_query(query):
                return ToolResult(
                    success=False,
                    error="This tool is configured as read-only. Write operations are not permitted."
                )
            
            prompt = self._build_prompt(query, context)
            
            result = await self.sql_agent.ainvoke({"input": prompt})
            
            output = result.get("output", "")
            
            return ToolResult(
                success=True,
                data=output,
                metadata={
                    "database": self.connection_string_alias,
                    "read_only": self.read_only,
                    "max_results": self.max_results
                }
            )
            
        except Exception as e:
            logger.error(f"SQL Tool execution error: {e}")
            return ToolResult(
                success=False,
                error=f"Failed to execute SQL query: {str(e)}"
            )
    
    def _is_write_query(self, query: str) -> bool:
        write_keywords = [
            "insert", "update", "delete", "drop", "create", "alter",
            "truncate", "grant", "revoke", "exec", "execute"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in write_keywords)
    
    def _build_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        prompt = query
        
        if context:
            if "previous_results" in context:
                prompt = f"Previous context: {context['previous_results']}\n\nNew query: {query}"
            
            if "user_role" in context:
                prompt += f"\n\nNote: User has role '{context['user_role']}'"
        
        prompt += "\n\nPlease provide a clear and concise answer. If showing data, format it as a table when appropriate."
        
        return prompt
    
    def validate_config(self) -> bool:
        if not self.connection_string_alias:
            logger.error("SQL Tool: connection_string_alias is required")
            return False
        
        if self.engine is None:
            logger.error("SQL Tool: Database engine not initialized")
            return False
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"SQL Tool config validation failed: {e}")
            return False
    
    def get_schema(self) -> Dict[str, Any]:
        schema = super().get_schema()
        schema["parameters"]["properties"]["context"] = {
            "type": "object",
            "description": "Optional context for the query",
            "properties": {
                "previous_results": {"type": "string"},
                "user_role": {"type": "string"}
            }
        }
        return schema