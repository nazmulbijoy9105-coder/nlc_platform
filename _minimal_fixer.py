import re, ast, sys
from pathlib import Path
H = re.compile(r'^import sys\ntry:\n    sys\.stdout\.reconfigure\(encoding=[^\n]+\n    sys\.stderr\.reconfigure\(encoding=[^\n]+\nexcept Exception:\n    pass\n', re.M)
N = 'import sys\ntry:\n    sys.stdout.reconfigure(encoding="utf-8", errors="replace")\n    sys.stderr.reconfigure(encoding="utf-8", errors="replace")\nexcept Exception:\n    pass\n'
TARGETS = ["verify_rls.py","verify_tenant_isolation.py","verify_transfer_mapping.py","verify_rule_integrity.py","verify_rescue_lifecycle.py","verify_rjsc_api.py","verify_db_ops.py","verify_commercial.py","verify_historical.py","run_all_verifications.py"]
for f in TARGETS:
    p = Path(f)
    if not p.exists():
        print(f"SKIP {f}: not found")
        continue
    t = p.read_text(encoding="utf-8")
    t2 = H.sub("", t)
    lines = t2.split("\n")
    ins = 0
    if lines and lines[0].startswith("#!"): ins = 1
    while ins < len(lines) and lines[ins].strip() == "": ins += 1
    if ins < len(lines) and (lines[ins].startswith('"""') or lines[ins].startswith("'''")):
        if lines[ins].count('"""') >= 2 or lines[ins].count("'''") >= 2:
            ins += 1
        else:
            q = '"""' if lines[ins].startswith('"""') else "'''"
            ins += 1
            while ins < len(lines) and q not in lines[ins]: ins += 1
            ins += 1
    while ins < len(lines) and re.match(r"^from\s+__future__", lines[ins]): ins += 1
    while ins < len(lines) and (lines[ins].strip() == "" or lines[ins].lstrip().startswith("#")): ins += 1
    while ins < len(lines) and not re.match(r"^(import\s+\w|from\s+\w)", lines[ins]): ins += 1
    if ins >= len(lines): ins = len(lines)
    lines.insert(ins, N.rstrip("\n"))
    t2 = "\n".join(lines)
    if t2 != t:
        p.write_text(t2, encoding="utf-8")
        try:
            ast.parse(p.read_text(encoding="utf-8"))
            print(f"OK  {f}: fixed, syntax OK")
        except SyntaxError as e:
            print(f"ERR {f}: {e}")
    else:
        print(f"--  {f}: no change needed")