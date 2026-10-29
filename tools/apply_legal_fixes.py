#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# nlc-legal-toolkit: self-excluded from citation audit
"""
apply_legal_fixes.py - applies the 2026-10-30 legal corrections to the NLC rule engine.

FIXES APPLIED
  F1  AUD-001  citation + template
        old: "First auditor not appointed within 120 days of incorporation. Section 210(2A): overdue by {d} days."
        new: "First auditor not appointed within 1 month (30 days) of registration. Section 210(6), Companies Act 1994: overdue by {d} days."
      (CA 1994 s.210(6): first auditor appointed by the Board within ONE MONTH of
       registration - NOT 120 days; s.210(2A) does not exist in the 1994 Act.)

  F2  REG-002  citation block + severity + impact + black-override membership
        citation block -> "Members (Sec 34-36), Directors (Sec 115), Charges (Sec 174; RJSC register Sec 163-165), GM & Board Minutes (Sec 89), Companies Act 1994."
        severity       : BLACK -> RED
        score impact   : 20 -> 12
        is_black_override : "REG-002" removed (it is a RED register defect, not a score-voiding event)

  F3  UNKNOWN evaluation policy
        a. ComplianceFlag gains  eval_state: str = "VIOLATION"
        b. __post_init__ forces score_impact = 0 when eval_state == "UNKNOWN"
        c. UNKNOWN_COVERAGE_CAP / UNKNOWN_COVERAGE_PER constants + coverage
           penalty subtracted after the category roll-up in _calculate_score
        d. _generate_rescue_sequence excludes UNKNOWN flags
        e. INC-001 (moa_aoa_filed is None) and AGM-001 (no AGM dates) are
           flagged with eval_state="UNKNOWN"
           AUD-001 stays VIOLATION (the overdue fact is determinate from the
           registration date)

BEHAVIOR
  * backs up every modified file to legal_audit/backup/<name>.<ts>.bak
  * every fix is idempotent (re-run reports ALREADY)
  * string fixes (F1, F2 citation/severity/impact) also run on tests/*.py
  * structural fixes (F2 black-override, F3 a-d) run on the engine file only
  * writes legal_audit/patch_report_<timestamp>.txt
  * exit 0 = all fixes applied or already applied; exit 1 = some fix needs
    manual action (see MANUAL SNIPPETS in the report / README section 6)

RUN
  python tools/apply_legal_fixes.py
  python tools/apply_legal_fixes.py --repo /f/NLC_RECOVERY_CLONES/nlc_platform_clean
  python tools/apply_legal_fixes.py --dry-run
"""

import argparse
import datetime
import glob
import re
import shutil
import sys
from pathlib import Path

TOOLKIT_MARKER = "# nlc-legal-toolkit: self-excluded from citation audit"

DECL_RE = re.compile(
    r'(?:rule_id|flag_code)\s*[:=]\s*["\']([A-Z]{1,6}-[0-9]{1,4}[A-Za-z0-9]*)["\']')

REPORT = []
def log(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))
    REPORT.append(str(msg))

def read_text(p):
    return p.read_text(encoding="utf-8", errors="surrogateescape")

def write_text(p, t):
    p.write_text(t, encoding="utf-8", errors="surrogateescape")

def rule_windows(text, rid, before=0):
    """(start, end) spans of declarations of rid, window ends at next decl."""
    ms = [(m.group(1), m.start(1)) for m in DECL_RE.finditer(text)]
    out = []
    for i, (r, pos) in enumerate(ms):
        if r != rid:
            continue
        start = max(0, pos - before)
        if i + 1 < len(ms):
            nxt = ms[i + 1][1]
            end = nxt if nxt - start <= 1800 + before else start + 1800 + before
        else:
            end = min(len(text), start + 1800 + before)
        out.append((start, end))
    return out


# ---------------------------------------------------------------------------
# F1  AUD-001 template
# ---------------------------------------------------------------------------
OLD_AUD = (r"First auditor not appointed within 120 days of incorporation\. "
           r"Section 210\(2A\): overdue by \{[a-z_]+\} days\.")
NEW_AUD = ("First auditor not appointed within 1 month (30 days) of registration. "
           "Section 210(6), Companies Act 1994: overdue by {d} days.")

def fix_aud001(text):
    changed = 0
    notes = []
    already_new = "1 month (30 days) of registration" in text
    # 1) description template FIRST (it contains "Section 210(2A)" itself,
    #    so it must be replaced before the window-level citation cleanup)
    if not already_new:
        text, n = re.subn(OLD_AUD, lambda m: NEW_AUD, text)
        if n:
            changed += n
            notes.append("%d template occurrence(s) replaced" % n)
    # 2) replace any remaining s.210(2A) citations inside AUD-001 declaration
    #    windows (e.g. statutory_basis="Section 210(2A).")
    wins = rule_windows(text, "AUD-001")
    for s, e in sorted(wins, reverse=True):
        w = text[s:e]
        w2, n1 = re.subn(r'Section 210\(2A\)', 'Section 210(6), Companies Act 1994', w)
        w2, n2 = re.subn(r'(?<!Section )210\(2A\)', 's.210(6)', w2)
        # half-patched leftovers: new citation but old "120 days" wording
        w2, n3 = re.subn(r'within 120 days of incorporation',
                         'within 1 month (30 days) of registration', w2)
        if n1 + n2 + n3:
            text = text[:s] + w2 + text[e:]
            changed += n1 + n2 + n3
            notes.append("%d residual AUD-001 fragment(s) fixed" % (n1 + n2 + n3))
    if changed:
        return text, "APPLIED", "; ".join(notes)
    if already_new:
        return text, "ALREADY", "new AUD-001 text already present"
    if not wins:
        return text, "N/A", "no AUD-001 text in this file"
    return text, "SKIP", ("old AUD-001 template not found verbatim - "
                          "update the AUD-001 description manually (README 6.1)")


# ---------------------------------------------------------------------------
# F2a  REG-002 citation block
# ---------------------------------------------------------------------------
OLD_REG = (r"Members \(Sec 34\), Directors \(Sec 90\), Charges \(Sec 87\), "
           r"AGM Minutes \(Sec 83\)\.")
NEW_REG = ("Members (Sec 34\u201336), Directors (Sec 115), Charges (Sec 174; "
           "RJSC register Sec 163\u2013165), GM & Board Minutes (Sec 89), "
           "Companies Act 1994.")

def fix_reg002_block(text):
    if "RJSC register Sec 163" in text:
        return text, "ALREADY", "new REG-002 citation block already present"
    new, n = re.subn(OLD_REG, lambda m: NEW_REG, text)
    if n:
        return new, "APPLIED", "%d occurrence(s) replaced" % n
    if not rule_windows(text, "REG-002"):
        return text, "N/A", "no REG-002 text in this file"
    return text, "SKIP", ("old REG-002 citation block not found verbatim - "
                          "update manually (README 6.2)")


# ---------------------------------------------------------------------------
# F2b/F2c  REG-002 severity + impact (inside REG-002 declaration windows only)
# ---------------------------------------------------------------------------
def fix_reg002_severity_impact(text, filename):
    wins = rule_windows(text, "REG-002")
    if not wins:
        return text, "N/A", "no REG-002 declaration found in %s" % filename
    changed, already = 0, 0
    for s, e in sorted(wins, reverse=True):  # reverse: keep earlier offsets valid
        w = text[s:e]
        if re.search(r'severity\s*[:=]\s*(["\']?)(RED|Severity\.RED|FlagSeverity\.RED)\b', w) \
                and re.search(r'(?:score_)?impact\s*[:=]\s*12\b', w):
            already += 1
            continue
        w2, n1 = re.subn(r'severity(\s*[:=]\s*["\']?)BLACK\b', r'severity\1RED', w)
        w2, n2 = re.subn(r'(FlagSeverity|Severity)\.BLACK\b', r'\1.RED', w2)
        w2, n3 = re.subn(r'score_impact(\s*[:=]\s*)20\b', r'score_impact\g<1>12', w2)
        w2, n4 = re.subn(r'(?<![a-z_])impact(\s*[:=]\s*)20\b', r'impact\g<1>12', w2)
        if n1 + n2 + n3 + n4:
            text = text[:s] + w2 + text[e:]
            changed += 1
    if changed:
        return text, "APPLIED", "%d REG-002 window(s): severity BLACK->RED, impact 20->12" % changed
    # (windows processed in reverse to keep offsets valid)
    if already == len(wins):
        return text, "ALREADY", "severity RED + impact 12 already set"
    return text, "SKIP", ("REG-002 window(s) found but severity/impact pattern "
                          "not recognized - update manually (README 6.3)")


# ---------------------------------------------------------------------------
# F2d  remove REG-002 from is_black_override
# ---------------------------------------------------------------------------
def _override_spans(text):
    """Char spans of (a) def is_black_override bodies and (b) module-level
    assignments whose variable name contains 'black'. Only inside these spans
    may a rule id be removed from the black-override context."""
    spans = []
    lines = text.splitlines(keepends=True)
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln))
    i = 0
    while i < len(lines):
        m = re.match(r'^([ \t]*)def\s+is_black_override\b', lines[i])
        if m:
            ind = len(m.group(1))
            j = i + 1
            while j < len(lines):
                if lines[j].strip() == "":
                    j += 1
                    continue
                li = len(re.match(r'^[ \t]*', lines[j]).group(0))
                if li <= ind:
                    break
                j += 1
            spans.append((offs[i], offs[j]))
            i = j
        else:
            i += 1
    for m2 in re.finditer(r'(?m)^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([\[\{\(])', text):
        if re.search(r'(?i)black', m2.group(1)):
            open_ch, close_ch = m2.group(2), {'[': ']', '{': '}', '(': ')'}[m2.group(2)]
            depth, k = 1, m2.end()
            while k < len(text) and depth:
                if text[k] == open_ch:
                    depth += 1
                elif text[k] == close_ch:
                    depth -= 1
                k += 1
            spans.append((m2.start(), k))
    return spans


def fix_black_override(text, rid="REG-002"):
    spans = _override_spans(text)
    if not spans:
        return text, "SKIP", ("is_black_override / BLACK_OVERRIDE set not found "
                              "- remove '%s' from it manually (README 6.4)" % rid)
    hits = []
    for s, e in spans:
        seg = text[s:e]
        for mm in re.finditer(r'["\']%s["\']' % rid, seg):
            hits.append((s + mm.start(), s + mm.end()))
    if not hits:
        return text, "ALREADY", "%s not in is_black_override / black set" % rid
    for hs, he in sorted(hits, reverse=True):
        pre, post = text[:hs], text[he:]
        m_tr = re.match(r'\s*,\s*', post)
        if m_tr:
            post = post[m_tr.end():]
        else:
            m_ld = re.search(r',\s*$', pre)
            if m_ld:
                pre = pre[:m_ld.start()]
        text = pre + post
    text = re.sub(r'\{\s*,', '{', text)
    text = re.sub(r'\[\s*,', '[', text)
    text = re.sub(r'\(\s*,', '(', text)
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r',\s*([\}\]\)])', r'\1', text)
    text = re.sub(r'"\s*,\s*"', '", "', text)
    return text, "APPLIED", "%d occurrence(s) removed from black-override context" % len(hits)


# ---------------------------------------------------------------------------
# F3a/F3b  ComplianceFlag.eval_state field + __post_init__ zeroing
# ---------------------------------------------------------------------------
FIELD_RE = re.compile(r'^[ \t]+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*[^=]+(?:=.*)?$')

def fix_eval_state_field(text):
    m = re.search(r'(?m)^class\s+ComplianceFlag\b[^\n]*$', text)
    if not m:
        return text, "SKIP", "class ComplianceFlag not found in engine file"
    if "eval_state" in text:
        return text, "ALREADY", "eval_state already present"
    # class block = from class line to next column-0 class/def
    rest = text[m.start():]
    block_end = len(rest)
    for mm in re.finditer(r'(?m)^(class\s+\w+|def\s+\w+)', rest[1:]):
        block_end = 1 + mm.start()
        break
    block = rest[:block_end]
    # dataclass?
    frozen = "frozen=True" in text[max(0, m.start() - 200):m.start() + 200]
    is_dc = "@dataclass" in text[max(0, m.start() - 200):m.end()]
    lines = block.splitlines(keepends=True)
    last_field_i = None
    for i, ln in enumerate(lines):
        if FIELD_RE.match(ln.rstrip("\n")):
            last_field_i = i
    if last_field_i is None:
        return text, "SKIP", ("ComplianceFlag has no typed fields - add the "
                              "eval_state field manually (README 6.5)")
    indent = re.match(r'^([ \t]+)', lines[last_field_i]).group(1)
    field_line = ('%seval_state: str = "VIOLATION"   # F3: UNKNOWN -> impact forced to 0\n'
                  % indent)
    zero_set = ("object.__setattr__(self, 'score_impact', 0)" if frozen
                else "self.score_impact = 0")
    post = ("\n%(i)sdef __post_init__(self):\n"
            "%(i)s    # F3 UNKNOWN policy: unknown facts are indeterminate, not violations\n"
            "%(i)s    if self.eval_state == \"UNKNOWN\":\n"
            "%(i)s        ZERO\n" % {"i": indent}).replace("ZERO", zero_set)
    if "__post_init__" in block:
        # insert zeroing at top of existing __post_init__ body
        pm = re.search(r'(?m)^[ \t]*def\s+__post_init__\s*\([^\)]*\)\s*:[^\n]*\n', block)
        fb = re.search(r'(?m)^[ \t]+\S', text[pm.end():pm.end() + 1000])
        body_indent = re.match(r'^([ \t]+)', fb.group(0)).group(1) if fb else (indent + "    ")
        zero = ("%(bi)s# F3 UNKNOWN policy: unknown facts are indeterminate, not violations\n"
                "%(bi)sif self.eval_state == \"UNKNOWN\":\n"
                "%(bi)s    Z\n" % {"bi": body_indent}).replace("Z", zero_set)
        new_block = block[:pm.end()] + zero + block[pm.end():]
        new_text = text[:m.start()] + field_line + new_block + text[m.start() + block_end:]
        mode = "field inserted + zeroing added to existing __post_init__"
    else:
        # insert field after last field line, and method right after it
        ins_at = sum(len(l) for l in lines[:last_field_i + 1])
        new_block = block[:ins_at] + field_line + post + block[ins_at:]
        new_text = text[:m.start()] + new_block + text[m.start() + block_end:]
        mode = "field inserted + new __post_init__ added"
    if not is_dc:
        mode += "  [NOTE: @dataclass not detected - verify __post_init__ is called]"
    return new_text, "APPLIED", mode


# ---------------------------------------------------------------------------
# F3c  constants + coverage penalty in _calculate_score
# ---------------------------------------------------------------------------
CONST_BLOCK = ("# F3 UNKNOWN policy constants (legal fix 2026-10-30)\n"
               "UNKNOWN_COVERAGE_CAP = 5   # max total points withheld for unknown facts\n"
               "UNKNOWN_COVERAGE_PER = 1   # points withheld per UNKNOWN flag\n\n")

def fix_unknown_constants_and_penalty(text):
    if "UNKNOWN_COVERAGE_CAP" in text:
        return text, "ALREADY", "constants already present"
    m = re.search(r'(?m)^(CATEGORY_CAPS\s*=)', text)
    if m:
        text = text[:m.start()] + CONST_BLOCK + text[m.start():]
    else:
        last = None
        for mm in re.finditer(r'(?m)^(import\s[^\n]+|from\s[^\n]+)\n', text[:6000]):
            last = mm
        if not last:
            return text, "SKIP", "no CATEGORY_CAPS and no import block - insert constants manually (README 6.6)"
        text = text[:last.end()] + "\n" + CONST_BLOCK + text[last.end():]
    # find the flags iterable name
    sig = re.search(r'def\s+_calculate_score\s*\(([^)]*)\)', text)
    it_name = None
    if sig:
        for p in sig.group(1).split(","):
            p = p.strip()
            if p and p != "self":
                it_name = p.split(":")[0].split("=")[0].strip()
                break
    body_m = re.search(r'(?m)^([ \t]*)raw\s*=\s*sum\(cat_scores\.values\(\)\)', text)
    if not (body_m and it_name):
        return text, "PARTIAL", ("constants inserted, but penalty NOT inserted: "
                                 "anchor 'raw = sum(cat_scores.values())' or flags param missing "
                                 "- paste the snippet from README 6.6")
    indent = body_m.group(1)
    ins = ("\n%(i)s# F3: UNKNOWN facts - coverage penalty (per-flag impact already zeroed)\n"
           "%(i)s_unk_n = sum(1 for _f in %(f)s if getattr(_f, 'eval_state', 'VIOLATION') == 'UNKNOWN')\n"
           "%(i)sif _unk_n:\n"
           "%(i)s    raw -= min(UNKNOWN_COVERAGE_CAP, _unk_n * UNKNOWN_COVERAGE_PER)"
           % {"i": indent, "f": it_name})
    text = text[:body_m.end()] + ins + text[body_m.end():]
    return text, "APPLIED", "constants + coverage penalty inserted (iterates '%s')" % it_name


# ---------------------------------------------------------------------------
# F3d  _generate_rescue_sequence excludes UNKNOWN
# ---------------------------------------------------------------------------
def fix_rescue_exclusion(text):
    m = re.search(r'def\s+_generate_rescue_sequence\s*\(([^)]*)\)', text)
    if not m:
        return text, "SKIP", "_generate_rescue_sequence not found (name may differ) - README 6.7"
    body = text[m.start():m.start() + 2500]
    if "eval_state" in body and "!= 'UNKNOWN'" in body.replace('"UNKNOWN"', "'UNKNOWN'"):
        return text, "ALREADY", "UNKNOWN exclusion already present"
    fname = None
    for p in m.group(1).split(","):
        p = p.strip()
        if p and p != "self":
            fname = p.split(":")[0].split("=")[0].strip()
            break
    if not fname:
        return text, "SKIP", "no flags parameter in _generate_rescue_sequence signature - README 6.7"
    def_line_end = text.find("\n", m.start())
    first_body = re.search(r'(?m)^[ \t]+\S', text[def_line_end:def_line_end + 4000])
    if not first_body:
        return text, "SKIP", "empty _generate_rescue_sequence body - README 6.7"
    indent = re.match(r'^([ \t]+)', first_body.group(0)).group(1)
    ins = ("%s%s = [f for f in %s if getattr(f, 'eval_state', 'VIOLATION') != 'UNKNOWN']"
           "  # F3: exclude UNKNOWN from rescue\n" % (indent, fname, fname))
    at = def_line_end + 1  # start of the first body line
    return text[:at] + ins + text[at:], "APPLIED", "UNKNOWN flags excluded from rescue sequence"


# ---------------------------------------------------------------------------
# F3e  INC-001 / AGM-001 -> eval_state="UNKNOWN"
# ---------------------------------------------------------------------------
def mark_rule_unknown(text, rid):
    ms = [(m.group(1), m.start(1)) for m in DECL_RE.finditer(text)]
    decls = [pos for r, pos in ms if r == rid]
    if not decls:
        return text, "SKIP", "no %s declaration found" % rid
    changed, already = 0, 0
    for pos in sorted(decls, reverse=True):  # reverse: keep earlier offsets valid
        line_start = text.rfind("\n", 0, pos) + 1
        line_end = text.find("\n", pos)
        line_end = len(text) if line_end == -1 else line_end
        line = text[line_start:line_end]
        window = text[line_start:min(len(text), line_start + 1200)]
        if "eval_state" in window:
            already += 1
            continue
        indent = re.match(r'^([ \t]*)', line).group(1)
        stripped = line.rstrip()
        if stripped.endswith('"') or stripped.endswith("'"):
            # declaration is the last token on its line -> terminate with a comma
            line = stripped + ","
            text = text[:line_start] + line + text[line_end:]
            line_end = line_start + len(line)
        ins_line = ('%seval_state="UNKNOWN",   # F3: missing input -> UNKNOWN, not VIOLATION\n'
                    % (indent + "    "))
        text = text[:line_end + 1] + ins_line + text[line_end + 1:]
        changed += 1
    if changed:
        return text, "APPLIED", "%d %s declaration(s) marked eval_state=UNKNOWN" % (changed, rid)
    return text, "ALREADY", "%s already marked" % rid


# ---------------------------------------------------------------------------
# file plumbing
# ---------------------------------------------------------------------------
SCAN_DIRS = ["app", "canonical_architecture", "scripts", "tests", "tools"]

def find_files(root):
    files = []
    for d in SCAN_DIRS:
        dp = root / d
        if dp.is_dir():
            files += [p for p in dp.rglob("*.py")
                      if not any(part in {".git", "__pycache__", "backup", "legal_audit"}
                                 for part in p.parts)]
    return sorted(set(files))

def find_engine_file(files):
    for p in files:
        t = read_text(p)
        if "ComplianceFlag" in t and ("_calculate_score" in t or "CATEGORY_CAPS" in t):
            return p
    for p in files:
        if "ComplianceFlag" in read_text(p):
            return p
    return None

def backup(p, backup_dir, ts, _done=set()):
    """Back up a file ONCE per run (repeated backup() calls are no-ops)."""
    if p in _done:
        return None
    _done.add(p)
    rel = re.sub(r'[^A-Za-z0-9_.-]', '__', str(p.relative_to(p.anchor)))
    dst = backup_dir / ("%s.%s.bak" % (rel, ts))
    shutil.copy2(p, dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="path to nlc_platform_clean")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.repo).resolve()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = root / "legal_audit" / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 78)
    log(" APPLY LEGAL FIXES - 2026-10-30 batch (AUD-001 / REG-002 / UNKNOWN policy)")
    log(" Repo: %s%s" % (root, "   [DRY RUN]" if args.dry_run else ""))
    log("=" * 78)

    files = find_files(root)
    engine = find_engine_file(files)
    if not engine:
        log("FATAL: engine file not found (looked for ComplianceFlag + _calculate_score)")
        return 2
    log("Engine file : %s" % engine.relative_to(root))
    test_files = [p for p in files if any(part == "tests" for part in p.parts)]

    statuses = {}

    # ---------- string fixes on engine + tests ----------
    string_targets = [engine] + test_files
    for fixname, fn in (("F1 AUD-001 template", fix_aud001),
                        ("F2a REG-002 citation block", fix_reg002_block)):
        for p in string_targets:
            t = read_text(p)
            new, st, detail = fn(t)
            key = "%s @ %s" % (fixname, p.relative_to(root))
            if st == "APPLIED" and not args.dry_run:
                backup(p, backup_dir, ts)
                write_text(p, new)
            log("%-9s %-38s %s  (%s)" % ("[" + st + "]", fixname, p.relative_to(root), detail))
            statuses[key] = st

    for p in string_targets:
        t = read_text(p)
        new, st, detail = fix_reg002_severity_impact(t, str(p.relative_to(root)))
        key = "F2b/c REG-002 severity+impact @ %s" % p.relative_to(root)
        if st == "APPLIED" and not args.dry_run:
            backup(p, backup_dir, ts)
            write_text(p, new)
        log("%-9s %-38s %s  (%s)" % ("[" + st + "]", "F2b/c REG-002 sev+impact", p.relative_to(root), detail))
        statuses[key] = st

    # ---------- structural fixes on engine only ----------
    et = read_text(engine)
    rel = str(engine.relative_to(root))
    structural = [
        ("F2d REG-002 out of black-override", lambda t: fix_black_override(t, "REG-002")),
        ("F3a/b eval_state field + __post_init__", fix_eval_state_field),
        ("F3c UNKNOWN constants + coverage penalty", fix_unknown_constants_and_penalty),
        ("F3d rescue excludes UNKNOWN", fix_rescue_exclusion),
    ]
    for fixname, fn in structural:
        new, st, detail = fn(et)
        # log now; the engine file is written once after all structural fixes
        log("%-9s %-38s %s  (%s)" % ("[" + st + "]", fixname, rel, detail))
        statuses["%s @ %s" % (fixname, rel)] = st
        et = new  # APPLIED -> patched text; ALREADY/SKIP/PARTIAL -> unchanged/partial

    # F3e depends on F3a success
    f3a_ok = statuses.get("F3a/b eval_state field + __post_init__ @ %s" % rel) in ("APPLIED", "ALREADY")
    if f3a_ok:
        for rid in ("INC-001", "AGM-001"):
            new, st, detail = mark_rule_unknown(et, rid)
            log("%-9s %-38s %s  (%s)" % ("[" + st + "]", "F3e %s -> UNKNOWN" % rid, rel, detail))
            statuses["F3e %s" % rid] = st
            et = new
    else:
        log("[SKIP  ] F3e INC-001/AGM-001 -> UNKNOWN        (requires F3a eval_state field)")

    # write engine once
    if not args.dry_run:
        cur = read_text(engine)
        if cur != et:
            backup(engine, backup_dir, ts)
            write_text(engine, et)

    # ---------- verification ----------
    log("-" * 78)
    log("VERIFY (post-patch)")
    vt = read_text(engine)
    checks = [
        ("F1 new AUD-001 text present", "1 month (30 days) of registration" in vt),
        ("F2a new REG-002 block present", "RJSC register Sec 163" in vt),
        ("F3a eval_state field present", "eval_state" in vt),
        ("F3c UNKNOWN_COVERAGE_CAP present", "UNKNOWN_COVERAGE_CAP" in vt),
    ]
    verify_ok = True
    for label, ok in checks:
        log("  %-42s %s" % (label, "OK" if ok else "MISSING"))
        verify_ok = verify_ok and ok

    # ---------- verdict ----------
    needs_manual = [k for k, v in statuses.items() if v in ("SKIP", "PARTIAL")]
    log("-" * 78)
    if needs_manual:
        log("RESULT: %d fix(es) need manual attention:" % len(needs_manual))
        for k in needs_manual:
            log("  - %s" % k)
        log("See README section 6 for before/after snippets; re-run afterwards (idempotent).")
        rc = 1
    else:
        log("RESULT: all fixes applied or already present.")
        rc = 0
    if not verify_ok:
        log("WARNING: post-patch verification incomplete - inspect the report.")
        rc = 1
    log("Backup dir: %s" % backup_dir)

    out_file = root / "legal_audit" / ("patch_report_%s.txt" % ts)
    out_file.parent.mkdir(exist_ok=True)
    out_file.write_text("\n".join(REPORT) + "\n", encoding="utf-8")
    log("Report written: %s" % out_file)
    return rc


if __name__ == "__main__":
    sys.exit(main())
