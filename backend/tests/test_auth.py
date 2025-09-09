import pytest
from unittest.mock import patch, MagicMock
from fastapi import status
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import get_password_hash, verify_password


class TestRegistration:
    def test_register_new_user(self, client, db_session):
        with patch.object(db_session, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            
            user_data = {
                "email": "test@example.com",
                "username": "testuser",
                "password": "testpassword123",
                "full_name": "Test User"
            }
            
            with patch.object(db_session, 'add') as mock_add, \
                 patch.object(db_session, 'commit') as mock_commit, \
                 patch.object(db_session, 'refresh') as mock_refresh:
                
                mock_user = MagicMock(spec=User)
                mock_user.id = 1
                mock_user.email = user_data["email"]
                mock_user.username = user_data["username"]
                mock_user.full_name = user_data["full_name"]
                mock_user.is_active = True
                mock_user.is_admin = False
                mock_user.created_at = "2024-01-01T00:00:00"
                mock_user.updated_at = None
                
                mock_refresh.side_effect = lambda x: setattr(x, 'id', 1)
                
                with patch('app.api.v1.auth.get_password_hash') as mock_hash:
                    mock_hash.return_value = "hashed_password"
                    
                    response = client.post("/api/v1/auth/register", json=user_data)
                    
                    assert response.status_code == status.HTTP_200_OK
                    mock_hash.assert_called_once_with(user_data["password"])
                    mock_add.assert_called_once()
                    mock_commit.assert_called_once()
    
    def test_register_duplicate_email(self, client, db_session):
        with patch.object(db_session, 'query') as mock_query:
            existing_user = MagicMock(spec=User)
            existing_user.email = "test@example.com"
            existing_user.username = "otheruser"
            
            mock_query.return_value.filter.return_value.first.return_value = existing_user
            
            user_data = {
                "email": "test@example.com",
                "username": "testuser",
                "password": "testpassword123"
            }
            
            response = client.post("/api/v1/auth/register", json=user_data)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "email already exists" in response.json()["detail"]
    
    def test_register_duplicate_username(self, client, db_session):
        with patch.object(db_session, 'query') as mock_query:
            existing_user = MagicMock(spec=User)
            existing_user.email = "other@example.com"
            existing_user.username = "testuser"
            
            mock_query.return_value.filter.return_value.first.return_value = existing_user
            
            user_data = {
                "email": "test@example.com",
                "username": "testuser",
                "password": "testpassword123"
            }
            
            response = client.post("/api/v1/auth/register", json=user_data)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "username already exists" in response.json()["detail"]
    
    def test_register_invalid_email(self, client):
        user_data = {
            "email": "invalid-email",
            "username": "testuser",
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_short_password(self, client):
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "short"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_short_username(self, client):
        user_data = {
            "email": "test@example.com",
            "username": "ab",
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLogin:
    def test_login_success(self, client, db_session):
        with patch.object(db_session, 'query') as mock_query:
            mock_user = MagicMock(spec=User)
            mock_user.id = 1
            mock_user.username = "testuser"
            mock_user.hashed_password = "hashed_password"
            mock_user.is_active = True
            
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            
            with patch('app.api.v1.auth.verify_password') as mock_verify, \
                 patch('app.api.v1.auth.create_access_token') as mock_create_token:
                
                mock_verify.return_value = True
                mock_create_token.return_value = "test_token_123"
                
                response = client.post(
                    "/api/v1/auth/token",
                    data={
                        "username": "testuser",
                        "password": "testpassword"
                    }
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["access_token"] == "test_token_123"
                assert data["token_type"] == "bearer"
                
                mock_verify.assert_called_once_with("testpassword", "hashed_password")
                mock_create_token.assert_called_once()
    
    def test_login_invalid_username(self, client, db_session):
        with patch.object(db_session, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "username": "nonexistent",
                    "password": "testpassword"
                }
            )
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_invalid_password(self, client, db_session):
        with patch.object(db_session, 'query') as mock_query:
            mock_user = MagicMock(spec=User)
            mock_user.hashed_password = "hashed_password"
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            
            with patch('app.api.v1.auth.verify_password') as mock_verify:
                mock_verify.return_value = False
                
                response = client.post(
                    "/api/v1/auth/token",
                    data={
                        "username": "testuser",
                        "password": "wrongpassword"
                    }
                )
                
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
                assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_inactive_user(self, client, db_session):
        with patch.object(db_session, 'query') as mock_query:
            mock_user = MagicMock(spec=User)
            mock_user.hashed_password = "hashed_password"
            mock_user.is_active = False
            
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            
            with patch('app.api.v1.auth.verify_password') as mock_verify:
                mock_verify.return_value = True
                
                response = client.post(
                    "/api/v1/auth/token",
                    data={
                        "username": "testuser",
                        "password": "testpassword"
                    }
                )
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "Inactive user" in response.json()["detail"]


class TestProtectedEndpoints:
    def test_get_current_user_valid_token(self, client, db_session):
        with patch('app.api.deps.verify_token') as mock_verify_token, \
             patch.object(db_session, 'query') as mock_query:
            
            mock_verify_token.return_value = {
                "sub": "testuser",
                "user_id": 1
            }
            
            mock_user = MagicMock(spec=User)
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.username = "testuser"
            mock_user.full_name = "Test User"
            mock_user.is_active = True
            mock_user.is_admin = False
            mock_user.created_at = "2024-01-01T00:00:00"
            mock_user.updated_at = None
            
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            
            headers = {"Authorization": "Bearer test_token_123"}
            response = client.get("/api/v1/users/me", headers=headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
    
    def test_get_current_user_invalid_token(self, client):
        with patch('app.api.deps.verify_token') as mock_verify_token:
            mock_verify_token.return_value = None
            
            headers = {"Authorization": "Bearer invalid_token"}
            response = client.get("/api/v1/users/me", headers=headers)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Could not validate credentials" in response.json()["detail"]
    
    def test_get_current_user_no_token(self, client):
        response = client.get("/api/v1/users/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Not authenticated" in response.json()["detail"]
    
    def test_get_current_user_user_not_found(self, client, db_session):
        with patch('app.api.deps.verify_token') as mock_verify_token, \
             patch.object(db_session, 'query') as mock_query:
            
            mock_verify_token.return_value = {
                "sub": "testuser",
                "user_id": 999
            }
            
            mock_query.return_value.filter.return_value.first.return_value = None
            
            headers = {"Authorization": "Bearer test_token_123"}
            response = client.get("/api/v1/users/me", headers=headers)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Could not validate credentials" in response.json()["detail"]
    
    def test_get_current_user_inactive_user(self, client, db_session):
        with patch('app.api.deps.verify_token') as mock_verify_token, \
             patch.object(db_session, 'query') as mock_query:
            
            mock_verify_token.return_value = {
                "sub": "testuser",
                "user_id": 1
            }
            
            mock_user = MagicMock(spec=User)
            mock_user.id = 1
            mock_user.is_active = False
            
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            
            headers = {"Authorization": "Bearer test_token_123"}
            response = client.get("/api/v1/users/me", headers=headers)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Inactive user" in response.json()["detail"]


class TestSecurity:
    def test_password_hashing(self):
        from app.core.security import get_password_hash, verify_password
        
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_jwt_token_creation_and_verification(self):
        from app.core.security import create_access_token, verify_token
        
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        
        assert token is not None
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 1
        assert "exp" in payload
    
    def test_jwt_token_invalid(self):
        from app.core.security import verify_token
        
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        
        assert payload is None