import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G03 MEMBERSHIP AUTHORIZATION AUDIT")
print("==============================================================")
api_dir = Path("app/api")
endpoints = 0; auth_deps = 0
for f in api_dir.glob("*.py"):
    txt = f.read_text(encoding='utf-8')
    endpoints += txt.count("@router.get") + txt.count("@router.post") + txt.count("@router.patch") + txt.count("@router.delete")
    auth_deps += txt.count("require_roles") + txt.count("require_company_access") + txt.count("get_current_user")
print(f"TOTAL_ENDPOINTS={endpoints}")
print(f"AUTH_DEPENDENCIES={auth_deps}")
if auth_deps > 0 and endpoints > 0:
    print("G03_RESULT=PASS"); sys.exit(0)
else:
    print("G03_RESULT=FAIL"); sys.exit(1)
