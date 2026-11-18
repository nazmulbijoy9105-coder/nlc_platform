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

The Companies Act family has 64 rules in this catalogue. The following official sources have been located and linked in the workpack:

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
