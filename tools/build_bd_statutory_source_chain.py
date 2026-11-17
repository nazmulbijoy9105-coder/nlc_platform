#!/usr/bin/env python3
"""Generate fail-closed Bangladesh statutory source-chain intake records."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
EXPECTED=85
QUESTIONS=[
 "Identify the exact statutory proposition represented by this historical rule ID.",
 "Locate the authentic Bangla primary instrument and exact provision.",
 "Identify all amendments, substitutions, repeals, commencement notifications, saving and transitional provisions.",
 "Establish operative date intervals from primary evidence; do not infer dates.",
 "Verify company scope, exceptions, and the current text against the authentic Bangla source.",
]
def build(manifest: dict[str, Any], snapshot_date: str) -> dict[str, Any]:
 rules=manifest.get("rules")
 if manifest.get("jurisdiction")!="BD": raise ValueError("provenance manifest jurisdiction must be BD")
 if not isinstance(rules,list) or len(rules)!=EXPECTED: raise ValueError("expected exactly 85 canonical provenance rules")
 ids=[r.get("rule_id") for r in rules]
 if ids!=sorted(ids) or len(set(ids))!=EXPECTED: raise ValueError("canonical rule IDs must be unique and sorted")
 return {
  "schema_version":"1.0.0","snapshot_date":snapshot_date,"jurisdiction":"BD",
  "record_type":"BANGLADESH_STATUTORY_SOURCE_CHAIN_INTAKE_NOT_LEGAL_VERIFICATION","canonical_rule_count":EXPECTED,
  "source_policy":{
   "primary_language":"BANGLA",
   "source_hierarchy":["AUTHENTIC_BANGLA_ACT_OR_ORDINANCE","BANGLADESH_GAZETTE","OFFICIAL_COMMENCEMENT_OR_AMENDMENT_NOTIFICATION","OFFICIAL_CONSOLIDATED_TEXT_AS_CROSS_CHECK_ONLY","ENGLISH_TRANSLATION_AS_RESEARCH_AID_ONLY"],
   "date_policy":"Publication, assent, commencement, and retrieval dates are separate fields. Never infer commencement from publication, assent, consolidation, or retrieval.",
   "amendment_policy":"Record every amendment, substitution, repeal, commencement notification, saving provision, and transitional provision affecting the proposition.",
   "status_policy":"FAIL_CLOSED"},
  "rules":[{"rule_id":rid,"source_chain_status":"UNRESOLVED","legal_proposition":None,"jurisdiction":"BD","instrument_refs":[],"amendment_events":[],"operative_periods":[],"unresolved_questions":list(QUESTIONS),"legal_review_status":"REVIEW_REQUIRED","source_review_status":"NOT_STARTED"} for rid in ids]}
def main():
 p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--snapshot-date",default="2026-11-18"); a=p.parse_args()
 result=build(json.loads(a.manifest.read_text(encoding="utf-8")),a.snapshot_date); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__": main()
