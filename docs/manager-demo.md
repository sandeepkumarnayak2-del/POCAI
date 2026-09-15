# Demo flow

The easiest way to show the prototype is to start with a normal support question
and then move into an action.

## 1. Knowledge question

Log in as `alice` and ask:

> My VPN stopped working after my laptop update. What should I check?

Point out that the answer comes from the IT knowledge base rather than from a
hard-coded response.

## 2. Create a ticket

Follow up with:

> The problem is still there. Please create a high priority ticket.

The agent should prepare the action and stop for approval.

## 3. Approval

Approve the pending request and show the newly created ticket.

## 4. Permissions

Try to access a ticket belonging to another user. The API should reject it.

## 5. Guardrail

Try a simple prompt-injection request. The request should be blocked instead of
exposing internal instructions.

## 6. API and monitoring

The FastAPI docs are available under `/docs`; the Prometheus endpoint is `/metrics`.

For the technical discussion, use `docs/architecture.md` to walk through the
agent, retrieval, tools, database and deployment pieces.
