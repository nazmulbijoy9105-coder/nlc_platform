# Bangladesh Companies Act, Schedules, Rules, RJSC Forms & NLC Services Master Matrix

**Audit date:** 13 November 2026  
**Repository:** `nlc_platform`  
**Status:** RESEARCH / COVERAGE TRIAGE — NOT A COUNSEL OPINION  
**Product scope:** Bangladesh private companies limited by shares, with conditional pathways explicitly separated  
**Release effect:** NONE. This document does not activate rules, scoring, reminders, filings or legal conclusions.

## 1. Executive determination

The current 85-rule NLC catalogue is a product rule inventory, not proof of complete coverage of Bangladesh company law. The repository's own master rulebook says the catalogue is not exhaustive. This matrix therefore distinguishes:

- **IDENTIFIED** — a legal topic, schedule, form or service has been located.
- **SOURCE_PENDING** — the primary instrument, current amendment chain or complete text has not yet been pinned.
- **COUNSEL_REQUIRED** — legal proposition, applicability, exception or consequence needs independent Bangladesh counsel approval.
- **CONDITIONAL** — only applies when a specified company type, transaction, sector, licence, order or other trigger exists.
- **OUT_OF_SCOPE_DEFAULT** — not enabled for an ordinary private company without a proven trigger.
- **IMPLEMENTATION_CHECK** — compare the legal requirement to NLC's actual code, database and customer workflow.
- **NOT_A_STATUTORY_SERVICE** — a professional/commercial service may be useful but is not itself a statutory obligation.

No row below is approved for autonomous legal determination merely because it appears in a statute, RJSC portal, this matrix or a test.

## 2. Source hierarchy and limits

1. Authentic Bangla text of the Companies Act 1994 and amending Acts / Ordinances in the official Bangladesh Laws database.
2. Gazette instruments, commencement notifications and applicable rules made under the Act.
3. Current prescribed forms and official RJSC filing instructions; useful for operational process, but an FAQ does not override the Act.
4. The company's registered Memorandum and Articles, certified registry records, resolutions and transaction evidence.
5. Applicable court judgments and Registrar / regulator orders.
6. Professional manuals and commentary are research aids only.

**Primary-source links**
- Bangladesh Laws, Companies Act 1994 (Act XVIII of 1994): https://bdlaws.minlaw.gov.bd/act-print-788.html
- Bangladesh Laws section page for registered office (s.77): https://bdlaws.minlaw.gov.bd/act-788/act-part-print-355.html
- RJSC official forms: https://roc.gov.bd/pages/forms/6922d9b8933eb65569dffa1c
- RJSC eBRS downloads: https://ebrs.rjsc.gov.bd/public/downloads
- RJSC eBRS FAQ: https://ebrs.rjsc.gov.bd/public/faqs
- RJSC fee information: https://app.roc.gov.bd/psp/rjsc_fees
- Bangladesh Government Press Gazette search: https://gazettes.dpp.gov.bd/

**Source limitations recorded on audit date**
- The official eBRS downloads page displays a notice that the system is being used for testing and tells users not to sign up, apply for name clearance, pay or register through that system. Verify operational status before directing a customer to transact.
- RJSC FAQ and forms pages are operational references. Their section references must be checked against the current Act text. Example: the FAQ associates the 30-day Form IX filing with s.92, while the statutory post-appointment filing proposition previously identified in the NLC audit is s.93(2). Do not silently copy the FAQ citation.
- A complete, authoritative consolidated text of the Companies Rules, 2009 and all amendments was not located in the official sources reviewed for this artifact. Rules-level completeness remains OPEN. Do not invent rule numbers or imply that this audit has verified every rule.

## 3. Companies Act schedule inventory

The Act contains twelve schedules. The descriptions below are an inventory/navigation aid; every schedule must be checked against the authentic text, amendments, company type and cross-referenced section before implementation.

| Schedule | Subject / apparent function | NLC implication | Status |
|---|---|---|---|
| I | Regulations for management of a company limited by shares (model/Table A regulations) | Build a company-specific Articles and default-regulation resolver; do not hard-code one universal set of governance rules | COUNSEL_REQUIRED / IMPLEMENTATION_CHECK |
| II | Table of fees payable to the Registrar (s.348) | Versioned RJSC fee catalogue; effective dates, entity type, filing type and fee source must be stored | SOURCE_PENDING |
| III | Prospectus particulars / reports incorporated in prospectus (s.135 cross-reference) | Public securities / prospectus workflow only where triggered | CONDITIONAL / SOURCE_PENDING |
| IV | Statement in lieu of prospectus (s.141 cross-reference) | Public-company formation / capital-raising pathway only where applicable | CONDITIONAL / SOURCE_PENDING |
| V | Memorandum and Articles specimen / constitutional forms for company types | Incorporation and constitutional-document drafting/reference; validate actual current schedule content | SOURCE_PENDING |
| VI | Prescribed statutory form schedule | Form-to-section mapping required; do not infer from form number alone | SOURCE_PENDING |
| VII | Prescribed statutory form schedule | Form-to-section mapping required; do not infer from form number alone | SOURCE_PENDING |
| VIII | Prescribed statutory form schedule | Form-to-section mapping required; do not infer from form number alone | SOURCE_PENDING |
| IX | Prescribed statutory form schedule | Form-to-section mapping required; do not infer from form number alone | SOURCE_PENDING |
| X | Annual return / annual summary of share capital and lists of shareholders/directors (s.36) | Annual return preparation, snapshot reconciliation, filing and receipt verification | IDENTIFIED / COUNSEL_REQUIRED |
| XI | Balance-sheet / profit-and-loss account formats and instructions (s.185 cross-reference) | Accounts preparation checklist and auditor coordination; accounting-standard overlays require separate review | IDENTIFIED / COUNSEL_REQUIRED |
| XII | Statements for specified banking, insurance, deposit / provident / benefit entities (s.192) | Do not apply to ordinary private companies; regulated-category trigger required | CONDITIONAL / OUT_OF_SCOPE_DEFAULT |

**Schedule I control — mandatory product design**
1. Store the exact registered Articles version, date, source/registry reference and hash.
2. Store whether Schedule I is adopted in whole, adopted with modifications, excluded where legally permitted, or applies as a statutory/default term.
3. Resolve regulation-by-regulation, including any regulation deemed included by s.17(2), the special treatment of regulations 78–82 for public companies and private subsidiaries, and the effect of pre-existing Articles.
4. Do not assume every Schedule I regulation is a separate RJSC filing or a universal obligation.
5. Create a lawyer-review state where the Articles are unavailable, inconsistent, ambiguous, amended or not authenticated.
6. Regression-test AGM quorum, director appointment/retirement, transfer restrictions, notices, board powers, dividends, accounts and auditor provisions against the actual Articles.

An ICAB 2021 manual is useful secondary research but must not be the final legal source. It lists mandatory Schedule I regulations and makes statements about Articles that should be checked against the authentic s.17 text and company-specific documents: https://www.icab.org.bd/icabadmin/uploads/ckeditor/6665Corporate%20Laws%20Manual%20Final%202021.pdf

## 4. Companies Act coverage map — domains to reconcile against the 85 rules

This is a coverage checklist, not a statement that every listed provision creates a recurring filing deadline.

| Domain | Act sections / schedule anchor to inspect | Obligation / evidence / service candidates | Applicability | NLC disposition |
|---|---|---|---|---|
| Company type, formation and capacity | ss.2–10 | Company type, subscribers, incorporation prerequisites, identity and registration evidence | All company formations; type-specific | IMPLEMENTATION_CHECK |
| Name and name change | ss.11–11A and s.88 where resolution filing applies | Name clearance, special resolution, Registrar approval, certificate / updated registry record | Name change event | COUNSEL_REQUIRED |
| Alteration of objects / Memorandum | ss.12–16 | Special resolution, court confirmation where required, filing confirmed alteration within statutory period | Only if alteration proposed | COUNSEL_REQUIRED |
| Articles and model regulations | ss.17–22; Schedule I | Registered Articles, statutory defaults, amendment resolutions and version history | Company type / Articles dependent | COUNSEL_REQUIRED |
| Registration documents | ss.23–29 and applicable prescribed forms | Incorporation forms, MoA/AoA, declarations, director consents and registry acceptance | Incorporation / later changes | IMPLEMENTATION_CHECK |
| Members and membership records | ss.30–38; s.36 / Schedule X | Register of members, member index where threshold applies, annual return, member admission/cessation and transfer evidence | Company/member facts | COUNSEL_REQUIRED |
| Share transfer | relevant provisions in ss.30–38; Articles; Form 117 | Instrument, stamp evidence, restrictions, board process, registration/refusal, certificate and register updates | Transfer transaction | IMPLEMENTATION_CHECK |
| Share capital alteration | ss.53–60 | Consolidation, division, conversion, increase, reduction and capital notices; court process where required | Capital transaction | COUNSEL_REQUIRED |
| Registered office | s.77; Form VI | Establishment/change, effective address, service continuity, notice and registry receipt | All companies | IDENTIFIED / COUNSEL_REQUIRED |
| Company name / publication / service | relevant Part IV provisions | Statutory name display, correspondence and registered-office service controls | All companies subject to exact section | SOURCE_PENDING |
| AGM | ss.81–85; Schedule I / Articles | First and subsequent AGM, notice, consent, quorum, chair, adjournment, minutes and evidence | Company type / exceptions / Articles | COUNSEL_REQUIRED |
| Statutory meeting / report | s.83 and related provisions | Statutory report and meeting obligations | Public company / conditional | CONDITIONAL |
| Resolutions and minutes | ss.86–89; Schedule I / Articles | Ordinary/special resolutions, filing, minute books, member access and proof of dispatch | Resolution / meeting event | IMPLEMENTATION_CHECK |
| Directors / officers | ss.90–115; Schedule I / Articles | Appointment, eligibility, consent, particulars, changes, cessation, registers and director duties | Company type and event | COUNSEL_REQUIRED |
| Director interests / contracts | provisions including ss.130 and 98 as relevant; verify exact current text | Disclosure at relevant board meeting, contract register and related evidence; do not collapse into generic director-register filing | Relevant interest/contract event | COUNSEL_REQUIRED |
| Allotment | s.151 and applicable capital provisions; Form XV | Authority, consideration, allotment date, return, member register and certificates | Allotment transaction | IDENTIFIED / COUNSEL_REQUIRED |
| Charges / mortgages | ss.159 onward and applicable provisions; Forms XVIII/XIX/XXVIII | Registrability, creation, particulars, modification, satisfaction, instrument and Registrar receipt | Security transaction | COUNSEL_REQUIRED |
| Books of account | applicable provisions in ss.181–190; Schedule XI | Accounting records, custody, financial period, inspection and retention | Company-specific statutory scope | COUNSEL_REQUIRED |
| Financial statements | ss.185–190; Schedule XI | Preparation, true and fair presentation, approval, signatures, presentation and filing | Company / accounting period | COUNSEL_REQUIRED |
| Audit | ss.210 onward and relevant rules | First auditor, appointment/reappointment, auditor notice, eligibility, resignation/removal and audit evidence | Company / auditor event | COUNSEL_REQUIRED |
| Annual filing | s.36 / Schedule X; s.190 and related provisions | Schedule X within applicable statutory period; financial statements and audit report; reconcile separate deadlines | Annual cycle | COUNSEL_REQUIRED |
| Banking / insurance statements | s.192 / Schedule XII | Prescribed statements and display requirements | Specified regulated entity only | CONDITIONAL / OUT_OF_SCOPE_DEFAULT |
| Inspection / certified copies | relevant Act provisions and RJSC procedure | Search, inspection, certified-copy request, fee and received certified record | Customer request | SERVICE_CANDIDATE |
| Registrar fees | s.348 / Schedule II and current Gazette changes | Fee estimate, filing cost, stamp duty, late fee; quote source and validity | Per filing / transaction | SOURCE_PENDING |
| Winding up | Part V and related provisions | Petition, voluntary winding up, court orders, liquidator appointment, notices, accounts, final meeting and dissolution | Case / resolution-specific | CONDITIONAL |
| Strike-off / restoration | s.346 and applicable rules / orders | Registrar action, notice, objection, restoration process and court evidence | Company status event | CONDITIONAL |
| Foreign companies | Part X, ss.378 onward (verify current numbering and amendments) | Branch/foreign-company registration, local representative, accounts, changes and cessation | Foreign company only | OUT_OF_SCOPE_DEFAULT |
| One-person company | ss.392A–392L (verify current amendment and commencement chain) | OPC-specific formation, member/director and reporting workflows | OPC only; not ordinary private company | OUT_OF_SCOPE_DEFAULT |
| Court and regulator orders | enabling provision + authenticated order | Addressee, service, operative terms, deadline, stay, appeal, compliance evidence | Order-specific | CONDITIONAL |

**Important:** the section ranges in this table are navigation anchors. Before turning any row into a rule, confirm exact subsection, current Bangla text, amendments, commencement, transitional provisions, company category, exception and legal consequence.

## 5. RJSC form and service inventory

RJSC's official pages list the forms below. The official portal's list is broader than NLC's current core private-company catalogue. A form's presence in a download list is not proof that it applies to every private company.

| Form / record | Official RJSC description or use indicated by FAQ/downloads | Trigger / statutory reference shown by RJSC | NLC workflow | Scope / review |
|---|---|---|---|---|
| Form I | Declaration on registration | s.25 | Incorporation package and registration evidence | Incorporation; verify prescribed version |
| Form III | Consolidation, division, subdivision or conversion of shares | ss.53–54 shown by FAQ | Capital restructuring filing | Transaction-specific |
| Form IV | Notice of increase of share capital | s.56; FAQ says 15 days | Capital increase workflow | Transaction-specific; reconcile trigger wording |
| Form VI | Registered-office situation/change | s.77; FAQ says 28 days | Registered-office change | All companies; verify actual due-date trigger |
| Form VII | Statutory report | s.83 | Statutory meeting/report workflow | Public-company pathway |
| Form VIII | Special/extraordinary resolution | s.88(1); FAQ says 15 days | Resolution filing workflow | Resolution-specific; not every board resolution |
| Form IX | Consent of director to act | FAQ says s.92 / 30 days | Director consent and filing evidence | Resolve FAQ/statute citation discrepancy before deadline activation |
| Form X | List of persons consenting to be directors | s.92 shown by FAQ | Incorporation/director onboarding | Confirm current applicability |
| Form XI | Form listed by RJSC downloads | Not established by retrieved FAQ | Hold as form inventory item pending official form inspection | SOURCE_PENDING |
| Form XII | Particulars of directors, manager and managing agents / changes | s.115; FAQ says 14 days | Director/officer appointment and change workflow | Event-specific |
| Form XIV | Form listed by RJSC downloads | Not established by retrieved FAQ | Hold pending form inspection and statutory mapping | SOURCE_PENDING |
| Form XV | Return of allotment | s.151; FAQ says 60 days | Share allotment workflow | Allotment event |
| Form XVIII | Particulars of mortgage/charge | ss.159 and 391 shown by FAQ; 21 days stated | Charge creation registration | Registrability and applicable security class required |
| Form XIX | Modification of mortgage/charge | ss.167(3) and 319 shown by FAQ; 21 days stated | Charge modification | Verify instrument / charge type |
| Form 23B | Auditor notice | s.210(2); FAQ says 30 days after auditor receives appointment information | Auditor notice status and receipt | Auditor-side duty; do not assign company duty without counsel |
| Form XXVIII | Satisfaction of mortgage/charge | FAQ cites ss.12 and 391; 21 days stated | Charge satisfaction | FAQ section reference requires source reconciliation |
| Form XXXVI–XLII | Listed in eBRS downloads | Exact form purposes not established from retrieved source | Inventory only; inspect each official form and map to enabling provision | SOURCE_PENDING |
| Form 117 | Instrument of transfer of shares | Listed by RJSC | Share transfer evidence/document preparation | Verify stamp, execution and Articles requirements |
| Schedule X | Annual summary of share capital and lists of shareholders/directors | s.36; FAQ says within 21 days of AGM | Annual return preparation, reconciliation and filing receipt | Annual cycle |
| Balance Sheet | Annual financial statement | s.190 / relevant accounts provisions; FAQ says within 30 days of AGM | Accounts filing workflow | Verify correct deadline trigger and separate filing |
| Profit & Loss Account | Annual financial statement | s.190 / relevant accounts provisions; FAQ says within 30 days of AGM | Accounts filing workflow | Verify current statutory format |
| Income & Expenditure Account | Listed in downloads | Exact applicability not established | Conditional inventory item | SOURCE_PENDING |
| Winding-up forms / court records | eBRS downloads include court orders, liquidator appointment, final meeting and dissolution documents | Part V / route-specific provisions | Winding-up case management | Case-specific; counsel-controlled |

**RJSC source URLs:**  
- https://ebrs.rjsc.gov.bd/public/downloads  
- https://ebrs.rjsc.gov.bd/public/faqs  
- https://roc.gov.bd/pages/forms/6922d9b8933eb65569dffa1c

## 6. NLC service-to-authority matrix

A commercial service must not be described as a statutory duty. Each service needs a defined scope, responsible professional, prerequisites, exclusions, deliverable and evidence of completion.

| Service ID | Proposed service | Legal / authority basis | Deliverables | Mandatory intake / evidence | Boundaries and release control |
|---|---|---|---|---|---|
| SVC-001 | Incorporation coordination | Companies Act formation provisions; RJSC prescribed forms and name clearance process | Application preparation, form checklist, filing coordination, incorporation record pack | Founder authority, proposed name, subscriber/director facts, capital, registered office, signed MoA/AoA and required declarations | Do not claim incorporation until RJSC certificate/record verified; legal drafting reviewed by counsel |
| SVC-002 | MoA/AoA drafting and review | ss.5–29; Schedule I; company-specific constitutional requirements | Draft/compare Articles, powers, transfer controls, governance and amendment record | Business purpose, company type, ownership, capital, governance preferences, current constitutional documents | No generic copy-paste Articles; identify statutory defaults and inconsistencies |
| SVC-003 | Schedule I / Articles governance audit | ss.17–22 and Schedule I | Regulation-by-regulation applicability matrix and Articles gap report | Authenticated registered Articles and amendments, company type, member/director facts | No conclusion from an unverified customer-uploaded draft |
| SVC-004 | Annual secretarial compliance | AGM, annual return, accounts/audit and register provisions | Annual calendar, AGM pack, annual return data pack, filing tracker and receipt archive | Financial year, AGM history, member/director/share capital snapshots, accounts and auditor evidence | Separate statutory deadline from internal target; no false filing status |
| SVC-005 | AGM and board meeting support | ss.81–89; Schedule I / Articles | Notice, agenda, consent, attendance, quorum worksheet, minutes and resolution pack | Current Articles, members/directors, notice service evidence, business to be transacted | Lawyer review for short notice, quorum disputes, validity or contentious resolutions |
| SVC-006 | Director appointment / cessation / change | ss.90–115; Forms IX/X/XII as applicable | Consent and resolution pack, register update, prescribed return preparation | Appointment/cessation event, identity, consent, eligibility, Articles, board/member resolution | Separate appointment, particulars change, resignation/removal and interest disclosure events |
| SVC-007 | Share transfer administration | ss.30–38, applicable Articles and Form 117 | Transfer checklist, instrument review, stamp evidence checklist, register/certificate update pack | Transferor/transferee, instrument, consideration, share certificate, Articles, board process | Do not adjudicate beneficial title or contested transfer automatically |
| SVC-008 | Share allotment / capital change | ss.53–60, s.151, prescribed forms | Authority/resolution, allotment schedule, return and capital-change pack | Board/member authority, subscription, consideration, class rights, payment proof | Counsel approval for pre-emption, class rights, reduction, court process or irregular allotment |
| SVC-009 | Charge registration / modification / satisfaction | ss.159 onward and applicable provisions; Forms XVIII/XIX/XXVIII | Registrability assessment, filing pack, deadline tracker and receipt | Facility/security instrument, secured amount, creation/modification/satisfaction date, lender and company evidence | No deadline until charge type and governing provision are confirmed |
| SVC-010 | Registered-office change | s.77; Form VI | Board/other approval as required, address evidence, filing and receipt pack | New address, effective date, occupation/consent evidence, dispatch records | Ensure service continuity; do not infer address validity from profile text |
| SVC-011 | Accounts and audit coordination | ss.181–213; Schedules XI / XII where applicable | Year-end checklist, auditor appointment coordination, accounts filing tracker | Books, financial statements, audit engagement/report, AGM dates and approval | NLC does not issue an audit opinion or represent unauthorised persons as auditors |
| SVC-012 | RJSC search, inspection and certified-copy service | Companies Act inspection/copy provisions and RJSC published procedure/fees | Search request, certified copy request, retrieved official record and provenance | Company identity/number, target record, authorization and fee | Preserve retrieval date, source, certification and limits; portal outage is not evidence of absence |
| SVC-013 | Late filing / regularization assessment | Underlying provision, applicable additional fee, condonation/extension or court/Registrar route | Defect inventory, legal options memo, sequence plan, fee estimate and filing pack | Full event chronology, prior filings, notices, orders, receipts, company records | Never promise that a default is curable or that a late filing cures every legal consequence |
| SVC-014 | Corporate rescue / distressed-company support | Case-specific Companies Act remedies, winding-up provisions and court process | Evidence-preserving status review, issue map, counsel-led remediation plan | Registry records, creditor claims, court papers, notices, financial status, director/member facts | No automatic BLACK/legal insolvency conclusion; separate legal advice, representation and engagement |
| SVC-015 | Winding-up / liquidation coordination | Part V and route-specific provisions | Case timeline, notices/filings checklist, liquidator/court document tracker | Authenticated petition/resolution/order, liquidator appointment, service and current case status | Court-controlled and counsel-led; petition is not an order and appointment route matters |
| SVC-016 | Strike-off / restoration support | s.346 and applicable rules / court directions | Status check, notice/objection chronology, restoration options pack | Official status, notices, grounds, company records, court/Registrar documents | Do not equate inactive company or missed return with automatic dissolution |
| SVC-017 | Tax registration / annual tax compliance coordination | Income Tax Act 2023, Finance Acts, NBR rules/orders | Applicability intake, tax calendar, document coordination and filing status | TIN, income year, taxpayer category, returns, tax payments and NBR notices | Separate from company-law catalogue; tax counsel/accountant review and current law required |
| SVC-018 | VAT registration / return coordination | VAT and Supplementary Duty Act 2012, Finance Acts, SROs and NBR orders | Threshold/applicability review, registration and return tracker | Taxable activity, turnover period, supplies, exemptions, BIN and NBR records | No fixed threshold/deadline hard-code without effective-dated primary source |
| SVC-019 | Trade licence and local permits | Applicable local-government law, rules and authority directions | Permit inventory, application/renewal tracker and receipt vault | Premises, local authority, business activity, sector and licence class | Jurisdiction- and activity-specific; not a universal Companies Act obligation |
| SVC-020 | Labour / factory licence compliance | Bangladesh Labour Act and Rules, amendments, Gazette directions and DIFE process | Applicability assessment, licence/renewal checklist and evidence tracker | Establishment class, factory status, workers, sector, Government direction and location | Conditional; verify 2026 amendment and operative direction before activating |
| SVC-021 | BSEC / listed issuer governance | Securities laws, BSEC rules/orders and applicable Corporate Governance Code | Listed issuer compliance calendar and governance evidence | Listing status, exchange, security type, issuer category and current BSEC orders | OUT_OF_SCOPE_DEFAULT for ordinary unlisted private company |
| SVC-022 | Foreign investment / FX support | Foreign Exchange Regulation Act, Bangladesh Bank circulars, BIDA instruments and transaction-specific rules | Transaction checklist and bank/BIDA evidence pack | Foreign ownership, subscription, remittance, AD bank, transaction date and zone status | Conditional; instrument and circular effective on transaction date must be pinned |
| SVC-023 | Regulatory / court order tracking | Enabling Act + authenticated order and proof of service | Order extraction, obligation record, deadline and evidence log | Complete order, issuing authority, addressee, service date, appeal/stay and operative terms | Human legal review; no AI-generated operative deadline without verification |
| SVC-024 | Legal opinion / representation | Applicable professional conduct and court/tribunal rules | Counsel-authored opinion, appearance or representation where engaged | Conflict check, engagement scope, client authority and complete factual record | Only appropriately qualified and engaged legal professional may provide reserved legal work |

## 7. Critical cross-cutting product controls

### 7.1 Separate legal obligation from service engagement
A statutory obligation can exist without a paid NLC engagement. A service engagement can exist without a statutory deadline. Never auto-create a fee, engagement or client instruction merely because a rule fires.

### 7.2 Separate obligation, task, filing and receipt
Use distinct records:
- legal obligation definition;
- company-specific obligation instance;
- internal work task;
- filing/application;
- authority acknowledgement / receipt;
- verified closure evidence.

A customer clicking “filed” is not proof of submission or acceptance.

### 7.3 Company-type and fact-based applicability
At minimum, represent:
- private company limited by shares;
- public company;
- private subsidiary of public company;
- company limited by guarantee;
- unlimited company;
- foreign company / branch;
- listed issuer;
- banking / insurance / regulated entity;
- one-person company;
- company in liquidation / winding up.

Unknown company type or trigger facts must result in UNKNOWN / NOT_EVALUATED, not a breach.

### 7.4 Statutory source metadata
Each legal source must store:
- instrument type, number, year and issuing authority;
- exact provision/subsection/schedule/regulation/form;
- authentic URL or document identifier and SHA-256;
- publication, commencement and effective dates;
- amendment / repeal / transitional chain;
- territorial, company-type and transaction scope;
- reviewer, counsel opinion reference and approval date.

### 7.5 Deadline metadata
Each deadline must store:
- event trigger and event evidence;
- whether trigger day is included/excluded;
- calendar-day, clear-day, working-day, month or year arithmetic;
- holiday and non-working-day treatment only where legally authorized;
- month-end convention;
- statutory extension / Registrar / court relief and actual order;
- statutory due date separate from internal target date;
- filing recipient/channel and evidence of receipt.

### 7.6 Approval state model
Do not overload APPROVED. Use independent states:
- OWNER_ATTESTED
- SOURCE_PINNED
- LEGAL_PROPOSITION_REVIEWED
- COUNSEL_VALIDATED
- IMPLEMENTATION_TESTED
- PRODUCTION_RELEASED

Only the release policy may decide whether a rule is eligible for a customer-facing conclusion. Owner attestation is not counsel validation.

## 8. Existing NLC repository reconciliation tasks

The following are repository tasks, not claims of completed code changes:

| Task | Required evidence | Priority |
|---|---|---|
| Reconcile 85 current rule IDs against the Act section/schedule inventory | Machine-readable mapping with no silent missing/duplicate IDs | P0 |
| Compare every rule with exact Bangla provision and amendment chain | Source URL/document hash, subsection, effective dates and counsel sign-off | P0 |
| Complete Companies Rules, 2009 acquisition and amendment search | Gazette/official source text, rule-by-rule index and prescribed-form crosswalk | P0 |
| Build Schedule I Articles resolver | Authenticated Articles versions, regulation applicability and golden tests | P0 |
| Map RJSC forms to statutory sections and company types | Official form file, form revision, enabling provision, trigger, deadline, recipient | P0 |
| Reconcile Forms XI, XIV, XXXVI–XLII and winding-up forms | Inspect actual form content and map to statutory procedure | P1 |
| Separate annual return, financial statements and auditor notice workflows | Independent obligations, duty-holder, deadline and receipt evidence | P0 |
| Reconcile Form IX statutory citation discrepancy | Authentic s.92/s.93 text, appointment timing and RJSC practice note | P0 |
| Create service catalogue and scope controls | Service ID, legal basis, deliverables, qualification, engagement and exclusions | P1 |
| Reconcile commercial revenue tiers to service SKUs | No engagement auto-created from a rule or rescue flag | P1 |
| Version fee catalogue | Official fee schedule/Gazette, date, company type, transaction and fee formula | P1 |
| Confirm eBRS operational status before customer instructions | Dated official notice/status check and fallback process | P1 |
| Keep tax/VAT/labour/BSEC/FX conditional modules isolated | Current sector/transaction applicability matrices and counsel review | P0 |
| Audit historical records and production data separately | Read-only production evidence; no bulk mutation during legal triage | P0 |

## 9. Required acceptance tests

1. A private company with Articles that modify a Schedule I regulation is evaluated against its registered Articles version, not generic Table A defaults.
2. A private subsidiary of a public company activates only the additional Schedule I provisions that the Act makes applicable after counsel validates the mapping.
3. A public-company statutory report requirement does not activate for an ordinary private company.
4. Schedule XII banking/insurance statements do not activate for an ordinary non-regulated private company.
5. An annual return, balance sheet, profit-and-loss account and auditor notice produce distinct obligations with distinct duty-holders and deadlines.
6. A Form IX FAQ citation mismatch cannot be converted into a production deadline until the statutory subsection is resolved.
7. A share transfer creates no Form XV allotment task; a share allotment creates no Form 117 transfer task.
8. A charge modification is not treated as creation or satisfaction; each has its own trigger and form.
9. A missing upload results in UNKNOWN / NOT_PRODUCED, not VERIFIED_ABSENT.
10. A filing marked “submitted” without authority receipt remains unverified.
11. A fee quote uses a dated fee source and never silently reuses a stale fee table.
12. A court/Registrar extension requires an authenticated order and does not overwrite the original statutory deadline.
13. A rule firing does not create a paid engagement, invoice or legal representation mandate.
14. Tax, VAT, labour, BSEC and foreign-exchange obligations remain NOT_APPLICABLE or UNKNOWN until their own trigger facts are established.
15. A service catalogue item cannot claim a statutory duty unless it links to a verified provision and a defined duty-holder.

## 10. Definition of done for legal coverage

This audit is not complete until:
- all 12 schedules are inspected from the authentic current Act text;
- all relevant Companies Rules, 2009 and amending instruments are located and indexed;
- every official RJSC form is inspected and mapped to an enabling provision and entity type;
- the 85-rule catalogue is reconciled to the complete in-scope legal obligation inventory;
- all missing obligations are either implemented or explicitly excluded with reason;
- every service is linked to authority, scope, responsible professional, prerequisites and deliverables;
- a Bangladesh-qualified independent company-law counsel signs the legal propositions and applicability matrices;
- tests demonstrate that unsupported, unknown and conditional obligations fail closed;
- production release remains separately authorized.

**Current conclusion:** this artifact establishes a structured coverage and service audit baseline. It does not establish exhaustive legal coverage, validate every deadline, approve the 85 rules, or authorize statutory scoring. The Companies Rules, 2009 source chain, Schedule I regulation-by-regulation matrix, complete form crosswalk and independent counsel review remain open blockers.
