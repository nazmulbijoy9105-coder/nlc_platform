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

## Round 3 - official pins (bdlaws TOC + s.210 full text) and second F-10 site identified
| ID | Location | Finding | Correction / status |
| --- | --- | --- | --- |
| F-19 | engine.py ~514 (INC-001) | Second eval_state UNKNOWN hardcode identified INSIDE the INC-001 violation branch (moa_aoa_filed is False + company older than 30 days), severity RED, impact 15 - deduction zeroed for every affected company. Closes round-2 F-10 second-site identity | Split semantics: AGM-001 :742 violation is computable from incorporation_date (False sentinel cannot fire the branch) - remove hardcode, restore deduction; INC-001 is a genuine NLC evidence gap (RJSC cannot register without MoA/AoA, s.23) - keep UNKNOWN. CRITICAL |
| F-20 | engine.py 1886-1896 | Severity floor lifts band on any active RED/BLACK flag with state NON_COMPLIANT; no eval_state check - UNKNOWN flags (impact 0) still force RED band, contradicting F3 policy at line 105 (unknown = indeterminate, not violation) | Add eval_state check to floor condition; gate on probe R3-P1 (construction of active). CRITICAL |
| F-21 | engine.py 1884 and 1950 | Corrupted merge-artifact comments: "(BLACK handled above)'t override" and duplicated rescue comment text | Clean text during the F-10/F-20 fix commit; no behavior change. LOW |
| F-22 | engine.py 373-377 | CORE_REGISTERS lacks statutory pins. Official TOC pins: members = s.34 (Register of members), directors = s.115 (Register of directors, managers and managing agents), charges = s.174 company register (RJSC filing s.159 Form XVIII), minutes_agm = s.89 (minutes of general and Board meetings) | Add pin comments and unify registry citations. MEDIUM |
| F-23 | statutory_rules.py REG-001/REG-002 | Registry bundle "Sections 34, 83, 87, 90" legally wrong: s.83 = statutory meeting and statutory report; s.87 = extraordinary and special resolutions; s.90 = minimum number of directors; register of directors = s.115 | Re-anchor registry to s.34, s.115, s.174, s.89 aligned with engine. HIGH |
| F-24 | statutory_rules.py AUD-003 | Bundle "Sections 151, 210" wrong: s.151 = Return as to allotment (Form XV), unrelated to auditors. s.210 full text pinned from bdlaws section-33854: 210(1) appoint at each AGM plus 7-day notice to auditor; 210(2) auditor informs Registrar within 30 days (duty-holder is the auditor, not the company); 210(3) retiring-auditor re-appointment with NO 120-day rule; 210(6) first auditors by Board within 1 month of incorporation | Engine and registry cite "Section 210" only; FIRST_AUDITOR_DEADLINE_DAYS=30 comment VERIFIED; AUD-005 anchor stays open under F-15. MEDIUM |
| F-13 CLOSED | engine.py SH-002 and constants | s.158 verified: official TOC title "Time limit for issuing certificate"; published legal commentary quotes 90 days from allotment or registration of transfer | SHARE_CERTIFICATE_DEADLINE_DAYS=90 and the s.158 citation are CORRECT; SH-002 severity dead branch stays open under its round-2 row |

Sources this round: bdlaws.minlaw.gov.bd act-788 TOC (sections 23, 34, 36, 52, 56, 77, 81-89, 90-93, 115, 151, 158-175, 181-190, 210); bdlaws act-788/section-33854 (s.210 full text); roc.gov.bd Form XXVIII page (s.172, from round 2).

## Round 3b - git-state reconciliation + VERIFIED_RULE_IDS gate + Form IX resolution
| ID | Location | Finding | Correction / status |
| --- | --- | --- | --- |
| F-25 | git state (main vs legal/s4-validation-gate) | Round-3 register landed on main (7c64e3a) but main advanced independently: origin/main has c5cc226 (P0+P1 production eligibility gate + TR-006 fix) and 39eb681 (P1 reference corpus, 27 cases). Branch-only: 66307f6 fail-closed validation gate and 769a579 register round-2 rows F-14..F-18 (probe confirmed absent on main) - round-3 rows F-19/F-24 reference F-15/F-14b which do not exist on main | Reconcile after state probes: cherry-pick 769a579 (docs-only) or merge branch; decide overlap between 66307f6 gate and c5cc226 gate before merging any code. HIGH |
| F-26 | engine.py ~1857-1862 (main) | Second silent deduction suppressor: _calculate_score deducts only for flags with state NON_COMPLIANT AND rule_id in VERIFIED_RULE_IDS. INC-001 confirmed in the list (line 394); AGM-001 membership unconfirmed - if missing, the F-10 fix restores eval_state but the deduction stays zero | Probe R3-P8 dumps the full list; the F-10 fix commit must ensure AGM-001 is a member. CRITICAL |
| F-27 | engine.py legacy scorer | Dual scoring paths: legacy module_sum scaled by int((module_sum / 125.0) * 100) vs _calculate_score 100-point CATEGORY_CAPS path | Pin the authoritative path before P4 measurement; probe R3-P9. MEDIUM |
| F-11 CONFIRMED | DIR-007 engine + registry line 1236 | Official RJSC Form IX page: FORM IX - Consent of Director to Act (See sec. 92), signed pursuant to section 92(1)(Ka); official RJSC returns table: Form IX filed within 30 days of appointment [Section 92]. Form IX is the CONSENT form (round-1 label return-of-appointment corrected); s.93 is a separate consent-of-candidate provision. Registry requirement text (consent, 30 days) semantically right but anchor Section 93(2) wrong; engine cites Section 93 too. Registry shows severity YELLOW impact 5 - engine value to be read and unified. If DIR-007 also fires on director CHANGES, Form XII (s.115, 14 days) applies to changes | Engine and registry both cite Section 92; probe R3-P5 window decides Form IX vs Form XII scope. CONFIRMED |
| F-28 | multi-file (bonus official pins) | Official RJSC returns-filing table: Balance Sheet AND P and L within 30 days of AGM; Form 23B (auditor notice) within 30 days [s.210(2), duty-holder auditor]; Form III 15 days [s.53 and 54]; Form IV 15 days [s.56 - reconfirms F-12]; Form VI 28 days [s.77]; Form VIII 15 days [s.88(1)]; Form XII 14 days [s.115]; Form XV 60 days [s.151]; Form XVIII 21 days [s.159 and 391]; Form XIX 21 days [s.167(3)]; Form XXVIII 21 days - RJSC process-brief cites [Section 12 and 391] but the Form XXVIII page and bdlaws TOC title for s.172 (registration of payment/satisfaction of mortgage and charge) say s.172 - prefer s.172, record discrepancy; Schedule X annual return clock = 21 days from AGM | Feed into F-12/F-6 fixes and the AR-001 anchor check (probe R3-P9). VERIFIED |
| F-10 STATUS | engine.py main lines 528 and 756 | Sites re-confirmed on main (line drift +14 vs branch). AGM-001 already has a proper upstream UNKNOWN branch (agm_count None or incorporation_date None - severity YELLOW, impact 0, state=RuleState.UNKNOWN, early return), which is the engine's own correct idiom for missing data. The 756 hardcode sits strictly inside the overdue branch where facts are determined | Fix pattern: 756 - delete the eval_state line (violation stands); 528 - replace eval_state hardcode with state=RuleState.UNKNOWN + score_impact 0; plus F-20 floor hardening. CRITICAL |

Sources this round: app.roc.gov.bd FORM IX page (Consent of Director to Act, sec. 92(1)(Ka)); app.roc.gov.bd RJSC Business Process Brief returns-filing tables (Form IX 30d s.92, Form XII 14d s.115, Form IV 15d s.56, Form 23B 30d s.210(2), Form XXVIII 21d, Schedule X 21d s.36); bdlaws act-788 TOC (s.93 = consent of candidate for director).

## P5 promotion log

- 2026-10-30 R4-P3: AR-001 (s.36, 21-day annual return; re-verified this round) and SH-002 (s.158, 90-day share certificate; F-13 CLOSED) promoted into VERIFIED_RULE_IDS. Allowlist 41 -> 43.
- 2026-10-30 R4-P4b (F-27 completion): stale inline caps confirmed at multiple sites with different groupings; grouping-independent per-term rewrite applied everywhere (all sites now read CATEGORY_CAPS). Divisor 240 retained in _calculate_raw_score. Dual score model flagged as F-28; BLACK-override eval_state gap flagged as F-29.
- R4-P5d (F-29 CLOSED): BLACK override + ESC-003 trigger now exclude UNKNOWN flags (eval_state != UNKNOWN) at 3 sites: _calculate_score critical primary (~1892), critical fallback (~1895), _run_escalation_rules has_black_override (~1767, context-anchored edit after C_COUNT=0 exposed invisible byte mismatch - cat -A diagnostics in transcript). Reporting counters intentionally un-gated (black_flag_count ~1955, lifecycle stage ~2112, rescue priority ~2045/2079). F-28 RESOLVED: _calculate_raw_score (Model A, caps-normalized /240) is ESC-003 trigger-only; _calculate_score (Model B, 100 minus capped deds) is user-facing; both P5-gated and UNKNOWN-safe. ESC-003 threshold pre_score<=29 equals >=71 percent cap budget consumed - policy decision point, unchanged. Zero live-behavior delta today (no BLACK rule emits UNKNOWN). New findings: F-30 black_count (~1771) unfiltered by state/eval_state; F-31 lifecycle has_black (~2112) unfiltered (descriptive); F-32 citation divergences engine vs statutory_rules (ESC-004 286/234/196, ESC-005 195/199, ESC-001/002 346/304-305, special resolution 87 vs 113, SH- internals, capital reduction 59 vs 150, form mismatches) - queued for bdlaws verification round.
- R4-P6b (F-30 CLOSED): ESC-003 black_count (line 1772) now counts only active BLACK indicators: adds state == RuleState.NON_COMPLIANT, eval_state != UNKNOWN, not resolved, conditional_applies - matching the active-flag convention used by both scoring paths. Zero live-behavior delta today (rule-emitted flags are NON_COMPLIANT and active by construction; no BLACK rule emits UNKNOWN). Prior attempt R4-P6 auto-reverted: post-guard expected GATE_TOTAL=4 but the new line itself contributes 1 match (correct value 5) - guard failed safe, no corruption. New decision point F-33: the BLACK override (final = 0) and the severity floor are not VERIFIED_RULE_IDS-gated by design (risk-policy mechanisms) - ESC-003 currently forces score 0 while itself unverified; charter owner to confirm whether the P5 production gate should extend to override/floor.

---

## EA-Series - External Audit Cross-Reference (2026-10-30)

Source: external audit of PDF NLC_Compliance_Report_5aab4f3f-80bf-4de8-8e84-39351038f77d
(Structural BLACK Co / TEST-BB3DDCF6, report date 2026-10-30), checked line by line against
bdlaws.minlaw.gov.bd act-788 (TOC titles for ss.34/35/36/89/94/115/163/164/165/174/210; verbatim
s.94 via section-32918 and s.115 via section-32939 fetched 2026-10-30) and against this engine tree.
F-series queue (F-22..F-33) unchanged by this section; EA rows add cross-cutting items only.

### EA-01 - DEF-001 five-year claim (audit s.2) - OPEN, P0
- VERDICT: audit CORRECT on the core defect. s.94 verbatim: five grounds only - (a) unsound mind
  found by competent court, finding in force; (b) undischarged insolvent; (c) pending insolvency
  application; (d) unpaid call, 180 days elapsed after last date fixed for payment; (e) minor.
  s.94(2): Articles may determine additional grounds. No time-bounded disqualification exists.
- AUDIT ERROR NOTED: ground (d) is 180 days per bdlaws, not six months as the audit says.
- Required rebuild: DEF-001 must require statutory/Articles ground + director identity + evidence
  + effective date + continuing status; unverified allegation => eval_state UNKNOWN, score_impact 0,
  review status - never BLACK. Policy decision open: DEF-001 membership in VERIFIED_RULE_IDS while
  its text is rebuilt. Note: the only "5 years" concept nearby is s.110 (managing-director tenure
  limit), unrelated to disqualification; the 5-year post-conviction bar is a foreign-law pattern.

### EA-02 - AUD-001 calendar month vs 30 days (audit s.4D) - OPEN, P0
- VERDICT: audit CORRECT. Flag text "1 month (30 days)" conflates calendar month with 30 days;
  s.210(6) says one month (calendar). Distinguish s.210(6) Board appointment from the auditor's
  own filing duty under s.210(2).
- Arithmetic (computed): overdue 1813 days => deadline = 2021-11-12 exactly. With incorporation
  2021-10-12, +1 calendar month reproduces 1813 while +30 days gives 1814; with incorporation
  2021-10-13, +30 days gives 1813. PDF shows no incorporation date => not independently
  verifiable from the report (audit CORRECT).
- Required: calendar-month arithmetic helper (month-end aware), remove the "(30 days)" gloss,
  expose incorporation date + deadline + convention on the flag.

### EA-03 - INC-001 evidence semantics (audit s.4A) - OPEN, P1
- Engine already separates impact 0 via eval_state UNKNOWN (single s.23 evidence-gap hardcode,
  two raise sites 576/593, >30-day company-age guard at 567). Remaining: the four evidence
  conditions (confirmed missing from company records / exists at RJSC not uploaded / registry
  unreachable / conflicting copies) must map to distinct states, not one RED flag; severity
  display must read as verification-pending.

### EA-04 - AGM-001 state distinctions (audit s.4C) - OPEN, P1
- Engine already gives YELLOW / 0 for unknown AGM history (correct). Remaining: evaluator must
  distinguish AGM held+verified / not held+overdue / not yet due / date disputed / evidence
  unavailable, computed from incorporation date, financial year, previous AGM date and any
  extension (ss.81-83 subjects confirmed from official TOC).

### EA-05 - REG-002 split (audit s.4B) - OPEN, P1
- VERDICT: split justified. Official TOC: s.34 Register of members; s.35 Index; s.36 Annual list
  and summary; s.89 minutes of GM and board meetings; s.174 register of mortgages (company).
- AUDIT ERROR NOTED: s.115 is BOTH the internal register of directors/managers/managing agents
  (s.115(1), kept at registered office) AND a filing duty to the Registrar within 14 days
  (s.115(2)); penalty s.115(4). The PDF mapping "Directors (Sec 115)" stands.
- Keep "RJSC register Sec 163-165" only for registration-side obligations (163 register, 164
  index, 165 certificate); never cite it for the company's own register (s.174).
- Required: one rule per independently testable obligation, own evidence and own score impact.

### EA-06 - displayed vs applied score impact (audit s.5) - OPEN, P1
- PDF shows AUD-001 "-10" while the P5 gate (VERIFIED_RULE_IDS, 43 members) excludes AUD-001
  from both score paths; ScoreBreakdown must expose P5-applied impact and mark excluded rules so
  a report never displays an impact the engine did not apply. Audit s.5 architecture (raw vs
  final separation, evidence-dependent gates, reproducibility) already implemented - this row
  closes only the display gap.

### EA-07 - rescue plan coverage (audit s.6) - OPEN, P1
- PDF: 5 flags -> 2 steps (_generate_rescue_sequence, engine.py 537); INC-001, AGM-001, AUD-001
  got no disposition. Required: one disposition per flag (action or documented no-action reason);
  plan fields: responsible professional, required documents, statutory basis, internal vs
  statutory deadline separation (29 Nov 2026 is a 30-day internal target, NOT a statutory
  deadline), dependencies, completion evidence, reviewer approval, final verification result.

### EA-08 - rule temporal/version metadata (audit s.7) - OPEN, P2
- Rules need effective_from, effective_to, jurisdiction, company_type, applicability_conditions,
  source_section, source_version, reviewed_by; a legal amendment must not rewrite historical
  assessments.

### EA-09 - report metadata + integrity (audit s.8) - OPEN, P2
- Missing on PDF: incorporation date, company type, financial year, assessment reference ID,
  engine version, legal-source verification date, evidence references, reviewer/approval status,
  score breakdown detail, integrity hash. TEST- prefix registration (TEST-BB3DDCF6) must render
  an explicit TEST ASSESSMENT marking.

### EA-10 - external audit test suite (audit s.9) - OPEN, P1
- Implement LEG-001..006, DATE-001..002, SCORE-001..004, RESCUE-001..002, AUDIT-001..002 as
  automated cases. P0 gates: SCORE-002 (unverified BLACK => no automatic override) and
  DATE-001 (calendar-month deadline arithmetic).

### EA-11 - audit claims confirmed, no change (audit s.1, s.5, s.10) - CLOSED
- Arithmetic: 100 - (20+0+12+0+10) = 58; BLACK override -> 0; banding 70/50/30 matches Model B;
  ESC-003 escalation threshold <=29 mirrors the BLACK band; NOT_EVALUATED band exists for
  insufficient data. Failure-safe direction (missing data != proven breach) matches the
  eval_state UNKNOWN design already in the engine.
