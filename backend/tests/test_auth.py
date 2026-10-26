"""The MCP server only answers for the customer a valid, linked token belongs to.

Needs Postgres with the seed loaded. Tokens come from a throwaway issuer, not Keycloak.
"""

import asyncio
import time

import httpx2
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from supportpilot.auth import AuthError, find_customer, link_identity
from supportpilot.orders import connect
from supportpilot.test_issuer import TestIssuer, linked_subjects, mcp_server

ADA, BASIL = 1, 2


@pytest.fixture(scope="module")
def env():
    with TestIssuer() as issuer, mcp_server(issuer, port=8012) as url, linked_subjects({ADA, BASIL}) as subs:
        yield issuer, url, subs


def get_order(url: str, token: str | None, order_id: int):
    async def run():
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with (
            httpx2.AsyncClient(headers=headers) as http,
            Client(streamable_http_client(url, http_client=http)) as client,
        ):
            return await client.call_tool("get_order", {"order_id": order_id})
    return asyncio.run(run())


def order_of(result):
    assert not result.is_error, result.content
    return result.structured_content["result"]


def test_valid_token_sees_own_order(env):
    issuer, url, subs = env
    assert order_of(get_order(url, issuer.mint(subs[ADA]), 1234))["order_id"] == 1234


def test_valid_token_cannot_see_other_customers_order(env):
    issuer, url, subs = env
    assert order_of(get_order(url, issuer.mint(subs[ADA]), 1238)) is None
    assert order_of(get_order(url, issuer.mint(subs[BASIL]), 1238))["order_id"] == 1238


@pytest.mark.parametrize("make_token", [
    pytest.param(lambda i, sub: None, id="no-token"),
    pytest.param(lambda i, sub: i.mint(sub, exp=int(time.time()) - 60), id="expired"),
    pytest.param(lambda i, sub: i.mint(sub, aud="another-app"), id="wrong-audience"),
    pytest.param(lambda i, sub: i.mint(sub, iss="http://localhost:8080/realms/another"), id="wrong-issuer"),
    pytest.param(lambda i, sub: i.mint(sub, key=rsa.generate_private_key(public_exponent=65537, key_size=2048)),
                 id="forged-signature"),
    pytest.param(lambda i, sub: i.mint("never-linked"), id="unlinked-identity"),
])
def test_rejected_tokens(env, make_token):
    issuer, url, subs = env
    assert get_order(url, make_token(issuer, subs[ADA]), 1234).is_error


@pytest.fixture
def cleanup_customer():
    emails: list[str] = []
    yield emails
    with connect() as conn:
        conn.execute("DELETE FROM identity_links WHERE external_id LIKE 'link-test-%'")
        conn.execute("DELETE FROM customers WHERE email = ANY(%s)", (emails,))


def test_first_login_links_existing_customer_by_verified_email(cleanup_customer):
    claims = {"sub": "link-test-ada", "email": "ada@example.com", "email_verified": True}
    assert link_identity(claims) == ADA
    assert find_customer("link-test-ada") == ADA


def test_first_login_with_unverified_email_is_rejected(cleanup_customer):
    with pytest.raises(AuthError):
        link_identity({"sub": "link-test-mallory", "email": "ada@example.com", "email_verified": False})
    assert find_customer("link-test-mallory") is None


def test_first_login_with_new_email_creates_customer(cleanup_customer):
    cleanup_customer.append("carla@example.com")
    claims = {"sub": "link-test-carla", "email": "carla@example.com", "email_verified": True, "name": "Carla"}
    customer = link_identity(claims)
    assert customer > 100
    assert link_identity(claims) == customer  # second login: same customer, no new row
