# 85-rule statutory source and evidence workpack

**Status:** research workpack; not a legal opinion, not counsel approval, not a scoring release.
**Rule inventory:** exactly 85 canonical rule IDs.
**Release effect:** none.

## What this workpack adds

`85_rule_source_and_evidence_workpack_v1.json` joins the canonical 85-rule catalogue to the current canonical statutory-registry claim, applicability-model fact candidates, and evidence-model candidates. It deliberately retains the distinction between:

- the rule's recorded seed/catalogue statutory basis;
- the current canonical registry's law/provision/requirement text;
- an official source document located by research;
- a rule-specific legal conclusion that still requires independent counsel.

The file is an evidence-intake and reconciliation workpack, not a machine-generated legal approval.

## Primary Companies Act instruments now pinned

The Companies Act family has 66 rules in this catalogue when AR-002 and AR-003 are resolved to the Companies Act source family through their current canonical source claims; their recorded catalogue bases omit the Act title. The following official sources have been located and linked in the workpack:

1. **Companies Act, 1994 (Act XVIII of 1994).** Official consolidated Bangla text: https://bdlaws.minlaw.gov.bd/act-print-788.html. Section 1 records commencement on 1 December 1994 by SRO No. 321-Law/1994 dated 10 November 1994. The original SRO Gazette artifact is pinned at https://www.dpp.gov.bd/upload_file/gazettes/321-Law-1994.pdf.
2. **Companies (Amendment) Act, 2020 (Act No. 7 of 2020).** Official text: https://bdlaws.minlaw.gov.bd/act-print-1308.html. Section 1(2) says immediately effective; publication date 25 February 2020. Gazette copy: https://bdlaws.minlaw.gov.bd/upload/act/2020-10-28-11-09-18-Act-No-7-of-2020.pdf. It amended, among other things, s.85(2)(ch) by removing the common-seal wording. That is not the amendment which changed the 21-day meeting notice.
3. **Companies (Second Amendment) Act, 2020 (Act No. 24 of 2020).** Official text: https://bdlaws.minlaw.gov.bd/act-print-1353.html. Section 1(2) says immediately effective; publication date 26 November 2020. Official Gazette copy: https://www.dpp.gov.bd/upload_file/gazettes/37932_40268.pdf. It amended s.85(1), including replacing fourteen with twenty-one days, and inserted s.38(3A), among other changes.

The dates above are instrument-level facts. They do **not** by themselves establish the effective interval, applicability or interpretation of every NLC rule. Each rule still needs clause-level amendment mapping, transitional/savings analysis, repeal/corrigendum screening and a signed counsel decision. The workpack therefore leaves rule-specific `effective_from` and `effective_to` null.

## Rule identity and statutory citation conflict handling

The workpack preserves both the recorded catalogue basis and the current canonical registry claim. Example: AGM-005's recorded catalogue basis says s.89, while the current canonical statutory registry says s.85(2)(b), read with the Articles. The conflict is retained, not silently overwritten. The current candidate is not counsel-approved.

INC-001's known source-definition conflict and INC-002's legacy quarantine remain governed by the canonical identity/provenance controls; this workpack does not create or reassign UUIDs or historical findings.

## Fact/evidence coverage found in source code

At the base commit recorded in the JSON:

- 43 of 85 rules have an entry in `canonical_architecture/evidence_model.py`.
- 41 of 85 rules have an entry in `canonical_architecture/applicability_model.py`.
- A mapping entry is not proof of legal sufficiency, correct issuer, admissibility, completeness or evidence-to-fact linkage.
- Evidence types are retained as candidates. Each has an expected issuer class, proposed collection procedure and verification standard, all explicitly marked unverified.
- Required facts are kept as individual records. The builder must not link every document to every fact. A rule-specific link must say exactly which evidence proves which fact, for which date/entity, and what evidence proves the contrary state.

AGM-005 has a specific candidate fact map for its nine required facts: company type, meeting held, member count, members present, attendance verification/reference, quorum basis verification/reference and required quorum. The candidate sources include the Articles in force on the meeting date, register of members, signed minutes and original attendance register. These are candidate mappings only; the company custodian, authenticity, completeness, and sufficiency must be independently verified.

## Minimum evidence capture protocol

For every evidence item, capture:

- issuer legal name and issuing office/registry;
- issuer record ID, document/form type and version;
- company registration number and entity identity;
- event date, execution date, submission date, acceptance/registration date, effective date and retrieval/knowledge date as separate fields;
- original file or issuer response, source URL/channel and retrieval timestamp;
- signature/seal/QR/digital verification result and verification endpoint;
- custodian, collector, reviewer and chain-of-custody events;
- SHA-256 digest of the original bytes;
- current status, amendments, correction/rejection, appeal/stay/variation and expiry;
- contradictions, missing pages, illegible content and unresolved questions.

### Evidence source classes

- **RJSC records and forms:** obtain from RJSC's official registry/filing channel or certified extract. Distinguish submitted, received, accepted, rejected and registered.
- **Company statutory records:** obtain original/certified minute books, registers, Articles, resolutions and notices from the authorised company custodian; verify execution and contemporaneous entries. Company uploads alone are assertions until authenticated.
- **Audit evidence:** verify signed auditor report and auditor identity/eligibility independently; distinguish auditor report from RJSC filing receipt.
- **Court/tribunal evidence:** certified copy or verifiable court-issued electronic record; check appeal, stay, variation, discharge and current status.
- **BSEC evidence:** signed notification/order or issuer filing from BSEC's official channel; verify issuer scope and current amendments.
- **NBR evidence:** taxpayer-specific certificate, return receipt, challan or account extract from official NBR channel; verify TIN/BIN and tax period.
- **Bank/remittance evidence:** original bank-issued advice/certificate and independent confirmation from the authorised-dealer bank; check the circular effective on the value date.
- **Labour/licensing/local authority evidence:** licence, inspection or order from the competent authority for the actual establishment and location; verify scope, issue/expiry and current status.

These are collection protocols and expected issuer classes, not a claim that any evidence source has already been authenticated. The workpack records zero independently verified issuers.

## Required completion before any rule can be released

For each of the 85 rules, close all of the following:

1. Resolve immutable historical source namespace and definition; preserve conflicts.
2. Retrieve original Bangla Act/Rule/Order and every applicable Gazette amendment, SRO, commencement notification, corrigendum, repeal, saving and transitional instrument.
3. Record exact provision/subsection and old/new text; publication and commencement dates separately.
4. Establish the legal-validity interval for the exact proposition and the NLC knowledge interval.
5. Sign company/entity scope, trigger, facts, exceptions, relief, deadline calculation and legal consequence.
6. Identify each fact's authoritative source and one-to-many evidence relation; do not leave any required fact without a mapped evidence role.
7. Verify issuer identity, collection channel, authentication method, freshness, evidence standard and contradiction procedure.
8. Run positive and negative tests against the signed rule payload and pin the evaluator version/hash.
9. Obtain independent Bangladesh-qualified counsel's rule-specific signature and separate product-owner scoring decision.

Until then, `legal_review=REVIEW_REQUIRED`, `product_decision=NOT_REVIEWED`, and `score_eligible=false` remain mandatory.

## Validation

The unit test `tests/unit/test_85_rule_source_evidence_workpack.py` checks the 85-ID inventory, fail-closed release fields, unverified issuer status and preservation of the AGM-005 historical/canonical citation conflict. It validates the integrity of this workpack; it does not validate the underlying legal conclusions.


## Additional statutory families identified for the 19 non-Companies-Act rules

The workpack now attaches official source candidates for these families. They are source-discovery results, not complete amendment histories or legal approvals:

- **BSEC-001–004:** BSEC Corporate Governance Code 2018 and official 2023/2024 amendment sources. BSEC-001 still has a citation mismatch: the catalogue says Code 2023 paragraph 8 while the canonical registry says a financial-reporting instrument. BSEC-004's catalogue says FERA 1947 although its name and canonical source claim point to the BSEC Audit Committee condition. Both conflicts remain open.
- **FX-001:** Foreign Exchange Regulation Act 1947, Bangladesh Bank GFET 2018 and later Bangladesh Bank circulars/portal material.
- **INC-005:** GFET 2018 Chapter 9 paragraph 2(A), Bangladesh Bank FE Circular No. 10 (21 June 2023) and FEID Circular No. 1 (27 January 2025), plus subsequent relevant circulars. A 2025 Bangladesh Bank circular confirms later changes to the reporting and temporary FC-account process; rule-specific applicability must be reconciled.
- **INC-006:** BIDA's official resource index identifies the 2023 foreign commercial office/work-permit guideline, but the exact guideline bytes, operative clauses, version and amendment history remain unpinned.
- **LBR-001–003:** Bangladesh Labour Act 2006, Labour (Amendment) Ordinance 2025 and Labour (Amendment) Act 2026. The current canonical candidate for LBR-001/002 is s.326(1)(b) with Labour Rules 2015 rr.354–355, while the seed basis says s.35. This is a material citation conflict; the exact licensing trigger and establishment scope must be validated.
- **TAX-001/003/004:** Income Tax Act 2023 and Finance Act 2026. TAX-003's canonical candidate is ss.170(2) and 171, not the older catalogue s.75 anchor. TAX-004's canonical candidate is ss.154–157 as amended by Finance Act 2026; tax period, taxpayer class and transitional rules remain open.
- **TAX-002 / VAT-002 / VAT-003:** VAT and Supplementary Duty Act 2012, VAT Amendment Act 2026 (Act 77), Finance Act 2026 (Act 96) and VAT Amendment Ordinance 2026 (Ordinance 38). The Ordinance 38 source records a new s.64 and an effective date indicated as 1 October 2026; rule-specific tax period, return class, holidays, extensions and savings must be reconciled.
- **TL-001/002:** Local Government (City Corporation) Act 2009 and Local Government (Paurashava) Act 2009, with the City Corporation (Amendment) Act 2026. The actual local authority depends on the company's premises; these are alternative jurisdictional routes.
- **TR-002:** Stamp Act 1899. Exact Schedule I item, current rate, execution-date version and all subsequent amendments remain open.

The source workpack's coverage counters are deliberately explicit: 43/85 evidence-model entries and 41/85 applicability-model entries; zero independently verified evidence issuers; zero complete fact-to-evidence maps; zero legally approved rules. Do not interpret the number of source URLs as proof that every amendment or Gazette has been screened.


## Expanded fact inventory and candidate evidence mapping

The workpack now also captures the current `scripts/seed_rules.py` claim and `rule_condition.data_points` for all 85 rules. This yields 246 seed fact candidates; when combined with applicability-model facts, the workpack contains 292 rule-specific fact records across all 85 rules.

Each fact record now has a candidate evidence contract. Candidate roles are generated from the fact's domain and existing evidence model, including expected issuer class, collection procedure and verification standard. The current workpack contains 283 candidate evidence roles across all 85 rules. 21 fact records still have an unresolved evidence type and are explicitly marked for rule-specific legal/custodian mapping.

**Important:** this is a complete inventory of candidate fact/evidence contracts, not a completed verified evidence system. The 43 evidence-model entries are curated source-code mappings; the additional candidate links are domain-based drafts. None of the issuer classes has been independently verified against the issuing authority, none of the candidate links has been signed off by counsel, and none of the evidence standards has been proven against real issuer-origin records. The verified counts remain zero.
