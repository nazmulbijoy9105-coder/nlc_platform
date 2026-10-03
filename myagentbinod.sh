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
rules(){ needgit; sec 'G01 RULE ID INVENTORY (app, canonical_architecture, scripts)'
  git -C "$REPO" grep -hoE "\b($PREFIXES)-[0-9]{3}\b" -- app canonical_architecture scripts | sort -u > "$RUN/rule_ids.txt" || true
  log "UNIQUE_RULE_COUNT=$(wc -l < "$RUN/rule_ids.txt" | tr -d ' ')"
  cat "$RUN/rule_ids.txt" | tee -a "$REPORT"; }
core(){ needgit; sec 'CORE-IP CANDIDATES (review required)'
  git -C "$REPO" ls-files | grep -Ei 'ilrmf|rule|matrix|corpus|legal|statut|applicab|evaluat' | tee "$RUN/core_ip_candidates.txt" | tee -a "$REPORT"; }
security(){ needgit; sec 'SECRET-LIKE TRACKED PATHS'
  git -C "$REPO" ls-files | grep -Ei '(^|/)(\.env|[^/]*\.pem|[^/]*\.key|[^/]*secret[^/]*|[^/]*credential[^/]*)$' | tee -a "$REPORT" || true; }
gate(){ case "$GATE" in
  G00) baseline;; G01) baseline; rules; core;;
  *) echo 'Supported: G00 G01'; exit 2;; esac
  log "GATE=$GATE  REPORT=$REPORT  (inventory only; legal correctness not checked)"; }
case "$CMD" in
  baseline) baseline;; rules) rules;; core) core;; security) security;;
  status) baseline;; gate) gate;;
  *) echo "usage: $0 {baseline|rules|core|security|status|gate G00|G01} [repo]"; exit 2;;
esac
