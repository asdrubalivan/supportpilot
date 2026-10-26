# AI-assisted development

SupportPilot is a learning lab. It was built with Claude Code in a "learn while building" mode: the AI asked for my approach before each piece, I made the design decisions, and the AI wrote the code I approved. This file records what I decided and understood, and what I left to the AI. It is meant to be honest, not flattering.

## Slice 1 (2026-10-26)

### Decisions I made

- **Scope:** read-only slice (write actions on orders go to slice 2), single-turn, simulated `customer_id` with real auth later, backend + evals in the README + a minimal working frontend.
- **Company and tools:** a classic-books store with 30-day returns from delivery, non-returnable signed copies, and non-cumulative promotions (Jules Verne −20 %, self-help −50 %, buy 5 get the cheapest free). Tools: `get_order`, `create_order`, `cancel_order` (only `get_order` in slice 1), plus `get_latest_order`.
- **Fixed tool over text-to-SQL** for order lookups.
- **Chunking** by heading with LlamaIndex, prepending document and section context to the embedded text, and **explicit Markdown anchors** for stable chunk ids.
- **Agent:** LlamaIndex `FunctionAgent` with multiple tools (no limit on the number of tools, routing still measurable, LlamaIndex for its relevance to job requirements).
- **After seeing failures:** the backend always retrieves policies; the citation format example goes inside XML tags marked "do not cite"; a partial-answer rule (answer what's covered, say what can't be verified).
- **Evals:** golden cases carry expected chunk ids; citations are compared against them; deterministic checks first, LLM-as-judge later.
- **Retrieval fixes:** doc2query enrichment, judged on the full table rather than the one failing case; a robustness set (English and English with typos) to decide between hybrid and vector; **vector** chosen from those results.
- **Frontend:** show citations and the user, single-turn, visible customer selector, Old Pages Books identity; picked the "Library Buckram" visual direction.

### What I understood

- An order lookup is a structured query, not semantic search, and a policy answer needs both the **rule** (retrieved passage) and the **facts** (order data).
- Authentication answers "who are you", not "what SQL runs": a fixed tool with the customer id outside the model's reach is the real boundary. Returning the same "not found" for missing and foreign orders prevents enumeration.
- Chunk ids derived from titles break golden cases silently on rename.
- Higher k raises recall and lowers precision; k should be chosen with evals.
- Small models anchor on one decision branch (I predicted this from a previous experiment; it was confirmed by testing the same question with and without an order number).
- LLMs shouldn't do date arithmetic; compute `days_since_delivery` in SQL.
- Lexical search adds noise from common words; generated questions close the gap between how customers ask and how policies are written.

### What I left to the AI or needed help with

- The AI wrote all the code, the policy texts (from my rules), the seed data, and the first draft of the golden and robustness cases, which I reviewed.
- Concepts the AI explained: hybrid search vs structured lookup, grounding, RRF, price snapshots per order line, doc2query, the limits of substring checks, and LLM-as-judge tradeoffs.
- Places where my first answer was weak and needed a hint: where the return rule lives (policy docs, not the order DB); that auth doesn't mitigate text-to-SQL prompt injection; that renaming a heading breaks id references rather than embeddings; that the refund amount needs order data; how to define citation accuracy ("no sé" before the hint).
- I chose the router and LLM-decided retrieval at first without stating a reason; the experiment showed why it failed.
- My justification for vector search was "the evals said so"; the README adds the sample-size caveat.

### Open for next time

- Validate an LLM judge against hand labels before reporting faithfulness.
- Spanish and slang question variants.
- Write actions with confirmation (slice 2).
