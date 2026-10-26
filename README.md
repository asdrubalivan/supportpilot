# SupportPilot

A support agent for **Old Pages Books**, a fictional online store of classic books. It answers questions about the store's policies with citations to the exact passage, and looks up the customer's orders through a fixed tool. Everything runs locally on Ollama.

This is a learning lab (see [`AI_ASSISTED_DEVELOPMENT.md`](AI_ASSISTED_DEVELOPMENT.md)). Slice 1 is read-only and single-turn.

## How it works

```
OFFLINE   data/policies/*.md ─ one chunk per heading (stable <!-- id --> anchors)
            ─ + 3 generated customer questions per chunk (doc2query)
            ─ embed (nomic-embed-text) ─> pgvector

ONLINE    question + customer_id
            ─> vector search on the customer's own words (k=4)        [always]
            ─> FunctionAgent (qwen3:8b) with tools:
                 get_order(order_id)      scoped to customer_id, SQL written by hand
                 get_latest_order()
                 search_policies(query)   optional extra search
            ─> answer with [file.md#section] citations
            ─> citations checked against what was actually retrieved
```

Design decisions worth knowing:

- **Fixed tools, not text-to-SQL.** `customer_id` is captured in a closure, never a tool argument, so the model can't ask for another customer's orders. A missing order and someone else's order return the same "not found".
- **Retrieval always runs.** With the LLM deciding when to search, the 8B model anchored on order numbers and skipped policy search ("Can I return order 1234?" → no policy, no answer). The backend now always retrieves with the customer's own words; `search_policies` stays available for extra searches.
- **Order ids must come from the customer.** `get_order` rejects ids that don't appear in the message or in a `get_latest_order` result, to block invented arguments.
- **Prices are snapshotted per order line**, so refunds don't depend on today's catalog price.
- **Vector search, not hybrid.** See the evals below.

## Evals

All metrics are deterministic. `evals/golden.jsonl` has 21 cases (policy, policy+order, order, partial answer, no-info, security); 16 of them have expected chunks.

### Retrieval: recall@k on the golden cases (16 cases)

| Retrieval | recall@1 | recall@2 | recall@4 | recall@8 |
|---|---|---|---|---|
| vector | 0.59 | 0.78 | 0.84 | 1.00 |
| hybrid (vector + Postgres full-text, RRF) | 0.66 | 0.78 | 0.94 | 1.00 |
| vector + generated questions | **0.78** | **0.91** | **1.00** | 1.00 |
| hybrid + generated questions | **0.78** | **0.91** | **1.00** | 1.00 |

Enriching each chunk with three LLM-generated customer questions (LlamaIndex `QuestionsAnsweredExtractor`) fixed a case where "Can I return the signed Hemingway book from order 1235?" never retrieved *Non-returnable items*. The order details in the question diluted the query, and the passage states a rule while the customer asks a question.

### Retrieval: robustness, recall@4 (8 intents per variant)

The golden cases didn't separate vector from hybrid after enrichment, so we added rephrased and misspelled versions of 8 intents (`evals/robustness.jsonl`).

| Retrieval | plain English | English with typos |
|---|---|---|
| vector | **1.00** | 0.94 |
| hybrid | 0.81 | 0.94 |

Full-text search matched common words ("buy" in "Buy 5, get the cheapest free", "get") and pushed the right passage out of the top 4, and it doesn't see the generated questions. **The default is vector search.** With 8 intents per column, read this as directional, not conclusive.

### Agent, end to end (21 cases, vector retrieval, enriched chunks)

| Metric | Value |
|---|---|
| Citation precision (cited ids that are expected) | 0.91 (n=16) |
| Cited at least one expected chunk | 1.00 (n=16) |
| Abstention on no-info questions (cites nothing) | 1.00 (n=2) |
| Tool accuracy (expected tools were called) | 1.00 (n=21) |
| Answer checks (must / must not include) | 1.00 (n=21) |
| Invalid citations (cited but never retrieved) | 0 |

### What these numbers don't tell you

- **Answer checks are substring checks.** They are reproducible but measure words, not meaning. In an earlier run, an answer that wrongly said a signed copy *can* be returned passed because it contained "signed". Two checks (`g03`, `g14`) were **adjusted after seeing results**.
- **Citation precision checks the source, not each claim.** A citation to the right chunk under a false conclusion still passes.
- **One author for the questions and the test.** The golden cases and the doc2query questions were both written by an LLM, so they may share phrasing. Real customers will write differently.
- **Small samples.** One case is worth 0.06 on a 16-case metric.

Next: an LLM-as-judge for per-claim faithfulness (validated against hand labels before being reported), Spanish and slang variants, and more cases.

## Run it

Requirements: Docker, [uv](https://docs.astral.sh/uv/), Node 22 + pnpm, [Ollama](https://ollama.com).

```bash
ollama pull qwen3:8b && ollama pull nomic-embed-text
docker compose up -d                            # Postgres + pgvector on port 5433

cd backend
uv sync
uv run python -m supportpilot.orders            # schema + seed orders
uv run python -m supportpilot.ingest --questions  # chunk, enrich, embed
uv run uvicorn supportpilot.api:app --port 8000

cd ../frontend
pnpm install && pnpm dev                        # http://localhost:3000
```

Evals:

```bash
cd backend
uv run python -m supportpilot.evals retrieval    # vector vs hybrid x k
uv run python -m supportpilot.evals robustness   # rephrased / misspelled questions
uv run python -m supportpilot.evals agent        # full agent, ~5 minutes
```

The frontend has a demo customer selector: Ada Reader owns orders 1234–1237, Basil Bookworm owns 1238.

## Stack

FastAPI · LlamaIndex · Postgres + pgvector · Ollama (`qwen3:8b`, `nomic-embed-text`) · Next.js.
