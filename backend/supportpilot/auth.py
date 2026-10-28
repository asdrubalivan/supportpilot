"""Who is asking: verify an OIDC access token and map its subject to a customer.

Identities are linked once, on first login, by verified email (link_identity). After that a
customer is found only by (provider, sub): the email can change, the sub can't.
"""

from functools import lru_cache

import jwt

from supportpilot import config
from supportpilot.orders import connect

PROVIDER = "keycloak"


class AuthError(Exception):
    pass


@lru_cache
def jwks_client() -> jwt.PyJWKClient:
    # Fetches the issuer's public keys and caches them; only the issuer holds the private keys.
    return jwt.PyJWKClient(config.OIDC_JWKS_URL)


def verify_token(token: str) -> dict:
    """Return the token's claims if the signature, issuer, audience and expiry all check out."""
    try:
        key = jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=config.OIDC_ISSUER,
            audience=config.OIDC_AUDIENCE,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise AuthError(f"Invalid token: {e}") from e


def find_customer(sub: str) -> int | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT customer_id FROM identity_links WHERE provider = %s AND external_id = %s",
            (PROVIDER, sub),
        ).fetchone()
    return row["customer_id"] if row else None


def link_identity(claims: dict) -> int:
    """On login: return the linked customer, linking (or creating) one by verified email if needed."""
    if (customer_id := find_customer(claims["sub"])) is not None:
        return customer_id
    # Anyone can register with any address, so an unverified email proves nothing.
    if claims.get("email_verified") is not True or not claims.get("email"):
        raise AuthError("Email not verified.")

    with connect() as conn:
        customer = conn.execute(
            """
            INSERT INTO customers (name, email) VALUES (%s, %s)
            ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
            RETURNING id
            """,
            (claims.get("name") or claims["email"], claims["email"]),
        ).fetchone()
        # Two first logins at once: the second insert does nothing and both read the same link.
        conn.execute(
            """
            INSERT INTO identity_links (customer_id, provider, external_id) VALUES (%s, %s, %s)
            ON CONFLICT (provider, external_id) DO NOTHING
            """,
            (customer["id"], PROVIDER, claims["sub"]),
        )
    return find_customer(claims["sub"])
