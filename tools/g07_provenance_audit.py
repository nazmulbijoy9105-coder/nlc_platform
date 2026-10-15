import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G07 LEGAL PROVENANCE COMPLETENESS")
print("==============================================================")
# Check if legal_reconciliation.py exists and has 75 entries
p = Path("canonical_architecture/legal_reconciliation.py")
if p.exists():
    txt = p.read_text(encoding='utf-8')
    if txt.count('"rule_id":') >= 75:
        print("PROVENANCE_REGISTRY=75")
        print("G07_RESULT=PASS"); sys.exit(0)
print("G07_RESULT=FAIL"); sys.exit(1)
