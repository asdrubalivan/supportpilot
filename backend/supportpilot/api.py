"""HTTP API. Run with: uv run uvicorn supportpilot.api:app --reload

Browser -> backend travels as an opaque session cookie; backend -> MCP as the session's bearer token.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from supportpilot import config, login, sessions
from supportpilot.agent import AgentResult, answer
from supportpilot.auth import AuthError, link_identity, verify_token
from supportpilot.sessions import Session

app = FastAPI(title="SupportPilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL],
    allow_credentials=True,  # needed for the browser to send the session cookie cross-origin
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

LOGIN_COOKIE_PATH = "/auth"


def current_session(request: Request) -> Session:
    """The logged-in session for this request, with a fresh access token, or 401."""
    session_id = request.cookies.get(config.SESSION_COOKIE)
    session = sessions.get_session(session_id) if session_id else None
    if session is None:
        raise HTTPException(401, "Not logged in.")

    margin = timedelta(seconds=config.REFRESH_MARGIN_SECONDS)
    if session.access_expires_at - datetime.now(timezone.utc) < margin:
        try:
            tokens = login.refresh(session.refresh_token)
        except login.LoginError:
            # Keycloak no longer honors this login (user disabled, session ended): end ours too.
            sessions.delete_session(session.id)
            raise HTTPException(401, "Session expired.")
        sessions.update_tokens(session.id, tokens.access_token, tokens.refresh_token, tokens.access_expires_at)
        session.access_token = tokens.access_token
        session.access_expires_at = tokens.access_expires_at
    return session


@app.get("/auth/login")
def start_login() -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    verifier, challenge = login.new_pkce()
    sessions.save_login_attempt(state, verifier)
    response = RedirectResponse(login.authorization_url(state, challenge), status_code=303)
    # Binds this login to this browser: the callback only accepts a state that this browser started.
    # Lax, not Strict: the callback is a navigation that Keycloak starts, and with Keycloak on another
    # site (any real deployment) a Strict cookie would not be sent and every login would be refused.
    response.set_cookie(
        config.LOGIN_COOKIE, state, max_age=config.LOGIN_ATTEMPT_TTL_SECONDS, path=LOGIN_COOKIE_PATH,
        httponly=True, samesite="lax", secure=config.COOKIE_SECURE,
    )
    return response


@app.get("/auth/callback")
def finish_login(request: Request, code: str | None = None, state: str | None = None) -> RedirectResponse:
    cookie_state = request.cookies.get(config.LOGIN_COOKIE)
    if not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        raise HTTPException(400, "Login was not started in this browser.")
    verifier = sessions.take_login_attempt(state)
    if verifier is None:
        raise HTTPException(400, "Unknown or expired login.")

    destination = config.FRONTEND_URL
    session_id = None
    try:
        if not code:
            raise login.LoginError("No code in the callback.")
        tokens = login.exchange_code(code, verifier)
        customer_id = link_identity(verify_token(tokens.access_token))
        session_id = sessions.create_session(
            customer_id, tokens.access_token, tokens.refresh_token, tokens.id_token, tokens.access_expires_at
        )
    except (login.LoginError, AuthError):
        destination = f"{config.FRONTEND_URL}/?login_error=1"

    response = RedirectResponse(destination, status_code=303)
    response.delete_cookie(config.LOGIN_COOKIE, path=LOGIN_COOKIE_PATH)
    if session_id:
        # Strict: the browser attaches it only to requests started by our own site. The frontend and the
        # backend are the same site (localhost; ports don't count), so the page's calls to /me and /chat
        # still carry it. It would stop doing so if they moved to different sites.
        response.set_cookie(
            config.SESSION_COOKIE, session_id, max_age=config.SESSION_MAX_AGE_SECONDS, path="/",
            httponly=True, samesite="strict", secure=config.COOKIE_SECURE,
        )
    return response


@app.post("/auth/logout")
def logout(request: Request) -> RedirectResponse:
    # Our session goes first: once the browser is on Keycloak we may never hear from it again,
    # and a half-finished logout must not leave our session open.
    session_id = request.cookies.get(config.SESSION_COOKIE)
    id_token = sessions.delete_session(session_id) if session_id else None
    # POST, not GET, so another site can't log a user out with an <img>. The 303 turns it into a GET.
    response = RedirectResponse(login.logout_url(id_token), status_code=303)
    response.delete_cookie(config.SESSION_COOKIE, path="/")
    return response


class Me(BaseModel):
    customer_id: int
    name: str


@app.get("/me")
def me(session: Session = Depends(current_session)) -> Me:
    return Me(customer_id=session.customer_id, name=session.customer_name)


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(request: ChatRequest, session: Session = Depends(current_session)) -> AgentResult:
    return await answer(request.message, session.access_token)
