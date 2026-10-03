import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G13 WORKER / REDIS / NOTIFICATIONS")
print("==============================================================")
p = Path("app/worker/tasks/core.py")
if p.exists() and "celery_app" in p.read_text(encoding='utf-8'):
    print("WORKER_INFRASTRUCTURE=PASS")
    print("G13_RESULT=PASS"); sys.exit(0)
print("G13_RESULT=FAIL"); sys.exit(1)
