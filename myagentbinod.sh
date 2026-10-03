#!/usr/bin/env bash
# NLC Enterprise Forensic Agent v2.1.0
set -uo pipefail

AGENT='MYAGENTBINOD'; VERSION='2.1.0'
CMD="${1:-help}"; GATE="${2:-}"
if [[ "$CMD" == gate ]]; then REPO_ARG="${3:-}"; else REPO_ARG="${2:-}"; fi
REPO="${REPO_ARG:-${NLC_REPO:-$(pwd)}}"
OUT="${NLC_AGENT_OUT:-$REPO/.nlc-agent}"
RUN="$OUT/$(date +%Y%m%d-%H%M%S)"; mkdir -p "$RUN"
REPORT="$RUN/report.txt"
PREFIXES='AGM|AR|AUD|BNK|BSEC|CAP|CHG|DEF|DIR|ESC|FX|INC|LBR|OFF|REG|SH|STR|TAX|TL|TR|VAT'

log(){ echo "$*" | tee -a "$REPORT"; }
sec(){ printf '\n== %s ==\n' "$1" | tee -a "$REPORT"; }
needgit(){ git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "NOT A GIT REPO: $REPO"; exit 2; }; }
worktree(){ if [[ -z "$(git -C "$REPO" status --porcelain)" ]]; then echo CLEAN; else echo DIRTY; fi; }

# A-02/A-03: Per-gate state
start_gate(){
  CURRENT_GATE="$1"
  GATE_PASS_COUNT=0
  GATE_FAIL_COUNT=0
  GATE_NOT_PROVEN_COUNT=0
  GATE_REVIEW_REQUIRED_COUNT=0
  sec "$1"
}

# A-04: Authoritative gate result
finish_gate(){
  local RESULT="FAIL"
  if [ "$GATE_FAIL_COUNT" -gt 0 ]; then RESULT="FAIL"
  elif [ "$GATE_NOT_PROVEN_COUNT" -gt 0 ]; then RESULT="NOT_PROVEN"
  elif [ "$GATE_REVIEW_REQUIRED_COUNT" -gt 0 ]; then RESULT="REVIEW_REQUIRED"
  else RESULT="PASS"; fi
  
  log "${CURRENT_GATE}_RESULT=$RESULT"
  log "${CURRENT_GATE}_PASS_COUNT=$GATE_PASS_COUNT"
  log "${CURRENT_GATE}_FAIL_COUNT=$GATE_FAIL_COUNT"
  log "${CURRENT_GATE}_NOT_PROVEN_COUNT=$GATE_NOT_PROVEN_COUNT"
  log "${CURRENT_GATE}_REVIEW_REQUIRED_COUNT=$GATE_REVIEW_REQUIRED_COUNT"
}

baseline(){
  needgit
  start_gate "G00"
  log "REPO=$REPO"
  log "BRANCH=$(git -C "$REPO" branch --show-current)"
  log "HEAD=$(git -C "$REPO" rev-parse HEAD)"
  log "WORKTREE=$(worktree)"
  git -C "$REPO" status --short | tee -a "$REPORT"
  git -C "$REPO" log -10 --oneline --decorate | tee -a "$REPORT"
  GATE_PASS_COUNT=$((GATE_PASS_COUNT+1))
  finish_gate
}

g01(){
  needgit
  start_gate "G01"
  git -C "$REPO" grep -hoE "\b($PREFIXES)-[0-9]{3}\b" -- app canonical_architecture scripts | sort -u > "$RUN/rule_ids.txt"
  log "TEXTUAL_UNIQUE_RULE_COUNT=$(wc -l < "$RUN/rule_ids.txt" | tr -d ' ')"
  
  (
    cd "$REPO" || exit 1
    python - <<'PY'
import inspect, re, sys
from app.rule_engine.engine import NLCRuleEngine
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY
from canonical_architecture.legal_reconciliation import LEGAL_RECONCILIATION
from scripts.seed_rules import ILRMF_RULES

EXPECTED = 75
engine = set(re.findall(r'rule_id="([A-Z]+-\d{3})"', inspect.getsource(NLCRuleEngine)))
registry = set(STATUTORY_RULE_REGISTRY)
rescue = set(STATUTORY_RESCUE_REGISTRY)
reconciliation = set(LEGAL_RECONCILIATION)
seed = {r["rule_id"] for r in ILRMF_RULES}

print(f"ENGINE_COUNT={len(engine)}")
print(f"REGISTRY_COUNT={len(registry)}")
print(f"RESCUE_COUNT={len(rescue)}")
print(f"RECONCILIATION_COUNT={len(reconciliation)}")
print(f"SEED_COUNT={len(seed)}")
print(f"CANONICAL_75_PARITY={'PASS' if len(engine)==EXPECTED and engine==registry==rescue==reconciliation==seed else 'FAIL'}")
sys.exit(0 if len(engine)==EXPECTED and engine==registry==rescue==reconciliation==seed else 1)
PY
  ) > "$RUN/canonical_parity.txt" 2>&1
  
  if [ $? -eq 0 ]; then
    log "G01_PARITY=PASS"
    GATE_PASS_COUNT=$((GATE_PASS_COUNT+1))
  else
    log "G01_PARITY=FAIL"
    GATE_FAIL_COUNT=$((GATE_FAIL_COUNT+1))
  fi
  cat "$RUN/canonical_parity.txt" | tee -a "$REPORT"
  finish_gate
}

g05(){
  needgit
  start_gate "G05"
  # A-09: Invoke real reconciliation tool
  if [ -f "tools/canonical_reconciliation.py" ]; then
    python tools/canonical_reconciliation.py > "$RUN/g05_reconciliation.txt" 2>&1
    if [ $? -eq 0 ]; then
      log "G05_RECONCILIATION=PASS"
      GATE_PASS_COUNT=$((GATE_PASS_COUNT+1))
    else
      log "G05_RECONCILIATION=FAIL"
      GATE_FAIL_COUNT=$((GATE_FAIL_COUNT+1))
    fi
  else
    log "G05_RECONCILIATION=NOT_PROVEN"
    GATE_NOT_PROVEN_COUNT=$((GATE_NOT_PROVEN_COUNT+1))
  fi
  finish_gate
}

gate(){
  case "$GATE" in
    G00) baseline;;
    G01) g01;;
    G05) g05;;
    *) echo "Supported: G00 G01 G05"; exit 2;;
  esac
}

case "$CMD" in
  baseline) baseline;;
  g01) g01;;
  g05) g05;;
  gate) gate;;
  *) echo "usage: $0 {baseline|g01|g05|gate G00|G01|G05} [repo]"; exit 2;;
esac

# A-06: Final Mutation Contract
log "DATABASE_MUTATION=NO"
log "LEGAL_SOURCE_MUTATION=NO"
log "APPLICATION_MUTATION=NO"
log "GIT_MUTATION=NO"
log "DEPLOYMENT=NO"
log "AUDIT_ARTIFACT_MUTATION=YES"
