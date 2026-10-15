import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G15 PRODUCTION READINESS")
print("==============================================================")
files = ["requirements.txt", "alembic.ini", "Dockerfile", ".env.example"]
if all(Path(f).exists() for f in files):
    print("PRODUCTION_FILES=PASS")
    print("G15_RESULT=PASS"); sys.exit(0)
print("G15_RESULT=FAIL"); sys.exit(1)
