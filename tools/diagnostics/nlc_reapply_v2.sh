# nlc_reapply_v2.sh — restore ALL eval_state guards lost in the 64d9259 engine.py rewrite.
# v1 lesson: the has_black_override line carries invisible-byte damage (documented in
# register R4-P5d, "cat -A diagnostics"), so v2 matches lines WHITESPACE-CANONICALLY,
# anchored by neighbor lines, preserving each line's own line-ending.
# All-or-nothing: if any REQUIRED site fails, NOTHING is written.
# Run from Git Bash (repo root or anywhere):  bash nlc_reapply_v2.sh

set -u
ISSUES=0

REPO=""
for d in /f/NLC_RECOVERY_CLONES/nlc_platform_clean /F/NLC_RECOVERY_CLONES/nlc_platform_clean /f/NLC*/* /F/NLC*/* /f/NLC* /F/NLC*; do
  if [ -d "$d/.git" ]; then REPO="$d"; break; fi
done
if [ -z "$REPO" ]; then echo "X: no git repo found"; exit 1; fi
cd "$REPO" || { echo "X: cannot cd"; exit 1; }
echo "REPO=$REPO"
ENGINE="app/rule_engine/engine.py"
[ -f "$ENGINE" ] || { echo "X: engine.py missing - abort"; exit 1; }
cp "$ENGINE" /tmp/engine_backup_before_reapply_v2.py && echo "backup: /tmp/engine_backup_before_reapply_v2.py"

echo "===== R0 SITE INVENTORY (before) ====="
grep -n 'f.eval_state != "UNKNOWN"' "$ENGINE" | head -n 8
echo "--- (0 lines above = all guards still missing) ---"
grep -n "is_black_override and f.state == RuleState.NON_COMPLIANT" "$ENGINE"
grep -n "black_count = len" "$ENGINE" | head -n 4
grep -n "severity_rank" "$ENGINE" | head -n 6

echo "===== R1 CANONICAL CONTEXT-ANCHORED PATCH ====="
python - "$ENGINE" <<'PY'
import sys, re

path = sys.argv[1]
text = open(path, encoding="utf-8", newline="").read()  # newline="" preserves CRLF

# Heal lone-CR damage (stray \r from mixed-endings edits): a lone \r NOT part of CRLF
# is treated as content whitespace, not a line break. Only if rare (< 10) - otherwise
# it might be an exotic line-ending scheme, leave it alone.
lone_cr = len(re.findall(r"(?<!\n)\r(?!\n)", text))
if 0 < lone_cr <= 10:
    text = re.sub(r"(?<!\n)\r(?!\n)", " ", text)
    print(f"healed {lone_cr} lone-CR byte(s) as whitespace")

lines = text.splitlines(keepends=True)
content = [l.rstrip("\r\n") for l in lines]
canon = lambda s: " ".join(s.split())
crlf_dominant = text.count("\r\n") * 2 > text.count("\n")

G = 'f.eval_state != "UNKNOWN"'
SITES = [
    # (id, required, unguarded_canon, guarded_content, prev_anchor_canon_or_None, next_anchor_canon_or_None)
    ("S1 escalation has_black_override", True,
     "f.is_black_override and f.state == RuleState.NON_COMPLIANT",
     "f.is_black_override and f.state == RuleState.NON_COMPLIANT and " + G,
     None, "for f in self._flags if not f.resolved and f.conditional_applies"),
    ("S2 critical primary (rescue)", True,
     "if f.is_black_override and f.state == RuleState.NON_COMPLIANT",
     "if f.is_black_override and f.state == RuleState.NON_COMPLIANT and " + G,
     "f for f in active", "]"),
    ("S3 critical fallback (rescue)", True,
     "if f.severity == Severity.BLACK and f.state == RuleState.NON_COMPLIANT",
     "if f.severity == Severity.BLACK and f.state == RuleState.NON_COMPLIANT and " + G,
     "f for f in active", "]"),
    ("S4 ESC-003 black_count filter", True,
     "black_count = len([f for f in self._flags if f.severity == Severity.BLACK and f.rule_id not in self._ESC_RULE_IDS])",
     'black_count = len([f for f in self._flags if f.severity == Severity.BLACK and f.state == RuleState.NON_COMPLIANT and f.eval_state != "UNKNOWN" and not f.resolved and f.conditional_applies and f.rule_id not in self._ESC_RULE_IDS])',
     None, None),
    ("S5 severity floor (39b4b9d)", False,
     "if f.severity in severity_rank and (f.severity in (Severity.RED, Severity.BLACK)) and f.state == RuleState.NON_COMPLIANT:",
     "if f.severity in severity_rank and (f.severity in (Severity.RED, Severity.BLACK)) and f.state == RuleState.NON_COMPLIANT and " + G + ":",
     None, None),
    ("S6 D16 comment artifact", False,
     "flags = [f for f in flags if getattr(f, \"eval_state\", \"VIOLATION\") != \"UNKNOWN\"] # F3: exclude UNKNOWN from rescue, 'VIOLATION') != 'UNKNOWN'] # F3: exclude UNKNOWN from rescue",
     "flags = [f for f in flags if getattr(f, \"eval_state\", \"VIOLATION\") != \"UNKNOWN\"]  # F3: exclude UNKNOWN from rescue",
     None, None),
]

def rebuild(orig_line, new_content):
    lead = re.match(r"^[ \t]*", orig_line).group(0)
    # write the DOMINANT line ending - heals double-\r / lone-\r rot on the replaced line
    end = "\r\n" if crlf_dominant else "\n"
    return lead + new_content + end

def find(c_text, prev_a, next_a):
    """Lines whose canon == c_text, whose nearest NON-EMPTY neighbors match anchors.
    Skipping empty neighbors tolerates phantom blank lines from stray-\r damage."""
    def nearest(idx, step):
        j = idx + step
        while 0 <= j < len(content):
            if canon(content[j]) != "":
                return j
            j += step
        return None
    hits = []
    for i, c in enumerate(content):
        if canon(c) != c_text:
            continue
        if prev_a is not None:
            p = nearest(i, -1)
            if p is None or canon(content[p]) != prev_a:
                continue
        if next_a is not None:
            q = nearest(i, +1)
            if q is None or canon(content[q]) != next_a:
                continue
        hits.append(i)
    return hits

required_failed = False
changed = False
for name, required, unguard, guard, prev_a, next_a in SITES:
    hits = find(unguard, prev_a, next_a)
    g_content = guard
    already = False
    for i, c in enumerate(content):
        if canon(c) != canon(g_content):
            continue
        if prev_a is not None:
            p = None
            j = i - 1
            while j >= 0:
                if canon(content[j]) != "":
                    p = j
                    break
                j -= 1
            if p is None or canon(content[p]) != prev_a:
                continue
        if next_a is not None:
            q = None
            j = i + 1
            while j < len(content):
                if canon(content[j]) != "":
                    q = j
                    break
                j += 1
            if q is None or canon(content[q]) != next_a:
                continue
        already = True
        break
    if already:
        print(f"SKIP:    {name} (already applied)")
    elif len(hits) == 1:
        i = hits[0]
        lines[i] = rebuild(lines[i], guard)
        content[i] = guard
        changed = True
        print(f"PATCHED: {name} (line {i+1})")
    elif len(hits) == 0:
        if required:
            print(f"FAIL:    {name} - unguarded form NOT FOUND (context anchors: prev={prev_a!r}, next={next_a!r})")
            required_failed = True
        else:
            print(f"WARN:    {name} - unguarded form not found; if intentional, ignore; else paste repr dump below")
    else:
        print(f"FAIL:    {name} - {len(hits)} candidate matches (ambiguous): lines {[h+1 for h in hits]}")
        required_failed = True

if required_failed:
    print("--- repr dump of every is_black_override / severity_rank / black_count line (paste back) ---")
    n = 0
    for i, l in enumerate(lines):
        if any(k in l for k in ("is_black_override", "severity_rank", "black_count")):
            print(f"{i+1}: {l!r}")
            n += 1
            if n >= 12:
                break
    print("X: REQUIRED site(s) failed - NO changes written (file untouched)")
    sys.exit(3)

if changed:
    open(path, "w", encoding="utf-8", newline="").write("".join(lines))
    print(f"wrote {path}")
else:
    print("no changes needed")
PY
if [ $? -ne 0 ]; then
  echo "X: patch aborted - see FAIL lines above"
  ISSUES=$((ISSUES+1))
fi

echo "===== R2 POST-PATCH VERIFY ====="
if python -m py_compile "$ENGINE" 2>/dev/null; then echo "OK: engine compiles"; else echo "X: engine.py FAILED to compile"; ISSUES=$((ISSUES+1)); python -m py_compile "$ENGINE" 2>&1 | head -n 5; fi
echo "--- eval_state guard sites (expect 5; 4 = severity floor S5 absent, see WARN) ---"
grep -n 'f.eval_state != "UNKNOWN"' "$ENGINE"
echo "--- restored escalation block (1994-2002) ---"
sed -n '1994,2002p' "$ENGINE"
echo "--- remaining unguarded is_black_override+NON_COMPLIANT (expect ONLY the lifecycle site, un-gated by design) ---"
grep -n "is_black_override and f.state == RuleState.NON_COMPLIANT" "$ENGINE" | grep -v "eval_state"

echo "===== R3 COLLATERAL PROBES (report-only, register decisions) ====="
echo "--- AR-001 / SH-002 dropped from VERIFIED_RULE_IDS in 64d9259 (43 -> 41): still emitting? ---"
grep -n '"AR-001"' "$ENGINE" | head -n 4
grep -n '"SH-002"' "$ENGINE" | head -n 4
echo "--- current _calculate_score deduction filter (F-26 context; old violations[] builder vanished) ---"
grep -n "rule_id in VERIFIED_RULE_IDS" "$ENGINE" | head -n 6
echo "--- ar_years assignment (old 'c.unfiled_returns_count' line vanished) ---"
grep -n "ar_years = " "$ENGINE" | head -n 3

echo "===== NEXT STEP (review, then run) ====="
git --no-pager diff --stat -- "$ENGINE"
echo "git add $ENGINE && git commit -m 'fix(engine): restore eval_state UNKNOWN guards regressed by 64d9259 (F-29 x3 sites, F-30, 39b4b9d severity floor); clean F3 comment artifact (D16)'"
echo "REAPPLY-V2-DONE issues=$ISSUES repo=$REPO"
exit $ISSUES
