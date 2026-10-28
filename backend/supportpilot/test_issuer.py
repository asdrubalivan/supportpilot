"""A throwaway token issuer for evals and tests, so they don't need Keycloak running.

The key pair lives in memory for one run. The MCP server is pointed at its public keys through the
same config it uses for Keycloak (OIDC_ISSUER, OIDC_JWKS_URL), so tokens go through the real
verifier. Once the run ends, nobody holds the private key, so nobody can mint more.
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from supportpilot.auth import PROVIDER
from supportpilot.orders import connect

ISSUER = "http://localhost/supportpilot-test-issuer"
AUDIENCE = "supportpilot"


class TestIssuer:
    """Use as a context manager: serves the public keys over HTTP on localhost while open."""

    __test__ = False  # not a pytest test class

    def __init__(self) -> None:
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        body = json.dumps({"keys": [{**jwk, "kid": "test", "use": "sig", "alg": "RS256"}]}).encode()

        class JwksHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), JwksHandler)
        self.jwks_url = f"http://127.0.0.1:{self.server.server_port}/jwks"

    def __enter__(self) -> "TestIssuer":
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()

    @property
    def env(self) -> dict[str, str]:
        """Environment that makes the MCP server trust this issuer instead of Keycloak."""
        return {"OIDC_ISSUER": ISSUER, "OIDC_AUDIENCE": AUDIENCE, "OIDC_JWKS_URL": self.jwks_url}

    def mint(self, sub: str, key=None, **claims) -> str:
        now = int(time.time())
        payload = {"iss": ISSUER, "aud": AUDIENCE, "sub": sub, "iat": now, "exp": now + 600, **claims}
        return jwt.encode(payload, key or self.key, algorithm="RS256", headers={"kid": "test"})


@contextmanager
def mcp_server(issuer: TestIssuer | None, port: int = 8011):
    """Run the MCP server in a subprocess that trusts `issuer` (or Keycloak if None); yields its URL."""
    env = {**os.environ, **(issuer.env if issuer else {}), "MCP_PORT": str(port)}
    proc = subprocess.Popen([sys.executable, "-m", "supportpilot.mcp_server"], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError("MCP server did not start.")
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        proc.terminate()
        proc.wait()


@contextmanager
def linked_subjects(customer_ids: set[int]):
    """Link one test subject per customer, as a first login would; yields {customer_id: sub}."""
    subs = {cid: f"test-customer-{cid}" for cid in customer_ids}
    with connect() as conn:
        for cid, sub in subs.items():
            conn.execute(
                "INSERT INTO identity_links (customer_id, provider, external_id) VALUES (%s, %s, %s)"
                " ON CONFLICT DO NOTHING",
                (cid, PROVIDER, sub),
            )
    try:
        yield subs
    finally:
        with connect() as conn:
            conn.execute("DELETE FROM identity_links WHERE external_id = ANY(%s)", (list(subs.values()),))
