import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.tools.base import Tool, ToolResult, ToolExecutionError
from app.tools.sql_tool import SQLTool
from app.tools.sharepoint_tool import SharePointRAGTool
from app.tools.box_tool import BoxRAGTool
from app.services.key_vault import KeyVaultService
from app.services.tool_manager import ToolManager


class TestToolBase:
    def test_tool_result_model(self):
        result = ToolResult(success=True, data="test data", metadata={"key": "value"})
        assert result.success is True
        assert result.data == "test data"
        assert result.metadata["key"] == "value"
    
    def test_tool_result_error(self):
        result = ToolResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None


class TestKeyVaultService:
    def test_key_vault_development_mode(self):
        with patch.dict('os.environ', {'ENVIRONMENT': 'development', 'TEST_SECRET': 'test_value'}):
            kv_service = KeyVaultService()
            secret = kv_service.get_secret('test-secret')
            assert secret == 'test_value'
    
    def test_key_vault_connection_string_mapping(self):
        with patch.dict('os.environ', {'SQL_CONNECTION_STRING': 'mssql://test'}):
            kv_service = KeyVaultService()
            conn_str = kv_service.get_connection_string('sql_primary')
            assert conn_str == 'mssql://test'
    
    def test_key_vault_api_key_mapping(self):
        with patch.dict('os.environ', {'AZURE_OPENAI_API_KEY': 'test_key'}):
            kv_service = KeyVaultService()
            api_key = kv_service.get_api_key('azure_openai')
            assert api_key == 'test_key'


class TestSQLTool:
    @pytest.mark.asyncio
    async def test_sql_tool_initialization(self):
        with patch('app.tools.sql_tool.create_engine') as mock_engine, \
             patch('app.tools.sql_tool.SQLDatabase'), \
             patch('app.tools.sql_tool.AzureChatOpenAI'), \
             patch('app.tools.sql_tool.create_sql_agent'):
            
            tool = SQLTool(config={"connection_string_alias": "sql_primary", "read_only": True})
            assert tool.name == "SQL_Query"
            assert tool.read_only is True
            assert tool.max_results == 100
    
    @pytest.mark.asyncio
    async def test_sql_tool_read_only_protection(self):
        tool = SQLTool(config={"read_only": True})
        
        result = await tool.execute("DELETE FROM users WHERE id = 1")
        assert result.success is False
        assert "read-only" in result.error
    
    @pytest.mark.asyncio
    async def test_sql_tool_execute_query(self):
        with patch('app.tools.sql_tool.create_engine'), \
             patch('app.tools.sql_tool.SQLDatabase'), \
             patch('app.tools.sql_tool.AzureChatOpenAI'), \
             patch('app.tools.sql_tool.create_sql_agent') as mock_agent:
            
            mock_agent_instance = MagicMock()
            mock_agent_instance.ainvoke = AsyncMock(return_value={"output": "Query result: 10 users"})
            mock_agent.return_value = mock_agent_instance
            
            tool = SQLTool()
            tool.sql_agent = mock_agent_instance
            
            result = await tool.execute("How many users are in the database?")
            assert result.success is True
            assert "10 users" in result.data


class TestSharePointRAGTool:
    @pytest.mark.asyncio
    async def test_sharepoint_tool_initialization(self):
        with patch('app.tools.sharepoint_tool.OpenAIEmbeddings'), \
             patch('app.tools.sharepoint_tool.chromadb.PersistentClient') as mock_chroma:
            
            mock_client = MagicMock()
            mock_chroma.return_value = mock_client
            
            tool = SharePointRAGTool(config={"site_url": "https://test.sharepoint.com"})
            assert tool.name == "SharePoint_Search"
            assert tool.site_url == "https://test.sharepoint.com"
            assert tool.top_k == 5
    
    @pytest.mark.asyncio
    async def test_sharepoint_tool_search(self):
        with patch('app.tools.sharepoint_tool.OpenAIEmbeddings') as mock_embeddings, \
             patch('app.tools.sharepoint_tool.chromadb.PersistentClient') as mock_chroma:
            
            mock_embedding_instance = MagicMock()
            mock_embedding_instance.embed_query = MagicMock(return_value=[0.1, 0.2, 0.3])
            mock_embeddings.return_value = mock_embedding_instance
            
            mock_collection = MagicMock()
            mock_collection.query = MagicMock(return_value={
                "documents": [["Document content"]],
                "metadatas": [[{"title": "Test Doc", "source": "test.docx"}]],
                "distances": [[0.1]]
            })
            
            mock_client = MagicMock()
            mock_client.get_collection = MagicMock(return_value=mock_collection)
            mock_chroma.return_value = mock_client
            
            tool = SharePointRAGTool()
            tool.embeddings = mock_embedding_instance
            tool.collection = mock_collection
            
            result = await tool.execute("Find policy documents")
            assert result.success is True
            assert "Test Doc" in result.data
            assert result.metadata["results_count"] == 1


class TestBoxRAGTool:
    @pytest.mark.asyncio
    async def test_box_tool_initialization(self):
        with patch('app.tools.box_tool.OpenAIEmbeddings'), \
             patch('app.tools.box_tool.chromadb.PersistentClient') as mock_chroma:
            
            mock_client = MagicMock()
            mock_chroma.return_value = mock_client
            
            tool = BoxRAGTool(config={"folder_id": "12345"})
            assert tool.name == "Box_Search"
            assert tool.folder_id == "12345"
            assert tool.top_k == 5
    
    @pytest.mark.asyncio
    async def test_box_tool_search_with_filter(self):
        with patch('app.tools.box_tool.OpenAIEmbeddings') as mock_embeddings, \
             patch('app.tools.box_tool.chromadb.PersistentClient') as mock_chroma:
            
            mock_embedding_instance = MagicMock()
            mock_embedding_instance.embed_query = MagicMock(return_value=[0.1, 0.2, 0.3])
            mock_embeddings.return_value = mock_embedding_instance
            
            mock_collection = MagicMock()
            mock_collection.query = MagicMock(return_value={
                "documents": [["Spreadsheet content"]],
                "metadatas": [[{"file_name": "report.xlsx", "file_type": "xlsx"}]],
                "distances": [[0.2]]
            })
            
            mock_client = MagicMock()
            mock_client.get_collection = MagicMock(return_value=mock_collection)
            mock_chroma.return_value = mock_client
            
            tool = BoxRAGTool()
            tool.embeddings = mock_embedding_instance
            tool.collection = mock_collection
            
            result = await tool.execute("Find spreadsheets", context={"file_type": "xlsx"})
            assert result.success is True
            assert "report.xlsx" in result.data
            assert result.metadata["results_count"] == 1


class TestToolManager:
    def test_tool_manager_initialization(self, db_session):
        with patch.object(db_session, 'query') as mock_query:
            mock_query.return_value.filter.return_value.all.return_value = []
            
            manager = ToolManager(bot_id=1, db=db_session)
            assert manager.bot_id == 1
            assert manager.tools == []
    
    def test_tool_manager_with_tools(self, db_session):
        from app.models.bot import BotTool
        
        mock_bot_tool = MagicMock(spec=BotTool)
        mock_bot_tool.tool_name = "SQL_Query"
        mock_bot_tool.tool_config_json = {"read_only": True}
        mock_bot_tool.is_enabled = True
        
        with patch.object(db_session, 'query') as mock_query, \
             patch('app.services.tool_manager.SQLTool') as MockSQLTool:
            
            mock_query.return_value.filter.return_value.all.return_value = [mock_bot_tool]
            MockSQLTool.return_value = MagicMock()
            
            manager = ToolManager(bot_id=1, db=db_session)
            assert manager.has_tools() is True
    
    @pytest.mark.asyncio
    async def test_tool_manager_execute_with_tools(self, db_session):
        manager = ToolManager(bot_id=1, db=db_session)
        
        with patch.object(manager, 'agent_executor') as mock_executor:
            mock_executor.ainvoke = AsyncMock(return_value={
                "output": "The database has 100 users",
                "intermediate_steps": []
            })
            
            result = await manager.execute_with_tools("How many users?")
            assert result["success"] is True
            assert "100 users" in result["output"]
    
    def test_tool_manager_get_available_tools_info(self):
        manager = ToolManager()
        
        mock_tool = MagicMock()
        mock_tool.name = "Test Tool"
        mock_tool.description = "A test tool"
        manager.tools = [mock_tool]
        
        info = manager.get_available_tools_info()
        assert len(info) == 1
        assert info[0]["name"] == "Test Tool"
        assert info[0]["description"] == "A test tool"