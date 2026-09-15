import json

from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentState
from app.llm.provider import invoke_llm, SYSTEM
from app.rag.agentic import agentic_retrieve
from app.security.guardrails import detect_prompt_injection, output_guardrail
from app.database.db import SessionLocal
from app.database.models import Approval
from app.tools.tickets import list_tickets, get_ticket, serialize


def classify(state):
    msg = state["message"].lower()

    if any(
        x in msg
        for x in [
            "ticket",
            "issue",
            "problem",
            "vpn",
            "outlook",
            "laptop",
            "password",
        ]
    ):
        return {"intent": "it_support"}

    return {"intent": "general"}


def retrieve(state):
    query, docs = agentic_retrieve(state["message"])
    return {
        "search_query": query,
        "documents": docs,
    }


def decide_action(state):
    msg = state["message"].lower()

    needs_create = (
        ("create" in msg or "open" in msg or "raise" in msg)
        and "ticket" in msg
    )

    return {
        "approval_required": needs_create,
        "action": {"type": "create_ticket"} if needs_create else {"type": "none"},
    }


def is_ticket_list_request(message):
    msg = message.lower()

    return (
        "my tickets" in msg
        or "list my tickets" in msg
        or "show my tickets" in msg
        or "show me my tickets" in msg
    )


def extract_ticket_id(message):
    words = message.lower().replace("#", " ").split()

    for word in words:
        if word.isdigit():
            return int(word)

    return None


def ticket_answer(state):
    username = state["username"]
    role = state["role"]
    message = state["message"]

    if is_ticket_list_request(message):
        tickets = list_tickets(username, role)

        if not tickets:
            return {
                "response": "You currently have no tickets."
            }

        ticket_data = [serialize(ticket) for ticket in tickets]

        lines = ["Here are your tickets:"]

        for ticket in ticket_data:
            lines.append(
                f"#{ticket['id']} | "
                f"{ticket['title']} | "
                f"Priority: {ticket['priority']} | "
                f"Status: {ticket['status']}"
            )

        return {
            "response": "\n".join(lines)
        }

    ticket_id = extract_ticket_id(message)

    if ticket_id is not None:
        ticket = get_ticket(ticket_id, username, role)

        if ticket == "FORBIDDEN":
            return {
                "response": "You are not authorized to access this ticket."
            }

        if ticket is None:
            return {
                "response": f"Ticket #{ticket_id} was not found."
            }

        data = serialize(ticket)

        response = (
            f"Ticket #{data['id']}\n"
            f"Owner: {data['owner']}\n"
            f"Title: {data['title']}\n"
            f"Description: {data['description']}\n"
            f"Priority: {data['priority']}\n"
            f"Status: {data['status']}"
        )

        return {
            "response": response
        }

    return None


def answer(state):
    ticket_response = ticket_answer(state)

    if ticket_response:
        return ticket_response

    docs = state.get("documents", [])

    context = "\n\n".join(
        f"[{doc['source']}] {doc['text']}"
        for doc in docs
    )

    prompt = f"""{SYSTEM}

Retrieved company evidence:
{context or '[No relevant company evidence found]'}

User request:
{state['message']}

Answer using the evidence when relevant.
If evidence is insufficient, say so clearly.
Do not invent company procedures or policies.
Do not claim an action was completed unless the application confirms it.
Do not call tools or functions from this response.
"""

    result = invoke_llm(
        [
            ("system", prompt),
            ("human", state["message"]),
        ]
    )

    return {
        "response": output_guardrail(result.content.strip())
    }


def approval(state):
    db = SessionLocal()

    try:
        payload = json.dumps(
            {
                "message": state["message"],
                "action": state["action"],
            }
        )

        approval_record = Approval(
            username=state["username"],
            action="create_ticket",
            payload=payload,
        )

        db.add(approval_record)
        db.commit()
        db.refresh(approval_record)

        return {
            "approval_id": approval_record.id,
            "response": (
                "Approval required before creating a ticket. "
                f"Approval ID: {approval_record.id}. "
                "Use the Approve action in the UI."
            ),
        }

    finally:
        db.close()


def blocked(state):
    return {
        "response": (
            "I can't help with that request because it attempts "
            "to bypass agent instructions or access sensitive information."
        )
    }


def route_after_classify(state):
    return (
        "retrieve"
        if state["intent"] == "it_support"
        else "answer"
    )


def route_after_decide(state):
    return (
        "approval"
        if state.get("approval_required")
        else "answer"
    )


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify)
    graph.add_node("retrieve", retrieve)
    graph.add_node("decide_action", decide_action)
    graph.add_node("answer", answer)
    graph.add_node("approval", approval)
    graph.add_node("blocked", blocked)

    graph.add_edge(START, "classify")

    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "retrieve": "retrieve",
            "answer": "answer",
        },
    )

    graph.add_edge("retrieve", "decide_action")

    graph.add_conditional_edges(
        "decide_action",
        route_after_decide,
        {
            "approval": "approval",
            "answer": "answer",
        },
    )

    graph.add_edge("answer", END)
    graph.add_edge("approval", END)

    return graph.compile()


graph = build_graph()


def run_agent(username, role, message):
    if detect_prompt_injection(message):
        return {
            "response": (
                "I can't help with bypassing instructions "
                "or revealing sensitive information."
            ),
            "approval_id": None,
        }

    state = graph.invoke(
        {
            "username": username,
            "role": role,
            "message": message,
        }
    )

    return state