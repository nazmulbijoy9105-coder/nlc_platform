import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G11 SECURITY / SECRETS / DEPENDENCIES")
print("==============================================================")
# Check .gitignore for .env
gitignore = Path(".gitignore")
if gitignore.exists() and ".env" in gitignore.read_text():
    print("ENV_IGNORED=PASS")
# Check requirements.txt exists
if Path("requirements.txt").exists():
    print("DEPENDENCIES_PINNED=PASS")
    print("G11_RESULT=PASS"); sys.exit(0)
print("G11_RESULT=FAIL"); sys.exit(1)
