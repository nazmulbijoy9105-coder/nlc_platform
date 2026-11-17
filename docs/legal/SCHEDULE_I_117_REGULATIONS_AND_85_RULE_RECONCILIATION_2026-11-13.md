# Schedule I Regulation-by-Regulation and 85-Rule Reconciliation
**Audit date:** 13 November 2026  
**Status:** PRELIMINARY LEGAL / COVERAGE AUDIT — NOT COUNSEL-APPROVED  
**Scope:** Companies Act 1994, Schedule I (regs. 1–117), and the 85-row NLC source-mapping audit CSV  
**Release effect:** NONE. No rule, score, calendar event, filing, penalty conclusion, or production release is authorised by this document.

## 1. Executive findings

1. The 85-row source-mapping file contains exactly 85 rule rows. Its current status distribution is:
   - CORRECTION_REQUIRED: 25
   - CANDIDATE_ONLY: 24
   - REVIEW_REQUIRED: 16
   - NO_MAPPING_YET: 7
   - APPLICABILITY_CONDITIONAL: 7
   - VERSION_REVIEW_REQUIRED: 3
   - INTERNAL_DERIVED: 3
2. Therefore 48/85 rows are expressly CORRECTION_REQUIRED, REVIEW_REQUIRED or NO_MAPPING_YET. Another 13 are conditional, internal-derived or version-review items; the remaining 24 are CANDIDATE_ONLY, not approved rules. The seven conditional rows must not be treated as universal private-company obligations. The three internal-derived rows must not be represented as independent statutory offences.
3. No authenticated, registered Articles of Association (AoA) for a named company were found in the repository or the relevant conversation/library search. No clause-by-clause company-specific AoA comparison can honestly be marked complete. The rule CSV itself marks COMPANY_ARTICLES_REQUIRED for TR-003 and TR-005.
4. The official Bangladesh Laws source is the authentic Bangla Companies Act 1994. Its section 17(2) lists deemed Schedule I regulations as **56, 66, 71, 78, 79, 80, 81, 82, 95, 97, 105, 108, 112, 113, 114, 115 and 116**. A secondary ICAB 2024 table instead says regulation 96 for interim dividend. That is a material source discrepancy: section 17(2) says 97, and the schedule copy also places interim dividend at regulation 97. Do not use the ICAB table's 96 without correction.
5. Section 17(2)'s deemed-inclusion mechanism and section 18's gap-filling mechanism must be modelled separately. For a private company, the proviso to s.17(2) says regs. 78–82 are not deemed included unless it is a subsidiary of a public company. Section 18 separately addresses Schedule I regulations not excluded or modified by registered Articles, so the precise interaction for regs. 78–82 and the phrase “so far as applicable” requires counsel opinion. Do not collapse this into a Boolean “private companies exempt from regs. 78–82”.
6. Schedule I is a governance/default-regulation framework, not a list of 117 recurring statutory filing deadlines. Many regulations operate only when a relevant transaction or governance event occurs; others are default terms that may be displaced by Articles, subject to mandatory Act provisions.
7. The accessible full Schedule I text used for the provisional crosswalk is a third-party reproduced PDF, not the official Bangladesh Laws source. ICAB's 2024 workbook is also secondary and expressly educational. The authentic Bangla schedule text and Gazette/amendment chain still need to be pinned before final legal validation.

## 2. Primary-source hierarchy and legal controls

- **Controlling statutory source:** Bangladesh Laws, Companies Act 1994, authentic Bangla text: https://bdlaws.minlaw.gov.bd/act-print-788.html
- **Official section 18 text:** https://bdlaws.minlaw.gov.bd/act-788/section-32044.html?lang=bn
- **Official Act page search result includes the Bangla s.17(2) list and s.18 text:** verify directly in the Act before each release.
- **Working Schedule I transcription (secondary reproduction):** https://cdn1.ogrlegal.com/files/rjsc/Schedule-1-of-Company-Act-1994.pdf
- **Secondary educational cross-check:** ICAB 2024 Corporate Laws & Practices workbook, chapter marked amended only up to 7 September 2020: https://www.icab.org.bd/icabadmin/uploads/ckeditor/1384Corporate%20Laws%20%26%20Practices.pdf

Important source defects to resolve:
- ICAB 2024's summary table says regulation 96 is deemed; official s.17(2) says 97. Its own Schedule I text places interim dividend at 97. Correct the secondary table reference; do not rewrite the statute.
- The third-party English Schedule I PDF has translation/typographical issues (for example, malformed phrases and the duplicate “transferor” field in reg.19). It is a locator, not the legally controlling text.
- The English versions contain differing text for some matters (including reg.105 location wording and reg.110 financial-statement circulation period). Resolve against the authentic Bangla schedule and current amendments; do not pick the more convenient English rendering.
- The s.17(2) private-company proviso is sometimes reproduced with duplicate/misordered regulation numbers in old English translations. Use the official Bangla list: 78, 79, 80, 81 and 82 are excluded from deemed inclusion for a private company unless it is a subsidiary of a public company.

## 3. Schedule I: all 117 regulations — provisional topic and NLC crosswalk

**Status meanings:**  
- **DEEMED-S17:** listed in s.17(2) as a deemed regulation (subject to the private-company proviso for 78–82); an equivalent-effect provision is deemed, not necessarily identical wording.  
- **S18-DEFAULT:** Schedule I default applies only to the extent the company is within s.18, the matter is applicable, and registered Articles do not exclude or modify it.  
- **CONDITIONAL:** event/company-type/transaction-specific.  
- **AOA-DEPENDENT:** cannot be decided without the registered Articles and amendments.  
- **SOURCE-VERIFY:** topic/wording requires checking against authentic Bangla Schedule I before relying on the English reproduction.

| Reg. | Topic in working Schedule I text | NLC 85-rule relationship | Preliminary treatment |
|---:|---|---|---|
| 1 | Interpretation of expressions and number/gender/person | None | S18-DEFAULT; interpretive only |
| 2 | Commencement of business restrictions under s.150 | INC-007 | SOURCE-VERIFY; INC-007 has no established “s.150 declaration” proposition |
| 3 | Special rights / preference or deferred shares by special resolution | CAP-001; SH-003 | CONDITIONAL; add class-rights / share-issue pathway |
| 4 | Variation of class rights; separate class meeting and quorum | CAP-001 | CONDITIONAL; no dedicated rule; read with s.71 and constitutional terms |
| 5 | Public subscription terms and compliance on allotment | SH-001; INC-007 | Public-company/offer pathway; not ordinary private-company recurring duty |
| 6 | Share certificate entitlement and joint-holder certificate | SH-002 | Candidate coverage only; distinguish statutory certificate deadline from default wording |
| 7 | Renewal of defaced, lost or destroyed share certificate | SH-002 | Transaction-triggered; no dedicated loss/indemnity workflow |
| 8 | Use of company funds to purchase own shares / loans on security, subject to s.58 | CAP-001 | Conditional; requires transaction and statutory exception checks |
| 9 | Company lien over specified shares and dividends | None | Missing transaction/control coverage |
| 10 | Sale of shares subject to lien after notice | None | Missing; strict evidence and process required |
| 11 | Application of lien-sale proceeds and purchaser registration | None | Missing; event-driven |
| 12 | Calls on unpaid shares; amount/interval/notice | None | Missing; capital-call workflow |
| 13 | Joint-holder joint and several liability for calls | None | Missing; shareholder-level liability fact |
| 14 | Interest on unpaid calls | None | Missing; do not calculate without source/effective terms |
| 15 | Interest rules for fixed-time unpaid share sums | None | Missing; linked to issue terms |
| 16 | Different calls/payment times for holders | None | Missing; board discretion / issue terms |
| 17 | Advance payment of uncalled share money and interest | None | Missing; optional transaction pathway |
| 18 | Transfer instrument executed by transferor and transferee | TR-001–TR-006 | Partial; TR-001 statutory section correction needed |
| 19 | Form of share transfer instrument | TR-001; TR-002 | Partial; actual current prescribed/stamped instrument must be verified |
| 20 | Refusal/suspension of transfer; lien/partly-paid shares; evidence and notice | TR-003–TR-005 | AOA-DEPENDENT; no blanket board-approval rule |
| 21 | Title on death of sole holder / joint holder survivorship | TR-006 | Missing succession/transmission sub-workflow |
| 22 | Rights of person entitled through death/insolvency | TR-006 | Missing; documentary proof and Articles needed |
| 23 | Rights before entry in register after transmission | TR-004; TR-006 | Partial; distinguish economic rights from membership/meeting rights |
| 24 | Notice to member in default on call | None | Missing |
| 25 | Forfeiture notice content and minimum period | None | Missing |
| 26 | Board resolution forfeiting shares | None | Missing; do not infer forfeiture from non-payment alone |
| 27 | Sale/disposal or cancellation of forfeiture | None | Missing |
| 28 | Consequences of forfeiture and continuing sums due | None | Missing |
| 29 | Director declaration as evidence and title on sale | None | Missing; evidentiary consequence requires counsel |
| 30 | Fixed-time unpaid issue sums treated as calls for forfeiture | None | Missing |
| 31 | Conversion of paid-up shares into stock / reconversion | CAP-001 | Missing specific transaction; current CAP-001 is too composite |
| 32 | Transfer of stock and restrictions | None | Missing |
| 33 | Rights attached to stock | None | Missing |
| 34 | Application of share regulations to stock | None | Missing |
| 35 | Issue of share warrants | None | Conditional/legacy; determine legal availability and private-company restrictions |
| 36 | Transfer of share warrant by delivery | None | Conditional/legacy |
| 37 | Surrender of warrant and entry in register | None | Conditional/legacy |
| 38 | Deposit of warrant and member-like rights | None | Conditional/legacy |
| 39 | Bearer rights and restrictions | None | Conditional/legacy; verify present legal use |
| 40 | Renewal of share warrant/coupon | None | Conditional/legacy |
| 41 | Increase of share capital by general meeting sanction | SH-003; CAP-001 | Partial; distinguish authority, resolution, notice and allotment |
| 42 | Pre-emption / offer of new shares to existing members | SH-001; CAP-001 | Missing dedicated pre-emption check; Articles/resolution may alter terms subject to Act |
| 43 | New shares subject to existing calls/lien/transfer/forfeiture terms | SH-001 | Missing issue-term inheritance check |
| 44 | Ordinary resolution: consolidation, subdivision, cancellation of untaken shares | CAP-001 | Split transaction types; current rule is composite |
| 45 | Special resolution: reduction of share capital | CAP-003 | Candidate only; court confirmation and statutory procedure required |
| 46 | Statutory general meeting under s.83 | AGM-007 / none | Conditional public-company pathway; distinct from AGM |
| 47 | General meeting within 18 months and thereafter annually / max 15 months | AGM-001; AGM-002 | Cross-check with s.81; do not let model regulation override Act |
| 48 | Ordinary and extraordinary general meeting distinction | AGM-007 | Missing event classification |
| 49 | EGM convening and requisition | None | Missing; cross-map s.84 and member thresholds/process |
| 50 | General meeting notice, content, service and accidental omission | AGM-003; AGM-004 | Partial; must preserve s.85 shorter-notice and accidental-omission provisions |
| 51 | Special business classification at general meetings | AGM-003 | Missing agenda classification |
| 52 | General meeting quorum | AGM-005 | AOA-DEPENDENT; compare s.85(2)(b), member count and actual attendance |
| 53 | Adjournment where quorum absent | AGM-007 | Partial; do not assume universal fresh-notice duty |
| 54 | Chairman of general meeting | None | Missing governance workflow |
| 55 | Appointment of chair if usual chair absent | None | Missing |
| 56 | Adjournment by chairman / notice if adjourned ten days or more | AGM-007 | DEEMED-S17; exact s.85/Articles interaction and notice facts required |
| 57 | Show of hands and evidentiary effect of chair's declaration | None | Missing voting record/evidence control |
| 58 | Poll process and result | None | Missing voting/poll workflow |
| 59 | Casting vote on equality | None | AOA-DEPENDENT / S18-DEFAULT; verify no contrary valid provision |
| 60 | Timing of poll on chair election/adjournment | None | Missing |
| 61 | Voting rights on show of hands and poll | None | AOA/class-rights dependent; member/share register evidence |
| 62 | Voting priority for joint holders | None | Missing |
| 63 | Voting by guardian/committee for member lacking capacity | None | Conditional; court/guardianship evidence |
| 64 | Restriction on voting where calls/sums due | None | Conditional; check Act, class rights and Articles |
| 65 | Voting by proxy and corporate member | None | Missing; link proxy and corporate authority evidence |
| 66 | Form/signature of proxy instrument | None | DEEMED-S17; equivalent-effect clause required |
| 67 | Deposit of proxy instrument and authority | None | S18-DEFAULT unless excluded/modified; verify actual current wording |
| 68 | Model proxy form | None | S18-DEFAULT; form is not automatically a statutory filing |
| 69 | Number and first directors determined by subscribers | INC-003; DIR-001 | Partial; reconcile s.90–93 and actual incorporation record |
| 70 | Director remuneration determined in general meeting | None | Missing; transaction/governance evidence |
| 71 | Director qualification shareholding | DIR-010 / INC-003 | DEEMED-S17; read with s.97 and company type; no automatic breach without appointment/qualification facts |
| 72 | General board management powers subject to Act/Articles/reserved matters | None | Missing governance authority matrix |
| 73 | Managing director/manager appointment, term and remuneration | DIR-010 | Candidate only; verify s.110, term, Articles and resolution |
| 74 | Board borrowing limit without general meeting sanction | None | Missing; compare financing/charge transactions and Articles |
| 75 | Directors' statutory filing/compliance responsibilities | CAP-002; CAP-004; CHG-001; AR-001; DIR-001/002; SH-003 | Overbroad umbrella; decompose by specific filing and actor |
| 76 | Board/member/committee minutes and director signatures | AGM-006; BOD-003; REG-001/002 | Partial; cite s.89 and distinguish minute books/records |
| 77 | Common seal use and execution formalities | None | Missing; first verify whether/how seal is used and current legal effect |
| 78 | Director vacation/disqualification events | DIR-008; DIR-004 | DEEMED-S17 only for public companies and private subsidiaries under s.17 proviso; s.18 interaction requires counsel |
| 79 | Retirement by rotation | None | Same conditional legal treatment as reg.78; not a universal ordinary-private-company scoring rule |
| 80 | Which directors retire | None | Same conditional legal treatment; needs company type and Articles |
| 81 | Eligibility for re-election | None | Same conditional legal treatment; needs company type and Articles |
| 82 | General meeting election to fill retiring director vacancies | None | Same conditional legal treatment; needs company type and Articles |
| 83 | Adjourned election meeting if retiring directors not replaced | None | S18-DEFAULT / AOA-DEPENDENT; not in s.17(2) deemed list |
| 84 | Increase/reduce board size and determine rotation | INC-003 | Partial; company type and Articles control within Act |
| 85 | Casual vacancy appointment and retirement timing | DIR-001 / DIR-002 | Partial; distinguish appointment authority from Form XII filing |
| 86 | Additional director appointment and retirement at next ordinary meeting | DIR-001 | Missing specific appointment workflow; Act/Articles constraints |
| 87 | Removal of director and replacement | DIR-001 / DIR-002 | Missing; verify statutory route and current text before any automated conclusion |
| 88 | Board meetings, adjournment, majority, casting vote, calling meeting | BOD-001; BOD-002 | Partial; BOD-001 frequency source and BOD-002 notice/Articles need review |
| 89 | Board quorum | None | Critical gap; not represented by current BOD rules |
| 90 | Continuing directors' limited power where board below quorum | None | Critical gap; restricted-purpose rule needed |
| 91 | Board chairman's term | None | Missing; Articles/board resolution required |
| 92 | Delegation to committees | None | Missing; authority/delegation evidence |
| 93 | Committee chair | None | Missing |
| 94 | Committee meetings and voting | None | Missing |
| 95 | Validity of acts despite later-discovered appointment defect/disqualification | DIR-004; DIR-008 | DEEMED-S17; must be harmonised with s.98 and its proviso; no automatic validation after defect shown |
| 96 | Dividend declaration and payment within two months, subject to exceptions | None | S18-DEFAULT; **not** the s.17(2) deemed interim-dividend regulation |
| 97 | Interim dividends justified by profits | None | DEEMED-S17; correct interim-dividend regulation number |
| 98 | Dividend only out of current/undistributed profits | None | S18-DEFAULT; no dedicated NLC rule |
| 99 | Dividend distribution according to amounts paid / special rights | None | S18-DEFAULT; share-class and payment facts needed |
| 100 | Creation and use of reserves | None | S18-DEFAULT; financial statements and board evidence |
| 101 | Receipt for dividends by joint holders | None | S18-DEFAULT; shareholder payment control |
| 102 | Notice of declared dividend | None | S18-DEFAULT; no NLC rule |
| 103 | No interest on dividend against company | None | S18-DEFAULT; legal consequence not a compliance score by itself |
| 104 | Proper books of account and categories of records | ACC-003; REG-001/002 | Partial; reconcile with ss.181–182 and accounting standards |
| 105 | Books location and directors' inspection | ACC-003; REG-003 | DEEMED-S17; English source wording conflict—verify authentic Bangla before location rule |
| 106 | Member inspection rights to books | ACC-003 | S18-DEFAULT; member-not-director access is limited by statute/Articles |
| 107 | Preparation and presentation of accounts under ss.183–184 | ACC-001; AUD-002/003 | Partial; distinguish preparation, audit, board approval and AGM presentation |
| 108 | P&L account content and multi-year expenditure explanation | ACC-001; ACC-002 | DEEMED-S17; correct number is 108; proviso to s.17(2) about deferred expenditure must be encoded accurately |
| 109 | Annual balance sheet and date not more than nine months before meeting; directors' report | ACC-001; ACC-002 | S18-DEFAULT; reconcile with ss.185–190 and current Bangla wording |
| 110 | Circulation of balance sheet/report before meeting | ACC-001; AGM-003 | S18-DEFAULT; source copies differ on days; authenticate Bangla text |
| 111 | Compliance with ss.181–191 | ACC-001–003; REG-001–003 | Umbrella cross-reference only; decompose into exact Act duties |
| 112 | Auditor appointment and duties | AUD-001–005 | DEEMED-S17; check cross-reference to current auditor sections and first/subsequent appointment separately |
| 113 | Service of notice to member | AGM-003/004 | DEEMED-S17; preserve proof of dispatch/service and current statutory exceptions |
| 114 | Newspaper notice where no Bangladesh address supplied | AGM-003/004 | DEEMED-S17; conditional on member address facts |
| 115 | Notice to joint holders through first-named holder | AGM-003/004 | DEEMED-S17; membership-register data required |
| 116 | Notice to persons entitled through death/insolvency | AGM-003/004; TR-006 | DEEMED-S17; succession/transmission facts required |
| 117 | Persons entitled to receive notice of general meeting | AGM-003/004 | S18-DEFAULT unless excluded/modified; do not confuse with s.17(2) deemed list |

### Schedule I implications

- The 85 rules cover only fragments of Schedule I. The most serious missing Schedule I areas are lien/calls/forfeiture (regs. 9–17, 24–30), share warrants/stock (31–40), class rights/pre-emption (3–5, 42–43), EGM and voting mechanics (49, 51, 54–55, 57–68), board quorum/delegation/committee (89–94), dividend governance (96–103), and detailed accounts/inspection/circulation (104–111).
- Several Schedule I matters are constitutional defaults or transaction controls, not recurring deadlines. They should be represented as event-triggered obligations/decision checks, not fabricated calendar reminders.
- Regulations 78–82 need a legal applicability resolver, not a blanket private-company exclusion flag. The s.17(2) proviso and s.18 must be read together by counsel for the company's registration date, type, subsidiary status, Articles and amendments.

## 4. Reconciliation of all 85 existing NLC rules

The full row-level source audit remains the controlling row inventory: `nlc_85_rule_source_mapping_audit_v2.csv`. The status counts above are computed from its 85 rows. Key correction and quarantine clusters:

### A. Companies Act section / form errors already visible in the CSV

- AGM-006: change s.83 to s.89 for minutes; s.83 is statutory meeting/report.
- AR-001–AR-004: replace the s.119 / Form XII premise with s.36 and Schedule X for annual return; separate annual return from financial statement filing under s.190.
- CAP-002: replace s.87 / 30-day basis with charge provisions (including s.159 and applicable charge provisions) and validate the 21-day period from primary text.
- CAP-004: special resolution filing is s.88(1), not s.87; verify the 15-day period and resolution class.
- CHG-001: distinguish charge satisfaction from modification; Form XXVIII is the RJSC operational reference, not Form XIX; verify statutory provision and 21-day trigger.
- DIR-001/002/003/004: director particulars/change are associated with s.115/Form XII; s.92 concerns consent. DIR-003's “over one year” threshold is internal escalation, not a statutory time period. DIR-004 cannot infer continuing director liability from registry lag alone.
- DIR-005 and DIR-007: probable duplicate consent-to-act rules; s.92/Form IX and the 30-day rule require exact current text verification. Do not label Form XII as consent form.
- OFF-001: use s.77, not s.81, for registered office notice; verify exact establishment/change trigger.
- REG-001/002/003: split each statutory register and map its own provision, custodian, location, inspection right and evidence; do not preserve a composite rule as if it were one offence.
- SH-003: use s.56 / Form IV candidate, not s.52 / 30 days; verify 15-day trigger from primary text.
- STR-001/002/003: separate name change (s.11), objects/Memorandum alteration (ss.12–16), Articles alteration (s.20), and the separate s.88 special-resolution filing. Do not reuse s.17/s.18 as the substantive amendment provisions.
- TR-001: transfer instrument is associated with s.38, not s.108. TR-003 and TR-005 require the current company-specific Articles. TR-004's alleged two-month register update deadline needs primary-text verification.
- TAX-003/TAX-004, VAT-002, TL-002: versioned tax-day, advance-tax, VAT and local trade-licence rules require current law/SRO/authority source chains; quarantine stale dates and thresholds.
- LBR-001/002: conditional establishment/licence coverage only; the 2026 amendment and commencement/source chain must be authenticated before use.
- BSEC-001–004: listed-issuer / Code-scope rules only; do not apply to ordinary private companies.

### B. No-mapping / derived / conditional rules

- BNK-001–003: determine whether the event is corporate winding-up under Companies Act or personal bankruptcy; no mapping until actual proceeding and order are identified.
- DEF-001: internal unmatched-filing classifier, not a statutory default.
- DEF-002: no penalty notice rule without the actual notice, enabling provision, offence, liable person and response date.
- ESC-003: internal rescue workflow; not a statutory offence or mandatory statutory deadline.
- FX-001, TR-002, VAT-003: remain unmapped until the exact transaction/instrument/obligation is established.
- BSEC-001–004, INC-005/006, LBR-001/002, TAX-001/002, TL-001/002, VAT-002: require explicit applicability facts and effective-dated legal sources; never run as universal rules.
- Rule IDs are exactly those in the CSV. Do not invent missing IDs (for example, gaps in numeric suffixes) or infer that an omitted suffix represents a missing rule without comparing the live canonical rule registry.

### C. Composite and duplicate rules to split

- DIR-005 / DIR-007: consent-to-act duplicate candidate.
- REG-001 / REG-002: overlapping composite register controls.
- CAP-001: separate class-rights variation, increase, consolidation/subdivision/cancellation, reduction and own-share transactions.
- STR-001/002/003: distinct legal change processes and filing steps.
- TR-001–TR-006: distinguish execution/form, stamp, Articles restriction, board decision, register update, transmission and derived aggregate risk.
- AR-001–AR-004: annual return, backlog, strike-off process and incomplete filing must be distinct.
- AUD-001–AUD-005: first auditor, AGM appointment, reappointment, audit readiness and actual appointment default must not collapse into one proposition.

## 5. Wider Companies Act inventory gaps beyond Schedule I

These are candidates for legal-inventory coverage, not assertions that each is an ordinary private-company recurring duty:

1. Company formation/type, incorporation documents, certificate and pre-incorporation contracts (ss.2–29).
2. Register of members, index, inspection and rectification (ss.34–45).
3. Class rights, capital, share issue, premium, own-share purchase, capital reduction and related court process (ss.53–76).
4. Registered office, company name display, AGM, statutory meeting, EGM, quorum, poll, resolutions, minutes and filing (ss.77–89).
5. Director minimums, appointment/consent, qualification, vacation, interests, contracts, managing director and officer particulars (ss.90–131).
6. Prospectus / statement in lieu / public capital raising and statutory disclosure (ss.132–150), with public-company/private-company exclusions.
7. Allotment and return of allotment (s.151), share certificates (s.158), mortgages/charges (ss.159 onward), and foreign-company charge overlays where applicable.
8. Books, financial statements, audit, auditor duties/appointments and Registrar filing (ss.181–213).
9. Company investigation, court powers, winding-up, liquidator and dissolution processes (Part V), each triggered by actual facts/orders.
10. Foreign companies, companies registered under other laws, OPC and later amendments; do not assume these are in scope for a standard private limited company.
11. Schedule II fees and Gazette amendments; Schedules III–V prospectus-related conditional workflows; Schedules VI–IX prescribed forms; Schedule X annual return; Schedule XI financial statement formats; Schedule XII specified regulated-company statements.
12. Rules, Gazette instruments, RJSC prescribed forms, tax/VAT, labour, BSEC, local licensing, Bangladesh Bank/BIDA and sector licences. Keep each instrument/version/applicability separate from the Companies Act baseline.

## 6. Required Articles-of-Association evidence for a company-specific comparison

A valid company-specific comparison cannot be done from a template, a generic RJSC form, an unsigned draft, or a company's name alone. Required inputs:

- Certified or RJSC-authenticated registered AoA as originally registered, including all pages and schedules.
- Every subsequent special resolution / alteration and the filed amended AoA, with effective/registration dates.
- Certificate of incorporation and current company type / status.
- Evidence whether the company is a subsidiary of a public company (relevant to s.17(2) proviso).
- Current register of members, director particulars and relevant resolutions/filing receipts where a particular regulation depends on those facts.

The repository and relevant file search did not surface a company-specific registered AoA. Therefore all company-specific rows remain **NOT_ASSESSED / EVIDENCE_MISSING**, not “compliant”, “non-compliant”, or “default Schedule I adopted”. For customer product design, avoid requiring customers to upload complete original constitutional documents if the chosen workflow forbids that; instead obtain the legally sufficient, consented structured clause facts and a lawyer-verified evidence reference/hash. For this legal audit, an appropriately redacted authenticated extract may be used if it preserves clause numbering, execution/registration status, and amendments.

## 7. Data model and release-gate requirements

Every regulation/rule needs these independent fields:

- instrument, provision/subsection/regulation, authoritative source URI/hash, language, version, Gazette/commencement date, effective-from/to;
- company category, incorporation date, public/private status, subsidiary status, sector/licence, transaction/event applicability predicates;
- Articles clause ID/version, whether expressly adopted, excluded, modified, inconsistent, or silent;
- duty actor, action, trigger, computation formula, day-count convention, exceptions, extension/consent/order state;
- evidence type, evidence provenance, identity binding, received/verified timestamps;
- legal validation state (owner-attested, primary-source-pinned, legal proposition reviewed, independent counsel validated);
- implementation state (unit/integration/parity tested) and production-release state (separate signed release event).

Use tri-state/typed outcomes such as SATISFIED, NOT_SATISFIED, UNKNOWN, NOT_APPLICABLE and REQUIRES_LAWYER_JUDGMENT. Missing Articles or missing evidence must resolve to UNKNOWN / EVIDENCE_MISSING, never FAIL.

## 8. Acceptance criteria before any Schedule I or 85-rule release

1. Obtain and pin the authentic Bangla Schedule I text and all amendment/Gazette instruments affecting it.
2. Have Bangladesh company-law counsel resolve s.17(2) and s.18 interaction, particularly regs.78–82 for private companies and private subsidiaries of public companies.
3. Correct the s.17(2) interim-dividend regulation number from 96 to 97 across seed data, source registry, documentation and tests.
4. Compare every reg.1–117 with the actual registered AoA and every filed amendment for the target company; record clause-level match/exclude/modify/silent/conflict evidence.
5. Reconcile all 85 CSV rows against the live canonical rule registry; explain any row absent from the database or any extra database rule absent from the CSV.
6. Split composite/duplicate/internal-derived rules; quarantine unmapped and version-review rules.
7. Add coverage tests for each accepted obligation and explicit negative tests for inapplicable company types, missing evidence, Articles overrides, exceptions and stale sources.
8. Keep statutory scoring, BLACK overrides and customer deadline events disabled until the exact rule, source, applicability, trigger, evidence, legal review and production release are all approved.

## 9. Decision / blocker

**This audit is not complete against registered Articles.** The company-specific Articles evidence is missing, and the primary official Bangla Schedule I text has not yet been pinned as a standalone source. The 85-row CSV is sufficient to identify major defects and gaps, but not to certify the live 85 rules as correct. Keep legal scoring paused.

