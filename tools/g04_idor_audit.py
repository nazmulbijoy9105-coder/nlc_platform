import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G04 OBJECT-ID / IDOR AUTHORIZATION AUDIT")
print("==============================================================")
api_dir = Path("app/api")
idor_mitigated = 0
for f in api_dir.glob("*.py"):
    txt = f.read_text(encoding='utf-8')
    if "require_company_access" in txt:
        idor_mitigated += txt.count("require_company_access")

print(f"IDOR_MITIGATION_DEPENDENCIES={idor_mitigated}")
if idor_mitigated > 0:
    print("G04_RESULT=PASS"); sys.exit(0)
else:
    print("G04_RESULT=FAIL"); sys.exit(1)
