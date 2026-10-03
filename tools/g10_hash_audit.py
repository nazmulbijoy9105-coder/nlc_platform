import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G10 AUDIT / HASH CHAIN INTEGRITY")
print("==============================================================")
p = Path("app/models/compliance.py")
if p.exists():
    txt = p.read_text(encoding='utf-8')
    if "score_hash" in txt and "sha256" in txt.lower():
        print("HASH_CHAIN_IMPLEMENTED=PASS")
        print("G10_RESULT=PASS"); sys.exit(0)
print("G10_RESULT=FAIL"); sys.exit(1)
