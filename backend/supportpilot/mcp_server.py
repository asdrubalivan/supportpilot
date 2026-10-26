"""MCP server exposing the read-only support tools over Streamable HTTP.

Run with: uv run python -m supportpilot.mcp_server

The customer comes from the X-Customer-Id header of the MCP connection, set by the caller's code,
never from tool arguments the model writes. Until real auth exists, anyone who can reach this port can
claim any customer, so it only listens on localhost.
"""

from functools import lru_cache

from mcp.server.mcpserver import Context, MCPServer
from pydantic import BaseModel

from supportpilot import config
from supportpilot.orders import Order, get_latest_order, get_order
from supportpilot.retrieval import build_retriever

CUSTOMER_HEADER = "x-customer-id"

server = MCPServer(name="supportpilot", instructions="Old Pages Books support tools (read-only).")


class Chunk(BaseModel):
    id: str
    document: str
    section: str
    # Full chunk content, starting with its "## Heading" line.
    content: str


@lru_cache
def get_retriever():
    return build_retriever()


def customer_id(ctx: Context) -> int:
    request = ctx.request_context.request
    value = request.headers.get(CUSTOMER_HEADER) if request is not None else None
    if value is None or not value.isdigit():
        raise ValueError("Missing or invalid X-Customer-Id on the MCP connection.")
    return int(value)


@server.tool()
def search_policies(query: str) -> list[Chunk]:
    """Search the store's policy documents (returns, refunds, shipping, promotions, catalog).
    Returns policy chunks, each with an id to cite."""
    return [
        Chunk(
            id=r.node.node_id,
            document=r.node.metadata["document"],
            section=r.node.metadata["section"],
            content=r.node.get_content(),
        )
        for r in get_retriever().retrieve(query)
    ]


@server.tool(name="get_order")
def get_order_tool(order_id: int, ctx: Context) -> Order | None:
    """Look up one of the customer's orders by its order number. Returns null if not found."""
    return get_order(order_id, customer_id(ctx))


@server.tool(name="get_latest_order")
def get_latest_order_tool(ctx: Context) -> Order | None:
    """Look up the customer's most recent order. Returns null if they have none."""
    return get_latest_order(customer_id(ctx))


if __name__ == "__main__":
    server.run("streamable-http", host="127.0.0.1", port=config.MCP_PORT)
