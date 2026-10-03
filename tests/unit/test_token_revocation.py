"""Regression: logout must revoke one token, not the user's next login."""
import time

import app.core.token_blacklist as tb
from app.core.security import create_access_token, decode_token


class FakeRedis:
    def __init__(self):
        self.d = {}

    def setex(self, key, ttl, value):
        self.d[key] = (ttl, value)

    def exists(self, key):
        return 1 if key in self.d else 0


def _token(user="u1"):
    return decode_token(create_access_token({"sub": user, "user_id": user}))


def test_tokens_for_same_user_get_distinct_jti():
    assert _token()["jti"] != _token()["jti"]


def test_revoking_old_token_does_not_revoke_next_login(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(tb, "_client", lambda: fake)
    old = _token()
    assert tb.revoke(old["jti"], old["exp"]) is True
    new = _token()
    assert tb.is_revoked(old["jti"]) is True
    assert tb.is_revoked(new["jti"]) is False


def test_revoke_ttl_follows_token_expiry(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(tb, "_client", lambda: fake)
    tb.revoke("x", time.time() + 120)
    ttl, _ = fake.d["blacklist:x"]
    assert 100 <= ttl <= 120
