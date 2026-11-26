import asyncio
import shlex
from pathlib import Path

import pytest
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

ROOT = Path(__file__).resolve().parents[2]


def _docker_trusted_hosts():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    (value,) = (
        shlex.split(line)[1].split("=", 1)[1]
        for line in dockerfile.splitlines()
        if line.startswith("ENV FORWARDED_ALLOW_IPS=")
    )
    return value


def _client_host(peer, forwarded_for=None, *, trusted_hosts=None):
    clients = []

    async def app(scope, receive, send):
        clients.append(scope["client"])

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        pass

    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("ascii")))
    scope = {
        "type": "http",
        "scheme": "http",
        "client": (peer, 54321),
        "headers": headers,
    }
    middleware = ProxyHeadersMiddleware(
        app,
        trusted_hosts=_docker_trusted_hosts() if trusted_hosts is None else trusted_hosts,
    )
    asyncio.run(middleware(scope, receive, send))
    return clients[0][0]


def test_spoofed_leading_entry_cannot_rotate_client_ip():
    for spoofed in ("198.51.100.77", "198.51.100.88"):
        host = _client_host("10.201.4.7", f"{spoofed}, 203.0.113.9")
        assert host == "203.0.113.9"
        assert host != spoofed


@pytest.mark.parametrize(
    "forwarded_for",
    [
        "198.51.100.77, 198.51.100.88, 198.51.100.99, 203.0.113.9",
        "198.51.100.77, 198.51.100.88, 203.0.113.9, 172.16.4.2, 192.168.1.2",
    ],
)
def test_several_spoofed_entries_still_use_rightmost_untrusted(forwarded_for):
    assert _client_host("10.201.4.7", forwarded_for) == "203.0.113.9"


def test_public_peer_cannot_supply_forwarded_client_ip():
    assert _client_host("203.0.113.50", "198.51.100.77") == "203.0.113.50"


def test_missing_forwarded_header_keeps_peer_ip():
    assert _client_host("10.201.4.7") == "10.201.4.7"


def test_old_wildcard_trust_uses_spoofed_leftmost_entry():
    # Wildcard trust lets the caller choose the rate-limit key (audit F-02).
    assert _client_host(
        "10.201.4.7", "198.51.100.77, 203.0.113.9", trusted_hosts="*"
    ) == "198.51.100.77"
