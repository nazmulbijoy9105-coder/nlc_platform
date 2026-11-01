import os
import redis

url = os.environ.get("REDIS_URL")

if not url:
    raise SystemExit("ERROR: REDIS_URL is missing.")

client = redis.Redis.from_url(
    url,
    decode_responses=True,
    socket_connect_timeout=10,
    socket_timeout=10,
)

print("PING:", client.ping())
print("SET:", client.set("nlc:audit:connectivity", "ok", ex=60))
print("GET:", client.get("nlc:audit:connectivity"))
print("DEL:", client.delete("nlc:audit:connectivity"))
