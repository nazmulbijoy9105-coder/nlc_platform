# NLC Continuous Legal Coverage Rebuild

**Status:** architecture baseline for implementation; not a representation that every statutory provision in the catalogue has been independently validated.  
**Product:** Neum Lex Counsel (NLC) — Bangladesh private-company secretarial and compliance workspace.  
**Architecture versions:** rule engine / ILRMF versions remain independent from scoring methodology version.

## 1. Product principle

A company owner needs continuous control over corporate obligations, deadlines, filings, records, evidence and corrective work. A compliance score is a derived summary only.

The authoritative data flow is:

`COMPANY FACTS + EVENTS + EVIDENCE -> APPLICABILITY -> OBLIGATION -> DEADLINE / TASK -> VERIFICATION -> REPORTING`

Scoring consumes verified, eligible findings from this flow. It must never be the source of legal truth.

## 2. Two legal layers

### Layer A — Core private limited company law

| Domain | Company records and events | Obligations / monitoring |
|---|---|---|
| Incorporation | Certificate, company number, MoA, AoA, incorporation date, amendments | Registration and constitutional-document verification |
| Membership | Members, addresses, share classes, dates admitted/ceased, beneficial ownership where legally applicable | Register of members; ownership history and annual-return reconciliation |
| Share capital | Authorised and paid-up capital, class rights, allotments, consideration, resolutions | Authority for capital changes, return of allotment, capital-increase filing |
| Share transfers | Transferor/transferee, instrument, stamp evidence, board/Articles process, register update, certificate cancellation/issue | Transfer registration, refusal notice, title-chain and certificate consistency |
| Directors | Identity, appointment, consent, effective date, cessation, eligibility, Articles, board composition | Consent, statutory particulars/Form XII, changes and evidence |
| AGM | Financial years, AGM dates, notices, service, consents, attendance, quorum, Articles, minutes | First/subsequent AGM deadlines, notice, quorum, minutes, annual-return dependencies |
| Board | Directors at each date, notices, dispatch/receipt, attendance, resolutions, minutes | Meeting frequency, notice, quorum, conflicts, records |
| Auditor | Appointment instrument, eligibility, term, AGM decisions, resignation/removal, notices | First appointment, subsequent appointment/reappointment, audit and reporting |
| Accounts | Accounting period, books, financial statements, approval, signatures, AGM presentation | Books, statements, approval, presentation and filing |
| Annual returns | Schedule X source data, AGM, members/directors/share capital snapshots, filing receipt | Section 36 / Schedule X filing and year-by-year backlog |
| Statutory registers | Members, directors, charges, minutes and custody/location | Separate internal record duties; never infer RJSC filing from missing internal book |
| Charges | Instrument, creation/modification/satisfaction dates, creditor, security, registration/receipt | Registrability, filing, modification and satisfaction |
| Registered office | Registered address, occupation evidence, board decision, effective date | Change notification, filing and service continuity |
| Winding-up | Petition, court, case number, orders, liquidator, notices, restoration | Corporate winding-up stages and statutory filings; distinct from personal bankruptcy |

### Layer B — Conditional obligations

Every conditional obligation must have an explicit applicability predicate, supporting company facts, exception handling and effective date.

| Domain | Activation facts (examples) | NLC treatment |
|---|---|---|
| Income tax / NBR | Taxpayer identity, income year, taxable status, return duty, applicable exemptions | Track registration, return periods, payments and proof; unknown status is UNKNOWN |
| VAT / supplementary duty | Taxable activity, turnover, supplies, mandatory-registration class, exemptions | Version thresholds and deadlines by effective-dated Act, Finance Act, SRO and NBR order |
| Labour | Establishment type, worker count, sector, factory status, Government direction | Activate only for the covered employer/establishment and applicable provisions |
| Trade licence | Place of business, local authority, activity and licence class | Track authority, validity, renewal and receipt |
| Fire / environment / sector licences | Premises, activity, capacity, sector and statutory thresholds | Conditional licence register and renewal calendar |
| Foreign investment / FX | Foreign shareholders, remittances, investor category, bank and BIDA records | Apply current GFET/BIDA instruments to the actual transaction |
| Bangladesh Bank | Regulated entity, bank relationship, foreign exchange or regulated activity | Do not apply prudential rules to an ordinary private company solely because it has a bank account |
| BSEC | Listed issuer, securities issuance, regulated instrument or other statutory trigger | Never activate for every private company |
| Court / regulator directions | Authenticated order, addressee, service date, scope and operative period | Company-specific obligation with deadline and order evidence |

## 3. Authoritative company workspace

### Company records
- Company profile and incorporation
- Shareholders, beneficial ownership where applicable, and shareholding history
- Directors and appointment / cessation history
- AGM and board meeting history
- Financial year, books and accounts
- Auditor details, appointment and audit history
- RJSC filing history and receipts
- Statutory registers and custody
- Tax, VAT and conditional licences

### Compliance operations
- Upcoming and overdue obligations
- Evidence and document vault
- Filing preparation, submission status and receipts
- Legal changes affecting this company
- Lawyer / professional assignments
- Rescue and regularization
- Annual compliance report

### Event-driven operation
The following company events must recalculate affected obligations and dependent deadlines:
- incorporation or constitutional amendment;
- director appointment, consent, resignation, removal or death;
- share allotment, transfer, capital change or certificate issue;
- AGM / board meeting scheduled, held, adjourned or cancelled;
- financial-year close, accounts approval and audit completion;
- charge created, modified or satisfied;
- registered-office change;
- tax/VAT/licence applicability facts change;
- court or regulator order received;
- filing submitted, accepted, rejected, corrected or withdrawn.

A filing task is not complete merely because a user clicks “filed”. Completion requires the applicable filing identity, company, form/period, submission date, acknowledgement/receipt and verification state.

## 4. Canonical obligation model

Each obligation definition must carry:

1. stable rule ID and independently versioned rule definition;
2. legal domain, Act/rule/order, exact section/subsection and source URL/document;
3. provision status: VERIFIED, RECONCILE, DISPUTED or SUPERSEDED;
4. actual duty, responsible legal person and recipient/authority;
5. applicability predicate and statutory exceptions;
6. triggering event and deterministic deadline calculation;
7. required evidence and acceptable evidence types;
8. evidence status, source, provenance, uploader, verifier and timestamps;
9. obligation lifecycle state and legal assessment;
10. dependencies, linked records and related rule IDs;
11. scoring eligibility / category / maximum contribution;
12. rescue template and explicit no-action disposition;
13. effective-from / effective-to dates and supersession relationship.

A rule definition is not a company obligation instance. The same rule may create separate annual obligations for different financial years or different event instances. Every obligation instance therefore needs a stable `obligation_id`, `event_id`, period/subject key, trigger date, calculated deadline and source rule version.

## 5. Evidence and legal state semantics

Use distinct states; do not collapse them into a boolean:

- `VERIFIED_PRESENT`: authenticated evidence proves the required fact/document exists.
- `VERIFIED_ABSENT`: an adequate, documented verification establishes absence.
- `UNKNOWN`: evidence has not been obtained or checked.
- `CONTRADICTORY`: reliable evidence conflicts.
- `DISPUTED`: legal interpretation or source text is materially disputed.
- `NOT_APPLICABLE`: applicability predicate is established false or a statutory exception applies.
- `REQUIRES_LAWYER_JUDGMENT`: facts exist but legal consequence needs case-specific judgment.
- `COMPLIANT` / `NON_COMPLIANT`: legal assessment after applicability, exceptions and evidence.

Missing upload != verified absence. A self-reported profile boolean != authenticated filing evidence. A filing default != invalid appointment, title defect or automatic personal liability.

## 6. One remediation record per finding

Every actionable finding must create one remediation record, or an explicit `NO_ACTION_REQUIRED` disposition with a reason. Required fields:

- remediation ID and obligation/finding ID;
- rule ID and exact statutory provision;
- actual legal obligation and legal assessment;
- verified evidence and missing/contradictory evidence;
- corrective action and required documents;
- responsible lawyer/professional and company owner;
- statutory deadline and internal target date (separate fields);
- dependencies and prerequisite actions;
- filing fees and professional costs (estimate/source/status);
- filing/authority and submission status;
- completion evidence and receipt;
- independent reviewer and review timestamp;
- final verification result, closure reason and audit history.

Rescue generation must not itself create commercial engagement or grant permission. Engagement, assignment, task creation and rescue-plan generation remain separate actions with their own authorization.

## 7. Scoring specification

### Versioning
- Statutory rule version: tracks the legal rule definition and source.
- Rule-engine / ILRMF version: tracks evaluator implementation and coverage.
- Scoring specification version: tracks category caps, allocation, scoring eligibility semantics and arithmetic.
- Product release switch: owner-controlled product configuration; not a claim of legal certification.

The initial authoritative customer-facing scoring specification is `canonical_architecture/scoring_spec.py`, version `2.0.0`.

### Headline score
`final_score = 100 - sum(applied_category_deductions) - risk_policy_override_adjustment`

The applied category deductions are allocated in a stable order after each category cap, with a global 100-point deduction budget. Therefore:

`sum(applied_category_deductions) <= 100`

`sum(applied_category_deductions) + risk_policy_override_adjustment + final_score = 100`

The policy override adjustment is reported separately; it is not a statutory deduction or legal penalty. A RED/BLACK operational classification is not a legal liability finding.

### Categories and nominal caps
| Category | Maximum |
|---|---:|
| Tax / VAT | 15 |
| AGM | 30 |
| Audit | 25 |
| Annual returns | 20 |
| Directors and related corporate identity rules | 25 |
| Shareholding / transfers | 20 |
| Capital / accounts / charges | 15 |
| Registered office | 10 |
| Registers | 10 |
| Corporate winding-up | 20 |
| Labour | 10 |
| BSEC | 15 |
| Foreign exchange | 10 |
| Internal escalation | 15 |
| **Nominal category capacity** | **240** |

Nominal category capacity is not the customer score denominator. It is the pre-global-cap ceiling. Applied category deductions are limited to the 100-point base. The 14 category deductions are the reconciled score components.

Legacy module scores (currently with nominal maxima totalling 125) are diagnostics only. They must be explicitly labelled **non-additive** and must not be displayed as components of the headline score. The API now exposes the scoring spec version and a reconciliation object; callers must use its category deductions for additive score display.

### Scoring invariants
1. Only active, applicable, confirmed findings admitted by the product allowlist can deduct points.
2. UNKNOWN, NOT_APPLICABLE, DISPUTED, CONTRADICTORY and REQUIRES_LAWYER_JUDGMENT deduct zero.
3. Excluded rule IDs deduct zero.
4. Per-category caps and global cap apply once, deterministically.
5. Duplicate rule triggers for the same underlying event must share one `event_id` / `obligation_id`; one event must not be penalized twice. Distinct years or distinct transactions remain distinct instances.
6. Authorized internal BLACK override is separate from statutory deductions and is recorded as a policy adjustment.
7. Risk severity and statutory legal state are separate dimensions.
8. The score hash includes the scoring spec version and exact allocation.
9. Historical score snapshots remain immutable when the scoring spec changes.
10. Independent golden examples cover compliant, unknown, not-applicable, verified-absent, category-cap, global-cap, duplicate-event, excluded-rule and policy-override cases.

## 8. Legal source and defect reconciliation backlog

The rule catalogue must be reconciled against the current official text, amendments, rules, Gazette instruments and applicable Articles before a provision is labelled VERIFIED. The current implementation must not silently convert the following known issues into established law:

| Rule / area | Reconciliation required |
|---|---|
| AGM-005 | Section 85(2)(b) quorum; calculate default by company/member count and check Articles before determining breach |
| AGM-007 | Exact adjournment provision, Articles, notice and statutory consequence |
| AUD-003 | Remove Section 151 if used as an audit duty; distinguish audit completion/reporting from return-of-allotment filing |
| AUD-004 / AUD-005 | Separate auditor reappointment, new appointment, notification and evidence duties |
| DIR-005 | Section 130 interest disclosure is not a generic register-of-contracts rule |
| DIR-006 | Keep review-only until an exact statutory / Articles obligation and contract class are established |
| DIR-007 | Reconcile director consent, Section 92, Section 93(2), Form IX and actual filing requirements |
| INC-007 | Apply Section 150 only after checking private-company exclusion and exact company status |
| SH-001 | Allotment return, Section 151, supporting documents and deadline; distinct from capital increase |
| SH-002 | Share certificate issue and Section 158 deadline; do not conflate with allotment filing |
| SH-003 | Increase of registered share capital and Section 56; separate trigger and filing |
| BNK-001/002/003 | Corporate winding-up, petition, liquidator and court order are distinct stages; never label these personal bankruptcy |
| REG-002 | Internal member/charges/minutes records must be separate from director particulars/Form XII RJSC filing |
| DIR-001 | Form XII filing event and director appointment validity are separate questions |
| TAX/VAT | Effective-date all thresholds and deadlines against the operative Finance Act, amendment Act, SRO and NBR order |
| BSEC | Explicit listed/issuer/securities applicability predicate; no blanket private-company activation |
| Foreign exchange | Activate by foreign investor/remittance/transaction facts and operative GFET/BIDA instruments |

Known source starting points:
- Laws of Bangladesh official portal: https://bdlaws.minlaw.gov.bd/
- Government Press Gazette archive: https://www.dpp.gov.bd/bgpress/
- NBR Acts, Rules, SROs and General Orders: https://nbr.gov.bd/regulations/
- RJSC official portal and forms: https://roc.gov.bd/

Source records must store the exact instrument, publication date, effective date, source document hash and supersession chain. A website page or secondary commentary alone is not sufficient evidence of a legal change.

## 9. Implementation sequence

### Phase 1 — scoring integrity (this branch)
- establish scoring spec independent of statutory rule version;
- reconcile all per-finding and category deductions;
- make the global 100-point budget explicit;
- separate BLACK policy override adjustment;
- expose immutable score reconciliation and add golden tests.

### Phase 2 — canonical legal catalogue
- reconcile existing catalogue and seed corpus by stable rule ID;
- normalize provision/source metadata and applicability predicates;
- correct the named AGM/AUD/DIR/INC/SH/BNK defects;
- preserve legacy IDs and historical records;
- build domain coverage and source-completeness audit.

### Phase 3 — company facts and event history
- authoritative shareholder, director, meeting, accounts, auditor, filing, register and licence records;
- event/obligation instance IDs and immutable evidence provenance;
- effective-dated company facts and historical snapshots.

### Phase 4 — obligation calendar and legal-change monitoring
- deterministic deadlines and dependencies;
- reminders, filings, receipts, renewals and overdue workflows;
- effective-dated legal updates with company-specific impact review.

### Phase 5 — remediation, assurance and reporting
- one remediation/no-action disposition per finding;
- assignments, documents, costs, review and completion evidence;
- annual compliance report and due-diligence-ready corporate history.

### Phase 6 — product workspace
- owner dashboard focused on upcoming obligations, overdue work, open legal reviews, pending filings and unresolved record changes;
- score as a secondary indicator with clear coverage and evidence limitations.

## 10. Release acceptance criteria

- Every active rule maps to a legal domain, source, applicability predicate, evidence contract and evaluation state.
- No conditional rule applies without a proven activation fact.
- Every deadline is traceable to a trigger, source provision and calculation.
- Every finding has one remediation or explicit no-action disposition.
- Every filing can be traced from preparation to verified receipt.
- Unknown evidence never becomes a proven violation or deduction.
- Every score component reconciles exactly to the final score, including any separate NLC policy adjustment.
- Legal rule, engine and scoring versions are independently visible in score snapshots.
- Golden legal/evidence examples and full rule/seed/API parity checks pass.
- Tenant isolation applies to every company record, document, filing and obligation.
