# DCRI GPT: Custom AI Chatbot Platform

DCRI GPT is a powerful, enterprise-ready platform for building, managing, and sharing custom AI chatbots. It allows users to create specialized AI assistants that can connect to internal data sources like SharePoint, Box, and SQL databases, providing accurate, context-aware answers.

## ✨ Key Features

- **Model Selection:** Choose from various LLMs (e.g., GPT-5, GPT-5-mini, GPT-5-nano, GPT-4, GPT-3.5-Turbo) for different tasks.
  
- **Custom Chatbots:** Users can create their own bots with unique system prompts and instructions.
  
- **Enterprise Tool Calling:** Securely connect bots to live data sources:
  
  - SharePoint (document retrieval)
    
  - Box (document retrieval)
    
  - SQL Server (natural language to query)
    
- **Persistent Chat History:** All conversations are saved and are fully searchable.
  
- **Granular Sharing:** Share bots with specific users, groups, or publicly via a link.
  
- **Usage & Cost Tracking:** Monitor token usage per user and per bot.
  
- **Response Feedback:** Users can rate AI responses (👍/👎) to help improve quality.
  
- **Admin Dashboard:** A central place for administrators to manage users, bots, and view system-wide analytics.
  
- **Asynchronous Tools:** Long-running tasks (like complex SQL queries) execute in the background without blocking the UI.
  

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python)
  
- **Frontend:** React (Vite)
  
- **Database:** SQLAlchemy ORM with support for SQLite (local) and Azure SQL/PostgreSQL (prod).
  
- **AI Framework:** LangChain
  
- **Vector Search:** ChromaDB (local) and Azure AI Search (prod)
  
- **Authentication:** JWT with OAuth2
  
- **Testing:** Pytest
  
- **Deployment:** Docker, Azure App Service, Azure Key Vault
  

## 🚀 Getting Started (Local Development)

### Prerequisites

- Python 3.10+
  
- Node.js 18+
  
- Docker & Docker Compose
  

### 1. Clone the Repository

```
git clone <your-repo-url>cd <your-repo-name>
```

### 2. Configure Environment

Copy the example environment file for the backend and fill in your details.

```
cd backendcp .env.example .env# Open .env and add your API keys, etc.
```

### 3. Launch Services

The entire local stack (FastAPI server, database, frontend) can be launched with Docker Compose.

```
docker-compose up --build
```

- Backend API will be available at `http://localhost:8000`
  
- API documentation at `http://localhost:8000/docs`
  
- Frontend will be available at `http://localhost:5173`
  

### 4. Running Tests

To run the backend test suite:

```
docker-compose exec backend pytest
```
