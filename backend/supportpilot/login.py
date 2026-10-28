"""The OIDC steps of the web login: Authorization Code with PKCE, and refreshing the access token.

The backend is a confidential client: it exchanges the code with its client secret, so the tokens
never pass through the browser.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx2

from supportpilot import config


class LoginError(Exception):
    pass


@dataclass
class Tokens:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    id_token: str = ""  # only the code exchange returns one we keep; see logout_url


def new_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge). Only the hash of the verifier goes to Keycloak."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def authorization_url(state: str, code_challenge: str) -> str:
    query = urlencode({
        "response_type": "code",
        "client_id": config.OIDC_CLIENT_ID,
        "redirect_uri": config.OIDC_REDIRECT_URI,
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    return f"{config.OIDC_AUTH_URL}?{query}"


def _token_request(data: dict[str, str], fallback_refresh_token: str | None = None) -> Tokens:
    response = httpx2.post(
        config.OIDC_TOKEN_URL,
        data={**data, "client_id": config.OIDC_CLIENT_ID, "client_secret": config.OIDC_CLIENT_SECRET},
        timeout=10.0,
    )
    if response.status_code != 200:
        # The body can name the reason (invalid_grant, ...); keep it out of anything user-facing.
        raise LoginError(f"Token endpoint answered {response.status_code}: {response.text}")
    body = response.json()
    refresh_token = body.get("refresh_token") or fallback_refresh_token
    if not refresh_token:
        raise LoginError("Token endpoint returned no refresh token.")
    return Tokens(
        access_token=body["access_token"],
        refresh_token=refresh_token,
        access_expires_at=datetime.now(timezone.utc) + timedelta(seconds=body["expires_in"]),
        id_token=body.get("id_token", ""),
    )


def exchange_code(code: str, code_verifier: str) -> Tokens:
    tokens = _token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.OIDC_REDIRECT_URI,
        "code_verifier": code_verifier,
    })
    if not tokens.id_token:
        raise LoginError("Token endpoint returned no ID token.")
    return tokens


def logout_url(id_token: str | None) -> str:
    """Where to send the browser to end Keycloak's SSO session (RP-initiated logout).

    Only the browser carries Keycloak's session cookie, so the backend can't end that session by
    calling Keycloak; the browser has to go there. With the ID token as a hint Keycloak knows which
    session to end and goes straight back to us; without it, it asks the user to confirm first.
    """
    params = {"client_id": config.OIDC_CLIENT_ID, "post_logout_redirect_uri": config.POST_LOGOUT_REDIRECT_URI}
    if id_token:
        params["id_token_hint"] = id_token
    return f"{config.OIDC_LOGOUT_URL}?{urlencode(params)}"


def refresh(refresh_token: str) -> Tokens:
    return _token_request({"grant_type": "refresh_token", "refresh_token": refresh_token}, refresh_token)
