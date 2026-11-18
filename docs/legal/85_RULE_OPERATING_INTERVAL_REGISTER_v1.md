# 85-rule provision-level amendment and operative-interval register

**Snapshot:** 2026-11-18  
**Status:** fail-closed research register; not a legal opinion or score-release approval.

## What this register establishes

This register normalises all 85 canonical rule candidates, their recorded provision candidates, parent instruments, and amendment/related-instrument candidates from the v1 workpack. It also defines issuer/document authentication and interval-construction standards, and pins three Companies Act Gazette anchors to the Bangladesh Government Press index and Gazette artifacts.

It deliberately does **not** claim that all 85 histories are complete. At this snapshot:
- 85/85 amendment histories remain open and non-exhaustive.
- 74/85 rules have at least one provision candidate; 11/85 do not.
- 0/85 rule-specific operative intervals are legally resolved.
- 0 issuer/document records have independent counsel authentication recorded.
- 0 artifact SHA-256 values have been captured from downloaded original bytes.
- 0 rules have counsel approval.

## Primary-record anchors located

1. **Companies Act 1994 commencement SRO:** Government Press November 1994 index lists SRO No. 321-Law/94, dated 10 November 1994, Ministry of Commerce, p.5033. The Companies Act section 1 footnote records commencement on 1 December 1994. The DPP-hosted one-page PDF is linked. Its extracted text is garbled, so page-image/certified-copy comparison remains required.
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

## Additional unresolved historical amendment lead

A Government Bangladesh Trade Portal-hosted Companies Act PDF carries a footnote attributing replacement of Companies Act 1994 section 2(2) and section 2(3) to section 7 of the Companies (Amendment) Act, 2005 (candidate Act No. 7 of 2005). The original Gazette artifact, DPP index entry, exact text and commencement clause have not yet been located/authenticated. It is recorded as an unresolved lead only; no date or operative interval is inferred.

## Explicit exclusions

No dates are inferred from publication alone. No current consolidated wording is projected backwards. No rule is marked legally verified by the presence of a source URL. No scoring, runtime, database, migration, production record or release flag is changed by this register.

## Files

- `85_rule_operating_interval_register_v1.json`: all 85 rule records and candidate amendment chains.
- `85_rule_operating_interval_register_v1.schema.json`: structural contract.
- `tests/unit/test_85_rule_operating_interval_register.py`: fail-closed structural tests.
