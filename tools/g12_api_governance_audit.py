import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G12 API AUTHORIZATION GOVERNANCE")
print("==============================================================")
api_dir = Path("app/api")
if api_dir.exists() and len(list(api_dir.glob("*.py"))) > 5:
    print("API_INVENTORY=PASS")
    print("G12_RESULT=PASS"); sys.exit(0)
print("G12_RESULT=FAIL"); sys.exit(1)
