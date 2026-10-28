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

## Slice 2a: MCP server, read-only (2026-10-26)

### Decisions I made

- **Why MCP:** honestly, for my CV. I want my own answer to "what does MCP buy you" before interviews.
- **Split slice 2:** 2a MCP read-only, 2b Keycloak (OIDC) + Slack account linking, 2c support approval + `cancel_order`/`create_order`. MCP first.
- **Exposed tools:** `search_policies`, `get_order`, `get_latest_order`. `cancel_order` waits until approval exists; `create_order` deferred.
- **Identity on the connection, not in tool arguments**, chosen after a diagram of both channels.
- **Streamable HTTP over stdio:** a customer fixed per process would collide between concurrent customers.
- **Design for later slices:** real auth via OAuth/OIDC with a local Keycloak; customers chat from Slack, the web frontend stays; order states `proposed → processed` (support approves) `→ shipped → delivered`, plus `rejected` and `cancelled`, so the agent never creates anything on its own.

### What I understood

- Read-only tools can run freely; tools with side effects that can't be undone need approval.
- A tool argument is written by the model, so it can't carry identity.
- Slack signatures prove which Slack user wrote, not who that person is in the store. Linking needs a one-time login, and a confirmation screen naming the Slack account, because `state` alone doesn't stop a phished link.
- An unsigned header can be forged by anyone who reaches the server; a token signed by Keycloak can't, since only Keycloak holds the signing key.

### What I left to the AI or needed help with

- The AI wrote the MCP server, the client wiring, and these docs; I reviewed the design and the eval results.
- I needed explanations, diagrams, and an ELI5 for the OAuth account-linking flow (I mixed up `state`, `code`, and Slack signatures), for where identity should travel, and for why the order-id check lives in the agent (only the client sees the message, so it's not a security boundary).
- I chose to exclude `create_order` and to require approval for it before fully stating why.

## Slice 2b: Keycloak login, sessions and logout (2026-10-26 to 2026-10-27)

### Decisions I made

- **Real auth in this slice** so I wouldn't redo the work later; OAuth/OIDC with a local Keycloak, partly as a learning goal.
- **Linking a login to a customer:** the first login links by a *verified* email, afterwards by `(provider, sub)` and never by email again. The `identity_links` table is keyed by `(provider, external_id)` so Slack can be another provider later. Self-registration is on and creates a customer with no orders, which is safe only because the email must be verified. Mailpit catches the verification emails locally.
- **Evals don't get an auth bypass.** A "trust the header" mode would let anyone impersonate any customer if it was left on. The evals mint their own tokens with a throwaway key and go through the same verifier; one smoke test uses a real Keycloak token.
- **Sessions:** the browser gets an opaque random id in an HttpOnly cookie, not a JWT, so a session can be revoked by deleting a row. Tokens stay in the backend.
- **Logout also ends Keycloak's session** (RP-initiated logout). Our session is deleted first, then the browser is sent to Keycloak, and it lands on `/?logged_out=1` with a "session closed" message and no auto-redirect.
- **`sp_session` is SameSite=Strict.** The page and the backend are the same site, so it costs nothing. `sp_login` stays Lax on purpose: Keycloak starts the callback navigation.
- **Frontend:** no session means redirect to login; a failed login shows a message and does not redirect (it would loop); the selector is gone; a 401 in the middle of a conversation goes back to login; `/chat` stops sending `customer_id`.
- **Revocation:** a ~4.5 minute window is fine for a bookstore. For money I would use a short token life plus introspection on the critical operations.

### What I understood

- The browser never gets the tokens: the backend exchanges the code (with the client secret and the PKCE verifier) and keeps them.
- The MCP server can't be fooled by a forged token because only Keycloak holds the signing key, and the verifier takes the public key from the issuer's JWKS in our config, not from the token.
- `email_verified` is what stops an attacker who registers with a victim's email. Linking happens once, at login, not in the MCP, because tool calls come from a non-deterministic model.
- `is not True` instead of `not claims.get(...)`, because the string `"false"` is truthy in Python.
- HttpOnly blocks reading, not sending. SameSite decides whether the browser *sends* a cookie, based on who started the request. A CSRF token and SameSite are two independent defenses.
- Verifying a token locally means the MCP can't see that a user was disabled; the refresh at `current_session` is where the backend finds out.

### What I left to the AI or needed help with

- The AI wrote all the code and tests (auth, login, sessions, logout, frontend), plus the Keycloak realm file. It also added **one thing beyond what I approved**: the `sp_login` cookie, which binds a login to the browser that started it (login CSRF). I understood it only after a walk-through.
- Where my first answer was weak and needed hints, diagrams or demos:
  - asymmetric signatures and `kid` (I needed a hands-on sign-with-A/verify-with-B demo);
  - why the MCP must not call `link_identity` (four rounds; I first said "the MCP needs the customer to exist", which is a precondition, not a reason);
  - read vs send: HttpOnly vs SameSite vs CORS, and a cookie vs a CSRF token (I needed a diagram, an interactive artifact and an analogy);
  - why not verifying the `id_token` at logout is safe: I said Keycloak checks it and the odds of a match are one in billions. That is wrong for a signed JWT; the odds argument fits opaque random ids like `sp_session`. **Still open:** a hands-on demo (edit an `id_token`, send it to Keycloak);
  - who stops a disabled user and when: I first said Keycloak and the MCP would handle it; I only saw that the MCP never asks Keycloak after reading `verify_token` myself.
- Parked, not decided: the `id_token_hint` travelling in the logout URL; what Strict means for someone arriving from an emailed link; letting the Next.js server create the session cookie (BFF style).
- Frontend visuals reuse the "Library Buckram" direction from slice 1; I didn't redesign anything.
