# NLC legal source corrections — 7 November 2026

**Status:** Source-corroborated engineering corrections only. **Not a legal opinion, not independent counsel approval, and not authority to activate any rule.** All 85 rules remain `NOT_EVALUATED / score_impact 0 / is_black_override false` pending individual review.

## 1. Source register and correction log

| Rule | Earlier representation | Source-supported correction | Engineering change | Remaining legal gate |
|---|---|---|---|---|
| SH-001 — Form XV / return of allotment | Seed said 30 days and cited s.50; canonical registry repeated that text | Companies Act 1994 s.151: file the return and prescribed supporting documents within 60 days after allotment; Registrar may extend time on a timely application. RJSC eBRS FAQ lists Form XV within 60 days under s.151. | Seed trigger/description changed to 60 days; canonical rule description corrected; tests now cover day 60 and day 61. | Confirm share-capital company scope, event-date evidence, non-cash allotment documents, timely extension and exact current form instructions. |
| SH-002 — share certificates | Canonical registry said 60 days and cited s.46 | Companies Act 1994 s.158: certificates are to be completed and ready for delivery within 90 days after allotment, or within 90 days after registration of a transfer. | Canonical rule description corrected to s.158 / 90 days. | Existing engine/seed currently model allotment only; transfer-registration event coverage must be implemented before completeness is claimed. Verify issue terms and exceptions. |
| SH-003 — Form IV / increase in registered share capital | Seed said 30 days and s.52; engine reused the 60-day allotment constant while describing 30 days / s.52 | Companies Act 1994 s.56: notice of increase in registered share capital is due within 15 days of the decision to increase. Official RJSC eBRS FAQ lists Form IV within 15 days under s.56. | Engine now has a distinct 15-day constant; seed trigger/description and canonical rule text corrected; tests cover day 15 and day 16. | The engine field `capital_increase_date` must be proven to represent the resolution/decision date, not an unrelated effective date. Verify company class and form version. |
| DIR-007 — director consent | Canonical registry cited s.92 for a 30-day post-appointment deadline | Companies Act text distinguishes s.92 pre-appointment consent/eligibility from s.93(2), which requires signed consent to be filed with the Registrar within 30 days after appointment. RJSC FAQ/Form IX materials label Form IX with s.92 while also describing a 30-day post-appointment filing. | Canonical description now anchors the 30-day trigger to s.93(2) and explicitly records the form-mapping issue. Engine/seed remain review-only. | Independent counsel must reconcile the statutory sub-section, current Form IX/Form X instructions, company type and appointment chronology before approval. |

| INC-007 — commencement declaration | Seed basis said ss.59–60 and the engine triggered on a bare `business_commencement_declaration_filed == false` for any company. | Companies Act 1994 s.150(1) sets conditions for commencement; s.150(6) excludes private companies and companies not issuing a prospectus inviting public subscription. | Engine now requires public-company type, verified prospectus issue, verified s.150 applicability and an evidence reference before generating a neutral review signal; seed/canonical source corrected. | Verify every s.150(1) condition (share allotment/minimum subscription, director payments, declaration and prospectus-in-lieu route) and current Registrar record. No automatic breach from a missing boolean. |
| BNK-001 — winding-up petition | Seed/engine cited Bankruptcy Act 1997 s.12. | Corporate winding-up is under Companies Act 1994 Part V. Sections 241–244 address court-winding-up grounds/petition procedure; s.242 addresses when inability to pay debts is deemed. | Engine/seed/canonical sources now refer to Companies Act Part V and require case-level verification; all BLACK overrides removed. | Verify petition provision, court, case number, grounds, service, status, dismissal/withdrawal/stay and authenticated court record. Do not infer insolvency or an order from a petition. |
| BNK-002 — liquidator appointed | Seed/engine cited Bankruptcy Act 1997 s.14. | Companies Act 1994 Part V governs company liquidation. Section 255 concerns court-appointed Official Liquidators; voluntary winding-up appointment follows separate Part V provisions. | Engine/seed/canonical sources now distinguish appointment route and use review-only status. | Verify appointment instrument, route, appointee authority, effective date and current status. |
| BNK-003 — court winding-up order | Seed/engine cited Bankruptcy Act 1997 s.18. | Court winding-up is a Companies Act 1994 Part V process, including ss.241–246. | Engine/seed/canonical sources corrected; no BLACK override or score impact. | Require authenticated operative order and verify jurisdiction, appeal/stay, suspension/discharge and current liquidation status. |
| ESC-004 — voluntary winding up | Engine description cited s.196 despite the rule being anchored at s.286. | Section 286 sets out circumstances in which voluntary winding up may occur; s.234 lists winding-up methods. | Engine description and canonical source now align to s.286 / Part V; severity remains NOT_EVALUATED. | Verify resolution type, statutory ground, solvency declaration where applicable, liquidator appointment and creditor process. |
| ESC-005 — investigation | Seed/engine mixed s.195 and s.199. | Sections 195 and 197 concern Government appointment of inspectors; s.199 concerns investigation of related entities/agents. | Engine/seed/canonical sources now distinguish the primary inspector appointment from related-entity scope; review-only. | Require authenticated Government/court appointment, scope, parties, status and any resulting proceedings. Investigation is not a finding of liability. |

## 2. Primary / official source locations

1. **Laws of Bangladesh — Companies Act 1994, Part covering sections 53–73 (includes s.56):**  
   https://bdlaws.minlaw.gov.bd/act-788/act-part-print-354.html  
   Relevant text: s.56(1) requires notice within 15 days after the decision to increase registered share capital (or the specified membership-count trigger).

2. **Laws of Bangladesh — Companies Act 1994, s.158:**  
   https://bdlaws.minlaw.gov.bd/act-print-788/section-print-33470.html  
   Relevant text: 90 days after allotment or, for a transfer, 90 days after registration of the transfer.

3. **Laws of Bangladesh — Companies Act 1994, Part covering management and administration (includes ss.92, 93 and 151):**  
   https://bdlaws.minlaw.gov.bd/act-788/act-part-print-355.html  
   Use the Bangla statutory text and verify the current consolidated text and amendment history before final approval.

4. **RJSC eBRS official FAQ:**  
   https://ebrs.roc.gov.bd/public/faqs  
   The FAQ lists Form XV within 60 days under s.151; Form IV within 15 days under s.56; Form IX/Form X with s.92; Form XII particulars within 14 days under s.115; and the 30-day post-appointment consent filing. The FAQ is administrative guidance and must not override the Act text where a citation mapping is inconsistent.

5. **Companies Act 1994 — official BDLaws Part V winding-up provisions (includes s.241 grounds and the Part V process):**  
   https://bdlaws.minlaw.gov.bd/act-788/section-33986.html?lang=bn  
   Also consult the official consolidated Act: https://bdlaws.minlaw.gov.bd/act-print-788.html

6. **Companies Act 1994 — official BDLaws management/inspection provisions (includes ss.150 and 195–201):**  
   https://bdlaws.minlaw.gov.bd/act-788/act-part-print-355.html

7. **RJSC official Form IX:**  
   https://roc.gov.bd/sites/default/files/files/roc.portal.gov.bd/forms/6ad39f2f_1cd0_4910_acce_7f477f3def68/FORM%20IX%20%282%29.pdf  
   The form itself cites s.92. Preserve this as a form-mapping issue; do not silently rewrite the statute or assume the form alone resolves s.93(2).

## 3. Provenance and temporal limitations

- Retrieval date: 7 November 2026.
- Primary-source content hashes: **NOT CAPTURED**. The rule source dossier is incomplete until exact downloaded Gazette/Act text is hashed and versioned.
- Gazette amendments, commencement dates, savings/transitional provisions, corrigenda and subsequent Registrar directions have not been fully reconciled for these four rules.
- No company-specific applicability, exceptions, relief, court order, extension, evidence custody or remedy review is complete.
- No independent Bangladesh-qualified counsel has signed any of these rules.
- A correct deadline is not proof of a breach; a missing upload is not proof of statutory absence.
- Legal consequence and NLC commercial severity remain separate decisions.

## 4. Release controls

Do not change `docs/legal/legal_approval_register.yaml` to approved. Preserve:

- `approved_rule_ids: []`
- 85/85 `REVIEW_REQUIRED`
- 85/85 `score_eligible: false`
- `VERIFIED_RULE_IDS = frozenset()`
- `LEGAL_SCORE_RELEASED = False`

Any future activation requires a complete rule-specific source dossier, applicability and evidence model, exceptions/remedies analysis, independent signed counsel disposition and passing positive/negative regression tests.
