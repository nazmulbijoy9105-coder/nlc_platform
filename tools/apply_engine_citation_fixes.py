#!/usr/bin/env python3
# Engine citation fixes - batch 2 (ground-truth sync, 2026-10-30)
import io, ast
P = "app/rule_engine/engine.py"
t = io.open(P, encoding="utf-8").read()

REPL = [
 ("FIRST_AUDITOR_DEADLINE_DAYS = 120  # Section 210(6): 30 days first auditor",
  "FIRST_AUDITOR_DEADLINE_DAYS = 30  # Section 210(6): first auditor within 1 month (30 days) of registration"),
 ("Share certificates not issued within 60 days. Section 158: overdue by",
  "Share certificates not issued within 90 days. Section 158: overdue by"),
 ("Section 151 requires audited accounts at AGM.",
  "Section 183 requires audited accounts to be laid before the AGM."),
 ("Section 210(2): mandatory at every AGM.",
  "Section 210(3): mandatory at every AGM."),
 ("Section 87: 30-day deadline. Unregistered charge void against liquidator.",
  "Section 174: registration deadline. Unregistered charge void against creditors and liquidator."),
 ("disqualified under Sec 94. Cannot act as director for 5 years.",
  "disqualified under Section 118(6). Cannot act as director for 5 years."),
 ("Capital reduction without court order. Sec 100.",
  "Capital reduction without court order. Section 150."),
 ("Charge satisfaction not filed via Form XIX. Sec 87.",
  "Charge satisfaction not filed via Form XIX. Section 159."),
 ("Core registers missing: {', '.join(core_missing)}. Members (Sec 34), Directors (Sec 90), Charges (Sec 87), AGM Minutes (Sec 89).",
  "Core registers missing: {', '.join(core_missing)}. Members (Sec 34-36), Directors (Sec 115), Charges (Sec 174; RJSC register Sec 163-165), GM & Board Minutes (Sec 89)."),
 ("Sections 34, 83, 87, 90, Companies Act 1994 (Bangladesh)",
  "Sections 34-36, 89, 115, 163-165, 174, Companies Act 1994 (Bangladesh)"),
 ("severity = Severity.RED if len(core_missing) <= 2 else Severity.BLACK",
  "severity = Severity.RED  # legal: REG-002 downgraded BLACK -> RED"),
 ("score_impact=10 if len(core_missing) <= 2 else 20,",
  "score_impact=12,"),
 ("revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION if severity == Severity.RED else RevenueTier.CORPORATE_RESCUE,",
  "revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,"),
 ("CHARGE_REGISTRATION_DEADLINE_DAYS = 30",
  "CHARGE_REGISTRATION_DEADLINE_DAYS = 30  # verify: s.174 window (RJSC practice 21 days)"),
]
for old, new in REPL:
    n = t.count(old); t = t.replace(old, new)
    print(("FIXED " if n else "MISS  ") + old[:58])

lines = t.split("\n")
def blocks(rule):
    return [i for i, l in enumerate(lines) if ('rule_id="%s"' % rule) in l]

# block-scoped statutory_basis corrections (CAP-002 151->174, SH-001 158->151)
for rule, old, new in [
 ("CAP-002", 'statutory_basis="Section 151, Companies Act 1994 (Bangladesh)"',
             'statutory_basis="Section 174, Companies Act 1994 (Bangladesh)"'),
 ("SH-001",  'statutory_basis="Section 158, Companies Act 1994 (Bangladesh)"',
             'statutory_basis="Section 151, Companies Act 1994 (Bangladesh)"'),
]:
    done = False
    for i in blocks(rule):
        for j in range(i, min(i + 14, len(lines))):
            if old in lines[j]:
                lines[j] = lines[j].replace(old, new); done = True; break
        if done: break
    print(("FIXED " if done else "MISS  ") + rule + " statutory_basis")

# remove the forbidden INC-002 duplicate declaration
removed = 0
for i in blocks("INC-002"):
    start = i
    while start > 0 and "if c.paid_up_capital_bdt" not in lines[start]:
        start -= 1
    end = i
    while end < len(lines) - 1 and lines[end].strip() != "))":
        end += 1
    del lines[start:end + 1]
    removed += 1
print("REMOVED %d INC-002 block(s)" % removed)

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
ast.parse(io.open(P, encoding="utf-8").read())
print("AST OK")
