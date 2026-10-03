#!/usr/bin/env bash
# NLC Enterprise Forensic Agent v3.0.0
set -uo pipefail

AGENT='MYAGENTBINOD'; VERSION='3.0.0'
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

start_gate(){
  CURRENT_GATE="$1"
  GATE_PASS_COUNT=0; GATE_FAIL_COUNT=0; GATE_NOT_PROVEN_COUNT=0; GATE_REVIEW_REQUIRED_COUNT=0
  sec "$1"
}

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

run_python_gate() {
  local gate_name="$1"
  local script_path="$2"
  if [ -f "$REPO/$script_path" ]; then
    if python "$REPO/$script_path" > "$RUN/${gate_name}_audit.txt" 2>&1; then
      cat "$RUN/${gate_name}_audit.txt" | tee -a "$REPORT"
      GATE_PASS_COUNT=$((GATE_PASS_COUNT+1))
    else
      cat "$RUN/${gate_name}_audit.txt" | tee -a "$REPORT"
      GATE_FAIL_COUNT=$((GATE_FAIL_COUNT+1))
    fi
  else
    log "${gate_name}_TOOL_MISSING=NOT_PROVEN"
    GATE_NOT_PROVEN_COUNT=$((GATE_NOT_PROVEN_COUNT+1))
  fi
}

g00(){ needgit; start_gate "G00"; log "REPO=$REPO"; log "HEAD=$(git -C "$REPO" rev-parse HEAD)"; GATE_PASS_COUNT=$((GATE_PASS_COUNT+1)); finish_gate; }
g01(){ needgit; start_gate "G01"; run_python_gate "g01" "tools/canonical_reconciliation.py"; finish_gate; }
g02(){ needgit; start_gate "G02"; run_python_gate "g02" "tools/g02_rls_audit.py"; finish_gate; }
g03(){ needgit; start_gate "G03"; run_python_gate "g03" "tools/g03_membership_audit.py"; finish_gate; }
g04(){ needgit; start_gate "G04"; run_python_gate "g04" "tools/g04_idor_audit.py"; finish_gate; }
g05(){ needgit; start_gate "G05"; run_python_gate "g05" "tools/canonical_reconciliation.py"; finish_gate; }
g06(){ needgit; start_gate "G06"; run_python_gate "g06" "tools/g06_historical_audit.py"; finish_gate; }
g07(){ needgit; start_gate "G07"; run_python_gate "g07" "tools/g07_provenance_audit.py"; finish_gate; }
g08(){ needgit; start_gate "G08"; run_python_gate "g08" "tools/g08_rescue_audit.py"; finish_gate; }
g09(){ needgit; start_gate "G09"; run_python_gate "g09" "tools/g09_determinism_audit.py"; finish_gate; }
g10(){ needgit; start_gate "G10"; run_python_gate "g10" "tools/g10_hash_audit.py"; finish_gate; }
g11(){ needgit; start_gate "G11"; run_python_gate "g11" "tools/g11_security_audit.py"; finish_gate; }
g12(){ needgit; start_gate "G12"; run_python_gate "g12" "tools/g12_api_governance_audit.py"; finish_gate; }
g13(){ needgit; start_gate "G13"; run_python_gate "g13" "tools/g13_worker_audit.py"; finish_gate; }
g14(){ needgit; start_gate "G14"; run_python_gate "g14" "tools/g14_document_audit.py"; finish_gate; }
g15(){ needgit; start_gate "G15"; run_python_gate "g15" "tools/g15_production_audit.py"; finish_gate; }
g16(){ needgit; start_gate "G16"; run_python_gate "g16" "tools/g16_final_freeze.py"; finish_gate; }

gate(){
  case "$GATE" in
    G00) g00;; G01) g01;; G02) g02;; G03) g03;; G04) g04;; G05) g05;;
    G06) g06;; G07) g07;; G08) g08;; G09) g09;; G10) g10;; G11) g11;;
    G12) g12;; G13) g13;; G14) g14;; G15) g15;; G16) g16;;
    *) echo "Supported: G00-G16"; exit 2;;
  esac
}

case "$CMD" in
  gate) gate;;
  *) echo "usage: $0 {gate G00..G16 | all} [repo]"; exit 2;;
esac

log "DATABASE_MUTATION=NO"
log "LEGAL_SOURCE_MUTATION=NO"
log "APPLICATION_MUTATION=NO"
log "GIT_MUTATION=NO"
log "DEPLOYMENT=NO"
log "AUDIT_ARTIFACT_MUTATION=YES"
