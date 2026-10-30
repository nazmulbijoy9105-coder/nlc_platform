# NLC platform — post-fix verification sweep (D0, D1, D11, D18, D13, D14, D15, D16)
# Hardened: no pager hangs, explicit X: markers on every silent-failure path.
# Run from Git Bash:  bash nlc_verify_D0-D16.sh
# NOTE: save/edit this file with LF line endings (not CRLF) or Git Bash will choke.

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

echo "===== D0 REPO STATE ====="
git --no-pager log --oneline -3
git status --short | head -n 5
if [ ! -f "$ENGINE" ]; then echo "X: engine.py missing - abort"; exit 1; fi
if python -m py_compile "$ENGINE" 2>/dev/null; then
  echo "OK: engine compiles"
else
  echo "X: engine.py FAILED to compile"
  ISSUES=$((ISSUES+1))
  python -m py_compile "$ENGINE" 2>&1 | head -n 5
fi
ELINES=$(wc -l < "$ENGINE")
echo "engine lines: $ELINES"

echo "===== D1 EA ROWS + F-QUEUE IN REGISTER ====="
if [ -f "$REGISTER" ]; then
  grep -n "### EA-" "$REGISTER" | head -n 14
  grep -nE "F-(2[2-9]|3[0-3])" "$REGISTER" | head -n 24
else
  echo "X: $REGISTER missing"
  ISSUES=$((ISSUES+1))
fi

echo "===== D11 DEF-001 EMIT BLOCK (engine 1880-1948) ====="
sed -n '1880,1948p' "$ENGINE"

echo "===== D18 INC-001 REGION (engine 555-595) ====="
sed -n '555,595p' "$ENGINE"

echo "===== D13 AUD-001 + CALENDAR HELPER (engine 720-762) ====="
sed -n '720,762p' "$ENGINE"

echo "===== D14 ESCALATION BLOCK + F-29/F-30 DIFFS ====="
sed -n '1994,2014p' "$ENGINE"
grep -n "conditional_applies" "$ENGINE" | head -n 6
for SHA in c95b0c7 c4d97c1; do
  if git cat-file -e "$SHA^{commit}" 2>/dev/null; then
    git --no-pager show "$SHA" -- "$ENGINE" | head -n 22
  else
    echo "X: commit $SHA not found in this repo"
    ISSUES=$((ISSUES+1))
  fi
done

echo "===== D15 VERIFIED_RULE_IDS BODY (engine 430-472) ====="
sed -n '430,472p' "$ENGINE"

echo "===== D16 LINE 2203 EXACT ====="
if [ "$ELINES" -ge 2203 ]; then
  sed -n '2203p' "$ENGINE"
else
  echo "X: engine has only $ELINES lines; no line 2203"
  ISSUES=$((ISSUES+1))
fi

echo "STEP-DONE"
echo "VERIFY-SWEEP-FINISHED issues=$ISSUES repo=$REPO"
