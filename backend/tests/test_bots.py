import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.bot import CustomBot, BotPermission, PermissionLevel


def create_test_bot(
    client: TestClient,
    token: str,
    name: str = "Test Bot",
    system_prompt: str = "You are a test bot",
    is_public: bool = False
) -> Dict[str, Any]:
    """Helper function to create a test bot"""
    response = client.post(
        "/api/v1/bots/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "description": "Test bot description",
            "system_prompt": system_prompt,
            "model_name": "gpt-4",
            "is_public": is_public,
            "tools": [
                {
                    "tool_name": "test_tool",
                    "tool_config_json": {"key": "value"},
                    "is_enabled": True
                }
            ]
        }
    )
    assert response.status_code == 201
    return response.json()


class TestBotCRUD:
    """Test bot CRUD operations with ownership rules"""
    
    def test_create_bot(self, client: TestClient, normal_user_token_headers: Dict[str, str]):
        """Test creating a new bot"""
        response = client.post(
            "/api/v1/bots/",
            headers=normal_user_token_headers,
            json={
                "name": "My Test Bot",
                "description": "A bot for testing",
                "system_prompt": "You are a helpful test assistant",
                "model_name": "gpt-4",
                "is_public": False
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Test Bot"
        assert data["system_prompt"] == "You are a helpful test assistant"
        assert data["model_name"] == "gpt-4"
        assert data["is_public"] is False
        assert "id" in data
        assert "share_uuid" in data
    
    def test_create_bot_with_tools(self, client: TestClient, normal_user_token_headers: Dict[str, str]):
        """Test creating a bot with tools configuration"""
        response = client.post(
            "/api/v1/bots/",
            headers=normal_user_token_headers,
            json={
                "name": "Bot with Tools",
                "system_prompt": "Test prompt",
                "tools": [
                    {
                        "tool_name": "sql_tool",
                        "tool_config_json": {"connection": "test_db"},
                        "is_enabled": True
                    },
                    {
                        "tool_name": "sharepoint_tool",
                        "tool_config_json": {"site_url": "https://test.sharepoint.com"},
                        "is_enabled": False
                    }
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["tools"]) == 2
        assert data["tools"][0]["tool_name"] == "sql_tool"
        assert data["tools"][0]["is_enabled"] is True
        assert data["tools"][1]["tool_name"] == "sharepoint_tool"
        assert data["tools"][1]["is_enabled"] is False
    
    def test_list_bots(self, client: TestClient, normal_user_token_headers: Dict[str, str]):
        """Test listing bots (own, shared, and public)"""
        # Create own bot
        own_bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1], "My Bot")
        
        # List bots
        response = client.get("/api/v1/bots/", headers=normal_user_token_headers)
        assert response.status_code == 200
        bots = response.json()
        assert len(bots) >= 1
        assert any(bot["id"] == own_bot["id"] for bot in bots)
    
    def test_get_bot_by_id(self, client: TestClient, normal_user_token_headers: Dict[str, str]):
        """Test getting a specific bot by ID"""
        # Create a bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # Get the bot
        response = client.get(f"/api/v1/bots/{bot['id']}", headers=normal_user_token_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bot["id"]
        assert data["name"] == bot["name"]
    
    def test_get_nonexistent_bot(self, client: TestClient, normal_user_token_headers: Dict[str, str]):
        """Test getting a bot that doesn't exist"""
        response = client.get("/api/v1/bots/99999", headers=normal_user_token_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_update_own_bot(self, client: TestClient, normal_user_token_headers: Dict[str, str]):
        """Test updating your own bot"""
        # Create a bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # Update the bot
        response = client.put(
            f"/api/v1/bots/{bot['id']}",
            headers=normal_user_token_headers,
            json={
                "name": "Updated Bot Name",
                "system_prompt": "Updated prompt",
                "is_public": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Bot Name"
        assert data["system_prompt"] == "Updated prompt"
        assert data["is_public"] is True
    
    def test_update_bot_tools(self, client: TestClient, normal_user_token_headers: Dict[str, str]):
        """Test updating bot tools configuration"""
        # Create a bot with tools
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # Update tools
        response = client.put(
            f"/api/v1/bots/{bot['id']}",
            headers=normal_user_token_headers,
            json={
                "tools": [
                    {
                        "tool_name": "new_tool",
                        "tool_config_json": {"new": "config"},
                        "is_enabled": True
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["tools"]) == 1
        assert data["tools"][0]["tool_name"] == "new_tool"
    
    def test_delete_own_bot(self, client: TestClient, normal_user_token_headers: Dict[str, str]):
        """Test deleting your own bot"""
        # Create a bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # Delete the bot
        response = client.delete(f"/api/v1/bots/{bot['id']}", headers=normal_user_token_headers)
        assert response.status_code == 204
        
        # Verify it's deleted
        response = client.get(f"/api/v1/bots/{bot['id']}", headers=normal_user_token_headers)
        assert response.status_code == 404
    
    def test_cannot_update_others_bot(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str]
    ):
        """Test that you cannot update someone else's bot without permission"""
        # User 1 creates a bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # User 2 tries to update it
        response = client.put(
            f"/api/v1/bots/{bot['id']}",
            headers=second_user_token_headers,
            json={"name": "Hacked name"}
        )
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()
    
    def test_cannot_delete_others_bot(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str]
    ):
        """Test that you cannot delete someone else's bot"""
        # User 1 creates a bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # User 2 tries to delete it
        response = client.delete(f"/api/v1/bots/{bot['id']}", headers=second_user_token_headers)
        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()


class TestBotSharing:
    """Test bot sharing functionality"""
    
    def test_share_bot_with_user(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        test_user2: User
    ):
        """Test sharing a bot with another user"""
        # Create a bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # Share with user2
        response = client.post(
            f"/api/v1/bots/{bot['id']}/share",
            headers=normal_user_token_headers,
            json={
                "user_email": test_user2.email,
                "permission_level": "chat"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "shared" in data["message"].lower()
        assert data["permission"]["user_id"] == test_user2.id
        assert data["permission"]["permission_level"] == "chat"
    
    def test_update_share_permission(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        test_user2: User
    ):
        """Test updating an existing share permission"""
        # Create and share bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # Share with VIEW permission
        response = client.post(
            f"/api/v1/bots/{bot['id']}/share",
            headers=normal_user_token_headers,
            json={
                "user_email": test_user2.email,
                "permission_level": "view"
            }
        )
        assert response.status_code == 200
        
        # Update to EDIT permission
        response = client.post(
            f"/api/v1/bots/{bot['id']}/share",
            headers=normal_user_token_headers,
            json={
                "user_email": test_user2.email,
                "permission_level": "edit"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "updated" in data["message"].lower()
        assert data["permission"]["permission_level"] == "edit"
    
    def test_unshare_bot(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        test_user2: User
    ):
        """Test removing a user's permission to access a bot"""
        # Create and share bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        response = client.post(
            f"/api/v1/bots/{bot['id']}/share",
            headers=normal_user_token_headers,
            json={
                "user_email": test_user2.email,
                "permission_level": "chat"
            }
        )
        assert response.status_code == 200
        
        # Unshare
        response = client.delete(
            f"/api/v1/bots/{bot['id']}/share/{test_user2.id}",
            headers=normal_user_token_headers
        )
        assert response.status_code == 204
    
    def test_cannot_share_others_bot(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str],
        test_user2: User
    ):
        """Test that only the owner can share a bot"""
        # User 1 creates a bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # User 2 tries to share it
        response = client.post(
            f"/api/v1/bots/{bot['id']}/share",
            headers=second_user_token_headers,
            json={
                "user_email": test_user2.email,
                "permission_level": "view"
            }
        )
        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()
    
    def test_toggle_bot_public(self, client: TestClient, normal_user_token_headers: Dict[str, str]):
        """Test toggling a bot's public status"""
        # Create a private bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        assert bot["is_public"] is False
        
        # Make it public
        response = client.patch(
            f"/api/v1/bots/{bot['id']}/public",
            headers=normal_user_token_headers,
            params={"is_public": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] is True
        assert data["share_url"] is not None
        assert bot["share_uuid"] in data["share_url"]
        
        # Make it private again
        response = client.patch(
            f"/api/v1/bots/{bot['id']}/public",
            headers=normal_user_token_headers,
            params={"is_public": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] is False
    
    def test_get_bot_by_share_uuid(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str]
    ):
        """Test accessing a bot via its share UUID"""
        # Create a public bot
        bot = create_test_bot(
            client,
            normal_user_token_headers["Authorization"].split()[1],
            is_public=True
        )
        
        # Another user accesses it via share UUID
        response = client.get(
            f"/api/v1/bots/share/{bot['share_uuid']}",
            headers=second_user_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bot["id"]
    
    def test_cannot_access_private_bot_via_uuid(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str]
    ):
        """Test that private bots cannot be accessed via share UUID without permission"""
        # Create a private bot
        bot = create_test_bot(
            client,
            normal_user_token_headers["Authorization"].split()[1],
            is_public=False
        )
        
        # Another user tries to access it
        response = client.get(
            f"/api/v1/bots/share/{bot['share_uuid']}",
            headers=second_user_token_headers
        )
        assert response.status_code == 403
    
    def test_shared_user_can_view_bot(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str],
        test_user2: User
    ):
        """Test that a user with VIEW permission can view the bot"""
        # Create and share bot
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        # Share with VIEW permission
        response = client.post(
            f"/api/v1/bots/{bot['id']}/share",
            headers=normal_user_token_headers,
            json={
                "user_email": test_user2.email,
                "permission_level": "view"
            }
        )
        assert response.status_code == 200
        
        # User 2 can view the bot
        response = client.get(f"/api/v1/bots/{bot['id']}", headers=second_user_token_headers)
        assert response.status_code == 200
        assert response.json()["id"] == bot["id"]
    
    def test_shared_user_with_edit_can_update(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str],
        test_user2: User
    ):
        """Test that a user with EDIT permission can update the bot"""
        # Create and share bot with EDIT permission
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        response = client.post(
            f"/api/v1/bots/{bot['id']}/share",
            headers=normal_user_token_headers,
            json={
                "user_email": test_user2.email,
                "permission_level": "edit"
            }
        )
        assert response.status_code == 200
        
        # User 2 can update the bot
        response = client.put(
            f"/api/v1/bots/{bot['id']}",
            headers=second_user_token_headers,
            json={"name": "Edited by shared user"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Edited by shared user"


class TestBotChatIntegration:
    """Test bot integration with chat sessions"""
    
    def test_create_chat_session_with_bot(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test creating a chat session with a custom bot"""
        # Create a bot
        bot = create_test_bot(
            client,
            normal_user_token_headers["Authorization"].split()[1],
            system_prompt="You are a specialized test assistant"
        )
        
        # Create a chat session with the bot
        response = client.post(
            "/api/v1/chat",
            headers=normal_user_token_headers,
            json={
                "content": "Hello bot!",
                "bot_id": bot["id"]
            }
        )
        assert response.status_code == 200
    
    def test_cannot_chat_with_private_bot_without_permission(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str]
    ):
        """Test that users cannot chat with private bots they don't have access to"""
        # User 1 creates a private bot
        bot = create_test_bot(
            client,
            normal_user_token_headers["Authorization"].split()[1],
            is_public=False
        )
        
        # User 2 tries to chat with it
        response = client.post(
            "/api/v1/chat",
            headers=second_user_token_headers,
            json={
                "content": "Hello bot!",
                "bot_id": bot["id"]
            }
        )
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()
    
    def test_can_chat_with_public_bot(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str]
    ):
        """Test that anyone can chat with public bots"""
        # User 1 creates a public bot
        bot = create_test_bot(
            client,
            normal_user_token_headers["Authorization"].split()[1],
            is_public=True
        )
        
        # User 2 can chat with it
        response = client.post(
            "/api/v1/chat",
            headers=second_user_token_headers,
            json={
                "content": "Hello public bot!",
                "bot_id": bot["id"]
            }
        )
        assert response.status_code == 200
    
    def test_shared_user_with_chat_permission_can_chat(
        self,
        client: TestClient,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str],
        test_user2: User
    ):
        """Test that users with CHAT permission can use the bot"""
        # Create and share bot with CHAT permission
        bot = create_test_bot(client, normal_user_token_headers["Authorization"].split()[1])
        
        response = client.post(
            f"/api/v1/bots/{bot['id']}/share",
            headers=normal_user_token_headers,
            json={
                "user_email": test_user2.email,
                "permission_level": "chat"
            }
        )
        assert response.status_code == 200
        
        # User 2 can chat with the bot
        response = client.post(
            "/api/v1/chat",
            headers=second_user_token_headers,
            json={
                "content": "Hello shared bot!",
                "bot_id": bot["id"]
            }
        )
        assert response.status_code == 200