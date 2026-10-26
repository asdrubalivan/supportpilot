# SupportPilot

Evidence project #1: a support agent that answers questions about fictional company policies with source citations, and calls a tool to look up an order. Slice 1 ships ~20 golden cases and a real table of recall@k and citation accuracy in the README. Declared as a lab; see `AI_ASSISTED_DEVELOPMENT.md`.

Proposed stack (confirm at kickoff): FastAPI + pgvector + Ollama (4B-8B models, 24 GB RAM), Next.js frontend.

## Language

Everything is in English: conversation, code, comments, commits, docs, and issues. The repo is public.

## How to work with me: learn while building

This project is for learning, not just shipping. Before implementing anything non-trivial:

- Ask me first how I would do it (free-form answer, not A/B/C options). If I say "I don't know", ask what I think before explaining.
- After each piece we build (ingestion, embeddings, retrieval, citations, the tool, evals), ask me 1-3 questions to check what I understood. Make them "why" and "what would happen if" questions, not definitions.
- If my answer is weak or wrong, don't correct it right away: give me a hint and let me try again. Explain only after.
- Don't write the design for me: I decide scope, behavior, and data model; you ask and point out gaps.
- Once the code is done, record in `AI_ASSISTED_DEVELOPMENT.md` what I understood and what I left to the AI.

## First step

Define the fictional customer and the 3 tools before writing code.
