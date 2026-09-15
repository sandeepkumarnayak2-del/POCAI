# POCAI — Enterprise AI Service Desk Agent

POCAI is an enterprise-style AI Service Desk Agent demonstrating **GenAI, RAG, AI agents, secure tool execution, RBAC, human approval, and cloud deployment**.

## 🚀 Live Demo

[Open POCAI](https://enterprise-ai-agent-api.onrender.com/ui/)

## ✨ Features

- **LLM:** Groq — `openai/gpt-oss-120b`
- **Agent:** LangGraph
- **RAG:** Chroma + internal IT documents
- **Backend:** FastAPI
- **Tools:** Ticket creation, listing and lookup
- **Security:** JWT authentication, RBAC, validation and prompt-injection guardrails
- **Human-in-the-loop:** Approval required before ticket creation
- **Database:** PostgreSQL in production, SQLite locally
- **Observability:** Logs, audit events and Prometheus metrics
- **Deployment:** Docker + Render
- **Frontend:** HTML/CSS/JavaScript

## 🏗️ Architecture

```text
User
 ↓
FastAPI → Authentication / RBAC
 ↓
LangGraph Agent
 ├── RAG → Chroma → IT Documents
 ├── Tools → Tickets
 └── MCP → External Services
 ↓
Human Approval
 ↓
PostgreSQL
 ↓
Response + Audit / Metrics
```

**Key principle:** The LLM handles reasoning, while application code enforces authorization and business rules.

## 🎫 Example

```text
"My VPN is not working"
        ↓
RAG retrieves IT guidance
        ↓
"Create a high-priority ticket"
        ↓
Human approval required
        ↓
Approved → Ticket created
```

## 🔐 Security

Users can only access resources they are authorized to access. For example, one user cannot access another user's ticket.

The system also handles basic prompt-injection attempts and keeps secrets such as API keys outside the application code and Git repository.

## 🧰 Tech Stack

Python · FastAPI · LangGraph · LangChain · Groq · Chroma · PostgreSQL · JWT · Docker · Render · Prometheus

## 🎯 Purpose

This project demonstrates practical **AI Engineering patterns for enterprise applications**, rather than a basic LLM chatbot.

## 🔮 Future Improvements

SSO/OAuth2, ServiceNow/Jira integration, stronger RAG evaluation, distributed tracing, centralized secrets, advanced security testing and production-grade vector infrastructure.
