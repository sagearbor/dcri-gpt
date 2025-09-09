# DCRI GPT: Detailed Developer Checklist

This checklist tracks the development of the DCRI GPT platform. Each task should have a corresponding branch and pull request. All code must include Pytest unit tests with sufficient coverage.

## Module 1: Project Setup & Core Backend

- `[ ] TODO` **1.1:** Initialize project mono-repo structure: `/backend`, `/frontend`, `docker-compose.yml`, `/docs`.
  
- `[ ] TODO` **1.2:** Initialize FastAPI project in `/backend` with a `/api/v1/health` endpoint.
  
- `[ ] TODO` **1.3:** Implement Pydantic `BaseSettings` for configuration management from a `.env` file. Include settings for `DATABASE_URL`, `JWT_SECRET_KEY`, `AZURE_OPENAI_KEY`, etc.
  
- `[ ] TODO` **1.4:** Integrate SQLAlchemy ORM and Alembic for database migrations. Create initial migration for `users` table (`id`, `email`, `hashed_password`, `is_active`, `is_admin`, `created_at`).
  
- `[ ] TODO` **1.5:** Configure SQLAlchemy to use a local SQLite file for development, specified via the `DATABASE_URL`.
  
- `[ ] TODO` **1.6:** Containerize the backend with a multi-stage `Dockerfile` for optimized production builds.
  
- `[ ] TODO` **1.7:** Create a `docker-compose.yml` to run the backend service and a PostgreSQL database for staging-like local testing.
  
- `[ ] TODO` **1.8:** Setup Pytest with fixtures for an isolated test database and an authenticated API client. Test the `/api/v1/health` endpoint.
  

## Module 2: User Management & Authentication

- `[ ] TODO` **2.1:** Create Pydantic schemas: `UserCreate`, `UserRead`, `Token`. Ensure passwords are not exposed in `UserRead`.
  
- `[ ] TODO` **2.2:** Implement `POST /api/v1/auth/register` endpoint. It should hash the password using `passlib.context.CryptContext` before storing.
  
- `[ ] TODO` **2.3:** Implement `POST /api/v1/auth/token` using FastAPI's `OAuth2PasswordRequestForm`. It must validate credentials and return a JWT access token.
  
- `[ ] TODO` **2.4:** Create a reusable `get_current_user` dependency that decodes the JWT from the `Authorization` header and fetches the user from the DB.
  
- `[ ] TODO` **2.5:** Implement a protected `GET /api/v1/users/me` endpoint using the `get_current_user` dependency.
  
- `[ ] TODO` **2.6:** Write Pytest unit tests for registration (success, duplicate email), login (success, wrong password), and the `/users/me` endpoint (with valid, invalid, and missing tokens).
  

## Module 3: Core Chat Logic & LLM Gateway

- `[ ] TODO` **3.1:** Create DB models: `ChatSession` (`id`, `user_id`, `bot_id`, `title`, `created_at`) and `ChatMessage` (`id`, `session_id`, `role` ['user' or 'ai'], `content`, `token_count`, `timestamp`).
  
- `[ ] TODO` **3.2:** Create a service module `llm_gateway.py`. Implement a class that can be initialized with a model name (e.g., 'gpt-4') and exposes a `get_completion(messages)` method.
  
- `[ ] TODO` **3.3:** Implement a streaming chat endpoint: `POST /api/v1/chat`. It should accept a user message and an optional `session_id`. If `session_id` is null, create a new session.
  
- `[ ] TODO` **3.4:** The endpoint logic must:
  
  - 1. Retrieve prior messages for the session from the DB.
  - 2. Format the message history for the LLM.
  - 3. Call the LLM gateway and stream the response using `StreamingResponse`.
  - 4. In a background task, after the stream is complete, save the user's message and the full AI response to the `ChatMessage` table.
- `[ ] TODO` **3.5:** Write Pytest tests for the chat endpoint, mocking the LLM gateway to test session creation, history retrieval, and message saving logic.
  

## Module 4: Custom Chatbot Management & Sharing

- `[ ] TODO` **4.1:** Create `CustomBot` DB model: (`id`, `name`, `system_prompt`, `model_name`, `user_id`, `is_public`, `share_uuid`).
  
- `[ ] TODO` **4.2:** Create `BotPermission` DB model: (`id`, `bot_id`, `user_id`, `permission_level` ['view', 'chat']). This enables granular sharing.
  
- `[ ] TODO` **4.3:** Implement full CRUD API endpoints under `/api/v1/bots/`. Ensure only the bot owner can update or delete.
  
- `[ ] TODO` **4.4:** Modify chat endpoint: if a `bot_id` is passed to a new session, use that bot's `system_prompt` and `model_name`.
  
- `[ ] TODO` **4.5:** Implement sharing endpoints:
  
  - `POST /api/v1/bots/{bot_id}/share` to add a user to `BotPermission` table.
    
  - `DELETE /api/v1/bots/{bot_id}/share` to remove a user's permission.
    
  - `PATCH /api/v1/bots/{bot_id}` to toggle `is_public` and generate a `share_uuid`.
    
- `[ ] TODO` **4.6:** Write Pytest tests for bot CRUD, ensuring ownership rules. Test sharing logic (e.g., user A can't create a share link for user B's bot).
  

## Module 5: Tool Calling (MCP) Framework

- `[ ] TODO` **5.1:** Design a generic Python `Tool` interface with `name`, `description`, and `execute(...)` methods.
  
- `[ ] TODO` **5.2:** Integrate with Azure Key Vault. Create a service to fetch secrets securely at runtime.
  
- `[ ] TODO` **5.3:** Create `BotTool` DB model to link a `CustomBot` to a configured tool (`id`, `bot_id`, `tool_name`, `tool_config_json`). `tool_config_json` would store SharePoint URL, SQL connection string alias, etc.
  
- `[ ] TODO` **5.4:** **SQL Connector:** Implement `SQLTool` using LangChain's SQL Agent. The `execute` method will take a natural language query and return the result. The tool is configured with a connection string alias from Key Vault.
  
- `[ ] TODO` **5.5:** **SharePoint/Box RAG Connector:**
  
  - `[ ] TODO` **5.5.1:** Create an ingestion script (`python -m scripts.ingest_sharepoint --site-url ...`). This script chunks, embeds, and stores document vectors in the vector DB with source pointers.
    
  - `[ ] TODO` **5.5.2:** Implement `SharePointRAGTool`. Its `execute` method takes a query, finds relevant chunks from the vector DB, and returns them as context.
    
  - `[ ] TODO` **5.5.3:** Repeat 5.5.1 and 5.5.2 for a `BoxRAGTool`.
    
- `[ ] TODO` **5.6:** Integrate tools into the chat logic. Use a LangChain Agent executor that, given the user prompt and the configured tools for the bot, decides whether to call a tool or respond directly.
  
- `[ ] TODO` **5.7:** Write Pytest tests for each tool, mocking external API calls (e.g., `psycopg2` for SQL, `msal` for SharePoint).
  

## Module 6: Chat History & Search

- `[ ] TODO` **6.1:** Implement paginated list endpoints: `GET /api/v1/sessions` and `GET /api/v1/sessions/{session_id}/messages`.
  
- `[ ] TODO` **6.2:** Implement a search endpoint `GET /api/v1/search?q=...`. Start with a simple SQL `ILIKE` on `ChatMessage.content`.
  
- `[ ] TODO` **6.3:** **(Advanced)** Switch search logic to use full-text search capabilities of PostgreSQL or Azure SQL for better performance and relevance.
  
- `[ ] TODO` **6.4:** Write Pytest tests to ensure a user can only list and search their own chat history.
  

## Module 7: Usage Tracking & Cost Management

- `[ ] TODO` **7.1:** Create `TokenUsageLog` DB model: (`id`, `user_id`, `bot_id`, `model_name`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `cost`, `timestamp`).
  
- `[ ] TODO` **7.2:** Modify the `llm_gateway` and chat logic to accurately count tokens for both prompt and completion (most model APIs return this).
  
- `[ ] TODO` **7.3:** After a chat completion, record the usage in the `TokenUsageLog` table as a background task.
  
- `[ ] TODO` **7.4:** Implement an API endpoint `GET /api/v1/usage/summary` to return aggregated usage data for the current user (e.g., total cost today, this month).
  
- `[ ] TODO` **7.5:** Write Pytest tests for the usage logging and summary endpoints.
  

## Module 8: Advanced Features (Feedback & Async Tools)

- `[ ] TODO` **8.1:** **Feedback:** Create `MessageFeedback` DB model (`id`, `message_id`, `user_id`, `rating` [1 for up, -1 for down], `comment`).
  
- `[ ] TODO` **8.2:** **Feedback:** Implement `POST /api/v1/messages/{message_id}/feedback` endpoint to record user feedback.
  
- `[ ] TODO` **8.3:** **Async Tools:** Integrate `Celery` or FastAPI's `BackgroundTasks` for long-running tools.
  
- `[ ] TODO` **8.4:** **Async Tools:** Modify the agent executor. If a tool is marked as async, it returns an immediate "I'm working on it..." message with a task ID. A separate mechanism (like WebSockets or polling) will be needed on the frontend to get the final result.
  

## Module 9: Admin Dashboard

- `[ ] TODO` **9.1:** Create a new set of API endpoints under `/api/v1/admin/` protected by an `is_admin` check on the user.
  
- `[ ] TODO` **9.2:** Admin endpoint: `GET /admin/usage/overview` to see system-wide token usage and costs.
  
- `[ ] TODO` **9.3:** Admin endpoint: `GET /admin/users` to list all users.
  
- `[ ] TODO` **9.4:** Admin endpoint: `GET /admin/feedback` to view all user-submitted feedback.
  
- `[ ] TODO` **9.5:** Write Pytest tests for all admin endpoints, ensuring they fail for non-admin users.
  

## Module 10: Frontend Development (React)

- `[ ] TODO` **10.1 - 10.7:** (As specified in the previous list: Login, Chat UI, Sidebar, Bot Forms, etc.)
  
- `[ ] TODO` **10.8:** Integrate a UI library like Material-UI or Shadcn/ui for a consistent look and feel.
  
- `[ ] TODO` **10.9:** Add UI elements for the feedback (thumbs up/down buttons on messages).
  
- `[ ] TODO` **10.10:** Build the UI for the Admin Dashboard with tables and charts for usage data.
  
- `[ ] TODO` **10.11:** Implement the UI for granular bot sharing (e.g., a modal to search for users and assign permissions).
  

## Module 11: Deployment & CI/CD

- `[ ] TODO` **11.1:** Create Bicep or Terraform scripts to provision Azure App Service, Azure SQL, Azure Key Vault, and Azure AI Search.
  
- `[ ] TODO` **11.2:** Create a GitHub Actions workflow that runs linting and Pytest on every PR.
  
- `[ ] TODO` **11.3:** On merge to `main`, the workflow should build and push the backend Docker image to Azure Container Registry.
  
- `[ ] TODO` **11.4:** The workflow should then trigger a deployment to the Azure App Service.
  
- `[ ] TODO` **11.5:** Configure production App Service settings to pull secrets from Azure Key Vault.
