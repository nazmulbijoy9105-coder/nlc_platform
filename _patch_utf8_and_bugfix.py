#!/usr/bin/env python3
import sys, re
from pathlib import Path

TARGETS = ["verify_rls.py", "verify_tenant_isolation.py", "verify_transfer_mapping.py",
           "verify_rule_integrity.py", "verify_rescue_lifecycle.py", "verify_rjsc_api.py",
           "verify_db_ops.py", "verify_commercial.py", "verify_historical.py",
           "run_all_verifications.py"]

REPL = [("\u2194","<->"), ("\u2192","->"), ("\u2190","<-"), ("\u2191","^"), ("\u2193","v"),
        ("\u2014","--"), ("\u2013","-"), ("\u2018","'"), ("\u2019","'"), ("\u201c",'"'),
        ("\u201d",'"'), ("\u2026","..."), ("\u00b7","*"), ("\u2022","*"), ("\u00d7","x"),
        ("\u00f7","/"), ("\u2212","-"), ("\u2264","<="), ("\u2265",">="), ("\u2260","!=")]

HDR = ("import sys\n"
       "try:\n"
       "    sys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
       "    sys.stderr.reconfigure(encoding='utf-8', errors='replace')\n"
       "except Exception:\n"
       "    pass\n")

for name in TARGETS:
    p = Path(name)
    if not p.exists():
        print(f"[SKIP] {name}: not found")
        continue
    t = p.read_text(encoding="utf-8")
    o = t
    bug = 0
    if "routes_by_file: dict[str, list[dict]] = []" in t:
        t = t.replace("routes_by_file: dict[str, list[dict]] = []",
                      "routes_by_file: dict[str, list[dict]] = {}")
        bug = 1
    n = 0
    for u, a in REPL:
        c = t.count(u)
        if c:
            t = t.replace(u, a)
            n += c
    hdr = 0
    if "sys.stdout.reconfigure" not in t:
        L = t.split("\n")
        ins = None
        for i, ln in enumerate(L):
            if re.match(r"^(import\s+\w|from\s+\w)", ln):
                ins = i
                break
        if ins is not None:
            L.insert(ins, HDR.rstrip("\n"))
            t = "\n".join(L)
            hdr = 1
    if t != o:
        p.write_text(t, encoding="utf-8")
        msg = f"[OK ] {name}: {n} unicode replaced"
        if bug: msg += ", list/dict bug FIXED"
        if hdr: msg += ", UTF-8 header ADDED"
        print(msg)
    else:
        print(f"[--] {name}: already patched")

print()
print("Done.")
