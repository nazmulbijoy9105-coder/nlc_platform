# Current-Law Correctness Register (P1) — Companies Act 1994 (Bangladesh)

Maintained by the deep tech+legal audit. Sources: bdlaws.minlaw.gov.bd (act-788),
roc.gov.bd RJSC returns and Form pages, ICAB Corporate Laws Manual 2021,
BCIC vs Registrar of Joint Stock Companies (High Court Division).

## Validation charter (5-point mandate)
1. Establish current-law correctness - this register; every citation checked against official text.
2. Validate high-consequence rules - priority: AGM-001, AGM-002, AUD-002, AUD-003, AUD-001, CHG-001, DIR-007, CAP-*, REG-*, DEF-002.
3. Independent test corpus - tests/corpus/legal_corpus.yaml; every case carries statute citation, source URL and reviewer fields; corpus authored from statute text, never from engine code.
4. Measure rule and evidence accuracy - scripts/measure_rule_accuracy.py -> reports/rule_accuracy.json (flag, severity, deduction, band, evidence-UNKNOWN accuracy per rule).
5. Production gate - only rules marked VALIDATED in validated_rules.yaml may drive production compliance decisions; CI fails on contradiction; threshold 100 pct for rules with severity >= RED, >= 95 pct otherwise.

## Verified-correct citations
| Section | Used by | Verified against |
| --- | --- | --- |
| s.36 (Schedule X, 21 days) | Annual Return | roc.gov.bd returns table |
| s.77 (Form VI, 28 days) | OFF registered office | roc.gov.bd |
| s.88(1) (Form VIII, 15 days) | Special resolutions | roc.gov.bd |
| s.92 (Form IX, 30 days) | DIR consent to act | roc.gov.bd Form IX page ("See sec. 92") |
| s.115 (Form XII, 14 days) | DIR particulars | roc.gov.bd |
| s.151 (Form XV, 60 days) | SH allotment return | roc.gov.bd |
| s.159(1) (Form XVIII, 21 days) | CHG registration | roc.gov.bd (ss.159 & 391) |
| s.81 (AGM duty; first AGM 18 months, subsequent 15 months) | AGM-001/002 | s.81(2) + BCIC vs RJSC (HD Div) |
| s.183 (accounts: P&L/income-expenditure, 183(3) balance sheet & P&L) | AUD | ICAB Corporate Laws Manual |
| s.210 (auditors; s.210(2) Form 23B) | AUD / first auditor | roc.gov.bd |

## Confirmed defects
| ID | Rule | Defect | Correction |
| --- | --- | --- | --- |
| F-2 | AGM-001/AGM-002 + helper | 548/456 fixed days encode calendar 18/15 months (drift both directions) | calendar-month arithmetic (relativedelta), 6 sites: lines 359, 360, 736, 754, 2138, 2144 |
| F-10 | AGM-001 line 742 | eval_state="UNKNOWN" hardcoded on violation branch (probable, probe pending) | must be VIOLATION state on overdue determination |
| F-4 | REG-004 seed | cites s.26 for registers | s.26 = copies of MoA/AoA to members; register of members = s.34 et seq. |
| F-5 | AUD-002/AUD-003 | cite s.151 for accounts at AGM | s.151 = Return of Allotment (Form XV, 60 days); cite s.183 accounts chapter |
| F-6 | CHG-001 | Form XIX + s.159 for satisfaction | satisfaction = Form XXVIII, 21 days (Form XIX = modification, s.167(3)) |
| F-7 | DEF-002 | s.447 "penalty notices, Tk 10,000" | s.447 = punishment for fraud; not applicable as cited |
| F-11 | DIR-007 | cites s.93(2) for consent | s.92 (Form IX, 30 days) |
| F-3 | REG-004 | seed-only orphan; absent from registry and engine | restore or delete seed entry (decision pending) |

## Probable / to pin
| ID | Location | Issue |
| --- | --- | --- |
| F-12 | CAP capital increase (engine ~999-1007) | cites s.52, 30 days; official Form IV = s.56, 15 days |
| F-13 | share certificates (engine ~985-993) | cites s.158, 90 days; s.158 borders charges chapter - pin exact section |
| F-2b | FY_END_AGM_DEADLINE_DAYS=182 | no Companies Act 1994 anchor (BSEC listed-company practice); scope per company type |
| - | AGM notice 21 clear days (engine ~774-799) | cites s.85 - pin exact section |
| - | first auditor 30 days | s.210(6) subsection pin |
| - | engine.py line 668 | 120-day deadline - anchor to provision or document derivation |
| - | engine.py line 1277 | +30 days extension - anchor to provision |
