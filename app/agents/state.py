from typing import TypedDict, Any

#Total false- All fileds are optional
#Used for shared agent stares, communication
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
