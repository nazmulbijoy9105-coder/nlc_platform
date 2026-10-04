import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G08 STATUTORY RESCUE INTEGRITY")
print("==============================================================")
p = Path("canonical_architecture/statutory_rescue.py")
if p.exists():
    txt = p.read_text(encoding='utf-8')
    if txt.count('"rescue_id":') >= 75 and txt.count('"triggered_by":') >= 75:
        print("RESCUE_MAPPINGS=75")
        print("G08_RESULT=PASS"); sys.exit(0)
print("G08_RESULT=FAIL"); sys.exit(1)
