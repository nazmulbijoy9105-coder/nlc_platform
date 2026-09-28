"""Keep-alive ping — prevents Render free tier from sleeping.

Deploy as a cron job (every 10 minutes) on any external service:
  */10 * * * * python3 scripts/keepalive.py

Or use UptimeRobot / cron-job.org to ping the URL directly.
"""
import os
import urllib.request
import urllib.error

URL = os.environ.get("KEEPALIVE_URL", "https://nlc-platform.onrender.com/api/v1/health/live")

def ping():
    try:
        req = urllib.request.Request(URL, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            if status == 200:
                print(f"✓ Keepalive OK: {URL} → {status}")
            else:
                print(f"⚠ Keepalive warning: {URL} → {status}")
    except urllib.error.URLError as e:
        print(f"✗ Keepalive FAIL: {URL} → {e}")
    except Exception as e:
        print(f"✗ Keepalive error: {e}")

if __name__ == "__main__":
    ping()
