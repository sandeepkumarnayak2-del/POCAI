"""
Local MCP server for the POC.

Run:
    python -m app.mcp.server

The MCP tools intentionally call application-layer functions rather than granting
the model direct database access.
"""
from mcp.server.fastmcp import FastMCP
from app.tools.tickets import list_tickets, get_ticket

mcp = FastMCP("enterprise-service-desk")

@mcp.tool()
def search_my_tickets(username: str, role: str = "employee") -> list[dict]:
    return [
        {"id": t.id, "title": t.title, "status": t.status, "priority": t.priority}
        for t in list_tickets(username, role)
    ]

@mcp.tool()
def get_ticket_for_user(ticket_id: int, username: str, role: str = "employee") -> dict:
    t = get_ticket(ticket_id, username, role)
    if t == "FORBIDDEN":
        return {"error": "forbidden"}
    if not t:
        return {"error": "not_found"}
    return {"id": t.id, "title": t.title, "status": t.status, "priority": t.priority}

if __name__ == "__main__":
    mcp.run()
