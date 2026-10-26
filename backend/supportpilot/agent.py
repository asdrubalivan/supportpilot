"""Support agent: a LlamaIndex FunctionAgent over Ollama that picks tools, then answers with citations.

Try it with: uv run python -m supportpilot.agent "Can I return order 1234?"
"""

import asyncio
import re
import sys
from datetime import date
from functools import lru_cache

from llama_index.core.agent.workflow import FunctionAgent, ToolCallResult
from llama_index.core.tools import FunctionTool
from llama_index.llms.ollama import Ollama
from pydantic import BaseModel

from supportpilot import config
from supportpilot.orders import Order, get_latest_order, get_order
from supportpilot.retrieval import build_retriever

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


@lru_cache
def get_retriever():
    return build_retriever()


def format_order(order: Order | None) -> str:
    return order.model_dump_json(indent=2) if order else "Order not found."


def retrieve(query: str, passages: dict[str, Passage]) -> str:
    """Retrieve policy chunks, record them in retrieval order, and format them for the prompt."""
    results = get_retriever().retrieve(query)
    for r in results:
        _, _, body = r.node.get_content().partition("\n")  # drop the "## Heading" line
        passages.setdefault(r.node.node_id, Passage(
            id=r.node.node_id,
            document=r.node.metadata["document"],
            section=r.node.metadata["section"],
            text=body.strip(),
        ))
    return "\n".join(f'<chunk id="{r.node.node_id}">\n{r.node.get_content()}\n</chunk>' for r in results)


def build_tools(message: str, customer_id: int, passages: dict[str, Passage]) -> list[FunctionTool]:
    # customer_id is captured here and never exposed to the LLM as a tool argument.
    # Order ids the model may look up: those the customer typed, plus any returned by get_latest_order.
    allowed_order_ids = {int(n) for n in re.findall(r"\d+", message)}

    def search_policies(query: str) -> str:
        """Search the store's policy documents (returns, refunds, shipping, promotions, catalog)
        with a different query than the customer's message. Returns policy chunks, each with an id to cite."""
        return retrieve(query, passages)

    def get_order_tool(order_id: int) -> str:
        """Look up one of the customer's orders by its order number."""
        if order_id not in allowed_order_ids:
            return "Rejected: the customer did not mention this order number. Ask them for it."
        return format_order(get_order(order_id, customer_id))

    def get_latest_order_tool() -> str:
        """Look up the customer's most recent order."""
        order = get_latest_order(customer_id)
        if order:
            allowed_order_ids.add(order.order_id)
        return format_order(order)

    return [
        FunctionTool.from_defaults(fn=search_policies),
        FunctionTool.from_defaults(fn=get_order_tool, name="get_order"),
        FunctionTool.from_defaults(fn=get_latest_order_tool, name="get_latest_order"),
    ]


async def answer(message: str, customer_id: int) -> AgentResult:
    passages: dict[str, Passage] = {}
    agent = FunctionAgent(
        tools=build_tools(message, customer_id, passages),
        llm=get_llm(),
        system_prompt=SYSTEM_PROMPT.format(today=date.today().isoformat(), no_info=NO_INFO),
        allow_parallel_tool_calls=True,
    )

    # Retrieval always runs on the customer's own words: a small model anchored on an order
    # number tends to skip search_policies, and its rewritten queries retrieved worse chunks.
    policies = retrieve(message, passages)
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
