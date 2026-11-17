# Bangladesh Companies Act — Accounting, Financial Statements and Audit Batch

**Review date:** 15 November 2026  
**Rules in scope:** ACC-001, ACC-002, ACC-003, AUD-001, AUD-002, AUD-003  
**Release status:** SOURCE REVIEW RECORDED — NOT COUNSEL APPROVED — NOT SCORE ELIGIBLE

> This is a source-mapping and implementation-control note, not a legal opinion, statutory certification or counsel approval. The six rule IDs remain `REVIEW_REQUIRED` in the approval register. No rule in this batch is activated for statutory scoring.

## 1. Primary source and amendment chronology

| Instrument | Provisions used | Legal effect for this batch | Status |
|---|---|---|---|
| Companies Act, 1994 (Act No. XVIII of 1994) | ss. 81, 181–185, 189–190, 210 | Books, annual accounts, audit, authentication and Registrar filing | Official Bengali consolidated text checked; English text used only as a working translation |
| Financial Reporting Act, 2015 (Act No. XVI of 2015), s. 62 | s. 62(a) inserts Companies Act s. 185(2A)–(2B); s. 62(b) inserts s. 190(1A); ss. 62(c)–(d) amend auditor eligibility for PIEs | PIE financial statements must follow FRC standards; PIE auditor/annual-report requirements are additional to the Companies Act baseline | Official Bangladesh Laws text checked |
| FRC Financial Reporting Framework, Edition January 2024 | Introduction, para. 4, reproducing FRA s. 2(8) criteria and 11 March 2020 Gazette thresholds | Identifies PIE categories and thresholds relevant to private companies | Official FRC publication checked; confirm the operative Gazette instrument and any later amendment before production use |

The Companies Act commencement material identifies 1 December 1994 as the commencement date. The Financial Reporting Act, 2015 is dated 9 September 2015 and its commencement provision states that it came into force immediately. The 2015 Act expressly amends s. 190; this batch does **not** assume that s. 181 or s. 183 was amended by that instrument. A complete instrument-by-instrument amendment search for every provision remains a counsel-register task.

## 2. Rule-by-rule source and applicability record

### ACC-001 — Financial Statements Not Presented at AGM

- **Source:** Companies Act 1994, s. 183(1)–(6); read with s. 81.
- **Baseline duty:** At every AGM held under s. 81, the Board must lay before the company a balance sheet together with a profit-and-loss account; a company not trading for profit uses an income-and-expenditure account.
- **Accounting-period conditions:** For the first AGM, the period begins on incorporation and ends on a date within nine months preceding the meeting. For a later AGM, the period begins immediately after the last account and ends within nine months before the meeting, or within twelve months where the company carries on business or has an interest outside Bangladesh. Section 183(2) also addresses an s. 81 meeting extension and permits a Registrar extension of up to three months on a timely application.
- **Financial-year limit:** Section 183(4) states a maximum of fifteen months, extendable to eighteen months with special Registrar permission.
- **Audit/report condition:** Under s. 183(3), the accounts must be audited; the auditor's report must be attached or referenced, read before the general meeting and open to member inspection. Section 183(6) requires the accounts and directors' report to be available for inspection at the registered office for at least fourteen days before the meeting.
- **Company scope:** The text says every company. A private limited company is not generally exempt from s. 183 merely because it is private or has low/no turnover.
- **Conditional facts:** Non-profit/non-trading status changes the account presented; overseas business/interest changes the subsequent accounting-period window; extensions and special permission change dates. The registered Articles and AGM history must be checked for the company's meeting mechanics, without treating Articles as authority to override mandatory statutory requirements.
- **Evidence required:** Incorporation certificate; prior accounts; AGM notice and proof of service; authenticated AGM minutes; attendance/quorum record; signed balance sheet and P&L or income/expenditure account; auditor's report; directors' report; registered-office inspection record; Registrar extension/permission and proof of operative dates.
- **Evaluator boundary:** A profile boolean such as `financial_statements_presented=False` is not proof of non-presentation. Missing minutes, missing uploads or an incomplete profile produce UNKNOWN, not a statutory default.

### ACC-002 — Financial Statements Not Filed with Registrar

- **Source:** Companies Act 1994, s. 190(1); Financial Reporting Act 2015, s. 62(b), inserting Companies Act s. 190(1A).
- **Baseline filing clock:** Section 190(1) measures thirty days from the date on which the balance sheet and profit-and-loss/income-and-expenditure account were **laid before the AGM**. If the AGM for that year was not held, the alternative clock is thirty days from the last day on which the meeting should have been held under the Act.
- **Critical distinction:** Do not calculate the ordinary filing deadline as automatically thirty days after the AGM date. The actual date on which the accounts were laid is the trigger. If no AGM was held, the statutory last date for holding it must be established, including any valid extension.
- **Private-company treatment:** The proviso requires a private company to file separate copies of the balance sheet and profit-and-loss account. The further proviso for a private company that is not a subsidiary of a public company limits non-member inspection/copy rights for the profit-and-loss account; it does **not** remove the filing obligation.
- **PIE overlay:** Under inserted s. 190(1A), a company that is a public interest entity under FRA 2015 s. 2(8) cannot furnish its financial statements unless the FRC standards made under FRA s. 40 were followed. This can affect a private limited company; private-company status alone does not exclude PIE status.
- **PIE screening:** FRA s. 2(8) includes, among other categories, banks, securities issuers required to report to BSEC, financial institutions, microcredit organisations, insurers, entities above the gazetted revenue threshold, and entities meeting the statutory asset/liability criteria; the provision also extends to specified public enterprises, statutory public authorities and other entities. The FRC's January 2024 framework reproduces thresholds of preceding-year revenue above BDT 5 crore, or both assets above BDT 3 crore and liabilities (excluding shareholders' equity) above BDT 1 crore, referring to the 11 March 2020 Gazette notification. Verify the Gazette and any later instrument for the relevant assessment year before using these amounts in production.
- **Evidence required:** AGM minutes showing the date accounts were laid; or proof AGM was not held plus the s. 81 due date and extension records; RJSC certified search/filing receipt and document IDs; filing date; signed copies; company type; subsidiary/holding-company status; PIE classification facts; FRC standard version and auditor eligibility where PIE.
- **Evaluator boundary:** A profile boolean such as `financial_statements_filed=False` cannot establish non-filing. A failed search without a defined authenticated RJSC search scope and date is UNKNOWN, not proof of default.

### ACC-003 — Books of Account Not Kept

- **Source:** Companies Act 1994, s. 181(1)–(7).
- **Baseline duty:** Every company must keep proper books recording all money received and expended and the matters to which they relate, sales and purchases, and assets and liabilities.
- **Sector-specific records:** A company engaged in production, distribution, marketing, transportation, processing, manufacturing, milling, extraction or mining must also keep particulars relating to use of materials, labour and overhead costs.
- **Quality test:** Under s. 181(2), books are not “proper” unless they are necessary to give a true and fair view of the company's affairs and explain its transactions.
- **Location and branch conditions:** The baseline location is the registered office, open to directors during business hours. The Board may decide that all or any books be kept elsewhere in Bangladesh for no more than six months; within seven days of that decision, the company must notify the Registrar in writing with the full address. Branch-office books may be kept at the branch if proper summarised returns are sent to the registered office (or permitted other place) at intervals not exceeding three months.
- **Retention:** Section 181(5) requires books and relevant vouchers for at least the twelve years immediately preceding the current year; a company incorporated less than twelve years ago preserves the entire preceding period.
- **Company scope:** The baseline applies to every company. The additional cost-record limb is conditional on the specified activities. Branch and alternative-location rules are conditional; they are not blanket exemptions from maintaining books.
- **Evidence required:** General ledger, journals, cash book, bank statements, receipts/payment vouchers, sales and purchase invoices, asset and liability schedules, stock records, relevant cost schedules, branch records and dated summarised returns, Board resolution for an alternative location, RJSC notice and delivery evidence, and period-specific retention inventory.
- **Evaluator boundary:** `books_of_account_kept=False` is a user assertion, not proof. Missing upload or missing one category of record does not by itself establish that proper books were not kept. An authenticated inspection/search record and a defined statutory test are required.

### AUD-001 — First Auditor Not Appointed Within One Calendar Month

- **Source:** Companies Act 1994, s. 210(6).
- **Baseline deadline:** The first auditor(s) are appointed by the Board within **one month** of the date of registration and hold office until conclusion of the first AGM. If the Board fails to exercise that power, the statutory proviso provides for appointment by the company in general meeting.
- **Date calculation:** Use a calendar-month calculation, not a blanket thirty-day calculation. The appointment date, incorporation/registration date and any applicable statutory interpretation of month-end dates must be retained.
- **Evidence required:** Certificate of incorporation/registration; Board meeting notice and minutes; signed appointment resolution; auditor consent and eligibility evidence; appointment/engagement letter; any member-meeting notice, minutes and appointment if the Board did not act.
- **Evaluator boundary:** An absent profile date is UNKNOWN. A late appointment assertion requires source documents and a check that a valid member appointment did not cure the Board's failure under the statutory proviso.

### AUD-002 — Audit Not Completed Before AGM

- **Source:** Companies Act 1994, s. 183(3), read with ss. 210–220.
- **Legal distinction:** A future AGM with an audit not yet marked complete is a readiness risk, not proof that the company has already breached s. 183(3). The statutory presentation event must be assessed when the AGM occurs.
- **Required evidence:** AGM scheduled date; auditor appointment and eligibility; engagement letter; audit progress/completion confirmation; final signed financial statements; auditor's signed report; Board report; AGM minutes and proof the report was laid/read.
- **Evaluator boundary:** Before the AGM, output a non-scoring readiness/UNKNOWN prompt. Do not publish RED/YELLOW statutory breach severity or deduct points solely because `audit_complete=False`.

### AUD-003 — AGM Held Without Completed Audit

- **Source:** Companies Act 1994, s. 183(3), read with s. 210.
- **Legal question:** Determine whether the accounts laid at the AGM had been audited and whether the auditor's report was attached/referenced and read before the meeting. Do not equate “auditor not appointed”, “audit work incomplete”, “report not uploaded” and “report not laid”; they are different facts.
- **Evidence required:** Authenticated AGM minutes; signed accounts; auditor's report and date; auditor appointment and engagement records; Board report; attendance and meeting date; evidence of report being read/available; any adjournment or reconvened meeting record.
- **Evaluator boundary:** Missing documents or a profile boolean cannot establish the event. Preserve UNKNOWN until the AGM event and source documents are verified and counsel has approved the legal interpretation.

## 3. Cross-rule dependencies and anti-duplication

1. ACC-001 and AUD-003 share the AGM financial-statement presentation event. The system must not double-count the same missing accounts/report as two independent monetary score deductions.
2. ACC-002 depends on the date the statements were laid (or the statutory last date for an AGM that did not occur). It must not infer a filing due date solely from the AGM date.
3. ACC-003 is a continuing books-and-vouchers duty; the existence of a missing financial statement does not itself prove books were not kept.
4. AUD-001 is a separate first-auditor appointment duty under s. 210(6). It must not be conflated with whether a later annual audit was completed.
5. A PIE classification can trigger additional FRC standards and auditor requirements. Company type alone is not enough to decide PIE applicability.

## 4. Implementation and activation decision

| Rule | Candidate implementation status | Score impact | Counsel register |
|---|---|---:|---|
| ACC-001 | Evidence-gated; profile-only absence becomes UNKNOWN | 0 | REVIEW_REQUIRED |
| ACC-002 | Evidence-gated; profile-only non-filing becomes UNKNOWN | 0 | REVIEW_REQUIRED |
| ACC-003 | Evidence-gated; profile-only missing-books assertion becomes UNKNOWN | 0 | REVIEW_REQUIRED |
| AUD-001 | Candidate evaluator remains quarantined until rule approval | 0 | REVIEW_REQUIRED |
| AUD-002 | Pre-AGM readiness only; no statutory default before the event | 0 | REVIEW_REQUIRED |
| AUD-003 | Candidate evaluator remains UNKNOWN until event and source proof | 0 | REVIEW_REQUIRED |

No `approved_rule_ids` entry is added by this document. No rule becomes score-eligible. Activation requires a named independent Bangladesh counsel reviewer to verify the authoritative current text, all amendment instruments and commencement dates, applicable Gazette notifications, company-type scope, statutory extensions/orders, the actual registered Articles and amendments, and the evidence contract. The reviewer must then record a rule-specific approval with provenance and effective date in the controlled register.

## 5. Sources checked

1. **Official Bangladesh Laws — Companies Act, 1994:** https://bdlaws.minlaw.gov.bd/act-print-788.html
2. **Official Bangladesh Laws — Companies Act, Part containing ss. 181–183:** https://bdlaws.minlaw.gov.bd/act-788/act-part-print-355.html
3. **Official Bangladesh Laws — Financial Reporting Act, 2015 (Act No. XVI of 2015), especially ss. 2(8), 40 and 62:** https://bdlaws.minlaw.gov.bd/act-print-1169.html
4. **Financial Reporting Council — Financial Reporting Framework, January 2024, Introduction para. 4:** https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-frc/2024/12/69d57e427caa45d9b8449ce548ad98ed.pdf
5. **Working English translation of Companies Act 1994 (secondary, not controlling):** https://www.icnl.org/research/library/bangladesh_comp/
6. **English reproduction of s. 190 with 2015 amendment note (secondary cross-check only):** https://www.unidaraassociates.bd/acts/companies-act-1994/section-190

**Source limitation:** Official Bengali text is controlling. English reproductions contain typographical/OCR errors and must not be treated as authoritative. The exact current Gazette notification setting PIE financial thresholds and any later amendments after the source publication must be retrieved and attached before a production rule is approved.
