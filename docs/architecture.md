# Architecture

The POC separates the system into API/security, agent orchestration, retrieval, tools, persistence, reliability, and observability.

Core flow:
User -> FastAPI -> JWT/RBAC -> LangGraph -> Agentic RAG/Tools -> Approval -> PostgreSQL -> Response.

Security principle:
The LLM proposes actions; application code decides whether the authenticated user is authorized to execute them.

Agentic RAG:
1. Analyze support intent
2. Rewrite query
3. Retrieve from vector store
4. Grade relevance
5. Retry retrieval with original query when evidence is weak
6. Generate grounded answer
