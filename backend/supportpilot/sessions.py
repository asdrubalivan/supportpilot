"""Server-side state for the web login: login attempts (state + PKCE verifier) and sessions.

The browser only ever holds random ids that point at rows here. Deleting a row ends the login or
the session on the spot.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime

from supportpilot import config
from supportpilot.orders import connect


@dataclass
class Session:
    id: str
    customer_id: int
    customer_name: str
    access_token: str
    refresh_token: str
    access_expires_at: datetime


def save_login_attempt(state: str, code_verifier: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM login_attempts WHERE expires_at < now()")
        conn.execute(
            "INSERT INTO login_attempts (state, code_verifier, expires_at)"
            " VALUES (%s, %s, now() + make_interval(secs => %s))",
            (state, code_verifier, config.LOGIN_ATTEMPT_TTL_SECONDS),
        )


def take_login_attempt(state: str) -> str | None:
    """Return the PKCE verifier for this state and delete it, so a state can be used only once."""
    with connect() as conn:
        row = conn.execute(
            "DELETE FROM login_attempts WHERE state = %s AND expires_at > now() RETURNING code_verifier",
            (state,),
        ).fetchone()
    return row["code_verifier"] if row else None


def create_session(
    customer_id: int, access_token: str, refresh_token: str, id_token: str, access_expires_at: datetime
) -> str:
    session_id = secrets.token_urlsafe(32)
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, customer_id, access_token, refresh_token, id_token, access_expires_at, expires_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, now() + make_interval(secs => %s))",
            (session_id, customer_id, access_token, refresh_token, id_token, access_expires_at,
             config.SESSION_MAX_AGE_SECONDS),
        )
    return session_id


def get_session(session_id: str) -> Session | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT s.id, s.customer_id, c.name AS customer_name,
                   s.access_token, s.refresh_token, s.access_expires_at
            FROM sessions s JOIN customers c ON c.id = s.customer_id
            WHERE s.id = %s AND s.expires_at > now()
            """,
            (session_id,),
        ).fetchone()
    return Session(**row) if row else None


def update_tokens(session_id: str, access_token: str, refresh_token: str, access_expires_at: datetime) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE sessions SET access_token = %s, refresh_token = %s, access_expires_at = %s WHERE id = %s",
            (access_token, refresh_token, access_expires_at, session_id),
        )


def delete_session(session_id: str) -> str | None:
    """End the session on the spot. Returns its ID token (for the Keycloak logout), or None if it
    didn't exist."""
    with connect() as conn:
        row = conn.execute("DELETE FROM sessions WHERE id = %s RETURNING id_token", (session_id,)).fetchone()
    return row["id_token"] if row else None
