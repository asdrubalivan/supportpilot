"""Smoke test: a real login against the real Keycloak, end to end.

Needs `docker compose up -d` (Keycloak with the imported realm) and Postgres with the seed loaded.
Skipped when Keycloak isn't reachable. Plays the browser: opens Keycloak's login page, submits Ada's
credentials, and hands the redirect back to the backend's callback.
"""

import asyncio
import html
import re
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest
from fastapi.testclient import TestClient
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from supportpilot import api, config
from supportpilot.auth import PROVIDER
from supportpilot.orders import connect
from supportpilot.test_issuer import mcp_server

ADA = 1


def keycloak_is_up() -> bool:
    try:
        return httpx2.get(f"{config.OIDC_ISSUER}/.well-known/openid-configuration", timeout=2).status_code == 200
    except httpx2.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not keycloak_is_up(), reason="Keycloak is not running")


@pytest.fixture
def cleanup():
    with connect() as conn:
        started = conn.execute("SELECT now() AS t").fetchone()["t"]
    yield
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE created_at >= %s", (started,))
        conn.execute("DELETE FROM identity_links WHERE provider = %s AND linked_at >= %s", (PROVIDER, started))


def allow_insecure_cookies(keycloak: httpx2.Client) -> None:
    # Keycloak marks its cookies Secure even on http://localhost. Real browsers treat localhost as
    # a secure context and send them; this stand-in browser needs to be told.
    for cookie in keycloak.cookies.jar:
        cookie.secure = False


def open_login_page(app: TestClient, keycloak: httpx2.Client) -> httpx2.Response:
    """Start a login in the backend and follow it to Keycloak, like a browser would."""
    start = app.get("/auth/login")
    assert start.status_code == 303
    page = keycloak.get(start.headers["location"])
    allow_insecure_cookies(keycloak)
    return page


def log_in_as_ada(app: TestClient, keycloak: httpx2.Client) -> None:
    page = open_login_page(app, keycloak)
    assert page.status_code == 200
    form_action = html.unescape(re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', page.text).group(1))
    submitted = keycloak.post(form_action, data={"username": "ada", "password": "ada"})
    assert submitted.status_code == 302, submitted.text[:500]
    allow_insecure_cookies(keycloak)  # the cookies of the SSO session were just set

    query = parse_qs(urlparse(submitted.headers["location"]).query)
    callback = app.get("/auth/callback", params={"code": query["code"][0], "state": query["state"][0]})
    assert callback.status_code == 303 and "login_error" not in callback.headers["location"]


def test_real_login_gives_a_session_and_the_token_works_on_the_mcp(cleanup):
    app = TestClient(api.app, follow_redirects=False)

    with httpx2.Client(follow_redirects=False) as keycloak:
        log_in_as_ada(app, keycloak)

    assert app.get("/me").json()["customer_id"] == ADA  # linked by Ada's verified email on first login
    with connect() as conn:
        (session,) = conn.execute("SELECT access_token FROM sessions WHERE customer_id = %s", (ADA,)).fetchall()

    async def get_order(url: str):
        headers = {"Authorization": f"Bearer {session['access_token']}"}
        async with (
            httpx2.AsyncClient(headers=headers) as http,
            Client(streamable_http_client(url, http_client=http)) as client,
        ):
            return await client.call_tool("get_order", {"order_id": 1234})

    # The MCP trusts Keycloak here (no test issuer): the real token goes through the real verifier.
    with mcp_server(None, port=8013) as url:
        result = asyncio.run(get_order(url))
    assert not result.is_error, result.content
    assert result.structured_content["result"]["order_id"] == 1234


def test_logout_ends_keycloaks_session_so_the_next_login_asks_for_a_password(cleanup):
    app = TestClient(api.app, follow_redirects=False)
    with httpx2.Client(follow_redirects=False) as keycloak:
        log_in_as_ada(app, keycloak)
        # While Keycloak's session is open, a new login is answered with a code and no password prompt.
        assert open_login_page(app, keycloak).status_code == 302

        logout = app.post("/auth/logout")
        assert app.get("/me").status_code == 401
        # The browser follows the redirect to Keycloak; the ID token hint means no confirmation page.
        ended = keycloak.get(logout.headers["location"])
        assert ended.status_code == 302, ended.text[:500]
        assert ended.headers["location"] == config.POST_LOGOUT_REDIRECT_URI

        # Now Keycloak has forgotten the browser: the login form is back.
        page = open_login_page(app, keycloak)
        assert page.status_code == 200 and 'id="kc-form-login"' in page.text
