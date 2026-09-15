import json, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from slowapi.errors import RateLimitExceeded
from pathlib import Path

from app.config import settings
from app.database.db import init_db, SessionLocal
from app.database.seed import seed
from app.database.models import Conversation, Approval, Ticket
from app.auth.security import authenticate, create_token, current_user
from app.security.validation import validate_username, validate_message, sanitize_input
from app.security.rate_limit import limiter
from app.agents.graph import run_agent
from app.observability.logging import configure_logging, logger
from app.observability.audit import audit
from app.tools.tickets import list_tickets, get_ticket, create_ticket, serialize
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)

class ApprovalRequest(BaseModel):
    approve: bool

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    seed()
    try:
        from app.rag.ingestion import ingest
        ingest()
    except Exception as e:
        logger.warning("rag_ingestion_failed", error=str(e))
    yield

app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app.mount(
    "/ui",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend",
)
app.state.limiter = limiter
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/ui/")

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return Response("Rate limit exceeded", status_code=429)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        logger.exception("request_failed", request_id=request_id)
        raise

@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = authenticate(form.username, form.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    validate_username(user.username)
    return {"access_token": create_token(user), "token_type": "bearer", "role": user.role}

@app.get("/status")
def status():
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment,
            "llm_provider": settings.llm_provider}

@app.get("/health")
def health():
    # Render uses this endpoint for instance health checks. Keep it fast and
    # verify the critical relational datastore rather than calling the LLM.
    db = SessionLocal()
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "ok"}
    except Exception as exc:
        logger.error("health_check_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="database unavailable")
    finally:
        db.close()

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, chat_request: ChatRequest, user=Depends(current_user)):
    validate_username(user.username)
    clean_message = sanitize_input(validate_message(chat_request.message, settings.max_message_length))
    result = run_agent(user.username, user.role, clean_message)
    reply = result["response"]
    db = SessionLocal()
    try:
        db.add(Conversation(username=user.username, role=user.role, message=clean_message, response=reply))
        db.commit()
    finally:
        db.close()
    audit(user.id, "chat", "conversation", f"message_length={len(clean_message)}")
    logger.info("agent_response", username=user.username)
    return {"reply": reply, "approval_id": result.get("approval_id"), "search_query": result.get("search_query"),
            "sources": [d["source"] for d in result.get("documents", [])]}

@app.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(request: Request, chat_request: ChatRequest, user=Depends(current_user)):
    clean = sanitize_input(validate_message(chat_request.message, settings.max_message_length))
    result = run_agent(user.username, user.role, clean)
    reply = result["response"]
    def iterator():
        for word in reply.split():
            yield word + " "
    return StreamingResponse(iterator(), media_type="text/plain")

@app.get("/tickets")
def tickets(user=Depends(current_user)):
    return [serialize(t) for t in list_tickets(user.username, user.role)]

@app.get("/tickets/{ticket_id}")
def ticket(ticket_id: int, user=Depends(current_user)):
    t = get_ticket(ticket_id, user.username, user.role)
    if t == "FORBIDDEN":
        raise HTTPException(403, "You are not allowed to access this ticket")
    if not t:
        raise HTTPException(404, "Ticket not found")
    return serialize(t)

@app.get("/history")
def history(user=Depends(current_user)):
    db = SessionLocal()
    try:
        rows = db.query(Conversation).filter_by(username=user.username).order_by(Conversation.id.desc()).limit(50).all()
        return [{"message": r.message, "response": r.response, "created_at": r.created_at} for r in rows]
    finally:
        db.close()

@app.delete("/history")
def clear_history(user=Depends(current_user)):
    db = SessionLocal()
    try:
        db.query(Conversation).filter(Conversation.username == user.username).delete()
        db.commit()
        audit(user.id, "delete_history", user.username)
        return {"message": "Your history was cleared"}
    finally:
        db.close()

@app.get("/approvals")
def approvals(user=Depends(current_user)):
    db = SessionLocal()
    try:
        q = db.query(Approval).filter(Approval.status == "pending")

        if user.role not in ("helpdesk", "admin"):
            q = q.filter(Approval.username == user.username)

        return [
            {
                "id": a.id,
                "username": a.username,
                "action": a.action,
                "payload": a.payload,
                "status": a.status,
            }
            for a in q.order_by(Approval.id.desc()).all()
        ]
    finally:
        db.close()

@app.post("/approvals/{approval_id}")
def resolve_approval(approval_id: int, req: ApprovalRequest, user=Depends(current_user)):
    db = SessionLocal()
    try:
        a = db.get(Approval, approval_id)
        if not a: raise HTTPException(404, "Approval not found")
        if a.username != user.username and user.role not in ("helpdesk", "admin"):
            raise HTTPException(403, "Not allowed")
        if a.status != "pending": return {"status": a.status}
        if not req.approve:
            a.status = "rejected"; db.commit()
            audit(user.id, "approval_rejected", str(a.id))
            return {"status": "rejected"}
        payload = json.loads(a.payload)
        title = "AI-created IT ticket"
        desc = payload["message"]
        t = create_ticket(a.username, title, desc, "high", idempotency_key=f"approval-{a.id}")
        a.status = "approved"; db.commit()
        audit(user.id, "approval_approved", str(a.id))
        return {"status": "approved", "ticket": serialize(t)}
    finally:
        db.close()
