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

| INC-001 — MoA/AoA registration | Seed description cited s.11 and claimed non-production means no valid constitution. | Section 23 governs registration of memorandum and articles. | Seed/canonical description corrected; missing NLC upload is no longer treated as proof of non-registration or invalidity. | Require authenticated RJSC search, certified filed MoA/AoA and amendment history. |
| DIR-003 — long-delayed Form XII | Description claimed a continuing offence under s.92 and a daily fine for each day after one year. | Section 115(2) provides the 14-day particulars filing duty. The 365-day threshold is NLC policy only; no separate daily continuing offence is inferred from it. | Engine now describes 365 days as internal escalation only; no statutory penalty assertion. | Counsel must verify exact liable persons, current s.115(4) consequence, amendments and any compounding/extension. |
| CAP-001 — capital alteration | Description said s.54 is the generic capital-increase procedure and assumed a special resolution. | Section 53 concerns alteration authority subject to Articles; s.54 covers specified consolidation/conversion/subdivision notices; s.56 separately governs increase of registered capital. | Engine/seed/canonical rule text now separates the provisions and does not assume a special resolution. | Verify transaction type, operative Articles, resolution type, statutory notice, company class and current RJSC form. |
| TR-001 — transfer instrument | Description cited s.108 and claimed a missing instrument makes the transfer void. | Section 38(3) requires a duly stamped, properly executed transfer instrument and relevant certificate, subject to statutory lost-instrument/indemnity exception. | Engine/seed/canonical sources corrected; review-only status and no automatic invalidity. | Verify original instrument, execution, stamping, certificate, lodgement and any statutory exception. |
| TR-002 — stamp duty | Description claimed any unstamped instrument is automatically inadmissible and title unenforceable. | Stamp duty depends on instrument category, execution facts, current Schedule I and amendments/exemptions. | Engine now emits only a neutral review signal where non-payment is explicitly recorded; applicability must be verified. | Confirm current rate, instrument category, exemption/adjudication and authenticated payment evidence. |
| TR-003 — board approval | Description cited s.47 and said board approval is universally required and breach makes transfer void. | Section 47 concerns share warrants; s.38(7) preserves the company's power under its Articles to refuse registration. | Engine/seed/canonical rule now checks a reported Articles restriction; no universal approval or automatic voidness claim. | Verify operative Articles clause, transfer class, notices, board powers, refusal and remedies. |
| TR-004 — refusal notice | Description claimed a universal two-month register-update deadline under s.34. | Section 38(4) requires notice of refusal to both transferor and transferee within 30 days after lodgement where registration is refused. | Engine now triggers only on verified refusal, instrument lodgement date and unverified notice; two-month deadline removed. | Verify lodgement, refusal decision, notice dispatch and delivery. |
| TR-005 — restricted transfer | Description claimed automatic voidness ab initio, no legal title, mandatory court order/unanimous ratification and BLACK override. | Section 38(7) preserves the company's power to refuse registration under the Articles; it does not automatically void every restricted transfer. | BLACK override and automatic-void claims removed; registered transfer with verified restriction becomes counsel-review-only. | Review Articles, instrument, registration record, notices, rights and available remedies. |
| TR-006 — composite transfer | Description claimed each deficiency independently voids the transfer and cited ss.34, 47 and 108. | Composite review must rely on the applicable provisions, principally ss.34 and 38 and the Articles, without inventing a voidness rule. | Engine/seed/canonical descriptions now make it an internal document-review prompt only. | Every constituent signal needs its own authenticated evidence and counsel disposition. |

## 2. Primary / official source locations

1. **Laws of Bangladesh — Companies Act 1994, Part covering sections 53–73 (includes ss.38, 53, 54 and 56):**  
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
   https://bdlaws.minlaw.gov.bd/act-print-788.html  
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


## CAP-003 — capital reduction citation correction (7 November 2026)

- Previous catalogue anchor: Companies Act 1994 section 150(1)/(6).
- Correct source anchor: Companies Act 1994 sections 59–60. Section 59 addresses reduction of share capital by special resolution subject to court approval; section 60 addresses the application to court for confirmation.
- Section 150 is the separate business-commencement provision and belongs to the INC-007 review, not CAP-003.
- The rule remains NOT_EVALUATED, score impact 0, BLACK override false, and counsel review open. Exact Articles authority, creditor-notice procedure, court order, registration and consequences remain to be validated individually.
- Official primary source: https://bdlaws.minlaw.gov.bd/act-788/part-354.html


## INC-005 and INC-006 — foreign investment source corrections (7 November 2026)

- INC-005 must not cite a nonexistent “BIDA Foreign Investment Act 1980”. The official Act is the Foreign Private Investment (Promotion and Protection) Act, 1980 (Act No. XI of 1980), but it is not the operative source for the AD-bank encashment certificate workflow. Primary source anchors identified are GFET-2018 Vol.1 Chapter 9 paragraph 2(A), Bangladesh Bank FE Circular No.10 dated 21 June 2023 (foreign-currency account retention) and FEID Circular No.01 dated 27 January 2025 (share issuance to non-residents). Later FEID circulars, including 8 March 2026 and 3 November 2026, must be considered where relevant. Zone and FC-account retention exceptions must be modelled.
- INC-006 is not a Companies Act statutory breach rule. The USD 50,000 amount appears in BIDA's investment handbook as an initial-establishment-cost reference for work-permit applications. The operative BIDA 2023 work-permit guideline, exact clause, current version, applicant category and exceptions must be obtained before treating the threshold as binding. The rule is renamed as an evidence-review prompt and remains NOT_EVALUATED / 0 / no BLACK override.
- Official sources: https://www.bb.org.bd/feidportal/circulars.php ; https://www.bb.org.bd/feidportal/fdi.php ; https://www.bb.org.bd/mediaroom/circulars/feid/jan272025feid01e.pdf ; https://www.bb.org.bd/mediaroom/circulars/fepd/jun212023fepd10e.pdf ; https://www.bida.gov.bd/resources


## Historical database dump preservation note (7 November 2026)

`db_rules.txt` is a historical `psql -At -F '|'` dump used by `tools/audit_db_vs_seed.py` to compare the prior production rule rows with the canonical seed. It is intentionally preserved byte-for-byte for audit provenance, including stale source anchors and historical scores. Do not treat it as the current approved catalogue and do not rewrite it to simulate remediation. Current intended legal-release state is represented by `scripts/seed_rules.py`, the canonical CSV/JSON registries, the approval register and the forward migration plan. A difference between this historical dump and the new seed is an audit finding, not a reason to alter the snapshot.
