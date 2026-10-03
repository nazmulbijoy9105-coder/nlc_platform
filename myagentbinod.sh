#!/usr/bin/env bash
set -uo pipefail
AGENT='MYAGENTBINOD'; VERSION='1.1.0'
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
baseline(){ needgit; sec 'G00 BASELINE'
  log "REPO=$REPO"
  log "BRANCH=$(git -C "$REPO" branch --show-current)"
  log "HEAD=$(git -C "$REPO" rev-parse HEAD)"
  log "WORKTREE=$(worktree)"
  git -C "$REPO" status --short | tee -a "$REPORT"
  git -C "$REPO" log -10 --oneline --decorate | tee -a "$REPORT"; }
rules(){ needgit; sec 'G01 CANONICAL 75-RULE RECONCILIATION'
  git -C "$REPO" grep -hoE "\b($PREFIXES)-[0-9]{3}\b" -- app canonical_architecture scripts | sort -u > "$RUN/rule_ids.txt" || true
  log "TEXTUAL_UNIQUE_RULE_COUNT=$(wc -l < "$RUN/rule_ids.txt" | tr -d ' ')"
  log "TEXTUAL_INVENTORY=$RUN/rule_ids.txt"

  (
    cd "$REPO" || exit 2
    python - <<'PY'
import inspect
import re
import sys

from app.rule_engine.engine import NLCRuleEngine
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY
from canonical_architecture.legal_reconciliation import LEGAL_RECONCILIATION
from scripts.seed_rules import ILRMF_RULES

EXPECTED = 75

engine = set(
    re.findall(
        r'rule_id="([A-Z]+-\d{3})"',
        inspect.getsource(NLCRuleEngine),
    )
)
registry = set(STATUTORY_RULE_REGISTRY)
rescue = set(STATUTORY_RESCUE_REGISTRY)
reconciliation = set(LEGAL_RECONCILIATION)
seed = {r["rule_id"] for r in ILRMF_RULES}

bad_registry = sorted(
    k for k, v in STATUTORY_RULE_REGISTRY.items()
    if v.get("rule_id") != k
)
bad_rescue = sorted(
    k for k, v in STATUTORY_RESCUE_REGISTRY.items()
    if v.get("triggered_by") != k
)

print(f"ENGINE_COUNT={len(engine)}")
print(f"REGISTRY_COUNT={len(registry)}")
print(f"RESCUE_COUNT={len(rescue)}")
print(f"RECONCILIATION_COUNT={len(reconciliation)}")
print(f"SEED_COUNT={len(seed)}")

print(f"ENGINE_EQ_REGISTRY={engine == registry}")
print(f"ENGINE_EQ_RESCUE={engine == rescue}")
print(f"ENGINE_EQ_RECONCILIATION={engine == reconciliation}")
print(f"ENGINE_EQ_SEED={engine == seed}")

print(f"ENGINE_MINUS_REGISTRY={sorted(engine - registry)}")
print(f"REGISTRY_MINUS_ENGINE={sorted(registry - engine)}")
print(f"ENGINE_MINUS_RESCUE={sorted(engine - rescue)}")
print(f"RESCUE_MINUS_ENGINE={sorted(rescue - engine)}")
print(f"ENGINE_MINUS_RECONCILIATION={sorted(engine - reconciliation)}")
print(f"RECONCILIATION_MINUS_ENGINE={sorted(reconciliation - engine)}")
print(f"ENGINE_MINUS_SEED={sorted(engine - seed)}")
print(f"SEED_MINUS_ENGINE={sorted(seed - engine)}")

print(f"BAD_REGISTRY_INTERNAL_IDS={bad_registry}")
print(f"BAD_RESCUE_INTERNAL_IDS={bad_rescue}")

ok = (
    len(engine) == EXPECTED
    and len(registry) == EXPECTED
    and len(rescue) == EXPECTED
    and len(reconciliation) == EXPECTED
    and len(seed) == EXPECTED
    and engine == registry == rescue == reconciliation == seed
    and not bad_registry
    and not bad_rescue
)

print(f"CANONICAL_75_PARITY={'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PY
  ) 2>&1 | tee "$RUN/canonical_parity.txt" | tee -a "$REPORT"

  parity_status=${PIPESTATUS[0]}

  if [[ "$parity_status" -eq 0 ]]; then
    log "G01_RESULT=PASS"
  else
    log "G01_RESULT=FAIL"
  fi

  return "$parity_status"
}
core(){ needgit; sec 'CORE-IP CANDIDATES (review required)'
  git -C "$REPO" ls-files | grep -Ei 'ilrmf|rule|matrix|corpus|legal|statut|applicab|evaluat' | tee "$RUN/core_ip_candidates.txt" | tee -a "$REPORT"; }
security(){ needgit; sec 'SECRET-LIKE TRACKED PATHS'
  git -C "$REPO" ls-files | grep -Ei '(^|/)(\.env|[^/]*\.pem|[^/]*\.key|[^/]*secret[^/]*|[^/]*credential[^/]*)$' | tee -a "$REPORT" || true; }
gate(){ case "$GATE" in
  G00) baseline;;
  G01)
    baseline
    rules || return $?
    core
    ;;
  *) echo 'Supported: G00 G01'; exit 2;; esac
  log "GATE=$GATE  REPORT=$REPORT  (inventory only; legal correctness not checked)"; }
case "$CMD" in
  baseline) baseline;; rules) rules;; core) core;; security) security;;
  status) baseline;; gate) gate;;
  *) echo "usage: $0 {baseline|rules|core|security|status|gate G00|G01} [repo]"; exit 2;;
esac
