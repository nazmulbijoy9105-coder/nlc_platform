from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"docs/legal/85_rule_provenance_manifest.json"
CATALOG=ROOT/"docs/legal/bd_statutory_source_chain.json"
BUILDER=ROOT/"tools/build_bd_statutory_source_chain.py"
def test_85_rule_source_chain_dossiers_are_fail_closed():
 m=json.loads(MANIFEST.read_text()); c=json.loads(CATALOG.read_text())
 expected=[r["rule_id"] for r in m["rules"]]; actual=[r["rule_id"] for r in c["rules"]]
 assert c["canonical_rule_count"]==85 and actual==expected==sorted(set(actual))
 assert c["jurisdiction"]=="BD" and c["source_policy"]["primary_language"]=="BANGLA"
 for r in c["rules"]:
  assert r["source_chain_status"]=="UNRESOLVED" and r["legal_proposition"] is None
  assert r["instrument_refs"]==[] and r["amendment_events"]==[] and r["operative_periods"]==[]
  assert r["legal_review_status"]=="REVIEW_REQUIRED" and r["source_review_status"]=="NOT_STARTED"
def test_builder_reproduces_committed_catalog(tmp_path):
 out=tmp_path/"out.json"
 subprocess.run([sys.executable,str(BUILDER),"--manifest",str(MANIFEST),"--output",str(out),"--snapshot-date","2026-11-18"],cwd=ROOT,check=True,capture_output=True,text=True)
 assert json.loads(out.read_text())==json.loads(CATALOG.read_text())
def test_builder_rejects_non_bd_manifest(tmp_path):
 bad=tmp_path/"bad.json"; out=tmp_path/"out.json"; bad.write_text(json.dumps({"jurisdiction":"UK","rules":[]}))
 p=subprocess.run([sys.executable,str(BUILDER),"--manifest",str(bad),"--output",str(out)],cwd=ROOT,capture_output=True,text=True)
 assert p.returncode!=0 and "jurisdiction must be BD" in p.stderr
