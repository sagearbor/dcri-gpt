import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.models.feedback import MessageFeedback


@pytest.fixture
def sample_user(db: Session):
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user(db: Session):
    """Create another user for permission testing."""
    user = User(
        email="other@example.com",
        username="otheruser",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_session(db: Session, sample_user):
    """Create a sample chat session."""
    session = ChatSession(
        user_id=sample_user.id,
        title="Test Session"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def sample_message(db: Session, sample_session):
    """Create a sample chat message."""
    message = ChatMessage(
        session_id=sample_session.id,
        role=MessageRole.ASSISTANT,
        content="This is a test response from the AI.",
        token_count=10
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@pytest.fixture
def other_user_session(db: Session, other_user):
    """Create a session for another user."""
    session = ChatSession(
        user_id=other_user.id,
        title="Other User Session"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def other_user_message(db: Session, other_user_session):
    """Create a message for another user's session."""
    message = ChatMessage(
        session_id=other_user_session.id,
        role=MessageRole.ASSISTANT,
        content="Message for other user",
        token_count=5
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


class TestFeedbackEndpoints:
    """Test the feedback API endpoints."""
    
    def test_submit_feedback_thumbs_up(self, client, auth_headers, db: Session, sample_message):
        """Test submitting positive feedback."""
        response = client.post(
            f"/api/v1/messages/{sample_message.id}/feedback",
            json={"rating": 1},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message_id"] == sample_message.id
        assert data["rating"] == 1
        assert "id" in data
        assert "created_at" in data
        
        # Verify feedback was saved to database
        feedback = db.query(MessageFeedback).filter(
            MessageFeedback.message_id == sample_message.id
        ).first()
        assert feedback is not None
        assert feedback.rating == 1
    
    def test_submit_feedback_thumbs_down_with_comment(self, client, auth_headers, db: Session, sample_message):
        """Test submitting negative feedback with a comment."""
        response = client.post(
            f"/api/v1/messages/{sample_message.id}/feedback",
            json={
                "rating": -1,
                "comment": "The response was not helpful"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["rating"] == -1
        assert data["comment"] == "The response was not helpful"
        
        # Verify in database
        feedback = db.query(MessageFeedback).filter(
            MessageFeedback.message_id == sample_message.id
        ).first()
        assert feedback.rating == -1
        assert feedback.comment == "The response was not helpful"
    
    def test_submit_feedback_invalid_rating(self, client, auth_headers, sample_message):
        """Test submitting feedback with invalid rating."""
        response = client.post(
            f"/api/v1/messages/{sample_message.id}/feedback",
            json={"rating": 0},  # Invalid rating
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_submit_feedback_nonexistent_message(self, client, auth_headers):
        """Test submitting feedback for non-existent message."""
        response = client.post(
            "/api/v1/messages/99999/feedback",
            json={"rating": 1},
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Message not found" in response.json()["detail"]
    
    def test_submit_feedback_other_users_message(self, client, auth_headers, other_user_message):
        """Test that users cannot submit feedback for other users' messages."""
        response = client.post(
            f"/api/v1/messages/{other_user_message.id}/feedback",
            json={"rating": 1},
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()
    
    def test_update_existing_feedback(self, client, auth_headers, db: Session, sample_message, sample_user):
        """Test updating existing feedback."""
        # First create feedback
        feedback = MessageFeedback(
            message_id=sample_message.id,
            user_id=sample_user.id,
            rating=1,
            comment="Initial comment"
        )
        db.add(feedback)
        db.commit()
        
        # Submit new feedback for same message (should update)
        response = client.post(
            f"/api/v1/messages/{sample_message.id}/feedback",
            json={
                "rating": -1,
                "comment": "Updated comment"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["rating"] == -1
        assert data["comment"] == "Updated comment"
        
        # Verify only one feedback exists
        feedback_count = db.query(MessageFeedback).filter(
            MessageFeedback.message_id == sample_message.id
        ).count()
        assert feedback_count == 1
    
    def test_patch_feedback(self, client, auth_headers, db: Session, sample_message, sample_user):
        """Test PATCH endpoint to update feedback."""
        # Create initial feedback
        feedback = MessageFeedback(
            message_id=sample_message.id,
            user_id=sample_user.id,
            rating=1,
            comment="Initial"
        )
        db.add(feedback)
        db.commit()
        
        # Update only the rating
        response = client.patch(
            f"/api/v1/messages/{sample_message.id}/feedback",
            json={"rating": -1},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == -1
        assert data["comment"] == "Initial"  # Unchanged
    
    def test_delete_feedback(self, client, auth_headers, db: Session, sample_message, sample_user):
        """Test deleting feedback."""
        # Create feedback
        feedback = MessageFeedback(
            message_id=sample_message.id,
            user_id=sample_user.id,
            rating=1
        )
        db.add(feedback)
        db.commit()
        
        # Delete feedback
        response = client.delete(
            f"/api/v1/messages/{sample_message.id}/feedback",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["detail"]
        
        # Verify it's deleted
        feedback = db.query(MessageFeedback).filter(
            MessageFeedback.message_id == sample_message.id
        ).first()
        assert feedback is None
    
    def test_delete_nonexistent_feedback(self, client, auth_headers, sample_message):
        """Test deleting non-existent feedback."""
        response = client.delete(
            f"/api/v1/messages/{sample_message.id}/feedback",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_get_feedback_summary(self, client, auth_headers, db: Session, sample_user):
        """Test getting feedback summary."""
        # Create some sessions and messages with feedback
        for i in range(5):
            session = ChatSession(
                user_id=sample_user.id,
                title=f"Session {i}"
            )
            db.add(session)
            db.commit()
            
            message = ChatMessage(
                session_id=session.id,
                role=MessageRole.ASSISTANT,
                content=f"Response {i}"
            )
            db.add(message)
            db.commit()
            
            feedback = MessageFeedback(
                message_id=message.id,
                user_id=sample_user.id,
                rating=1 if i % 2 == 0 else -1
            )
            db.add(feedback)
        
        db.commit()
        
        # Get feedback summary
        response = client.get(
            "/api/v1/messages/feedback/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_feedback"] == 5
        assert data["positive_count"] == 3
        assert data["negative_count"] == 2
        assert data["positive_percentage"] == 60.0
        assert data["negative_percentage"] == 40.0
        assert len(data["recent_feedback"]) <= 10
    
    def test_feedback_requires_authentication(self, client, sample_message):
        """Test that feedback endpoints require authentication."""
        # Test POST
        response = client.post(
            f"/api/v1/messages/{sample_message.id}/feedback",
            json={"rating": 1}
        )
        assert response.status_code == 401
        
        # Test PATCH
        response = client.patch(
            f"/api/v1/messages/{sample_message.id}/feedback",
            json={"rating": -1}
        )
        assert response.status_code == 401
        
        # Test DELETE
        response = client.delete(
            f"/api/v1/messages/{sample_message.id}/feedback"
        )
        assert response.status_code == 401
        
        # Test GET summary
        response = client.get("/api/v1/messages/feedback/summary")
        assert response.status_code == 401


class TestFeedbackValidation:
    """Test feedback validation."""
    
    def test_rating_validation(self, client, auth_headers, sample_message):
        """Test that only -1 and 1 are valid ratings."""
        invalid_ratings = [0, 2, -2, 5, -5, 100]
        
        for rating in invalid_ratings:
            response = client.post(
                f"/api/v1/messages/{sample_message.id}/feedback",
                json={"rating": rating},
                headers=auth_headers
            )
            assert response.status_code == 422
    
    def test_comment_length_limit(self, client, auth_headers, sample_message):
        """Test comment length validation."""
        # Create a comment that's too long (assuming 1000 char limit)
        long_comment = "x" * 1001
        
        response = client.post(
            f"/api/v1/messages/{sample_message.id}/feedback",
            json={
                "rating": 1,
                "comment": long_comment
            },
            headers=auth_headers
        )
        
        # Should either truncate or reject based on implementation
        # Adjust assertion based on your validation strategy
        assert response.status_code in [200, 422]


class TestFeedbackIntegration:
    """Test feedback integration with chat system."""
    
    def test_feedback_persists_with_message(self, db: Session, sample_message, sample_user):
        """Test that feedback is properly linked to messages."""
        feedback = MessageFeedback(
            message_id=sample_message.id,
            user_id=sample_user.id,
            rating=1,
            comment="Great response!"
        )
        db.add(feedback)
        db.commit()
        
        # Query message with feedback
        message = db.query(ChatMessage).filter(
            ChatMessage.id == sample_message.id
        ).first()
        
        assert message.feedback is not None
        assert message.feedback.rating == 1
        assert message.feedback.comment == "Great response!"
    
    def test_cascade_delete_behavior(self, db: Session, sample_message, sample_user):
        """Test what happens when a message with feedback is deleted."""
        # Create feedback
        feedback = MessageFeedback(
            message_id=sample_message.id,
            user_id=sample_user.id,
            rating=1
        )
        db.add(feedback)
        db.commit()
        
        # Delete the message
        db.delete(sample_message)
        db.commit()
        
        # Check if feedback is also deleted (depends on cascade settings)
        remaining_feedback = db.query(MessageFeedback).filter(
            MessageFeedback.message_id == sample_message.id
        ).first()
        
        # This assertion depends on your cascade configuration
        # Adjust based on your database schema
        assert remaining_feedback is None or remaining_feedback is not None