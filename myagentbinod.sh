#!/usr/bin/env bash
# NLC Enterprise Forensic Agent v4.0.0
set -uo pipefail

AGENT='MYAGENTBINOD'; VERSION='4.0.0'
CMD="${1:-help}"; GATE="${2:-}"
if [[ "$CMD" == gate ]]; then REPO_ARG="${3:-}"; else REPO_ARG="${2:-}"; fi
REPO="${REPO_ARG:-${NLC_REPO:-$(pwd)}}"
OUT="${NLC_AGENT_OUT:-$REPO/.nlc-agent}"
RUN="$OUT/$(date +%Y%m%d-%H%M%S)"; mkdir -p "$RUN"
REPORT="$RUN/report.txt"

# Global state for sequential execution
FINAL_RESULT="PASS"
FAILED_GATE=""

log(){ echo "$*" | tee -a "$REPORT"; }
sec(){ printf '\n== %s ==\n' "$1" | tee -a "$REPORT"; }
needgit(){ git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "NOT A GIT REPO: $REPO"; exit 2; }; }

start_gate(){
  CURRENT_GATE="$1"
  sec "$1"
}

finish_gate(){
  local RESULT="$1" # PASS or FAIL
  log "${CURRENT_GATE}_RESULT=$RESULT"
  
  if [ "$RESULT" != "PASS" ]; then
    FINAL_RESULT="FAIL"
    FAILED_GATE="$CURRENT_GATE"
  fi
}

run_python_gate() {
  local gate_name="$1"
  local script_path="$2"
  if [ -f "$REPO/$script_path" ]; then
    python "$REPO/$script_path" > "$RUN/${gate_name}_audit.txt" 2>&1
    local EXIT_CODE=$?
    cat "$RUN/${gate_name}_audit.txt" | tee -a "$REPORT"
    if [ $EXIT_CODE -eq 0 ]; then
      finish_gate "PASS"
    else
      finish_gate "FAIL"
    fi
  else
    log "${gate_name}_TOOL_MISSING=FAIL"
    finish_gate "FAIL"
  fi
}

# G00: Must enforce clean worktree
g00(){
  needgit
  start_gate "G00"
  log "REPO=$REPO"
  log "HEAD=$(git -C "$REPO" rev-parse HEAD)"
  
  local WT_STATUS=$(git -C "$REPO" status --porcelain)
  if [ -z "$WT_STATUS" ]; then
    log "WORKTREE=CLEAN"
    finish_gate "PASS"
  else
    log "WORKTREE=DIRTY"
    echo "$WT_STATUS" | tee -a "$REPORT"
    finish_gate "FAIL"
  fi
}

g01(){ start_gate "G01"; run_python_gate "g01" "tools/canonical_reconciliation.py"; }
g05(){ start_gate "G05"; run_python_gate "g05" "tools/canonical_reconciliation.py"; }
g02(){ start_gate "G02"; run_python_gate "g02" "tools/g02_rls_audit.py"; }
g03(){ start_gate "G03"; run_python_gate "g03" "tools/g03_membership_audit.py"; }
g04(){ start_gate "G04"; run_python_gate "g04" "tools/g04_idor_audit.py"; }
g06(){ start_gate "G06"; run_python_gate "g06" "tools/g06_historical_audit.py"; }
g07(){ start_gate "G07"; run_python_gate "g07" "tools/g07_provenance_audit.py"; }
g08(){ start_gate "G08"; run_python_gate "g08" "tools/g08_rescue_audit.py"; }
g09(){ start_gate "G09"; run_python_gate "g09" "tools/g09_determinism_audit.py"; }
g10(){ start_gate "G10"; run_python_gate "g10" "tools/g10_hash_audit.py"; }
g11(){ start_gate "G11"; run_python_gate "g11" "tools/g11_security_audit.py"; }
g12(){ start_gate "G12"; run_python_gate "g12" "tools/g12_api_governance_audit.py"; }
g13(){ start_gate "G13"; run_python_gate "g13" "tools/g13_worker_audit.py"; }
g14(){ start_gate "G14"; run_python_gate "g14" "tools/g14_document_audit.py"; }
g15(){ start_gate "G15"; run_python_gate "g15" "tools/g15_production_audit.py"; }

# G16: Verify all previous gates passed
g16(){
  start_gate "G16"
  
  local ALL_PASS=true
  local REQUIRED_GATES="G00 G01 G05 G02 G03 G04 G06 G07 G08 G09 G10 G11 G12 G13 G14 G15"
  
  for g in $REQUIRED_GATES; do
    local RES=$(grep -E "^${g}_RESULT=PASS$" "$REPORT" | tail -1)
    if [ -z "$RES" ]; then
      log "G16_MISSING_PREREQ=$g"
      ALL_PASS=false
    fi
  done
  
  if [ "$ALL_PASS" = true ] && [ "$FINAL_RESULT" = "PASS" ]; then
    finish_gate "PASS"
  else
    finish_gate "FAIL"
  fi
}

# Strict Sequential Execution
run_all_gates(){
  g00
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g01
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g05
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g02
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g03
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g04
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g06
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g07
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g08
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g09
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g10
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g11
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g12
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g13
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g14
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g15
  if [ "$FINAL_RESULT" != "PASS" ]; then stop_run; return; fi
  
  g16
}

stop_run(){
  sec "EXECUTION HALTED"
  log "FAILED_AT_GATE=$FAILED_GATE"
  sec "FINAL ENTERPRISE RESULT"
  log "MYAGENTBINOD_ENTERPRISE_FINAL=FAIL"
  
  log "DATABASE_MUTATION=NO"
  log "LEGAL_SOURCE_MUTATION=NO"
  log "APPLICATION_MUTATION=NO"
  log "GIT_MUTATION=NO"
  log "DEPLOYMENT=NO"
  log "AUDIT_ARTIFACT_MUTATION=YES"
  
  exit 1
}

gate(){
  case "$GATE" in
    G00) g00;; G01) g01;; G02) g02;; G03) g03;; G04) g04;; G05) g05;;
    G06) g06;; G07) g07;; G08) g08;; G09) g09;; G10) g10;; G11) g11;;
    G12) g12;; G13) g13;; G14) g14;; G15) g15;; G16) g16;;
    all) run_all_gates;;
    *) echo "Supported: G00-G16, all"; exit 2;;
  esac
  
  if [ "$GATE" != "all" ]; then
    log "DATABASE_MUTATION=NO"
    log "LEGAL_SOURCE_MUTATION=NO"
    log "APPLICATION_MUTATION=NO"
    log "GIT_MUTATION=NO"
    log "DEPLOYMENT=NO"
    log "AUDIT_ARTIFACT_MUTATION=YES"
  fi
}

case "$CMD" in
  gate) gate;;
  *) echo "usage: $0 {gate G00..G16 | all} [repo]"; exit 2;;
esac

# If we reached here via `gate all`, it means all gates passed
if [ "$GATE" == "all" ] && [ "$FINAL_RESULT" == "PASS" ]; then
  sec "FINAL ENTERPRISE RESULT"
  log "MYAGENTBINOD_ENTERPRISE_FINAL=PASS"
  
  log "DATABASE_MUTATION=NO"
  log "LEGAL_SOURCE_MUTATION=NO"
  log "APPLICATION_MUTATION=NO"
  log "GIT_MUTATION=NO"
  log "DEPLOYMENT=NO"
  log "AUDIT_ARTIFACT_MUTATION=YES"
fi
