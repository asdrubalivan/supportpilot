import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICIES_DIR = REPO_ROOT / "data" / "policies"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "supportpilot")
DB_USER = os.getenv("DB_USER", "supportpilot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "supportpilot")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = 768
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3:8b")

# LlamaIndex prefixes the table name with "data_", so the real table is data_policy_chunks.
POLICY_TABLE = "policy_chunks"

# The return window in days. policies/returns.md is the source of truth; tests/test_evals.py fails if
# the two disagree. It lives here only so get_order can hand the agent the subtraction already done.
RETURN_WINDOW_DAYS = 30

MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
MCP_URL = os.getenv("MCP_URL", f"http://127.0.0.1:{MCP_PORT}/mcp")

# OIDC: tokens must be signed by this issuer's keys and issued for this audience (the client id).
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "http://localhost:8080/realms/oldpages")
OIDC_AUDIENCE = os.getenv("OIDC_AUDIENCE", "supportpilot")
OIDC_JWKS_URL = os.getenv("OIDC_JWKS_URL", f"{OIDC_ISSUER}/protocol/openid-connect/certs")

# Web login (Authorization Code + PKCE). The client secret below is the public dev value from the
# imported realm; set OIDC_CLIENT_SECRET for anything that isn't a local lab.
OIDC_AUTH_URL = os.getenv("OIDC_AUTH_URL", f"{OIDC_ISSUER}/protocol/openid-connect/auth")
OIDC_TOKEN_URL = os.getenv("OIDC_TOKEN_URL", f"{OIDC_ISSUER}/protocol/openid-connect/token")
OIDC_LOGOUT_URL = os.getenv("OIDC_LOGOUT_URL", f"{OIDC_ISSUER}/protocol/openid-connect/logout")
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", OIDC_AUDIENCE)
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "supportpilot-dev-secret")
OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "http://localhost:8000/auth/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
# Where Keycloak sends the browser after ending its session; must match the client's
# post.logout.redirect.uris in the realm. The query param only makes the page say "signed out".
POST_LOGOUT_REDIRECT_URI = f"{FRONTEND_URL}/?logged_out=1"

# Sessions: the cookie holds an opaque id; tokens stay in the sessions table.
SESSION_COOKIE = "sp_session"
LOGIN_COOKIE = "sp_login"
# Secure cookies are HTTPS-only, which would break http://localhost; turn on for real deployments.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(8 * 3600)))
LOGIN_ATTEMPT_TTL_SECONDS = 600
# Renew the access token when it has less than this left, so the MCP never gets an expired one.
REFRESH_MARGIN_SECONDS = 30
