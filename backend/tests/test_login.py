"""Web login: Authorization Code + PKCE, the session cookie, and token refresh.

Needs Postgres with the seed loaded. Keycloak is replaced by FakeKeycloak, which also checks the PKCE
verifier against the challenge, so a wrong verifier fails the way the real server would.
"""

import base64
import hashlib
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from fastapi.testclient import TestClient

from supportpilot import api, auth, config, login
from supportpilot.agent import AgentResult
from supportpilot.orders import connect
from supportpilot.test_issuer import ISSUER, TestIssuer, linked_subjects

ADA, BASIL = 1, 2


@dataclass
class FakeResponse:
    status_code: int
    body: dict

    def json(self):
        return self.body

    @property
    def text(self):
        return str(self.body)


class FakeKeycloak:
    """Stands in for the token endpoint. Set `sub`/`extra` to choose who the code belongs to."""

    def __init__(self, issuer: TestIssuer):
        self.issuer = issuer
        self.calls: list[dict] = []
        self.challenge: str | None = None
        self.sub = ""
        self.extra: dict = {}
        self.first_expires_in = 300
        self.refresh_works = True

    def post(self, url, data, timeout):
        self.calls.append(dict(data))
        if data["grant_type"] == "authorization_code":
            digest = hashlib.sha256(data["code_verifier"].encode()).digest()
            if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != self.challenge:
                return FakeResponse(400, {"error": "invalid_grant"})
            return self._tokens("refresh-1", self.first_expires_in)
        if not self.refresh_works:
            return FakeResponse(400, {"error": "invalid_grant"})
        return self._tokens("refresh-2", 300)

    def _tokens(self, refresh_token: str, expires_in: int) -> FakeResponse:
        # Like Keycloak, give every token a unique id; otherwise two minted in one second are identical.
        access = self.issuer.mint(self.sub, jti=f"token-{len(self.calls)}", **self.extra)
        return FakeResponse(
            200,
            {"access_token": access, "refresh_token": refresh_token, "id_token": f"id-token-{self.sub}",
             "expires_in": expires_in},
        )


@pytest.fixture(scope="module")
def issuer():
    with TestIssuer() as i:
        yield i


@pytest.fixture(scope="module")
def subs():
    with linked_subjects({ADA, BASIL}) as s:
        yield s


@pytest.fixture
def fake(monkeypatch, issuer, subs):
    # verify_token runs for real, against the test issuer's keys.
    monkeypatch.setattr(config, "OIDC_ISSUER", ISSUER)
    monkeypatch.setattr(auth, "jwks_client", lambda: jwt.PyJWKClient(issuer.jwks_url))
    keycloak = FakeKeycloak(issuer)
    monkeypatch.setattr(login.httpx2, "post", keycloak.post)
    with connect() as conn:
        started = conn.execute("SELECT now() AS t").fetchone()["t"]
    yield keycloak
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE created_at >= %s", (started,))
        conn.execute("DELETE FROM login_attempts")


@pytest.fixture
def client():
    return TestClient(api.app, follow_redirects=False)


def begin_login(client: TestClient, fake: FakeKeycloak) -> str:
    """Hit /auth/login like a browser would; returns the state Keycloak was given."""
    response = client.get("/auth/login")
    query = parse_qs(urlparse(response.headers["location"]).query)
    fake.challenge = query["code_challenge"][0]
    return query["state"][0]


def log_in(client: TestClient, fake: FakeKeycloak, sub: str, **extra):
    fake.sub, fake.extra = sub, extra
    state = begin_login(client, fake)
    return client.get("/auth/callback", params={"code": "some-code", "state": state})


def session_rows(customer_id: int) -> list[dict]:
    with connect() as conn:
        return conn.execute("SELECT * FROM sessions WHERE customer_id = %s", (customer_id,)).fetchall()


def test_login_sends_the_browser_to_keycloak_with_state_and_pkce(client, fake):
    response = client.get("/auth/login")

    assert response.status_code == 303
    url = urlparse(response.headers["location"])
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert f"{url.scheme}://{url.netloc}{url.path}" == config.OIDC_AUTH_URL
    assert query["response_type"] == "code"
    assert query["client_id"] == config.OIDC_CLIENT_ID
    assert query["redirect_uri"] == config.OIDC_REDIRECT_URI
    assert query["code_challenge_method"] == "S256"
    assert client.cookies.get(config.LOGIN_COOKIE) == query["state"]
    login_cookie = next(h for h in response.headers.get_list("set-cookie") if h.startswith(config.LOGIN_COOKIE))
    assert "samesite=lax" in login_cookie.lower()  # must stay Lax: Keycloak starts the callback navigation
    with connect() as conn:
        stored = conn.execute("SELECT code_verifier FROM login_attempts WHERE state = %s", (query["state"],)).fetchone()
    # Only the hash of the verifier went to Keycloak, never the verifier itself.
    assert stored["code_verifier"] != query["code_challenge"]


def test_successful_login_creates_a_session_cookie(client, fake, subs):
    response = log_in(client, fake, subs[ADA])

    assert response.status_code == 303
    assert response.headers["location"] == config.FRONTEND_URL
    cookie = next(h for h in response.headers.get_list("set-cookie") if h.startswith(config.SESSION_COOKIE))
    assert "httponly" in cookie.lower() and "samesite=strict" in cookie.lower()
    session_id = client.cookies.get(config.SESSION_COOKIE)
    # The cookie is only a key: no token inside it, and the tokens are in the table.
    assert "eyJ" not in session_id
    (row,) = session_rows(ADA)
    assert row["id"] == session_id and row["refresh_token"] == "refresh-1"
    assert client.cookies.get(config.LOGIN_COOKIE) is None
    assert client.get("/me").json()["customer_id"] == ADA


def test_callback_refuses_a_login_that_this_browser_did_not_start(client, fake, subs):
    state = begin_login(client, fake)  # someone else's login
    fake.sub = subs[ADA]
    stranger = TestClient(api.app, follow_redirects=False)  # no login cookie

    response = stranger.get("/auth/callback", params={"code": "stolen", "state": state})

    assert response.status_code == 400
    assert fake.calls == []  # never reached the token endpoint
    assert session_rows(ADA) == []


def test_callback_refuses_a_state_that_does_not_match_the_cookie(client, fake):
    begin_login(client, fake)

    response = client.get("/auth/callback", params={"code": "x", "state": "someone-elses-state"})

    assert response.status_code == 400
    assert fake.calls == []


def test_a_state_works_only_once(client, fake, subs):
    state = begin_login(client, fake)
    fake.sub = subs[ADA]
    assert client.get("/auth/callback", params={"code": "x", "state": state}).status_code == 303

    client.cookies.set(config.LOGIN_COOKIE, state, path="/auth")  # replay with the cookie restored
    replay = client.get("/auth/callback", params={"code": "x", "state": state})

    assert replay.status_code == 400
    assert len(fake.calls) == 1


def test_callback_with_an_error_from_keycloak_gives_no_session(client, fake):
    state = begin_login(client, fake)

    response = client.get("/auth/callback", params={"error": "access_denied", "state": state})

    assert response.status_code == 303 and "login_error" in response.headers["location"]
    assert config.SESSION_COOKIE not in response.headers.get("set-cookie", "")


def test_unverified_email_with_no_link_gets_no_session(client, fake):
    response = log_in(client, fake, "never-linked", email="ada@example.com", email_verified=False)

    assert "login_error" in response.headers["location"]
    assert client.cookies.get(config.SESSION_COOKIE) is None
    assert session_rows(ADA) == []


def test_me_and_chat_need_a_session(client):
    assert client.get("/me").status_code == 401
    assert client.post("/chat", json={"message": "hi"}).status_code == 401


def test_chat_uses_the_session_token_and_ignores_a_customer_id_in_the_body(client, fake, subs, monkeypatch):
    seen = {}

    async def fake_answer(message, access_token):
        seen.update(message=message, token=access_token)
        return AgentResult(answer="ok", citations=[], invalid_citations=[], tools_called=[],
                           retrieved_ids=[], passages=[])

    monkeypatch.setattr(api, "answer", fake_answer)
    log_in(client, fake, subs[BASIL])

    response = client.post("/chat", json={"message": "hi", "customer_id": ADA})

    assert response.status_code == 200
    (row,) = session_rows(BASIL)
    assert seen == {"message": "hi", "token": row["access_token"]}
    assert jwt.decode(seen["token"], options={"verify_signature": False})["sub"] == subs[BASIL]


def test_expired_session_is_rejected(client, fake, subs):
    log_in(client, fake, subs[ADA])
    with connect() as conn:
        conn.execute("UPDATE sessions SET expires_at = now() - interval '1 minute' WHERE customer_id = %s", (ADA,))

    assert client.get("/me").status_code == 401


def test_access_token_is_renewed_when_it_is_about_to_expire(client, fake, subs):
    fake.first_expires_in = 5  # inside the refresh margin
    log_in(client, fake, subs[ADA])
    (before,) = session_rows(ADA)

    assert client.get("/me").status_code == 200

    (after,) = session_rows(ADA)
    assert fake.calls[-1]["grant_type"] == "refresh_token" and fake.calls[-1]["refresh_token"] == "refresh-1"
    assert after["access_token"] != before["access_token"] and after["refresh_token"] == "refresh-2"


def test_token_with_plenty_of_time_is_not_renewed(client, fake, subs):
    log_in(client, fake, subs[ADA])

    client.get("/me")

    assert [c["grant_type"] for c in fake.calls] == ["authorization_code"]


def test_failed_renewal_ends_the_session(client, fake, subs):
    fake.first_expires_in = 5
    log_in(client, fake, subs[ADA])
    fake.refresh_works = False

    assert client.get("/me").status_code == 401
    assert session_rows(ADA) == []


def test_logout_deletes_the_session_and_sends_the_browser_to_keycloak(client, fake, subs):
    log_in(client, fake, subs[ADA])
    session_id = client.cookies.get(config.SESSION_COOKIE)

    response = client.post("/auth/logout")

    # Our session is already gone by the time the browser is told to go to Keycloak.
    assert session_rows(ADA) == []
    assert response.status_code == 303
    url = urlparse(response.headers["location"])
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert f"{url.scheme}://{url.netloc}{url.path}" == config.OIDC_LOGOUT_URL
    # The ID token tells Keycloak which session to end; without it Keycloak asks the user to confirm.
    assert query == {
        "client_id": config.OIDC_CLIENT_ID,
        "post_logout_redirect_uri": config.POST_LOGOUT_REDIRECT_URI,
        "id_token_hint": f"id-token-{subs[ADA]}",
    }
    assert client.cookies.get(config.SESSION_COOKIE) is None
    client.cookies.set(config.SESSION_COOKIE, session_id)  # a copied cookie is worthless now
    assert client.get("/me").status_code == 401


def test_logout_without_a_session_still_ends_keycloaks_session(client):
    # Our session may have expired while Keycloak's is still open; the user must still be able to sign out.
    response = client.post("/auth/logout")

    assert response.status_code == 303
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert "id_token_hint" not in query
    assert query["post_logout_redirect_uri"] == [config.POST_LOGOUT_REDIRECT_URI]


def test_logout_is_post_only(client):
    # A GET would let any page log the user out with an <img src=".../auth/logout">.
    assert client.get("/auth/logout").status_code == 405


def test_login_without_an_id_token_gives_no_session(client, fake, subs, monkeypatch):
    original = fake._tokens
    monkeypatch.setattr(
        fake, "_tokens",
        lambda *a: FakeResponse(200, {k: v for k, v in original(*a).body.items() if k != "id_token"}),
    )

    response = log_in(client, fake, subs[ADA])

    assert "login_error" in response.headers["location"]
    assert session_rows(ADA) == []
