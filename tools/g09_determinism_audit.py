import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G09 RULE ENGINE DETERMINISM")
print("==============================================================")
# Static check: ensure no random or datetime.now() in engine evaluation
p = Path("app/rule_engine/engine.py")
if p.exists():
    txt = p.read_text(encoding='utf-8')
    if "random" not in txt and "datetime.now()" not in txt:
        print("ENGINE_DETERMINISM=PASS")
        print("G09_RESULT=PASS"); sys.exit(0)
print("G09_RESULT=FAIL"); sys.exit(1)
