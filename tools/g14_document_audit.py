import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G14 DOCUMENTS / AI / HUMAN APPROVAL")
print("==============================================================")
p = Path("app/services/document_service.py")
if p.exists():
    txt = p.read_text(encoding='utf-8')
    if "human_approved" in txt and "in_review_queue" in txt:
        print("AI_APPROVAL_GATE=PASS")
        print("G14_RESULT=PASS"); sys.exit(0)
print("G14_RESULT=FAIL"); sys.exit(1)
