import json, pathlib, collections, datetime
from canonical_architecture.evaluator import evaluate_rule, EvidenceStatus
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY as R
cases = [c for c in json.loads(pathlib.Path("tests/legal_corpus/cases.json").read_text()) if c["status"]=="REVIEWED"]
m = collections.defaultdict(lambda: dict(n=0, ok=0, harmful=0, missed=0))
for c in cases:
    got = evaluate_rule(R[c["rule_id"]], c["facts"], {k: EvidenceStatus[v] for k, v in c["evidence"].items()}).state.value
    s = m[c["rule_id"]]; s["n"] += 1; s["ok"] += got == c["expected_state"]
    s["harmful"] += got == "NON_COMPLIANT" and c["expected_state"] != "NON_COMPLIANT"
    s["missed"] += c["expected_state"] == "NON_COMPLIANT" and got != "NON_COMPLIANT"
out = {"generated": datetime.datetime.now().isoformat(), "rules": m}
pathlib.Path("legal_audit").mkdir(exist_ok=True)
pathlib.Path("legal_audit/accuracy_latest.json").write_text(json.dumps(out, indent=2))
for k, v in sorted(m.items()): print(k, v)
