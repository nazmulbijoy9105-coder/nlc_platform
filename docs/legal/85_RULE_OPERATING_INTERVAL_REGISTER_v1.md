# 85-rule provision-level amendment and operative-interval register

**Snapshot:** 2026-11-18  
**Status:** fail-closed research register; not a legal opinion or score-release approval.  
**Located source anchors:** 26 Government Press/official-issuer records; 75 rule-level amendment-candidate entries.

## What this register establishes

This register normalises all 85 canonical rule candidates, their recorded provision candidates, parent instruments, and amendment/related-instrument candidates from the v1 workpack. It also defines issuer/document authentication and interval-construction standards, and pins four Companies Act-family Gazette anchors (including the Financial Reporting Act amendment) to the Bangladesh Government Press index and Gazette artifacts.

It deliberately does **not** claim that all 85 histories are complete. At this snapshot:
- 85/85 amendment histories remain open and non-exhaustive.
- 84/85 rules have at least one provision candidate; 1/85 does not (FX-001).
- 0/85 rule-specific operative intervals are legally resolved.
- 0/26 located issuer/document anchors have independent counsel authentication recorded.
- 0 artifact SHA-256 values have been captured from downloaded original bytes.
- 0 rules have counsel approval.

## Provision-level gaps that remain open

The 85-rule inventory currently has 84 provision candidates and one explicit gap. These are deliberately not filled with guessed section numbers:

| Rule | Recorded source claim | What is still missing |
|---|---|---|
| BSEC-001 | Catalogue says BSEC Corporate Governance Code 2023, paragraph 8 | A quarterly-report provision candidate is now identified in BSEC's separate 20-Jun-2018 Financial Reporting and Disclosure Notification, Condition 4(1)–(3). Resolve the source-identity conflict; do not silently rewrite the historical claim. |
| FX-001 | Foreign Exchange Regulation Act 1947 | Exact FERA enabling section and current GFET chapter/paragraph/circular clause for the actual rule proposition. |
| INC-006 | BIDA 2023 foreign commercial office/work-permit procedure | A signed 21-May-2023 copy and paragraphs 6.5.2.3 / Appendix 9 are located; Bangladesh Bank confirms an updated 29-May-2023 version whose original PDF remains unretrieved. Authenticate the final version and scope. |
| TR-002 | Stamp Act 1899, Schedule I | Articles 61(a), 5(b)(ii) and historical 62(a) are now mapped with 2012/2022 Finance Act events. Remaining work is transaction-specific instrument classification, consideration, execution date, listed-company exemption and territorial/current-law review. |

The register contains 75 amendment/related-instrument candidate entries across 29 rules; 56 rules have no amendment candidate entry in this snapshot. These are research candidates, not exhaustive amendment histories. All 85 histories remain OPEN_NOT_EXHAUSTIVE. No missing section, date or rate is to be inferred merely to make the register appear complete.

## Primary-record anchors located

1. **Companies Act 1994 commencement SRO:** Government Press November 1994 index lists SRO No. 321-Law/94, dated 10 November 1994, Ministry of Commerce, p.5033. The Companies Act section 1 footnote records commencement on 1 December 1994; the SRO scan remains only partially text-authenticated. The DPP-hosted one-page PDF is linked. Its extracted text is garbled, so page-image/certified-copy comparison remains required.
2. **Companies (Amendment) Act 2020, Act No. 7:** DPP index lists the Act on 25 February 2020, pp.2779–2781. The Gazette header identifies Bangladesh Gazette Extraordinary, National Parliament and Act No.7. Section 1(2) says immediate commencement. Section 8's section-85 amendment removes seal wording from s.85(2)(ch); do not treat that as a notice-period amendment.
3. **Financial Reporting Act 2015, Act No. 16:** DPP index lists the Act on 9 September 2015, pp.7029–7059. The Gazette header identifies Bangladesh Gazette Extraordinary and National Parliament; section 1(2) says immediate commencement. Section 62 inserts Companies Act provisions in ss.185, 190, 212 and 220. In particular, s.62(b) inserts Companies Act s.190(1A) for a company meeting the public-interest-entity definition in F.R. Act s.2(8), not every private company.\n4. **Companies (Second Amendment) Act 2020, Act No. 24:** DPP index lists the Act on 26 November 2020, pp.12417–12427. Gazette header identifies Bangladesh Gazette Extraordinary, National Parliament and Act No.24. Section 1(2) says immediate commencement. Section 5 amends Companies Act s.85(1), so it is a relevant notice-rule event candidate; final rule effect still requires clause-level comparison and counsel approval.

## Issuer and document authentication standard

- **Acts:** confirm Parliament as enacting authority, Act number/year, assent/promulgation, Gazette publication, exact Bangla text and commencement clause.
- **Ordinances:** additionally establish constitutional promulgation authority, continuation/laying/approval where relevant, repeal or replacement, and savings.
- **SROs and Rules:** establish the delegated rulemaker, enabling section, SRO/rule number, authorised signatory, Gazette issue and date, scope, commencement and amendments.
- **BSEC notifications/codes:** verify BSEC statutory competence, enabling provision, Board/Commission resolution, notification number/date, signed issuer copy, Gazette record where applicable, applicability and supersession.
- **Bangladesh Bank circulars:** verify issuing department, circular number/date, signed official PDF, legal basis, addressees, effective date and replacement/cancellation.
- **NBR tax SROs:** verify NBR/Finance Ministry competence, enabling tax provision, SRO number, Gazette publication, relevant tax period and retrospective/savings clauses.
- **Administrative guidance:** do not treat a guideline as legislation unless its binding effect is established by an enabling Act, Rule, SRO or valid direction.
- **Company/auditor/RJSC/court records:** authenticate the actual issuer, authority, signature, entity, event date, register entry and chain of custody. This is separate from authenticating the statute that requires the record.

For every artifact preserve original bytes, SHA-256, retrieval timestamp, issuer, index record, Gazette series/date/pages, signature/authentication markers, language, page-level references, OCR comparison, corrigenda/supersession and reviewer. A URL alone is not authentication. OCR is discovery text, not the authoritative Bangla record.

## Interval construction

Use `from` inclusive and `to_exclusive` exclusive. Keep instrument publication date separate from legal commencement date. For each exact rule proposition, enumerate every amendment, substitution, repeal, delegated rule, SRO, regulator instrument, corrigendum and binding judicial order. Apply express retrospective provisions only within their stated scope and subject to savings/transitional provisions. Split intervals only where the specific proposition legally changes. An open-ended interval is not proof that the law remains unchanged.

## BSEC Corporate Governance Code source chain

The BSEC Code is separately anchored to the DPP Gazette:
- 2018 Code, notification dated 3 June and published 10 June 2018, DPP pp.6871–6902. Relevant provisions include Condition 1(2)(a), Condition 5(1)(a), and Condition 9(1)–(3).
- 2023 amendment, notification dated 16 October and published 20 November 2023, DPP pp.16911–16914. It changes Condition 1(2)(a) and other provisions. The final sentence says “This shall have immediate effect” after item 13; the register does not assume that this applies to every preceding item.
- 2024 amendment, notification dated 4 April and published 29 April 2024, DPP pp.11071–11072. It adds the female independent-director proviso to Condition 1(2)(a), with compliance required within one year of issuance.
- BSEC letter dated 26 July 2026, ref. BSEC/ICAD/CGD/2023/106/Part-I/333, on the official BSEC domain, extends that appointment deadline to 31 December 2026. It is an official issuer letter, not a Gazette; authority/delegation and supersession remain review items.

The BSEC-004 title/source conflict remains explicit: the rule title points to Condition 5(1)(a) of the Code, while its recorded statutory basis says the Foreign Exchange Regulation Act 1947. BSEC-001 remains without a provision candidate because its exact quarterly-report instrument and due date are still unidentified.

## Bangladesh Bank foreign-investment / account source chain

The official Bangladesh Bank sources now pinned include:
- GFET 2018 Volumes 1–2 and FE Circular No.08 dated 4 March 2018, issued under FERA 1947 s.20(3).
- FE Circular No.10 dated 21 June 2023 on foreign-currency accounts for foreign investment.
- FEID Circular No.01 dated 27 January 2025, which cites GFET Vol.1 Chapter 9 paragraph 2(A), requires qualifying share-issue reporting within 14 days and preserves Appendix 5/39 or 5/40 encashment certificates with online transaction IDs.
- FEID Circular No.03 dated 30 September 2025, effective immediately, which relaxes opening-account reporting but requires post-incorporation notification and documentary evidence within 14 days.
- **FEFD-2 Circular No.12 dated 12 November 2026.** Paragraph 1 repeals existing foreign-currency account instructions in GFET-2018 Vol.1 and subsequent account circulars with issuance, subject to its stated GFET Vol.2 monthly-reporting exception. Part E paragraph 31(3)(a) requires an AD certificate in Appendix 5 for foreign-investment remittances; paragraph 20 says the circular is valid for one year from issue.

The 2026 circular is a material current-law event for INC-005's account evidence chain. It does not automatically repeal every separate share-issuance reporting requirement in GFET Chapter 9. The register flags the need to reconcile the new Appendix-5 certificate with FEID Circulars 1/2025 and 3/2025 and to distinguish account-operation duties from share-issue reporting.

## Local-government trade-licence source chain

Primary Gazette records now pinned:
- City Corporation Model Tax Schedule 2016, SRO 13-Law/2016, DPP 31-Jan-2016, pages 965–996. Clause 1(2) applies to all City Corporations; clause 10(3) permits annual trade-licence fees to be collected together for up to five years. No universal 31-March renewal date appears in the schedule reviewed.
- Paurashava Model Tax Schedule 2014, SRO 246-Law/2014, DPP 23-Oct-2014, pages 19127–19162. Clause 1(2) applies by class to all Paurashavas; clause 6 sets annual business/profession taxes; clause 26 imposes a 5% surcharge if renewal has not occurred by 30 September and a separate 10% annual surcharge on arrears. That date is a surcharge trigger, not proof of licence expiry.
- SRO 200-Law/2017, effective 1-Jul-2017, amends only the 2016 schedule's holding-tax exemption clause 3(3), not the trade-licence provisions.
- Local Government (Paurashava) Amendment Act 2026 (Act 60) and City Corporation Amendment Act 2026 (Act 61), both effective immediately on 10-Apr-2026. Act 60 changes definitions/repeals s.20A; Act 61 adds e-rickshaw-specific licence/registration rules in Third Schedule item 19.2 and Fifth Schedule item 60A. Neither is treated as a general company trade-licence renewal amendment.

**Rule correction:** the workpack's generic “renew by 31 March annually” claim is unsupported as a universal rule. For a City Corporation, the 2016 schedule allows up to five years' advance fee collection and does not set a universal renewal date. For a Paurashava, clause 26 uses 30 September for a surcharge trigger, not necessarily the licence expiry date. The actual licence and current local authority order must control.

## VAT return provision source chain

The annual-return rule is not supported as a universal obligation. The current source chain for VAT Act 2012 section 64 is:
- **Finance Act 2026 (Act 96)**, published 30-Jun-2026; section 1(2) brings it into force on 1-Jul-2026. Section 11 replaced s.64 with a return after every three tax periods, generally within 15 days (20 days for specified categories).
- **VAT Amendment Ordinance 38/2026**, Gazette 14-Oct-2026; section 1(2) deems it effective from 1-Oct-2026. Section 2 replaces s.64 again, requiring a return for each tax period within 15 days (20 days for specified government bodies, banks, insurers and nil-return filers).
- **VAT Amendment Act 77/2026**, effective 9-Jan-2025 by section 1(2), changes VAT definitions/schedules and repeals the 2025 amendment ordinance with savings; it does not amend s.64.

Therefore, as of 18-Nov-2026, the located s.64 text is periodic, not a universal annual return. Taxpayer registration status, assigned tax period and any NBR extension order control the assessment.

## BSEC quarterly-report source correction

BSEC-001 is not Corporate Governance Code 2018 Condition 8. The exact candidate is BSEC Notification No. BSEC/CMRRCD/2006-158/208/Admin/81, dated 20-Jun-2018 and published in the Bangladesh Gazette on 8-Aug-2018:
- Condition 4(1): Q1 within 45 days; listed life insurers within 90 days.
- Condition 4(2): Q2 within one month.
- Condition 4(3): Q3 within one month.
- It applies to companies listed with any Bangladesh stock exchange.
- Condition 10(1) repeals named earlier reporting instruments; Condition 10(2) contains savings. The notification text reviewed does not state an exact commencement date.

BSEC's 2-Jul-2026 public statement about a proposed move to half-yearly reporting is recorded as a non-binding policy watch only. No formal Gazette/notification replacing Condition 4 was located as of 18-Nov-2026; do not disable the quarterly rule on the strength of the public statement.

## BIDA 2023 procedure — USD 50,000 remittance and work-permit evidence

A signed BIDA Procedure 2023 copy dated 21-May-2023 is located in a Government-hosted PDF. Paragraph 2 says the procedure is effective from issue date. Paragraph 6.5.2.3 requires approved branch/liaison/representative/project offices to bring USD 50,000 (or equivalent) through banking channels within two months of permission; each month of delay attracts an additional 6% amount. Appendix 9 separately lists encashment certificate/proof of USD 50,000 for specified foreign/joint-investment work-permit applications.

However, Bangladesh Bank FEID Circular Letter No.06 dated 17-Oct-2023 confirms that BIDA issued an updated version on 29-May-2023 under memo No.03.219.344.00.00.1142.2019-849 and links the BIDA-hosted PDF. That final BIDA PDF could not be retrieved here. The 21-May copy must not be assumed to be the final operative version.

The USD 50,000 condition is therefore a **conditional administrative application requirement**, not a universal statutory minimum capital for every locally incorporated company with a foreign shareholder. The rule must distinguish office permission, PI-visa recommendation and work-permit application, and must verify the final BIDA guideline and actual bank evidence.

## Current VAT legislative watch — 18 November 2026

BSS reported that Parliament passed a VAT and Supplementary Duty (Amendment) Bill on 16 November 2026. The report is a discovery lead only: this register does not yet pin an authenticated assent/Gazette artifact or Act number for the post-Ordinance bill. Until the official parliamentary and Gazette records are checked, do not silently assume that Ordinance 38/2026 remains the current section 64 text beyond the parliamentary passage event, and do not treat the news report as a primary legal source. See [BSS report of 16 November 2026](https://www.bssnews.net/js-session/447084).

## Share-transfer stamp duty source chain

The share-transfer duty has a clear schedule transition:
- **Finance Act 2012 (Act 26)**, Gazette 30-Jun-2012, effective 1-Jul-2012 under s.1(2). Section 8 replaced Stamp Act Schedule I; Article 62(a) charged 1.5% of consideration for transfer of shares. Article 62(2) exempted transfers of shares/debentures of public limited companies whose shares were listed.
- **Finance Act 2022 (Act 13)**, Gazette 30-Jun-2022, effective 1-Jul-2022 under s.1(2). Section 3 replaced Schedule I; share transfer was renumbered to Article 61(a), retaining 1.5% of consideration and the listed-public-company exemption in Article 61(2).
- The 2022 Schedule separately charges a **share-sale agreement** under Article 5(b)(ii) at 2 Taka per 1,000 Taka or part thereof of share value. Do not apply the 1.5% transfer-instrument rate to every document in the same transaction.
- Stamp Act s.17 requires an instrument executed in Bangladesh to be stamped before or at execution. Section 35 concerns admissibility until duty and penalty are paid; it does not automatically make the share title void.

## Additional unresolved historical amendment lead

A Government Bangladesh Trade Portal-hosted Companies Act PDF carries a footnote attributing replacement of Companies Act 1994 section 2(2) and section 2(3) to section 7 of the Companies (Amendment) Act, 2005 (candidate Act No. 7 of 2005). The original Gazette artifact, DPP index entry, exact text and commencement clause have not yet been located/authenticated. It is recorded as an unresolved lead only; no date or operative interval is inferred.

## Explicit exclusions

No dates are inferred from publication alone. No current consolidated wording is projected backwards. No rule is marked legally verified by the presence of a source URL. No scoring, runtime, database, migration, production record or release flag is changed by this register.

## Files

- `85_rule_operating_interval_register_v1.json`: all 85 rule records and candidate amendment chains.
- `85_rule_operating_interval_register_v1.schema.json`: structural contract.
- `tests/unit/test_85_rule_operating_interval_register.py`: fail-closed structural tests.
