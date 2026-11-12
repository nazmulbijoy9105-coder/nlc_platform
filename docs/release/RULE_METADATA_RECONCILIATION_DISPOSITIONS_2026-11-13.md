# Rule metadata reconciliation dispositions — 13 November 2026

## Scope and decision standard

This register assigns a controlled disposition to every field-level difference in the production audit CSV. It is a **triage and change-control decision register**, not a signed legal opinion. A disposition tells the implementation team what to do next; it does not by itself authorize a production write or establish that a statutory proposition is correct.

- Comparison baseline: main `95223789e7ecf581ff514d2e49ce9db76daab4cb`; production Alembic revision `0110_legal_provenance_acl`.
- Compared: nine fields from `tools/audit_rule_parity.py::DB_PARITY_FIELDS`.
- 85 seed definitions; 85 active DB rules; one inactive historical `INC-002` row.
- 269 active-ID field differences, plus one separate historical identity row.
- The DB remains the live inventory source for this audit; the seed is not automatically declared legally canonical.

## Disposition counts

- `REWRITE_WITH_SOURCE`: **69**
- `REQUIRES_PRODUCT_OWNER_DECISION`: **142**
- `KEEP_SEED`: **51**
- `KEEP_DATABASE`: **8**

## Meaning of dispositions

- `KEEP_SEED`: retain the seed value for now because it is materially more cautious in its customer-facing claim. This is not legal validation.
- `KEEP_DATABASE`: retain the DB value for now because it contains an explicit evidence/verification qualifier or preserves an inactive historical identity. This is not legal validation.
- `REWRITE_WITH_SOURCE`: neither citation is accepted; reconstruct from controlling primary text, amendments, commencement and effective date, then obtain counsel sign-off.
- `REQUIRES_PRODUCT_OWNER_DECISION`: behavior, taxonomy, commercial routing or wording cannot safely be inferred from the two values.

## Hard stop: no blanket migration

**No production metadata write is authorized by this register.** The seed docket states that all 85 rules remain open for independent Bangladesh-qualified counsel review. Product-owner approval, rule verification, legal-source registration, and scoring eligibility are separate states.

Before any metadata migration:
1. Resolve every `REWRITE_WITH_SOURCE` row with official gazette/official consolidated text, provision, amendment chain, commencement and effective interval.
2. Resolve every `REQUIRES_PRODUCT_OWNER_DECISION` row with the evaluator function, fact schema, evidence gates, exceptions and regression tests.
3. Re-check every `KEEP_SEED`/`KEEP_DATABASE` choice against the underlying code and actual customer-facing use.
4. Obtain independent counsel signatures per rule, not per module.
5. Preserve rule IDs, inactive `INC-002`, owner-release ledger, legal verification status and historical snapshots.
6. Only then create a forward-only migration and run full production DB/API/engine/seed parity.

## Official-source starting points

These are source-discovery starting points, not proof that every rule's cited provision is correct or that the source is the latest controlling consolidation:
- Companies Act 1994 (official Bangladesh Laws): https://bdlaws.minlaw.gov.bd/act-print-788.html
- Income Tax Act publications (NBR): https://nbr.gov.bd/regulations/acts/income-tax-acts/eng/eng
- VAT Acts and regulations (NBR): https://nbr.gov.bd/regulations/acts/vat-acts/eng/contents/eng
- Bangladesh Labour (Amendment) Act 2026 (Government Press Gazette listing): https://www.dpp.gov.bd/bgpress/index.php/document/extraordinary_gazettes_monthly/2026-04-02
- BSEC Act/rules/notifications: https://sec.gov.bd/act-rules-and-regulations
- Bangladesh Bank foreign exchange guideline portal: https://www.bb.org.bd/en/index.php/about/guidelist

The register deliberately marks source URIs as `PRIMARY_SOURCE_NOT_YET_VERIFIED` where an authoritative source was not established in this pass. It does not infer statutory text from unofficial summaries.

## Automated coverage gate

`tests/unit/test_rule_metadata_reconciliation.py` requires exact one-to-one coverage between the original mismatch CSV and this disposition register, rejects duplicate/missing pairs and unknown dispositions, and checks that no historical ID is silently converted into an active rule.
