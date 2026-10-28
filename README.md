# SupportPilot

A support agent for **Old Pages Books**, a fictional online store of classic books. It answers questions about the store's policies with citations to the exact passage, and looks up the customer's orders. Its tools are served by an **MCP server** (Model Context Protocol, Streamable HTTP) that the agent connects to as a client. Everything runs locally on Ollama.

![SupportPilot demo: a customer asks to return an order and gets a cited answer; another customer asks about the same order and is told nothing](demo/out/supportpilot.gif)

This is a learning lab (see [`AI_ASSISTED_DEVELOPMENT.md`](AI_ASSISTED_DEVELOPMENT.md)). Slice 1 is read-only and single-turn; slice 2a moved the tools behind an MCP server; slice 2b replaced the simulated customer with a real login (Keycloak, OpenID Connect).

## How it works

```
OFFLINE   data/policies/*.md ─ one chunk per heading (stable <!-- id --> anchors)
            ─ + 3 generated customer questions per chunk (doc2query)
            ─ embed (nomic-embed-text) ─> pgvector

ONLINE    question + session cookie (the customer comes from the login, never from the request body)
            ─> FunctionAgent (qwen3:8b), an MCP client; the customer's access token rides on the MCP connection
            ─> MCP server (Streamable HTTP, localhost:8001) verifies the token, then runs the tools:
                 search_policies(query)   vector search, k=4; always run on the customer's own words
                 get_order(order_id)      scoped to customer_id, SQL written by hand
                 get_latest_order()
            ─> answer with [file.md#section] citations
            ─> citations checked against what was actually retrieved
```

Design decisions worth knowing:

- **Tools behind an MCP server.** The customer comes from a signed access token on the MCP connection, never from tool arguments the model writes. The server verifies the token itself (signature, issuer, audience, expiry) and maps its `sub` to a customer.
- **Fixed tools, not text-to-SQL.** `customer_id` is captured in a closure, never a tool argument, so the model can't ask for another customer's orders. A missing order and someone else's order return the same "not found".
- **Retrieval always runs.** With the LLM deciding when to search, the 8B model anchored on order numbers and skipped policy search ("Can I return order 1234?" → no policy, no answer). The backend now always retrieves with the customer's own words; `search_policies` stays available for extra searches.
- **Order ids must come from the customer.** `get_order` rejects ids that don't appear in the message or in a `get_latest_order` result, to block invented arguments.
- **Prices are snapshotted per order line**, so refunds don't depend on today's catalog price.
- **Vector search, not hybrid.** See the evals below.

## MCP server

`backend/supportpilot/mcp_server.py` exposes the agent's tools over MCP (official Python SDK, Streamable HTTP at `http://127.0.0.1:8001/mcp`):

| Tool | What it does |
|---|---|
| `search_policies(query)` | Vector search over the policy chunks; returns ids to cite |
| `get_order(order_id)` | One of the customer's orders, or `null` (missing and foreign orders look the same) |
| `get_latest_order()` | The customer's most recent order |

- **Identity rides on the connection.** The backend opens one MCP session per question with `Authorization: Bearer <access token>`, the token Keycloak issued at login. No tool takes a customer id, so the model can't ask for someone else's orders.
- **The server checks the token itself.** Signature against Keycloak's public keys (JWKS), issuer, audience and expiry. It never asks Keycloak whether the user is still active, so a disabled user's token keeps working until it expires (about 5 minutes; see [Login](#login)).
- **Read-only for now.** `cancel_order` waits for support approval (slice 2c).
- **Some checks stay in the client.** "The order id must appear in the customer's message" lives in the agent, because only the client sees the message. It stops invented ids, but it isn't a security boundary.

Any MCP client that holds a valid access token can connect, e.g. the MCP Inspector: `npx @modelcontextprotocol/inspector`, URL `http://127.0.0.1:8001/mcp`, header `Authorization: Bearer <token>`. For a local token, log in through the app and read `access_token` from the `sessions` table.

## Login

Keycloak (realm `oldpages`, client `supportpilot`) is the identity provider. The web login is the OpenID Connect **Authorization Code flow with PKCE (S256)**; the backend is a confidential client.

```
browser ── GET /auth/login ──────────────> backend: random state + PKCE verifier saved, sp_login cookie set
browser <─ 303 to Keycloak ──────────────
browser ── password form ────────────────> Keycloak
browser <─ 302 /auth/callback?code&state ─
browser ── GET /auth/callback ───────────> backend: state must match the sp_login cookie, then
                                            code + verifier + client secret -> tokens;
                                            verify, link to a customer, create a session
browser <─ 303 to the frontend + sp_session cookie
page ───── GET /me, POST /chat ──────────> the cookie says who is asking
```

- **Tokens never reach the browser.** The browser holds `sp_session`, an opaque random id (HttpOnly, SameSite=Strict) that points at a row in the `sessions` table. Deleting the row ends the session.
- **`sp_login` binds a login to the browser that started it**, so a callback link someone else started is refused (login CSRF). It stays SameSite=Lax because Keycloak starts the callback navigation.
- **Linking a login to a customer** happens once, at login: by a *verified* email, then by `(provider, sub)` in `identity_links`. The MCP server never links; it only reads the `sub`.
- **Renewal.** When the access token has less than 30 s left, the backend uses the refresh token. If Keycloak refuses (user disabled, session ended), our session is deleted and the next call is a 401, which sends the page back to login.
- **Logout** is a form POST to `/auth/logout`. The backend deletes our session first, then answers with a 303 to Keycloak's `end_session_endpoint` (with `id_token_hint`), which ends Keycloak's single sign-on session too and sends the browser to `/?logged_out=1`. Without that, the next visit would sign the user straight back in.
- **The page** asks `GET /me`. A 401 with no hint redirects to login; `?login_error=1` and `?logged_out=1` show a message with a Sign in button and never redirect (a failed login would loop).

Known limits (it is a lab):

- **Tokens are stored in plain text** in the `sessions` table (access, refresh and ID token). A real deployment should encrypt them at rest.
- **Revocation is not immediate.** Verifying a token locally means the MCP can't see that a user was disabled. The window is about 4.5 minutes (5-minute token minus the 30 s refresh margin). For high-risk operations the answer would be a shorter token life plus introspection on those operations; it isn't built.
- **`id_token_hint` travels in the logout redirect URL**, so it can end up in browser history or logs. It only tells Keycloak which session to end, but it does bend "tokens stay in the backend".
- **Dev credentials are public**: the client secret, the admin password and the demo users' passwords are in the repo. Set `OIDC_CLIENT_SECRET` and `COOKIE_SECURE=true` for anything else.

## Evals

All metrics are deterministic. `evals/golden.jsonl` has 22 cases (policy, policy+order, order, partial answer, no-info, security); 16 of them have expected chunks.

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

### Agent, end to end (22 cases, vector retrieval, enriched chunks)

Re-run after slice 2b (every question now goes through a signed token that the MCP server verifies) and with a new case, `g22`: the same results as before the MCP and the auth changes, except citation precision, 0.91 → 0.94, and `g22`, which fails. The local model is not deterministic, so read that difference as noise. The evals mint their own tokens with a throwaway key instead of logging in through Keycloak.

| Metric | Value |
|---|---|
| Citation precision (cited ids that are expected) | 0.94 (n=16) |
| Cited at least one expected chunk | 1.00 (n=16) |
| Abstention on no-info questions (cites nothing) | 1.00 (n=2) |
| Tool accuracy (expected tools were called) | 1.00 (n=22) |
| Answer checks (must / must not include) | 0.95 (n=22) |
| Invalid citations (cited but never retrieved) | 0 |

### Known failure: `g22`

Asked "How many days late am I to return order 1234?", the agent answers "you are 41 days past the 30-day return window". 41 is how long ago the order was delivered (`days_since_delivery`); the right answer is 11 days past the window. The case stays red on purpose. Its expected numbers are placeholders (`{days_over_window}`) that `check_answer` fills from the database, because the seed dates are relative to when the data was loaded.

A system-prompt rule for it ("subtract the limit from `days_since_delivery`") did not fix `g22` and made `g06` stop citing `returns.md#refunds`, so it was reverted. That is the reason to run the full set after every prompt change, not just the case being fixed.

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
docker compose up -d                            # Postgres + pgvector (5433), Keycloak (8080), Mailpit (8025)

cd backend
uv sync
uv run python -m supportpilot.orders            # schema + seed orders
uv run python -m supportpilot.ingest --questions  # chunk, enrich, embed
uv run python -m supportpilot.mcp_server        # MCP server on :8001
uv run uvicorn supportpilot.api:app --port 8000  # in another terminal

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

Sign in at http://localhost:3000. Keycloak imports the realm on first start with two demo users: `ada` / `ada` (Ada Reader, orders 1234–1237) and `basil` / `basil` (Basil Bookworm, order 1238). Mailpit (http://localhost:8025) catches the emails Keycloak sends, such as email verification. Keycloak's admin console is at http://localhost:8080 (`admin` / `admin`).

Tests (`cd backend && uv run pytest tests -q`) need the compose services up and the schema loaded. The login smoke test runs against the real Keycloak and is skipped if it isn't reachable.

The demo GIF is rebuilt from the running app: `cd demo && pnpm install && pnpm capture && pnpm render && pnpm gif` (Remotion, real screenshots and real model answers).

## Stack

FastAPI · MCP (Python SDK, Streamable HTTP) · Keycloak (OIDC) · LlamaIndex · Postgres + pgvector · Ollama (`qwen3:8b`, `nomic-embed-text`) · Next.js.
