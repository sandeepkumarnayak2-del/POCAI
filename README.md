# Enterprise AI Service Desk Agent

A small AI service-desk prototype built to explore how an LLM can work with company
knowledge, internal tools and approval workflows.

The idea is deliberately simple: a user asks a support question, the agent looks up
relevant internal documentation, and it can create a ticket when an action is needed.

## What is included

- FastAPI backend
- Streamlit demo UI
- LangGraph agent workflow
- RAG over the example IT documents
- Ticket tools with user-level access checks
- Approval step before ticket creation
- Basic prompt/output guardrails
- JWT authentication
- PostgreSQL support (SQLite is useful for local development)
- Redis support for rate limiting
- Request IDs and Prometheus metrics
- MCP example server
- Docker and Render deployment files
- A few focused tests

## Local setup

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add the Groq key.

Start the API:

```bash
uvicorn app.main:app --reload
```

Start the UI in another terminal:

```bash
streamlit run frontend/streamlit_app.py
```

The API is available at `http://localhost:8000` and the UI at
`http://localhost:8501`.

Demo users are created automatically on startup. They are only for the local demo.

## Deployment

The repository contains a `render.yaml` Blueprint plus separate API and UI Dockerfiles.
The Groq API key should be configured as a secret in Render, not committed to git.

## Project layout

```text
app/
  agents/          agent state and workflow
  auth/            authentication helpers
  database/        database models and setup
  llm/             model configuration
  observability/   logging, metrics and audit helpers
  rag/             document indexing and retrieval
  security/        validation, guardrails and rate limiting
  tools/           business actions exposed to the agent
frontend/           Streamlit demo
data/documents/     example IT knowledge
tests/              focused unit tests
docs/               architecture and demo notes
```

This is a portfolio/POC project rather than a production security boundary. The
authentication, permissions, model access and deployment settings would need another
security review before being used with real company data.
