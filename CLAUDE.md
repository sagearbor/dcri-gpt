# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DCRI GPT is an enterprise-ready platform for building and managing custom AI chatbots with connections to internal data sources. The platform uses a microservices architecture with FastAPI backend and React frontend.

## Architecture

### Tech Stack
- **Backend**: FastAPI (Python 3.10+) with SQLAlchemy ORM
- **Frontend**: React with Vite
- **Database**: SQLAlchemy with SQLite (dev) / Azure SQL or PostgreSQL (prod)
- **AI Framework**: LangChain for LLM orchestration
- **Vector Search**: ChromaDB (local) / Azure AI Search (prod)
- **Authentication**: JWT with OAuth2
- **Testing**: Pytest for backend
- **Deployment**: Docker, Azure App Service, Azure Key Vault

### Key Components
- **LLM Gateway**: Service module for managing different AI models (GPT-5, GPT-4, GPT-3.5-Turbo)
- **Tool Calling Framework**: MCP-based system for connecting to SharePoint, Box, and SQL databases
- **Chat Management**: Session-based conversation tracking with persistent history
- **Bot Management**: Custom chatbot creation with granular sharing permissions
- **Usage Tracking**: Token counting and cost management system
- **Admin Dashboard**: System-wide analytics and user management

## Common Development Commands

### Local Development Setup
```bash
# Clone and setup environment
cd backend
cp .env.example .env  # Configure API keys and database URL

# Launch full stack with Docker Compose
docker-compose up --build
```

### Testing
```bash
# Run backend tests
docker-compose exec backend pytest

# Run specific test
docker-compose exec backend pytest tests/test_auth.py::test_user_registration
```

### Database Migrations
```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Project Structure

- `/backend/`: FastAPI application
  - `/api/v1/`: API endpoints organized by domain (auth, chat, bots, admin)
  - Models use SQLAlchemy ORM with Alembic migrations
  - Services layer for business logic (llm_gateway.py, tool implementations)
  - Pydantic schemas for request/response validation
  
- `/frontend/`: React application (Vite-based)
  
- `/docs/`: Documentation (when created)

- `docker-compose.yml`: Local development orchestration

## Development Guidelines

### API Endpoints Pattern
- All API routes under `/api/v1/`
- Protected endpoints use `get_current_user` dependency
- Admin endpoints require `is_admin` check
- Streaming responses for chat completions

### Database Models
Core models include:
- `User`: Authentication and authorization
- `ChatSession` & `ChatMessage`: Conversation tracking
- `CustomBot` & `BotPermission`: Bot management and sharing
- `BotTool`: Tool configuration per bot
- `TokenUsageLog`: Usage and cost tracking
- `MessageFeedback`: User feedback on responses

### Tool Implementation
Tools follow a generic interface:
- Implement `Tool` base class with `name`, `description`, `execute()` methods
- SQL tools use LangChain SQL Agent
- RAG tools (SharePoint/Box) use vector search for document retrieval
- Async tools for long-running operations

### Testing Requirements
- **MANDATORY**: Write Pytest unit tests for EVERY module/feature as you develop
- Create tests DURING development, not after
- Mock all external dependencies and input data:
  - Use `unittest.mock` or `pytest-mock` for mocking
  - Mock LLM responses, database connections, external APIs
  - Create fixture data for all test scenarios
- Use fixtures for test database isolation
- Test coverage expectations:
  - Happy path scenarios
  - Error handling and edge cases
  - Authentication and authorization checks
  - Input validation
- Run tests before committing: `docker-compose exec backend pytest`

## Environment Configuration

Required environment variables in `.env`:
- `DATABASE_URL`: SQLAlchemy connection string
- `JWT_SECRET_KEY`: For token generation
- `AZURE_OPENAI_KEY`: LLM API access
- Azure Key Vault settings for production secrets

## Development Workflow

Follow the developer_checklist.md for implementation order. Each module should:
1. Create feature branch
2. Implement with tests
3. Create pull request
4. Ensure CI passes (when configured)