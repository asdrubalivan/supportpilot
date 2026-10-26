"""MCP server exposing the read-only support tools over Streamable HTTP.

Run with: uv run python -m supportpilot.mcp_server

The customer comes from the bearer token on the MCP connection: an access token signed by the
identity provider, mapped to a customer through identity_links. Never from tool arguments the model writes.
"""

from functools import lru_cache

from mcp.server.mcpserver import Context, MCPServer
from pydantic import BaseModel

from supportpilot import config
from supportpilot.auth import AuthError, find_customer, verify_token
from supportpilot.orders import Order, get_latest_order, get_order
from supportpilot.retrieval import build_retriever

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
    scheme, _, token = (request.headers.get("authorization", "") if request is not None else "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("Missing bearer token on the MCP connection.")
    claims = verify_token(token)
    # Linking happens at login; an unlinked identity has no orders to see.
    if (customer := find_customer(claims["sub"])) is None:
        raise AuthError("This identity is not linked to a customer.")
    return customer


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
