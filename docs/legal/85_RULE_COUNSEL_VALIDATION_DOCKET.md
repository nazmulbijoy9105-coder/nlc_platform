# NLC Bangladesh 85-rule counsel validation docket

**Repository:** nazmulbijoy9105-coder/nlc_platform  
**Review baseline:** fix/legal-corpus-current-law-reconciliation  
**Prepared:** 7 November 2026  
**Status:** Research docket for independent Bangladesh-qualified counsel; NOT a legal opinion or approval.

## Executive control

The source catalogue contains 85 rule records. The approval register has an empty `approved_rule_ids` allowlist and each rule remains `REVIEW_REQUIRED / score_eligible: false`. Preserve this. The present catalogue's company-type, evidence and reviewer fields are generic placeholders; no claim of full legal validation can honestly be made from those records.

This docket expands the source triage into a separate signed-review record for every ID. It does not invent statutory conclusions, commencement dates, or counsel signatures. A rule is eligible only after the exact proposition, current law, scope, evidence, exceptions, remedy, severity policy and test cases are individually signed.

## Mandatory review protocol

1. Retrieve the official Bangla Gazette text and any official authentic English text; the Bangla promulgated text controls where translation differs.
2. Build chronological amendment history from publication through 7 November 2026, including commencement, retrospective effect, transitional provisions, repeal, savings and corrigenda.
3. State the exact legal proposition in element form: actor + duty/prohibition + trigger + deadline/standard + breach + consequence.
4. Determine applicability from company type, listed status, subsidiary status, sector, employee/factory classification, turnover, registration, transaction and constitutional documents. Do not assume that all 85 rules apply to every private limited company.
5. Define admissible evidence, identity binding, source provenance, verification method and freshness. An absent upload is not proof that a statutory act did not occur.
6. Model exceptions, exemptions, extensions, condonation, court/Registrar orders, appeals, stays, cure periods and procedural preconditions.
7. Separately assess NLC severity, score deduction and override as product policy; a statute does not prescribe NLC's 0–100 score.
8. Approve positive and negative test vectors. The negative tests must demonstrate fail-closed behaviour.
9. Sign each rule separately. No batch or module-level signature silently approves all its rules.

## Review statuses

- `RESEARCH_OPEN`: source or legal proposition not yet established.
- `VALIDATED_WITH_LIMITS`: counsel has signed a precisely bounded scope; only that scope may be activated.
- `VALIDATED`: source, effective date, proposition, applicability, evidence, exceptions and remedy approved.
- `REJECTED`: rule must not activate; preserve reasons.
- `NOT_EVALUATED`: insufficient evidence or unresolved applicability; no compliance conclusion.

## Rule-by-rule signed docket

### ACC-001 — Financial Statements Not Presented at AGM

- **Catalogue anchor:** Section 183, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### ACC-002 — Financial Statements Not Filed with Registrar

- **Catalogue anchor:** Section 190, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### ACC-003 — Books of Account Not Kept

- **Catalogue anchor:** Section 181, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AGM-001 — First AGM Default

- **Catalogue anchor:** Section 81(1), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AGM-002 — Subsequent AGM Default

- **Catalogue anchor:** Section 81(1), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AGM-003 — AGM Short Notice — Consent Verification

- **Catalogue anchor:** Section 85(1)(a), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AGM-004 — AGM Notice or Short-Notice Consent Missing

- **Catalogue anchor:** Section 85(1)(a), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AGM-005 — AGM Quorum Not Met

- **Catalogue anchor:** Section 85(2)(b), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AGM-006 — AGM Minutes Status Requires Verification

- **Catalogue anchor:** Section 89, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AGM-007 — AGM Adjourned Without Proper Notice

- **Catalogue anchor:** Section 85, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AR-001 — Annual Return Default — Single Year

- **Catalogue anchor:** Section 36 (Schedule X), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AR-002 — Annual Return Backlog — Review Required

- **Catalogue anchor:** Section 36 and Schedule X (annual-return duty); Section 346 (separate Registrar strike-off process)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AR-003 — Annual Return Backlog — Extended Review Required

- **Catalogue anchor:** Section 36 and Schedule X (annual-return duty); Section 346 (separate Registrar strike-off process)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AR-004 — Annual Return Filed But Incomplete

- **Catalogue anchor:** Section 36, Schedule X, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AUD-001 — First Auditor Not Appointed Within One Calendar Month

- **Catalogue anchor:** Section 210(6), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AUD-002 — Audit Not Completed Before AGM

- **Catalogue anchor:** Section 183, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AUD-003 — AGM Held Without Completed Audit

- **Catalogue anchor:** Sections 183 and 210, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AUD-004 — Auditor Not Reappointed at AGM

- **Catalogue anchor:** Section 210(3), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### AUD-005 — Subsequent Auditor Reappointment Status Unknown

- **Catalogue anchor:** Section 210(3), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BNK-001 — Winding Up Petition Filed

- **Catalogue anchor:** Companies Act 1994 (Bangladesh), Part V, sections 241–244; exact petition provision and case status require review
- **Source correction (7 Nov 2026):** Corporate company winding-up is governed by Part V of the Companies Act 1994, not the personal Bankruptcy Act 1997. Sections 241–244 address court-winding-up grounds/petition procedure. A petition is not a winding-up order or proof of insolvency without the authenticated case record.
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BNK-002 — Liquidator Appointed

- **Catalogue anchor:** Companies Act 1994 (Bangladesh), Part V; section 255 for court-appointed Official Liquidators; voluntary route requires separate mapping
- **Source correction (7 Nov 2026):** A liquidator appointment must be classified by route. Section 255 addresses court-appointed Official Liquidators; voluntary winding-up appointments arise under separate Part V provisions. Do not apply one section or BLACK status to every appointment.
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BNK-003 — Court-Ordered Winding Up

- **Catalogue anchor:** Companies Act 1994 (Bangladesh), Part V, sections 241–246; exact order provision requires case review
- **Source correction (7 Nov 2026):** Court-ordered company winding-up is a Companies Act Part V process. Require the authenticated order, operative date, jurisdiction, appeal/stay/suspension and current status. Do not cite Bankruptcy Act 1997 or infer the order from a petition.
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BOD-001 — Board Meeting Not Held Within Quarter

- **Catalogue anchor:** Section 96, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BOD-002 — Board Meeting Notice Not Given

- **Catalogue anchor:** Section 95, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BOD-003 — Board Meeting Minutes Not Prepared

- **Catalogue anchor:** Section 89, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BSEC-001 — Quarterly Report Status Requires Verification

- **Catalogue anchor:** Applicable BSEC financial-reporting instrument; exact notification, issuer class, reporting period and due date require verification
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BSEC-002 — CG Certificate Status Requires Verification

- **Catalogue anchor:** BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BSEC-003 — Board Composition Status Requires Verification

- **Catalogue anchor:** BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### BSEC-004 — Audit Committee Status Requires Verification

- **Catalogue anchor:** BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### CAP-001 — Capital Alteration Authority Requires Review

- **Source correction (7 Nov 2026):** Section 53 concerns alteration of share capital subject to Articles authority; section 54 addresses specified consolidation/conversion/subdivision notices; section 56 separately governs increase of registered share capital. The prior claim that s.54 is the generic capital-increase procedure was removed. The exact resolution type must be checked against the Articles and transaction.

- **Catalogue anchor:** Sections 53, 54 and 56, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### CAP-002 — Charge Not Registered With RJSC Within 21 Days

- **Catalogue anchor:** Section 159(1), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### CAP-003 — Capital Reduction — Court Confirmation Review

- **Catalogue anchor:** Sections 59-60, Companies Act 1994 (Bangladesh)
- **Source correction (7 Nov 2026):** The earlier Section 150(1)/(6) citation was a category error: Section 150 concerns commencement of business, not reduction of share capital. The official Companies Act places reduction of share capital in Section 59 and the application for court confirmation in Section 60. The rule remains NOT_COUNSEL_VALIDATED; the exact Articles authority, special-resolution, creditor-notice, court-order and registration steps require rule-level counsel review.
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### CAP-004 — Special Resolution Not Filed With RJSC

- **Catalogue anchor:** Section 88(1), Companies Act 1994 (Bangladesh) — 15 days
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### CHG-001 — Charge Satisfaction Not Filed

- **Catalogue anchor:** Section 172, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DEF-001 — Director Disqualified

- **Catalogue anchor:** Section 94, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DEF-002 — Unresolved Penalty Notices

- **Catalogue anchor:** Case-specific enabling provision required; not a universal section
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DIR-001 — Director Appointment Not Filed Within 14 Days

- **Catalogue anchor:** Section 115, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DIR-002 — Director Departure Not Filed Within 14 Days

- **Catalogue anchor:** Section 115, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DIR-003 — Director Filing Delay — Internal 365-Day Escalation

- **Source correction (7 Nov 2026):** Section 115(2) contains the 14-day Form XII particulars filing duty. The 365-day threshold is NLC internal escalation policy only. The prior assertions of a continuing offence under s.92 and a daily statutory fine were removed; no such consequence is inferred without a separate verified provision.

- **Catalogue anchor:** Section 115, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DIR-004 — Late Director Cessation Filing - Legal Effect Review

- **Catalogue anchor:** Section 115, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DIR-005 — Register of Directors Interests Missing

- **Catalogue anchor:** Section 130, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DIR-006 — Register of Contracts Missing

- **Catalogue anchor:** Section 130, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DIR-007 — Director Consent Not Filed Within 30 Days

- **Source reconciliation (7 Nov 2026):** The Companies Act text distinguishes s.92 pre-appointment consent/eligibility requirements from s.93(2), which requires the signed consent to be filed with the Registrar within 30 days after appointment. The RJSC eBRS FAQ/Form IX materials label Form IX with s.92 while also describing a 30-day post-appointment filing. Do not collapse the form reference and statutory trigger into one unqualified citation. The current 30-day engine rule is provisionally anchored to s.93(2); counsel must confirm the applicable form mapping and any transitional/current RJSC instructions before approval.


- **Catalogue anchor:** Section 93(2), Companies Act 1994 (Bangladesh); section 92/Form IX mapping requires counsel reconciliation
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DIR-008 — Director Holding Office of Profit Without Consent

- **Catalogue anchor:** Section 104, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### DIR-010 — Managing Director Appointed for More Than 5 Years

- **Catalogue anchor:** Section 110, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### ESC-001 — Strike-Off Risk Elevated

- **Catalogue anchor:** Section 346, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### ESC-002 — Strike-Off Status Requires Verification

- **Catalogue anchor:** Section 346, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### ESC-003 — Corporate Rescue Mandatory — Systemic Failure

- **Catalogue anchor:** NLC internal risk policy; not a statutory risk band under the Companies Act 1994.
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### ESC-004 — Voluntary Winding Up

- **Catalogue anchor:** Section 286, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### ESC-005 — Investigation Order Pending

- **Catalogue anchor:** Sections 195 and 197; section 199 where related entities are included, Companies Act 1994 (Bangladesh)
- **Source correction (7 Nov 2026):** Sections 195 and 197 concern Government appointment of inspectors; section 199 concerns extending investigation to related entities/agents. A reported inquiry or investigation is not itself a finding of liability; require the authenticated appointment/order and scope.
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### FX-001 — Foreign Exchange Violation

- **Catalogue anchor:** Foreign Exchange Regulation Act 1947 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### INC-001 — MoA/AoA Registration Status Requires Verification

- **Source correction (7 Nov 2026):** The governing registration provision is section 23, not section 11. The prior assertion that non-production means the company has no valid constitution was removed. NLC absence is a data gap; only an authenticated RJSC search/record can support a verified-absence status.

- **Catalogue anchor:** Section 23, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### INC-003 — Minimum Directors Not Appointed

- **Catalogue anchor:** Sections 90(1) and 90(2), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### INC-004 — Paid-Up / Authorized Capital Mismatch — Legal Review

- **Catalogue anchor:** Section 56, Companies Act 1994 (Bangladesh) — applicability and consequences require lawyer review
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### INC-005 — Encashment Certificate Missing — Foreign Shareholding

- **Catalogue anchor:** BIDA Foreign Investment Act 1980; Bangladesh Bank FDI Circular
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### INC-006 — Remittance Below Work Permit Threshold

- **Catalogue anchor:** BIDA Foreign Investment Act 1980
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### INC-007 — Business Commenced Without Section 150 Declaration

- **Catalogue anchor:** Sections 59-60, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### LBR-001 — Factory License Missing

- **Catalogue anchor:** Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### LBR-002 — Factory License Expired

- **Catalogue anchor:** Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### LBR-003 — Labour Court Order Pending

- **Catalogue anchor:** Bangladesh Labour Act 2006 and the specific Labour Court order; enabling provision and operative status require case-specific verification
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Fail-closed control:** A profile boolean is not the order. Require certified order, party identity, service, operative terms, current status, appeal/revision and stay evidence before any adverse finding. Keep NOT_EVALUATED.
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### MEM-001 — Company Operating with Fewer than Minimum Members

- **Catalogue anchor:** Section 222, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### OFF-001 — Change of Registered Office Not Filed Within 28 Days

- **Catalogue anchor:** Section 77, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### REG-001 — Statutory Registers Incomplete

- **Catalogue anchor:** Section 38(4), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### REG-002 — Core Statutory Registers Missing

- **Catalogue anchor:** Sections 34, 89, 115, 174, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### REG-003 — Registers Not Kept at Registered Office

- **Catalogue anchor:** Section 34(2), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### SH-001 — Share Allotment Not Filed — Form XV

- **Source correction (7 Nov 2026):** Companies Act 1994, s.151 requires the return of allotment and prescribed supporting documents within 60 days after allotment; the section also permits a Registrar extension on timely application. The earlier seed text stating 30 days and citing s.50 was incorrect. Official RJSC eBRS guidance independently lists Form XV within 60 days under s.151. Engine/seed deadline is now 60 days, but the rule remains NOT_EVALUATED and counsel approval is still required.


- **Catalogue anchor:** Section 151, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### SH-002 — Share Certificates Not Issued Within 90 Days

- **Catalogue anchor:** Section 158, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### SH-003 — Capital Increase Not Filed — Form IV

- **Source correction (7 Nov 2026):** Companies Act 1994, s.56 requires notice of an increase in registered share capital within 15 days of the decision to increase the share capital. Official BDLaws text and RJSC eBRS guidance support the 15-day period. The prior engine used the 60-day allotment constant and the seed described a 30-day/s.52 period; this was incorrect. Engine/seed now use 15 days, but the exact event-date field must represent the resolution/decision date and the rule remains NOT_EVALUATED pending counsel review.


- **Catalogue anchor:** Section 56, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### STR-001 — Name Change Not Filed

- **Catalogue anchor:** Sections 11 and 88(1), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### STR-002 — Object Clause Change Not Filed

- **Catalogue anchor:** Sections 12, 15-16 and 88(1), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### STR-003 — AoA Alteration Not Filed

- **Catalogue anchor:** Sections 20 and 88(1), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TAX-001 — TIN Status Requires Verification

- **Catalogue anchor:** Income Tax Act 2023, sections 166, 261 and 264; company-specific duty and evidence require verification
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Fail-closed control:** A profile boolean is not authenticated proof of TIN absence or the company's exact duty. Verify legal entity/taxpayer identity, s.166 return duty, s.261 registration trigger, s.264 proof-of-return requirement, exceptions and operative period. Keep NOT_EVALUATED until independently evidenced.
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TAX-002 — VAT Registration or Turnover-Tax Enlistment Status Requires Verification

- **Catalogue anchor:** Value Added Tax and Supplementary Duty Act 2012, as amended by Act No. 77 of 2026; exact current section and taxpayer-specific instruments require counsel verification
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TAX-003 — Annual Tax Return Overdue

- **Catalogue anchor:** Income Tax Act 2023, Sections 170(2) and 171, as amended by Finance Act 2026 (Act No. 96 of 2026)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TAX-004 — Advance Tax Missed

- **Catalogue anchor:** Income Tax Act 2023, sections 154-157, as amended by Finance Act 2026 (Act 96/2026), sections 87-88
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Current-law correction:** Finance Act 2026 s.87 raises s.154(1) threshold to BDT 10 lakh; s.88 amends s.155(2) and (5). s.156 retains a separately stated BDT 6 lakh new-assessee threshold in the current Act text. Verify A-B computation, source deductions, exclusions, estimates, four instalments and holiday roll-forward. Keep NOT_EVALUATED.
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TL-001 — Trade License Not Obtained

- **Catalogue anchor:** Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TL-002 — Trade License Expired

- **Catalogue anchor:** Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TR-001 — No Share Transfer Instrument — Form 117

- **Source correction (7 Nov 2026):** Section 38(3) requires a proper transfer instrument duly stamped and executed by transferor and transferee, with the relevant certificate, subject to the statutory lost-instrument/indemnity exception. The prior s.108 citation and automatic-void assertion were removed.

- **Catalogue anchor:** Section 38(3), Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TR-002 — Share Transfer Stamp Duty Requires Verification

- **Source correction (7 Nov 2026):** Stamp duty applicability and amount depend on the instrument category, execution facts and current Schedule I/amendments. The prior automatic inadmissibility/unenforceable-title assertions were removed; missing payment evidence is not proof of non-payment.

- **Catalogue anchor:** Stamp Act 1899, Schedule I, Item 62
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TR-003 — Articles-Based Transfer Restriction Review

- **Source correction (7 Nov 2026):** Section 38(7) preserves the company's power under its Articles to refuse registration. Board approval is not a universal statutory requirement; the operative Articles restriction must be verified. The prior s.47 citation and automatic-void/title assertions were removed.

- **Catalogue anchor:** Section 38(7), Companies Act 1994 (Bangladesh), and the company's Articles
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TR-004 — Notice of Refusal to Register Transfer

- **Source correction (7 Nov 2026):** The prior two-month register-update deadline under s.34 was unsupported. The corrected rule is limited to s.38(4): where registration is refused, notice of refusal must be sent to both transferor and transferee within 30 days after lodgement. It triggers only with verified refusal, lodgement date and notice status.

- **Catalogue anchor:** Section 34, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TR-005 — Share Transfer Violates AoA Restriction — Counsel Review

- **Source correction (7 Nov 2026):** Section 38(7) concerns the company's power to refuse registration under its Articles; it does not automatically make every restricted transfer void ab initio. The prior BLACK override, no-title conclusion and unverified court-order/unanimous-ratification assertions were removed.

- **Catalogue anchor:** Section 38; AoA, Companies Act 1994 (Bangladesh)
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### TR-006 — Composite Transfer Record Review

- **Source correction (7 Nov 2026):** Composite transfer-record signals are internal review prompts only. The previous s.47/s.108 references and assertion that each deficiency may independently void a transfer were removed; use sections 34 and 38 plus the operative Articles as applicable.

- **Catalogue anchor:** Sections 34 and 38, Companies Act 1994 (Bangladesh), and applicable Articles
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### VAT-002 — VAT Return Period Requires Verification

- **Catalogue anchor:** Value Added Tax and Supplementary Duty Act 2012, section 64 as amended by Finance Act 2026 and VAT Amendment Ordinance 2026, with applicable VAT Rules/SROs
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Current s.64 rule:** The current consolidated VAT Act text requires filing within 15 days after each tax period; if day 15 is a government holiday, the next working day applies. Government, semi-government and autonomous bodies, banks, insurance and zero-return filers have a 20-day window. Board extensions and taxpayer-specific classification must be checked. This replaced the 1 July 2026 three-tax-period cycle; no overdue calculation is enabled.
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.

### VAT-003 — VAT Annual Return Status Requires Verification

- **Catalogue anchor:** Value Added Tax Act 2012 (Bangladesh); specific annual-return obligation and due date require current-law verification
- **Current seed default severity / score impact / BLACK override:** NOT_EVALUATED / 0 / false (fail-closed pending counsel approval)
- **Catalogue scope:** UNCONFIRMED_REQUIRES_COUNSEL_MAPPING
- **Current review finding:** OPEN — NOT COUNSEL VALIDATED
- **Legal proposition:** NOT YET SIGNED — counsel must state the exact duty, duty-holder, statutory trigger, breach elements and legal consequence in a single testable proposition.
- **Source/effective date:** exact Gazette/Act/SRO/Rule, section/subsection, publication and commencement dates, transitional/repeal effect and review-date consolidation required.
- **Applicability:** determine company type, listed/subsidiary status, sector, employee/factory status, tax/VAT registration, transaction facts, constitutional documents and territorial authority as applicable. Unknown scope = NOT_EVALUATED.
- **Evidence:** obtain authenticated source record and dated company evidence; distinguish VERIFIED_ABSENT from NOT_PRODUCED, UNKNOWN, DISPUTED and REGISTRY_UNAVAILABLE. Preserve issuer, identity, provenance and custody.
- **Exceptions/remedies:** record exclusions, exemptions, extensions, condonation, waiver, court/Registrar orders, appeal/stay, cure and limitation; no adverse finding until checked.
- **Deadline calculation:** identify triggering event, start/end inclusion, calendar/working days, holiday rule, extension and evidence of service/filing.
- **NLC severity approval:** NOT APPROVED. Severity/deduction/BLACK policy is a separate product-risk decision and must not be inferred from the statute.
- **Minimum positive test:** applicable company + proven trigger + reliable evidence + deadline expired/no valid relief + exact legal predicate met.
- **Minimum negative tests:** wrong company class; unknown fact; missing document only; valid extension/condonation; timely filing; appeal/stay/order; inapplicable sector/listing; contradictory evidence.
- **Counsel decision:** PENDING — reviewer, enrolment/chamber, signed date, exact scope and next review required.


## Cross-cutting negative-test matrix (required for every applicable rule)

| Test | Input condition | Expected engine disposition |
|---|---|---|
| N01 | Company type/scope not established | NOT_EVALUATED; no deduction/override |
| N02 | Evidence not uploaded but statutory event may have occurred | NOT_EVALUATED; request evidence |
| N03 | Registry/API unavailable | NOT_EVALUATED; do not infer default |
| N04 | Valid extension, condonation or exemption | No default for the covered period/scope |
| N05 | Court/Registrar order or appeal/stay changes operative status | Apply only after verified order and legal effect |
| N06 | Filing/payment/meeting evidence is timely and authentic | No adverse finding |
| N07 | Conflicting evidence or identity mismatch | DISPUTED / NOT_EVALUATED; human review |
| N08 | Effective date falls outside the rule version | Apply correct historical version; otherwise NOT_EVALUATED |
| N09 | Statutory duty exists but NLC severity policy is unsigned | Legal fact may be described; no score impact |
| N10 | Rule has no exact current-law source or TBD source | Keep disabled |

## Current official-source discovery index

- BDLaws Companies Act 1994: https://bdlaws.minlaw.gov.bd/act-print-788.html
- BSEC Acts, Rules and Regulations / Corporate Governance Code and notices: https://www.sec.gov.bd/act-rules-and-regulations
- NBR Finance Acts (Finance Act 2026 listed 6 July 2026): https://nbr.gov.bd/regulations/acts/finance-acts/eng
- NBR Income Tax Acts (authentic English Income Tax Act 2023 listed 20 November 2025): https://nbr.gov.bd/regulations/acts/income-tax-acts/eng/eng
- NBR Income Tax Rules (includes Withholding Tax Rules 2026 and 6 July 2026 amendment): https://nbr.gov.bd/regulations/rules/income-tax-rules/eng
- NBR Income Tax SROs (2026 notices listed): https://nbr.gov.bd/regulations/sros/income-tax-sros/eng
- NBR VAT Acts: https://nbr.gov.bd/regulations/acts/vat-acts/eng
- NBR VAT Rules (authentic English 2016 Rules listed 20 November 2025): https://nbr.gov.bd/regulations/rules/vat-rules/eng
- NBR VAT SROs (2026 notices listed, including rule amendments): https://nbr.gov.bd/regulations/sros/vat-sros/eng
- Ministry of Labour legislative register: https://mole.gov.bd/pages/legislative-informations
- BDLaws Bangladesh Labour Act: https://bdlaws.minlaw.gov.bd/act-details-952.html?lang=en
- Bangladesh Government Press extraordinary gazettes: https://dpp.gov.bd/bgpress/index.php/document/extraordinary_gazettes_monthly/2026-04-14

The NBR's current site separately lists Finance Act 2026 (6 July 2026), the authentic English Income Tax Act (20 November 2025), and dedicated VAT/Income Tax Rules and SRO directories. Each applicable instrument must be downloaded and mapped; a landing page is not proof that every SRO was reviewed.

- **BSEC scope and condition map:** The 2018 Code is imposed on companies listed on a Bangladesh stock exchange; Condition 2 separately addresses subsidiary-company board governance. Condition 1 governs board composition; Condition 5 the Audit Committee; Condition 8 maintaining a company website; Condition 9 annual corporate-governance certification/reporting. Quarterly financial reporting is not Condition 8. For NLC's private-limited-company product, do not apply the listed-issuer Code universally; subsidiary scope requires separate modelling and evidence.
- **Amendment chronology:** BSEC's 20 November 2023 notification (No. BSEC/CMRRCD/2009-193/66/PRD/148) amended the Code; the 29 April 2024 Gazette (No. BSEC/CMRRCD/2009-193/76/PRD/151) inserted at least one female independent director under Condition 1(2)(a), initially within one year. BSEC's official register lists a further 26 July 2026 extension; published reports state the current deadline is 31 December 2026. Obtain and pin the original 2026 notice before automating the deadline.

## Current research findings requiring counsel confirmation

- BSEC Corporate Governance Code is the 2018 Code as amended by 2023 and 2024 notifications; map conditions 1, 5, 8 and 9 precisely and enforce listed-company scope. Do not call it a generic “Code 2023”.
- VAT threshold work must use the VAT Act as amended by Act No. 77 of 2026: BDT 30 lakh enlistment threshold and BDT 50 lakh registration threshold, subject to the statutory turnover measure and mandatory categories. Finance Act 2026 (Act No. 96 of 2026) then amended several VAT provisions and substituted s.64 from 1 July 2026, requiring filing after every three monthly tax periods (quarterly cycle). VAT Amendment Ordinance 2026 (Ordinance No. 38 of 2026), gazetted 14 October 2026, again substituted s.64 and the consolidated Act footnote records effect from 1 October 2026. The post-1 October regime is therefore the current period-specific return rule; do not leave a quarterly calendar active. Verify exact classes, holiday rule, extensions and transitional treatment from the ordinance text before computing a deadline.
- Company return deadlines must use Income Tax Act 2023 s.170(2) and s.171 as substituted by Finance Act 2026 (Act 96/2026), not the earlier Tax Day formula. For non-individuals the deadline is the 15th day of the ninth month after income-year end, but not earlier than the following 15 September. Holiday roll-forward, extensions, taxpayer class and subsequent amendments still require verification. The NBR lists Finance Act 2026, the authentic English Act and current Rules/SROs separately.
- Labour Act s.326 licensing is conditional on Government directions and establishment/factory class. Read Act No. 43 of 2026 together with the current consolidated Labour Act, Labour Rules and every relevant Gazette direction; do not universalise licensing to all companies.
- Companies Act citation corrections in the source triage remain candidate corrections until each exact statutory text and RJSC form/deadline is verified against official sources and counsel signs.

## Counsel sign-off sheet (one per rule)

| Field | Required entry |
|---|---|
| Rule ID and version | Exact ID, rule version and hash |
| Counsel | Full name, Bangladesh Bar enrolment/chamber and contact |
| Authority | Exact official source URL, Gazette/Act/SRO number and archived copy hash |
| Text | Exact section/subsection/rule/condition and relevant text extract |
| Time | Publication, commencement, retrospective and transitional dates |
| Interpretation | Elements, duty-holder, trigger, breach and consequence |
| Scope | Company class, sector, listing, subsidiary, territorial and transaction conditions |
| Exceptions | Exemption, extension, waiver, condonation, order, appeal, stay and cure |
| Evidence | Documents, issuing authority, identity, authenticity and verification method |
| Tests | Positive and negative case IDs, expected output and actual result |
| Product policy | Severity, score, BLACK override and rationale approved separately |
| Decision | VALIDATED / VALIDATED_WITH_LIMITS / REJECTED / NOT_EVALUATED |
| Signature | Date, signature, next review and amendment-monitoring owner |

## Release rule

Do not populate `approved_rule_ids`, do not set `score_eligible: true`, and do not set `LEGAL_SCORE_RELEASED = true` merely because this docket is complete. Only independent counsel's rule-specific signed decisions plus passing tests and canonical parity can authorise a later release. Any unresolved TBD, unavailable authoritative source, unknown scope or unverified evidence keeps the rule NOT_EVALUATED.


## Primary-source research update — 7 November 2026

Official source locations identified for the next rule-by-rule verification pass:

- Bangladesh Laws consolidated Companies Act 1994: https://bdlaws.minlaw.gov.bd/act-print-788.html
- Companies Act section 38 (transfer instrument, registration and Articles restrictions): https://bdlaws.minlaw.gov.bd/act-788/section-32862.html
- Companies Act section 90 (director-number distinctions by company type): https://bdlaws.minlaw.gov.bd/act-788/section-32914.html
- Companies Act section 158 (share-certificate period): https://bdlaws.minlaw.gov.bd/act-print-788/section-print-33470.html
- Companies Act section 183 (annual accounts and accounting-period rules): https://bdlaws.minlaw.gov.bd/act-print-788/section-print-33572.html
- Companies Act section 241 (winding-up grounds): https://bdlaws.minlaw.gov.bd/act-788/section-33986.html
- Bangladesh Laws Stamp Act 1899: https://bdlaws.minlaw.gov.bd/act-print-77.html
- NBR Finance Acts, Income Tax Acts, VAT Acts, rules and SRO index: https://nbr.gov.bd/regulations/acts/finance-acts and https://nbr.gov.bd/regulations/acts/income-tax-acts
- Ministry of Labour legislative index, including the Bangladesh Labour (Amendment) Act 2026: https://mole.gov.bd/pages/legislative-informations
- BSEC Acts, Rules and Regulations index: https://www.sec.gov.bd/act-rules-and-regulations
- DSE regulations index: https://www.dse.com.bd/regulations

This is source discovery and citation triage, not completed validation. A section link alone does not establish amendment chronology, commencement, transitional effect, exact proposition, entity scope, exception, evidence or remedy. The 85 rule records still require individual dossiers and signed independent counsel dispositions. The approval allowlist remains empty; every rule remains REVIEW_REQUIRED / score_eligible=false.
