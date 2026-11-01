import time
import uuid
from urllib.parse import urlsplit

from app.core import token_blacklist as tb

url = tb._redis_url()
parsed = urlsplit(url)

print("NLC REDIS SCHEME:", parsed.scheme)
print("NLC REDIS HOST:", parsed.hostname)
print("NLC REDIS PORT:", parsed.port)

jti = "nlc-audit-" + str(uuid.uuid4())
key = f"blacklist:{jti}"

try:
    exp = time.time() + 120

    result = tb.revoke(jti, exp)
    print("NLC REVOKE:", result)

    revoked = tb.is_revoked(jti)
    print("NLC IS_REVOKED:", revoked)

    ttl = tb._client().ttl(key)
    print("NLC KEY TTL:", ttl)

    assert parsed.scheme == "rediss", "NLC is not using TLS"
    assert result is True, "Revocation write failed"
    assert revoked is True, "Revoked token not recognised"
    assert 0 < ttl <= 120, "Unexpected blacklist TTL"

    print("RESULT: PASS")

finally:
    tb._client().delete(key)
    tb._client().close()
