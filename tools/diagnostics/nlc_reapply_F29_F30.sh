# nlc_reapply_F29_F30.sh — restore F-29/F-30 guards regressed in working tree,
# clean D16 comment artifact, and re-print the windows cut from the last sweep.
# Run from Git Bash:  bash nlc_reapply_F29_F30.sh
# Idempotent: safe to re-run. Does NOT commit — review the diff, then commit.

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
REGISTER="docs/legal/current_law_register.md"
[ -f "$ENGINE" ] || { echo "X: engine.py missing - abort"; exit 1; }
cp "$ENGINE" /tmp/engine_backup_before_reapply.py && echo "backup: /tmp/engine_backup_before_reapply.py"

echo "===== R0 DIAGNOSIS ====="
git --no-pager log --oneline -6
echo "branch: $(git branch --show-current)"
git status --short | head -n 8
if git merge-base --is-ancestor c4d97c1 HEAD 2>/dev/null; then
  echo "OK: c4d97c1 IS an ancestor of HEAD (fix was committed, then lost)"
else
  echo "X: c4d97c1 NOT in HEAD history (fix never merged into current branch)"
  ISSUES=$((ISSUES+1))
fi
git --no-pager diff c4d97c1 -- "$ENGINE" > /tmp/nlc_delta_vs_c4d97c1.diff 2>/dev/null
echo "--- guard lines LOST since c4d97c1 (should be EMPTY) ---"
grep -E "^-" /tmp/nlc_delta_vs_c4d97c1.diff | grep -E "eval_state|is_black_override|black_count" | head -n 15
echo "--- (full delta saved: /tmp/nlc_delta_vs_c4d97c1.diff) ---"

echo "===== R1 IDEMPOTENT PATCH (F-29 + F-30 + D16 comment) ====="
python - "$ENGINE" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8", newline="").read()  # newline="" preserves CRLF
crlf = "\r\n" in text
def prep(s):
    return s.replace("\n", "\r\n") if crlf else s

SITES = [
    ("F-29 has_black_override guard",
     '''            f.is_black_override and f.state == RuleState.NON_COMPLIANT
            for f in self._flags if not f.resolved and f.conditional_applies
''',
     '''            f.is_black_override and f.state == RuleState.NON_COMPLIANT and f.eval_state != "UNKNOWN"
            for f in self._flags if not f.resolved and f.conditional_applies
'''),
    ("F-30 black_count active filter",
     '''            black_count = len([f for f in self._flags if f.severity == Severity.BLACK and f.rule_id not in self._ESC_RULE_IDS])
''',
     '''            black_count = len([f for f in self._flags if f.severity == Severity.BLACK and f.state == RuleState.NON_COMPLIANT and f.eval_state != "UNKNOWN" and not f.resolved and f.conditional_applies and f.rule_id not in self._ESC_RULE_IDS])
'''),
    ("D16 comment artifact cleanup",
     ''' != "UNKNOWN"]  # F3: exclude UNKNOWN from rescue, 'VIOLATION') != 'UNKNOWN']  # F3: exclude UNKNOWN from rescue''',
     ''' != "UNKNOWN"]  # F3: exclude UNKNOWN from rescue'''),
]

aborted = False
for name, old, new in SITES:
    old, new = prep(old), prep(new)
    n_old, n_new = text.count(old), text.count(new)
    if n_old == 1:
        text = text.replace(old, new)
        print(f"PATCHED: {name}")
    elif n_old == 0 and n_new >= 1:
        print(f"SKIP:    {name} (already applied)")
    else:
        print(f"ABORT:   {name} (old_matches={n_old}, new_matches={n_new}) - manual review needed")
        aborted = True

if aborted:
    print("X: one or more sites ambiguous - NO changes written")
    sys.exit(3)
open(path, "w", encoding="utf-8", newline="").write(text)
print(f"wrote {path} (crlf={crlf})")
PY
if [ $? -ne 0 ]; then ISSUES=$((ISSUES+1)); fi

echo "===== R2 POST-PATCH VERIFY ====="
if python -m py_compile "$ENGINE" 2>/dev/null; then echo "OK: engine compiles"; else echo "X: engine.py FAILED to compile"; ISSUES=$((ISSUES+1)); python -m py_compile "$ENGINE" 2>&1 | head -n 5; fi
echo "--- eval_state guard sites (expect 4 after full restore; 2 = critical-gate sites from c95b0c7 hunk2 still missing) ---"
grep -n 'f.eval_state != "UNKNOWN"' "$ENGINE"
echo "--- black_count computations ---"
grep -n "black_count = len" "$ENGINE" | head -n 6
echo "--- regression check: line 1996 area ---"
grep -n "is_black_override and f.state" "$ENGINE"

echo "===== R3 c95b0c7 HUNK 2+ (critical primary/fallback gates) ====="
echo "--- if R2 shows only 2 eval_state sites, these gates are ALSO regressed; paste this output back ---"
git --no-pager show c95b0c7 -- "$ENGINE" | sed -n '25,75p'

echo "===== R4 WINDOWS CUT FROM LAST SWEEP ====="
echo "--- DEF-001 confirmed-missing branch (engine 1949-1993) ---"
sed -n '1949,1993p' "$ENGINE"
echo "--- AUD-001 elif False branch (engine 763-790) ---"
sed -n '763,790p' "$ENGINE"
echo "--- D1 re-check: EA rows + F-queue in register ---"
if [ -f "$REGISTER" ]; then
  grep -n "### EA-" "$REGISTER" | head -n 14
  grep -nE "F-(2[2-9]|3[0-3])" "$REGISTER" | head -n 24
else
  echo "X: $REGISTER missing"; ISSUES=$((ISSUES+1))
fi

echo "===== NEXT STEP (review first, then run) ====="
git --no-pager diff --stat -- "$ENGINE"
echo "git add $ENGINE && git commit -m 'fix(engine): reapply F-29/F-30 guards regressed from c95b0c7/c4d97c1; clean F3 comment artifact (D16)'"
echo "REAPPLY-DONE issues=$ISSUES repo=$REPO"
