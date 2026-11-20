# Evidence-gated scoring and statutory control audit — 21 November 2026

## Purpose and limits

This is a technical release-control record for the evidence-gating patch. It is not a Bangladesh counsel opinion, statutory certification, or approval to mark any rule `VERIFIED`. The independent counsel register remains fail-closed: the 85 rule-specific legal dispositions remain `RECONCILE` / `PENDING`.

## Product scoring control

- This patch does not turn off `LEGAL_SCORE_RELEASED` or remove the 85-rule product scoring allowlist.
- Product scoring and independent statutory verification are separate controls. The product score may be produced only from sufficient evidence-backed inputs and score-eligible findings.
- `CompanyProfile.verified_fact_keys` is internal trust metadata. It is populated only from CompanyFact rows with `trust_level=AUTHORIZED_DOCUMENT_BACKED` and `verification_status=VERIFIED`.
- User assertions, unattributed legacy company-table booleans, missing uploads, and empty arrays do not become verified negative facts.
- The profile coverage denominator remains the existing weighted input set, but a field contributes only when its reviewer/evidence gate or verified document-backed fact is satisfied. Insufficient coverage produces `NOT_EVALUATED`, not a default GREEN.
- Engine/ILRMF version 2.3 invalidates cached 2.2 evaluations for current-score presentation. The old 15 November TechBridge evaluation must not be treated as current after 2.3 is deployed.

## Production evidence that triggered the patch

Read-only production Neon inspection for TechBridge Solutions Limited found:

- Latest stored run: `3150a0df-de28-4dd3-ab97-6bb16e1d7683`, 15 November 2026, engine 2.2, score 85 / RED.
- The run contains 86 outcomes: 77 NOT_EVALUATED, 4 UNKNOWN, 2 NON_COMPLIANT, and 3 REQUIRES_LAWYER_JUDGMENT. The stored snapshot has no explicit applicability evidence; all 86 applicability states resolve to UNKNOWN.
- Two active scored findings were `REG-002` and `TL-001`. Their provenance snapshot identifies the inputs as unattributed legacy profile fields and says source/verification status is unknown.
- The company has no CompanyFact rows at the time of this read-only check.
- Score history does not contain a matching 15 November engine 2.2 score row. The newest score-history row is 9 November with null score / NOT_RELEASED.

This is why the old 85 / RED result is not safe to reuse as a current statutory assessment. No production company rows, flags, score history, or facts were modified by this patch.

## Rule-level technical decisions

| Rule | Control after patch | Scoring disposition |
|---|---|---|
| REG-001 | Generic non-core register inventory is not a single statutory proposition; requires lawyer mapping | Review-only, zero impact |
| REG-002 | Only verified document-backed absence of a specific core record can create a finding; includes members register, charges register, AGM minutes and Board minutes | Scored only on verified absence |
| REG-003 | Section 34(2) is not relied on as a register-location authority; the location proposition remains unresolved | Review-only, zero impact |
| TL-001 / TL-002 | Licence absence/expiry requires verified licence status and, for expiry, a verified expiry date | Scored only on verified facts |
| AR-004 | Requires verified filing status and verified content-completeness fact | Scored only on verified evidence; otherwise UNKNOWN |
| CAP-004 | Requires verified special-resolution date and verified RJSC filing status | Scored only on verified absence |
| STR-001 / STR-002 / STR-003 | A workflow pending flag/date alone does not establish overdue filing; Section 88 filing status is checked separately | Review-only, zero impact |
| OFF-001 | Requires verified registered-office change date and verified Form VI filing status | Scored only on verified facts |
| MEM-001 | Section 222 requires below-minimum membership for more than six months while carrying on business; personal liability also requires proof that the individual member remained and knew | Review-only, zero impact; no automatic member liability score |

## Primary statutory text checked

- Companies Act 1994, section 36(1) and (3): annual list and summary of members; the list/certificate is completed and filed within 21 days after the first or only AGM: https://bdlaws.minlaw.gov.bd/act-788/section-32860.html
- Companies Act 1994, section 77(2): notice of registered-office location/change to the Registrar within 28 days: https://bdlaws.minlaw.gov.bd/act-788/section-32901.html
- Companies Act 1994, section 85(1)(a): at least 21 days' written AGM notice; short notice requires written consent from all members entitled to attend and vote at an AGM: https://bdlaws.minlaw.gov.bd/act-788/section-32909.html
- Companies Act 1994, section 88(1): special and extraordinary resolution copies filed with the Registrar within 15 days: https://bdlaws.minlaw.gov.bd/act-788/section-32912.html
- Companies Act 1994, section 89: minutes of general meetings and directors' meetings must be recorded; section 89(2) gives evidentiary effect to minutes signed by the chair of that meeting or the next meeting: https://bdlaws.minlaw.gov.bd/act-788/section-32913.html
- Companies Act 1994, section 222: below-minimum membership must continue while the company carries on business for more than six months; liability attaches to a member who remained during that period and knew of the shortfall: https://bdlaws.minlaw.gov.bd/act-788/section-33866.html

Section 34(2) is treated as a penalty provision and is not used as authority for the REG-003 location proposition. That proposition remains unresolved pending a separate primary-source and counsel review.

## Release gates still outstanding

1. CI must pass on the final PR head, including unit, PostgreSQL integration, lint and Docker runtime smoke.
2. Merge the code patch and deploy the exact merged SHA through the controlled migration/deploy workflow.
3. Confirm the deployed engine version is 2.3 and that the old 2.2 TechBridge evaluation is presented as stale/not current.
4. Obtain an authenticated production response from `GET /api/v1/companies/{company_id}/rule-coverage` using a signed user with company access. Do not share the bearer token in chat.
5. Review the six-state applicability and evidence counts before requesting a fresh authorized evaluation.
6. Keep independent counsel sign-off pending. Do not populate `VERIFIED_RULE_IDS` or claim legal certification based solely on this technical audit.
