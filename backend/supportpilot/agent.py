"""Support agent: a LlamaIndex FunctionAgent over Ollama that picks tools, then answers with citations.

The tools live in the MCP server (supportpilot.mcp_server); this agent is its client. Start the server first.

Try it with: uv run python -m supportpilot.agent "Can I return order 1234?"
"""

import asyncio
import json
import re
import sys
from datetime import date
from functools import lru_cache

import httpx2
from llama_index.core.agent.workflow import FunctionAgent, ToolCallResult
from llama_index.core.tools import FunctionTool
from llama_index.llms.ollama import Ollama
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel

from supportpilot import config
from supportpilot.mcp_server import CUSTOMER_HEADER

MAX_ITERATIONS = 5
NO_INFO = "I don't have information about that."
CITATION_RE = re.compile(r"\[([a-z0-9-]+\.md#[a-z0-9-]+)\]")

SYSTEM_PROMPT = """You are the customer support agent for Old Pages Books, an online store of classic books.
Today is {today}.

Each customer message comes with the most relevant policy chunks inside <policies>, each in a <chunk id="...">.

Rules:
- Answer only from the policy chunks, order data, and tool results. Never use outside knowledge about the store.
- Only state what the chunks or order data say. If a chunk doesn't mention something, don't assume it.
- For questions about a specific order, call get_order with the order number the customer gave.
  If the customer refers to their last or most recent order without a number, call get_latest_order.
- If the provided chunks don't cover the question, you may call search_policies with a different query.
- You may call several tools, in parallel or one after another.
- After every statement based on a policy, cite the id of the chunk that supports it in square brackets.
  Only cite ids of chunks you were given. Do not cite order data.
- If you can answer part of the question, answer that part with citations, and say clearly which part
  you can't verify.
- Only if nothing you were given answers any part of the question, reply exactly: "{no_info}" and cite nothing.
- Be brief and concrete. Use the order's dates and amounts when relevant.

<example>
This example only shows the citation format. Its id is fictional: NEVER cite it.
"Books can be exchanged within 10 days [file.md#section-id]."
</example>"""


class Passage(BaseModel):
    id: str
    document: str
    section: str
    text: str


class AgentResult(BaseModel):
    answer: str
    citations: list[str]
    invalid_citations: list[str]
    tools_called: list[str]
    retrieved_ids: list[str]
    # Retrieved chunks in retrieval order, so a client can show the cited passages.
    passages: list[Passage]


@lru_cache
def get_llm() -> Ollama:
    return Ollama(
        model=config.CHAT_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        request_timeout=120.0,
        thinking=False,
        temperature=0,
    )


async def call(client: Client, tool: str, arguments: dict | None = None):
    result = await client.call_tool(tool, arguments or {})
    if result.is_error:
        raise RuntimeError(f"MCP tool {tool} failed: {result.content}")
    return result.structured_content["result"]


def format_order(order: dict | None) -> str:
    return json.dumps(order, indent=2) if order else "Order not found."


async def retrieve(client: Client, query: str, passages: dict[str, Passage]) -> str:
    """Retrieve policy chunks, record them in retrieval order, and format them for the prompt."""
    chunks = await call(client, "search_policies", {"query": query})
    for c in chunks:
        _, _, body = c["content"].partition("\n")  # drop the "## Heading" line
        passages.setdefault(c["id"], Passage(
            id=c["id"], document=c["document"], section=c["section"], text=body.strip()
        ))
    return "\n".join(f'<chunk id="{c["id"]}">\n{c["content"]}\n</chunk>' for c in chunks)


def build_tools(client: Client, message: str, passages: dict[str, Passage]) -> list[FunctionTool]:
    # The customer is fixed on the MCP connection and never exposed to the LLM as a tool argument.
    # Order ids the model may look up: those the customer typed, plus any returned by get_latest_order.
    # This check stays here because only the client sees the customer's message.
    allowed_order_ids = {int(n) for n in re.findall(r"\d+", message)}

    async def search_policies(query: str) -> str:
        """Search the store's policy documents (returns, refunds, shipping, promotions, catalog)
        with a different query than the customer's message. Returns policy chunks, each with an id to cite."""
        return await retrieve(client, query, passages)

    async def get_order_tool(order_id: int) -> str:
        """Look up one of the customer's orders by its order number."""
        if order_id not in allowed_order_ids:
            return "Rejected: the customer did not mention this order number. Ask them for it."
        return format_order(await call(client, "get_order", {"order_id": order_id}))

    async def get_latest_order_tool() -> str:
        """Look up the customer's most recent order."""
        order = await call(client, "get_latest_order")
        if order:
            allowed_order_ids.add(order["order_id"])
        return format_order(order)

    return [
        FunctionTool.from_defaults(async_fn=search_policies),
        FunctionTool.from_defaults(async_fn=get_order_tool, name="get_order"),
        FunctionTool.from_defaults(async_fn=get_latest_order_tool, name="get_latest_order"),
    ]


async def answer(message: str, customer_id: int) -> AgentResult:
    # One MCP session per question, with the customer set by our code on the connection.
    async with (
        httpx2.AsyncClient(headers={CUSTOMER_HEADER: str(customer_id)}, timeout=120.0) as http,
        Client(streamable_http_client(config.MCP_URL, http_client=http)) as client,
    ):
        return await run_agent(client, message)


async def run_agent(client: Client, message: str) -> AgentResult:
    passages: dict[str, Passage] = {}
    agent = FunctionAgent(
        tools=build_tools(client, message, passages),
        llm=get_llm(),
        system_prompt=SYSTEM_PROMPT.format(today=date.today().isoformat(), no_info=NO_INFO),
        allow_parallel_tool_calls=True,
    )

    # Retrieval always runs on the customer's own words: a small model anchored on an order
    # number tends to skip search_policies, and its rewritten queries retrieved worse chunks.
    policies = await retrieve(client, message, passages)
    user_msg = f"<policies>\n{policies}\n</policies>\n\n<customer_message>\n{message}\n</customer_message>"

    tools_called = []
    handler = agent.run(user_msg=user_msg, max_iterations=MAX_ITERATIONS)
    async for event in handler.stream_events():
        if isinstance(event, ToolCallResult):
            tools_called.append(event.tool_name)
    response = await handler

    text = str(response.response.content or "").strip()
    citations = list(dict.fromkeys(CITATION_RE.findall(text)))
    return AgentResult(
        answer=text,
        citations=citations,
        invalid_citations=[c for c in citations if c not in passages],
        tools_called=tools_called,
        retrieved_ids=list(passages),
        passages=list(passages.values()),
    )


if __name__ == "__main__":
    result = asyncio.run(answer(" ".join(sys.argv[1:]), customer_id=1))
    print(result.model_dump_json(indent=2))
