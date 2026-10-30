import csv, re, collections
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY as R
def g(o, k, d=""):
    v = getattr(o, k, d); return str(getattr(v, "value", v))
sec = collections.defaultdict(list)
for rid, r in R.items():
    for s in re.findall(r"Sections? ([0-9]+)", g(r, "law") + " " + g(r, "provision")):
        sec[s].append(rid)
rows = []
for rid, r in sorted(R.items()):
    sev, imp = g(r, "severity"), int(getattr(r, "score_impact", 0))
    prov, st = g(r, "provision"), g(r, "provision_status")
    if sev in ("RED", "BLACK") or imp >= 15 or prov in ("", "TBD") or st.upper() != "VERIFIED":
        s = re.findall(r"Sections? ([0-9]+)", g(r, "law"))
        rows.append([rid, sev, imp, g(r, "law"), prov, st, g(r, "requirement")[:200],
                     max((len(sec[x]) for x in s), default=0), "", "", "", ""])
with open("docs/legal_review/tier1_review_sheet.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["rule_id","severity","impact","law","provision","status","requirement",
                "rules_sharing_section","gazette_citation","verdict","reviewer","review_date"])
    w.writerows(rows)
print(len(rows), "tier-1 rules")
