#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# nlc-legal-toolkit: self-excluded from citation audit
"""
Deep legal citation audit - NLC rule engine vs Companies Act 1994 (Bangladesh).

WHAT IT DOES
  1. Scans the repo (app/, canonical_architecture/, scripts/, tests/, tools/,
     alembic/ plus top-level *.py / *.json rule files) for every rule
     declaration:  rule_id="XXX"  /  "rule_id": "XXX"  /  flag_code="XXX".
  2. Verifies the citation text inside each declaration window against the
     CA-1994 ground-truth table (EXPECTED) agreed in the legal research phase,
     and against per-rule + global FORBIDDEN (wrong-statute) citations.
  3. Verifies the engine code-patch state:
       C1 CATEGORY_CAPS must sum to 100
       C2 eval_state field present        (F3 UNKNOWN policy)
       C3 is_black_override membership    (REG-002 out, CHG-001 in)
       C4 UNKNOWN_COVERAGE_CAP present
       C5 is_black_override defined
  4. Writes a full report to legal_audit/legal_audit_<timestamp>.txt.

EXIT CODES : 0 = pass, 1 = violations found, 2 = fatal error
RUN        : python tools/legal_citation_audit.py
             python tools/legal_citation_audit.py --repo /f/NLC_RECOVERY_CLONES/nlc_platform_clean

Lines tagged with  audit-ok  are skipped by the global forbidden scan.
Files containing the marker  nlc-legal-toolkit  (the toolkit itself) are skipped.
"""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. GROUND TRUTH - Companies Act 1994 (Bangladesh) citation table
#    rule_id -> list of acceptable fragments (ANY ONE must appear inside the
#    declaration window). Matching is case-insensitive substring.
#    None => rule is exempt (internal escalation / non-CA-1994 basis).
# ---------------------------------------------------------------------------
EXPECTED = {
    # incorporation / registered office
    "INC-001": ["Section 23", "s.23"],                      # registration of MOA/AOA, s.23(1)
    "INC-003": ["Section 90", "s.90"],                      # minimum number of directors, s.90
    "OFF-001": ["Section 77", "s.77"],                      # change of registered office, s.77(2), Form VI, 28 days
    # registers / returns
    "REG-001": ["Section 34", "Sec 34", "s.34"],            # register of members, s.34
    "REG-002": ["Section 34", "Sec 34", "Section 115", "Sec 115",
                "Section 174", "Sec 174", "Sec 163", "Section 89", "Sec 89"],
    # general meetings
    "AGM-001": ["Section 81", "s.81"],                      # annual general meeting, s.81
    "AGM-002": ["Section 81", "s.81"],  # AGM deadline (subsequent AGM within 15 months)
    # audit & accounts
    "AUD-001": ["Section 210(6)", "s.210(6)", "210(6)"],    # first auditor within 1 month of registration
    "AUD-002": ["Section 183", "s.183"],                    # books of account, s.183
    "AUD-005": ["Section 210(3)", "210(3)"],                # auditor access / powers
    "ACC-002": ["Section 190", "s.190", "Form XII"],        # filing of financial statements, 30 days
    "AR-001":  ["Section 36", "s.36", "Form X"],            # annual return, 21 days after AGM
    # directors
    "DIR-001": ["Section 90", "s.90"],                      # number of directors
    "DIR-002": ["Section 93", "s.93"],
    "DIR-003": ["Section 115", "s.115"],                    # register of directors, Form IX
    "DIR-004": ["Section 109", "Section 110", "s.109", "s.110"],
    # defaults / enforcement
    "DEF-001": ["Section 182(9)", "Section 118(6)"],
    # shares & transfers
    "SH-001":  ["Section 158", "s.158"],
    "TR-001":  ["Section 38", "s.38"],
    "MEM-001": ["Section 222", "s.222"],
    # capital & charges
    "CAP-001": ["Section 53", "Section 56", "s.53", "s.56"],
    "CAP-002": ["Section 151", "s.151", "Form XV"],         # return of allotment, 30 days
    "CAP-003": ["Section 150", "s.150"],                    # TODO confirm against RJSC form schedule
    "CHG-001": ["Section 159", "s.159"],                    # registration of charges, 21 days, void if late
    # internal / cross-regime rules
    "ESC-001": None,                                        # internal escalation policy - no CA citation needed
    "TL-001":  ["City Corporation", "Pourashava", "Trade License"],  # trade license law (non-CA-1994)
}

# Fragments that must ALL appear in ONE declaration window (stricter checks).
REQUIRED_ALL = {
    "REG-002": ["sec 34", "sec 115", "companies act 1994"],
    "AUD-001": ["210(6)"],
}

# rule_ids that must NO LONGER exist in the code (split / renamed).
FORBIDDEN_RULE_IDS = {
    "INC-002": "D2 fix: INC-002 duplicated INC-001; it was split into OFF-001 "
               "(s.77(2) registered-office notice, 28 days, Form VI).",
}

# Per-rule forbidden fragments (old wrong citations that must disappear).
FORBIDDEN = {
    "AUD-001": ["210(2a)", "120 days"],        # s.210(2A) is an India-style citation; BD 1994 s.210(6) = 1 month
    "REG-002": ["sec 87", "sec 90)", "sec 83)"],  # old wrong register citations
}

# Globally forbidden strings anywhere in the repo (wrong-statute citations).
GLOBAL_FORBIDDEN = [
    "210(2a)",              # sub-section does not exist in CA 1994 s.210
    "companies act 1956",   # Indian statute - wrong act
    "companies act 2013",   # Indian statute - wrong act
]

SCAN_DIRS = ["app", "canonical_architecture", "scripts", "tests", "tools"]  # alembic excluded (migrations are historical)
SCAN_GLOBS = (".py", ".json")
DECL_RE = re.compile(
    r'(?:rule_id|flag_code)\s*[:=]\s*["\']([A-Z]{1,6}-[0-9]{1,4}[A-Za-z0-9]*)["\']')
WINDOW_BEFORE = 200        # chars of context kept BEFORE a declaration
MAX_WINDOW_AFTER = 1600    # max chars AFTER a declaration
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
             "legal_audit", ".idea", ".vscode", "backup"}
TOOLKIT_MARKER = "self-excluded from citation audit"


def safe_print(msg):
    """Print without crashing on Windows consoles (cp1252)."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def read_text(p):
    return p.read_text(encoding="utf-8", errors="surrogateescape")


def collect_files(root):
    files = []
    for d in SCAN_DIRS:
        dp = root / d
        if not dp.is_dir():
            continue
        for p in dp.rglob("*"):
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix in SCAN_GLOBS:
                files.append(p)
    for p in root.iterdir():
        if p.is_file() and p.suffix in SCAN_GLOBS:
            files.append(p)
    return sorted(set(files))


def build_windows(text):
    """Return list of (rule_id, start, end, line_no) declaration windows."""
    decls = [(m.group(1), m.start(1)) for m in DECL_RE.finditer(text)]
    out = []
    for i, (rid, pos) in enumerate(decls):
        start = max(0, pos - WINDOW_BEFORE)
        if i + 1 < len(decls):
            nxt = decls[i + 1][1]
            end = nxt if nxt - start <= MAX_WINDOW_AFTER + WINDOW_BEFORE \
                else start + MAX_WINDOW_AFTER + WINDOW_BEFORE
        else:
            end = min(len(text), start + MAX_WINDOW_AFTER + WINDOW_BEFORE)
        line_no = text.count("\n", 0, pos) + 1
        out.append((rid, start, end, line_no))
    return out


def git_state(root):
    lines = []
    for args, label in ((["rev-parse", "--abbrev-ref", "HEAD"], "branch"),
                        (["log", "-3", "--oneline"], "last 3 commits")):
        try:
            r = subprocess.run(["git"] + args, cwd=str(root), capture_output=True,
                               text=True, timeout=10)
            val = (r.stdout or "").strip() or "N/A"
        except Exception:
            val = "N/A"
        lines.append("    %-15s %s" % (label + ":", val.replace("\n", " | ")))
    try:
        r = subprocess.run(["git", "status", "--short"], cwd=str(root),
                           capture_output=True, text=True, timeout=10)
        dirty = [l for l in (r.stdout or "").splitlines() if l.strip()]
        lines.append("    %-15s %d dirty file(s)" % ("working tree:", len(dirty)))
        for d in dirty[:10]:
            lines.append("      " + d)
    except Exception:
        pass
    return lines


def engine_candidates(files):
    out = []
    for p in files:
        if p.suffix != ".py":
            continue
        try:
            t = read_text(p)
        except Exception:
            continue
        if TOOLKIT_MARKER in t:
            continue
        if ("ComplianceFlag" in t or "_calculate_score" in t
                or "CATEGORY_CAPS" in t):
            out.append(p)
    return out


def parse_caps_sum(text):
    m = re.search(r'CATEGORY_CAPS\s*=\s*\{', text)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(text) and depth:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        i += 1
    body = text[m.end():i - 1]
    total = 0
    for k, v in re.findall(r'["\']?([A-Za-z_]+)["\']?\s*:\s*(\d+)', body):
        total += int(v)
    return total


def black_override_body(text):
    """Return the exact body of def is_black_override (function only, not the
    rest of the file - rule_id declarations further down must not leak in)."""
    m = re.search(r'(?m)^([ \t]*)def\s+is_black_override\b', text)
    if not m:
        return None
    indent = m.group(1)
    lines = text[m.start():].splitlines(keepends=True)
    body = [lines[0]]
    for ln in lines[1:]:
        if ln.strip() == "":
            body.append(ln)
            continue
        li = re.match(r'^[ \t]*', ln).group(0)
        if len(li) <= len(indent):
            break
        body.append(ln)
    return "".join(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="path to nlc_platform_clean")
    ap.add_argument("--strict", action="store_true",
                    help="treat MISSING rules as failures too")
    args = ap.parse_args()
    root = Path(args.repo).resolve()

    out_lines = []
    emit = out_lines.append
    emit("=" * 78)
    emit(" DEEP LEGAL CITATION AUDIT - NLC RULE ENGINE")
    emit(" Statute: Companies Act 1994 (Bangladesh) - rule-map ground truth v1.0")
    emit(" Generated: %s  |  Repo: %s" % (datetime.datetime.now().isoformat(timespec='seconds'), root))
    emit("=" * 78)

    fails, warns, passes = [], [], []

    # ---- [A] repo state -----------------------------------------------------
    emit("")
    emit("[A] REPO STATE")
    for l in git_state(root):
        emit(l)

    # ---- [B] scan -----------------------------------------------------------
    files = collect_files(root)
    scan_py = [p for p in files if p.suffix == ".py"]
    scan_json = [p for p in files if p.suffix == ".json"]
    emit("")
    emit("[B] SCAN SUMMARY")
    emit("    files scanned: %d (py: %d, json: %d)"
         % (len(files), len(scan_py), len(scan_json)))

    decl_windows = []  # (file, rid, start, end, line_no)
    global_forbidden_hits = []
    for p in files:
        try:
            text = read_text(p)
        except Exception as e:
            warns.append("unreadable file: %s (%s)" % (p, e))
            continue
        if TOOLKIT_MARKER in text:
            continue
        for rid, s, e, ln in build_windows(text):
            decl_windows.append((p, rid, s, e, ln))
        for ln_no, line in enumerate(text.splitlines(), 1):
            if "audit-ok" in line:
                continue
            low = line.lower()
            for g in GLOBAL_FORBIDDEN:
                if g in low:
                    global_forbidden_hits.append((p, ln_no, g, line.strip()[:150]))

    rule_map = {}
    for p, rid, s, e, ln in decl_windows:
        rule_map.setdefault(rid, []).append((p, s, e, ln))

    emit("    rule declarations found: %d (distinct rule_ids: %d)"
         % (len(decl_windows), len(rule_map)))

    # ---- [C] citation audit per rule ----------------------------------------
    emit("")
    emit("[C] CITATION AUDIT PER RULE")
    for rid in sorted(rule_map):
        windows = rule_map[rid]
        where = "; ".join("%s:%d" % (p.relative_to(root), ln)
                          for p, s, e, ln in windows[:3])
        if rid in FORBIDDEN_RULE_IDS:
            msg = "FAIL  %-9s forbidden rule id still present (%d decl) - %s" % (
                rid, len(windows), FORBIDDEN_RULE_IDS[rid])
            emit("    " + msg)
            emit("        at " + where)
            fails.append(msg)
            continue
        exp = EXPECTED.get(rid, "UNMAPPED")
        if exp == "UNMAPPED":
            msg = "WARN  %-9s unmapped rule (%d decl) - extend EXPECTED table" % (
                rid, len(windows))
            emit("    " + msg)
            emit("        at " + where)
            warns.append(msg)
            continue
        if exp is None:
            msg = "PASS  %-9s exempt (internal/non-CA basis), %d decl" % (rid, len(windows))
            emit("    " + msg)
            passes.append(msg)
            continue
        req = REQUIRED_ALL.get(rid, [])
        forbidden = [f.lower() for f in FORBIDDEN.get(rid, [])]
        ok_any, ok_all = False, (not req)
        bad_hits = []
        snippets = []
        for p, s, e, ln in windows:
            text = read_text(p)
            w = text[s:e]
            low = w.lower()
            if any(f in low for f in (x.lower() for x in exp)):
                ok_any = True
            if req and all(f in low for f in req):
                ok_all = True
            for f in forbidden:
                if f in low:
                    idx = low.find(f)
                    frag = " ".join(w[max(0, idx - 40):idx + 60].split())
                    bad_hits.append("%s:%d  forbidden '%s'  ...%s..." % (
                        p.relative_to(root), ln, f, frag))
        if bad_hits:
            msg = "FAIL  %-9s forbidden citation(s) found" % rid
            emit("    " + msg)
            for b in bad_hits:
                emit("        " + b)
            fails.append(msg)
            continue
        if ok_any and ok_all:
            msg = "PASS  %-9s %d decl(s), citation OK  [%s]" % (
                rid, len(windows), where.split(";")[0])
            emit("    " + msg)
            passes.append(msg)
        else:
            miss = []
            if not ok_any:
                miss.append("expected any of: " + " / ".join(exp))
            if not ok_all:
                miss.append("expected ALL of: " + " + ".join(req))
            msg = "FAIL  %-9s %d decl(s) at %s" % (rid, len(windows), where)
            emit("    " + msg)
            for mline in miss:
                emit("        " + mline)
            fails.append(msg)

    for rid in sorted(k for k in EXPECTED if k not in rule_map):
        msg = "WARN  %-9s declared in truth table but not found in code (dead rule or renamed)" % rid
        emit("    " + msg)
        warns.append(msg)
        if args.strict:
            fails.append(msg)

    # ---- [D] forbidden rule ids ---------------------------------------------
    emit("")
    emit("[D] FORBIDDEN RULE IDS (must be removed / renamed)")
    found_bad = [r for r in rule_map if r in FORBIDDEN_RULE_IDS]
    if not found_bad:
        emit("    PASS  none present")
    else:
        for r in found_bad:
            msg = "FAIL  %s - %s" % (r, FORBIDDEN_RULE_IDS[r])
            emit("    " + msg)
            fails.append(msg)

    # ---- [E] global forbidden citations --------------------------------------
    emit("")
    emit("[E] GLOBAL FORBIDDEN CITATIONS (wrong-statute strings)")
    if not global_forbidden_hits:
        emit("    PASS  none found")
    else:
        for p, ln, g, line in global_forbidden_hits:
            msg = "FAIL  %s:%d contains '%s'" % (p.relative_to(root), ln, g)
            emit("    " + msg)
            emit("        line: %s" % line)
            fails.append(msg)

    # ---- [F] engine patch state ----------------------------------------------
    emit("")
    emit("[F] ENGINE PATCH STATE")
    cands = engine_candidates(files)
    if not cands:
        msg = "WARN  no engine file detected (searched for ComplianceFlag/_calculate_score/CATEGORY_CAPS)"
        emit("    " + msg)
        warns.append(msg)
    for p in cands:
        text = read_text(p)
        rel = p.relative_to(root)
        total = parse_caps_sum(text)
        if total is None:
            msg = "WARN  C1 %s: CATEGORY_CAPS not found" % rel
            emit("    " + msg)
            warns.append(msg)
        elif total == 100:
            msg = "PASS  C1 %s: CATEGORY_CAPS sums to 100" % rel
            emit("    " + msg)
            passes.append(msg)
        else:
            msg = "FAIL  C1 %s: CATEGORY_CAPS sums to %d (must be 100) - apply D1 score merge" % (
                rel, total)
            emit("    " + msg)
            fails.append(msg)
        if "eval_state" in text:
            msg = "PASS  C2 %s: eval_state field present (F3 UNKNOWN policy)" % rel
            emit("    " + msg)
            passes.append(msg)
        else:
            msg = "WARN  C2 %s: 'eval_state' not found - F3 UNKNOWN policy not applied (run tools/apply_legal_fixes.py)" % rel
            emit("    " + msg)
            warns.append(msg)
        body = black_override_body(text)
        if body is None:
            msg = "WARN  C5 %s: is_black_override not defined" % rel
            emit("    " + msg)
            warns.append(msg)
        else:
            msg = "PASS  C5 %s: is_black_override defined" % rel
            emit("    " + msg)
            passes.append(msg)
            if '"REG-002"' in body or "'REG-002'" in body:
                msg = "FAIL  C3 %s: REG-002 still in is_black_override (must be removed: severity RED, impact 12)" % rel
                emit("    " + msg)
                fails.append(msg)
            else:
                msg = "PASS  C3 %s: REG-002 not a black override" % rel
                emit("    " + msg)
                passes.append(msg)
            if '"CHG-001"' in body or "'CHG-001'" in body:
                emit("    INFO  C3 %s: CHG-001 stays BLACK (unregistered charge void vs creditor/liquidator, s.159 + s.165)" % rel)
            else:
                msg = "WARN  C3 %s: CHG-001 missing from is_black_override (G4: should be BLACK)" % rel
                emit("    " + msg)
                warns.append(msg)
        if "UNKNOWN_COVERAGE_CAP" in text:
            msg = "PASS  C4 %s: UNKNOWN_COVERAGE_CAP present (coverage penalty)" % rel
            emit("    " + msg)
            passes.append(msg)
        else:
            emit("    INFO  C4 %s: UNKNOWN_COVERAGE_CAP not found (optional coverage penalty not applied)" % rel)

    # ---- [G] verdict -----------------------------------------------------------
    fails = list(dict.fromkeys(fails))   # dedupe identical failures
    warns = list(dict.fromkeys(warns))
    emit("")
    emit("[G] VERDICT: %d FAIL / %d WARN / %d PASS"
         % (len(fails), len(warns), len(passes)))
    if fails:
        emit("    REMEDIATION:")
        emit("      1. python tools/apply_legal_fixes.py        (auto-applies F1/F2/F3)")
        emit("      2. update stale test expectations manually  (see README section 5)")
        emit("      3. re-run: python tools/legal_citation_audit.py   until exit 0")
    else:
        emit("    ALL CHECKS PASSED - citations match the CA-1994 ground truth table.")
    emit("=" * 78)

    out_dir = root / "legal_audit"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / ("legal_audit_%s.txt" % ts)
    out_file.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    safe_print("")
    safe_print("Report written: %s" % out_file)

    for line in out_lines:
        safe_print(line)

    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fatal
        print("FATAL AUDIT ERROR: %r" % exc)
        sys.exit(2)
