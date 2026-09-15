from typing import TypedDict, Any

class AgentState(TypedDict, total=False):
    username: str
    role: str
    message: str
    intent: str
    search_query: str
    documents: list[dict[str, Any]]
    response: str
    approval_required: bool
    approval_id: int | None
    action: dict[str, Any]
