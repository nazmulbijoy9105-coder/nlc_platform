# NLC platform — FINAL acceptance sweep (post-commit 26ea991).
# Pins: restored eval_state guards (F-29 x3, F-30 black_count, 39b4b9d severity floor),
#       cleaned F3 comment artifact (D16), VERIFIED_RULE_IDS = 41 pin (D15).
# Run from Git Bash (any location):  bash nlc_verify_final.sh
# Optional repo override (testing):  NLC_REPO=/path/to/repo bash nlc_verify_final.sh
# NOTE: save/edit this file with LF line endings (not CRLF) or Git Bash will choke.

set -u
ISSUES=0

REPO="${NLC_REPO:-}"
if [ -z "$REPO" ]; then
  for d in /f/NLC_RECOVERY_CLONES/nlc_platform_clean /F/NLC_RECOVERY_CLONES/nlc_platform_clean /f/NLC*/* /F/NLC*/* /f/NLC* /F/NLC*; do
    if [ -d "$d/.git" ]; then REPO="$d"; break; fi
  done
fi
if [ -z "$REPO" ] || [ ! -d "$REPO/.git" ]; then echo "X: no git repo found"; exit 1; fi
cd "$REPO" || { echo "X: cannot cd"; exit 1; }
echo "REPO=$REPO"
ENGINE="app/rule_engine/engine.py"
REGISTER="docs/legal/current_law_register.md"

[ -f "$ENGINE" ] || { echo "X: engine.py missing - abort"; exit 1; }
ELINES=$(wc -l < "$ENGINE")

echo "===== D0 REPO STATE ====="
git --no-pager log --oneline -3
git status --short | head -n 5
if python -m py_compile "$ENGINE" 2>/dev/null; then
  echo "OK: engine compiles"
else
  echo "X: engine.py FAILED to compile"
  ISSUES=$((ISSUES+1))
  python -m py_compile "$ENGINE" 2>&1 | head -n 5
fi
echo "engine lines: $ELINES"

win() {
  local a=$1 b=$2 label=$3
  echo "--- $label (engine $a-$b) ---"
  if [ "$ELINES" -ge "$b" ]; then sed -n "${a},${b}p" "$ENGINE"; else echo "INFO: engine shorter than $b lines, window skipped"; fi
}

echo "===== G1 eval_state GUARD SITES (expect 5: F-29 x3 + F-30 + severity floor) ====="
GUARDOUT=$(grep -n 'f.eval_state != "UNKNOWN"' "$ENGINE" || true)
echo "$GUARDOUT"
GCOUNT=$(printf '%s\n' "$GUARDOUT" | grep -c . || true)
if [ "$GCOUNT" -eq 5 ]; then
  echo "OK: 5 guard sites"
else
  echo "X: expected 5 guard sites, found $GCOUNT"
  ISSUES=$((ISSUES+1))
fi

echo "===== G2 F-30 black_count FULL FILTER ====="
S4COUNT=$(grep -cF 'not f.resolved and f.conditional_applies and f.rule_id not in self._ESC_RULE_IDS])' "$ENGINE" || true)
if [ "$S4COUNT" -eq 1 ]; then
  echo "OK: F-30 black_count filter present x1"
else
  echo "X: F-30 black_count filter count=$S4COUNT (expect 1)"
  ISSUES=$((ISSUES+1))
fi
OLDRES=$(grep -cF 'Severity.BLACK and f.rule_id not in' "$ENGINE" || true)
if [ "$OLDRES" -eq 0 ]; then
  echo "OK: no unguarded black_count residue"
else
  echo "X: unguarded black_count residue x$OLDRES:"
  grep -nF 'Severity.BLACK and f.rule_id not in' "$ENGINE"
  ISSUES=$((ISSUES+1))
fi

echo "===== G3 D16 F3 COMMENT (cleaned form, no residue) ====="
F3RES=$(grep -cF ") != 'UNKNOWN'] # F3" "$ENGINE" || true)
if [ "$F3RES" -eq 0 ]; then
  echo "OK: no F3 comment residue"
else
  echo "X: F3 residue x$F3RES:"
  grep -nF ") != 'UNKNOWN'] # F3" "$ENGINE"
  ISSUES=$((ISSUES+1))
fi
F3OK=$(grep -cF '# F3: exclude UNKNOWN from rescue' "$ENGINE" || true)
if [ "$F3OK" -eq 1 ]; then
  echo "OK: cleaned F3 comment present x1"
else
  echo "X: '# F3: exclude UNKNOWN from rescue' count=$F3OK (expect 1)"
  grep -nF '# F3: exclude UNKNOWN from rescue' "$ENGINE"
  ISSUES=$((ISSUES+1))
fi

echo "===== G4 UNGUARDED OVERRIDE SITES (expect 0 or 1: lifecycle site allowed) ====="
UNGUARDOUT=$(grep "is_black_override and f.state == RuleState.NON_COMPLIANT" "$ENGINE" | grep -v "eval_state" || true)
echo "$UNGUARDOUT"
UCOUNT=$(printf '%s\n' "$UNGUARDOUT" | grep -c . || true)
if [ "$UCOUNT" -le 1 ]; then
  echo "OK: unguarded override sites = $UCOUNT (lifecycle site allowed)"
else
  echo "X: $UCOUNT unguarded override sites (expect <=1)"
  ISSUES=$((ISSUES+1))
fi

echo "===== G5 VERIFIED_RULE_IDS PIN (expect 41; AR-001/SH-002/ESC-003 excluded) ====="
python - "$ENGINE" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8", newline="").read()
m = re.search(r"\bVERIFIED_RULE_IDS\b[^\n]*=", text)
if not m:
    print("X: VERIFIED_RULE_IDS definition not found in source")
    sys.exit(1)
hint = text[m.start():m.start() + 120]
rest = text[m.end():]
rest = re.sub(r"^\s*(?:frozenset|set)\s*\(", "(", rest, count=1)
ob = re.search(r"[\{\[\(]", rest)
if not ob:
    print(f"X: no literal after VERIFIED_RULE_IDS assignment near: {hint!r}")
    sys.exit(1)
open_ch = rest[ob.start()]
close_ch = {"{": "}", "[": "]", "(": ")"}[open_ch]
depth, i = 1, ob.start() + 1
while i < len(rest) and depth:
    ch = rest[i]
    if ch == open_ch:
        depth += 1
    elif ch == close_ch:
        depth -= 1
    i += 1
if depth != 0:
    print(f"X: unbalanced brackets in VERIFIED_RULE_IDS literal near: {hint!r}")
    sys.exit(1)
body = rest[ob.start() + 1:i - 1]
ids = re.findall(r'["\']([A-Z][A-Z0-9]*-[0-9A-Z]+)["\']', body)
uniq = set(ids)
dupes = len(ids) - len(uniq)
forbidden = [r for r in ("AR-001", "SH-002", "ESC-003") if r in uniq]
print(f"VERIFIED_RULE_IDS: {len(uniq)} unique ids (raw {len(ids)}), sample: {sorted(uniq)[:6]} ... {sorted(uniq)[-3:]}")
if dupes:
    print(f"X: {dupes} duplicate entr(ies) in VERIFIED_RULE_IDS near: {hint!r}")
    sys.exit(1)
if len(uniq) != 41:
    print(f"X: expected 41 verified rules, found {len(uniq)} — definition form near: {hint!r}")
    sys.exit(1)
if forbidden:
    print(f"X: forbidden members present: {forbidden}")
    sys.exit(1)
print("OK: 41 rules; AR-001 / SH-002 / ESC-003 excluded")
sys.exit(0)
PY
if [ $? -ne 0 ]; then ISSUES=$((ISSUES+1)); fi

echo "===== D1 EA ROWS + F-QUEUE IN REGISTER ====="
if [ -f "$REGISTER" ]; then
  grep -n "### EA-" "$REGISTER" | head -n 14
  grep -nE "F-(2[2-9]|3[0-3])" "$REGISTER" | head -n 24
else
  echo "X: $REGISTER missing"
  ISSUES=$((ISSUES+1))
fi

echo "===== WINDOWS (report-only; line numbers unchanged by 26ea991: six in-place replacements) ====="
win 1880 1948 "D11 DEF-001 emit block"
win 555 595  "D18 INC-001 region"
win 720 762  "D13 AUD-001 + calendar helper"
win 1994 2014 "D14 escalation block (guarded)"
win 430 472  "D15 VERIFIED_RULE_IDS body"

echo "===== D16 F3 COMMENT LINE (report) ====="
grep -n 'F3: exclude UNKNOWN from rescue' "$ENGINE" || echo "INFO: none (counted in G3)"

echo "===== FORENSIC RECORD (report-only) ====="
for SHA in c95b0c7 c4d97c1 64d9259; do
  if git cat-file -e "$SHA^{commit}" 2>/dev/null; then
    echo "--- $SHA exists in history ---"
  else
    echo "INFO: commit $SHA not found (history may have been rewritten) - report only"
  fi
done
git --no-pager show 64d9259 --stat --oneline 2>/dev/null | head -n 8
HEADSUB=$(git --no-pager log -1 --format=%s)
echo "HEAD: $HEADSUB"
case "$HEADSUB" in
  *"restore eval_state UNKNOWN guards"*) echo "OK: guard-restore commit is HEAD" ;;
  *) echo "INFO: HEAD is not the guard-restore commit (commit first if needed)" ;;
esac

echo "STEP-DONE"
echo "VERIFY-FINAL-FINISHED issues=$ISSUES repo=$REPO"
exit $ISSUES
