# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js frontend (as proposed in CLAUDE.md) calling a FastAPI backend (`POST /chat`). Local models via Ollama.

## Users

Two audiences on the same screen:

- **Store customer (fictional):** a customer of Old Pages Books asking a support question about returns, refunds, shipping, promotions, the catalog, or one of their orders.
- **Evaluator:** a recruiter or engineer reviewing SupportPilot as a public portfolio project. They want to see the RAG system work and check why it answered what it answered: which policy passages it cited and which tools it called.

## Product Purpose

SupportPilot is a support agent that answers questions about a fictional company's policies with source citations, and looks up the customer's orders through a fixed tool. It is a learning lab and evidence project: success means answers are grounded in the policy documents, citations point to the passage that supports them, and the eval results in the README are real.

## Positioning

Every policy claim is traceable to a specific passage (`returns.md#refunds`), and the system says "I don't have information about that" instead of guessing. Order lookups are scoped to the current customer: another customer's order is indistinguishable from a missing one.

## Operating Context

- Slice 1 is single-turn: one question, one answer, no conversation history.
- No real authentication yet: a visible customer selector (customer 1 "Ada Reader", customer 2 "Basil Bookworm") stands in for the logged-in customer and lets evaluators demo order scoping.
- Answers take roughly 10–20 seconds on a local 8B model.
- Backend response: `answer`, `citations` (chunk ids), `invalid_citations`, `tools_called`, `retrieved_ids`.

## Capabilities and Constraints

- Read-only in slice 1: no creating or cancelling orders.
- Policy corpus: four documents (catalog, promotions, returns, shipping) in `data/policies/`, split into sections with stable ids.
- Seed orders 1234–1238; 1238 belongs to customer 2.
- English only for now.

## Brand Commitments

The UI wears the identity of **Old Pages Books**, the fictional online store of classic books. The company is fictional; nothing on the page should imply a real business.

## Evidence on Hand

- Policy documents: `data/policies/*.md`.
- Eval results: `evals/results/`, summarized in the README.
- No testimonials, customers, or metrics beyond the eval tables; do not invent any.

## Product Principles

1. Show the source: a policy answer without its passage is incomplete.
2. Honest uncertainty beats a confident guess.
3. The customer's view comes first; the evaluator's inspection details are available but secondary.
4. Never reveal another customer's data.
