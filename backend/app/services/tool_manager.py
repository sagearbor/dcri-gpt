from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import AzureChatOpenAI
from langchain.tools import Tool as LangchainTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from sqlalchemy.orm import Session
from app.models.bot import BotTool
from app.tools import SQLTool, SharePointRAGTool, BoxRAGTool
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class ToolManager:
    def __init__(self, bot_id: Optional[int] = None, db: Optional[Session] = None):
        self.bot_id = bot_id
        self.db = db
        self.tools = []
        self.agent_executor = None
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize tools based on bot configuration"""
        if not self.bot_id or not self.db:
            logger.info("No bot_id or database session, tools not initialized")
            return
        
        # Get tool configurations for this bot
        bot_tools = self.db.query(BotTool).filter(
            BotTool.bot_id == self.bot_id,
            BotTool.is_enabled == True
        ).all()
        
        for bot_tool in bot_tools:
            tool_instance = self._create_tool_instance(
                bot_tool.tool_name,
                bot_tool.tool_config_json
            )
            if tool_instance:
                self.tools.append(tool_instance)
                logger.info(f"Initialized tool: {bot_tool.tool_name}")
    
    def _create_tool_instance(self, tool_name: str, config: Dict[str, Any]):
        """Create a tool instance based on name and config"""
        try:
            if tool_name == "SQL_Query":
                return SQLTool(config)
            elif tool_name == "SharePoint_Search":
                return SharePointRAGTool(config)
            elif tool_name == "Box_Search":
                return BoxRAGTool(config)
            else:
                logger.warning(f"Unknown tool name: {tool_name}")
                return None
        except Exception as e:
            logger.error(f"Failed to create tool {tool_name}: {e}")
            return None
    
    def has_tools(self) -> bool:
        """Check if any tools are available"""
        return len(self.tools) > 0
    
    def get_langchain_tools(self) -> List[LangchainTool]:
        """Convert our tools to LangChain tools"""
        langchain_tools = []
        
        for tool in self.tools:
            langchain_tool = LangchainTool(
                name=tool.name,
                description=tool.description,
                func=lambda query, t=tool: self._execute_tool_sync(t, query),
                coroutine=lambda query, t=tool: t.execute(query)
            )
            langchain_tools.append(langchain_tool)
        
        return langchain_tools
    
    def _execute_tool_sync(self, tool, query: str):
        """Synchronous wrapper for tool execution"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, schedule the coroutine
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, tool.execute(query))
                    result = future.result()
            else:
                result = loop.run_until_complete(tool.execute(query))
            
            if result.success:
                return result.data
            else:
                return f"Error: {result.error}"
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Error executing tool: {str(e)}"
    
    def create_agent_executor(self, llm: Optional[AzureChatOpenAI] = None) -> AgentExecutor:
        """Create a LangChain agent executor with available tools"""
        if not self.has_tools():
            logger.info("No tools available, agent executor not created")
            return None
        
        if not llm:
            llm = AzureChatOpenAI(
                deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                temperature=0
            )
        
        langchain_tools = self.get_langchain_tools()
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant with access to various tools. Use them when appropriate to answer questions accurately."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create the agent
        agent = create_openai_functions_agent(
            llm=llm,
            tools=langchain_tools,
            prompt=prompt
        )
        
        # Create the agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=langchain_tools,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True,
            return_intermediate_steps=False
        )
        
        return self.agent_executor
    
    async def execute_with_tools(self, query: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """Execute a query using the agent with tools"""
        if not self.agent_executor:
            self.create_agent_executor()
        
        if not self.agent_executor:
            return {
                "output": "No tools are configured for this bot.",
                "tool_used": None
            }
        
        try:
            # Convert chat history to LangChain format
            langchain_history = []
            if chat_history:
                for msg in chat_history:
                    if msg["role"] == "user":
                        langchain_history.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        langchain_history.append(AIMessage(content=msg["content"]))
            
            # Execute with the agent
            result = await self.agent_executor.ainvoke({
                "input": query,
                "chat_history": langchain_history
            })
            
            # Extract tool usage information if available
            tool_used = None
            if "intermediate_steps" in result:
                for step in result["intermediate_steps"]:
                    if len(step) > 0 and hasattr(step[0], "tool"):
                        tool_used = step[0].tool
                        break
            
            return {
                "output": result.get("output", ""),
                "tool_used": tool_used,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error executing with tools: {e}")
            return {
                "output": f"An error occurred while processing your request: {str(e)}",
                "tool_used": None,
                "success": False
            }
    
    def get_available_tools_info(self) -> List[Dict[str, str]]:
        """Get information about available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools
        ]