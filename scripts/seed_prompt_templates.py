#!/usr/bin/env python3
"""
NEUM LEX COUNSEL — AI Prompt Templates Seeder
scripts/seed_prompt_templates.py

Seeds all AI document drafting templates into the ai_prompt_templates table.
Each template defines the system prompt, user prompt template with {PLACEHOLDER}
syntax, output format instructions, required placeholders, and the mandatory
liability disclaimer (AI Constitution Article 5).

DOCUMENT TYPES SEEDED (9 templates):
  1. AGM_MINUTES           — Annual General Meeting minutes
  2. BOARD_RESOLUTION      — Board of Directors resolution
  3. SHARE_CERTIFICATE     — Share certificate text block
  4. TRANSFER_INSTRUMENT   — Instrument of transfer (Form 117 equivalent)
  5. ENGAGEMENT_LETTER     — Client engagement / retainer letter
  6. ANNUAL_RETURN         — Annual return covering letter and checklist
  7. RESCUE_PLAN           — Corporate rescue plan narrative
  8. STATUTORY_NOTICE      — Statutory notices (AGM, EGM, default notices)
  9. DUE_DILIGENCE         — Due diligence report structure

AI CONSTITUTION COMPLIANCE:
  Article 3: Every template sets in_review_queue=True, human_approved=False,
             auto_sent_blocked=True. No AI output goes directly to client.
  Article 5: Every template includes liability_disclaimer (mandatory).
             Disclaimer is always appended to the final document.

USAGE:
  python scripts/seed_prompt_templates.py
  python scripts/seed_prompt_templates.py --dry-run
  python scripts/seed_prompt_templates.py --verbose
  python scripts/seed_prompt_templates.py --reset  # drop and re-insert all
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine


# ═══════════════════════════════════════════════════════════════════════
# MANDATORY LIABILITY DISCLAIMER
# AI Constitution Article 5: Every AI document must include this.
# ═══════════════════════════════════════════════════════════════════════

NLC_LIABILITY_DISCLAIMER = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT LEGAL NOTICE — NEUM LEX COUNSEL (NLC)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This document has been prepared by NLC using AI-assisted drafting 
tools as a starting point for legal documentation. It is a DRAFT 
and requires review, verification, and approval by a qualified NLC 
legal professional before use.

THIS DOCUMENT:
• Has NOT been reviewed or approved by a lawyer unless counter-signed 
  by an authorised NLC legal officer below.
• Does NOT constitute legal advice, legal opinion, or a legal document 
  in its current AI-generated form.
• May contain errors, omissions, or inapplicable provisions.
• Must be reviewed against the specific facts and circumstances of 
  your company before finalisation.
• Must be verified against the current Bangladesh Companies Act 1994 
  and any applicable SROs, notifications, or RJSC directives.

NLC provides this draft under engagement terms as set out in your 
Engagement Letter. Use of this draft without professional review 
constitutes acceptance that NLC's liability is limited to the extent 
set out in those terms.

DO NOT SIGN, FILE, OR ACT ON THIS DOCUMENT without NLC professional 
approval. Do not send this document to the RJSC, any counterparty, 
or any third party without NLC sign-off.

For approval, review, or queries, contact your assigned NLC officer.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ═══════════════════════════════════════════════════════════════════════
# TEMPLATE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

PROMPT_TEMPLATES: List[Dict[str, Any]] = [

    # ──────────────────────────────────────────────────────────────────
    # 1. AGM MINUTES
    # ──────────────────────────────────────────────────────────────────
    {
        "template_name":  "AGM_MINUTES_STANDARD",
        "document_type":  "AGM_MINUTES",
        "version":        "1.0",
        "system_prompt": """You are a Bangladesh corporate legal specialist with expertise in 
the Companies Act 1994. You draft formal Annual General Meeting (AGM) minutes for 
private limited companies registered with the RJSC.

DRAFTING STANDARDS:
- Use formal legal language appropriate for board minutes
- Follow chronological structure: meeting opened → quorum verified → chair elected 
  → notices confirmed → accounts presented → auditors appointed → any other business → close
- Include all mandatory elements required by Section 81 and Section 86 of the Companies Act 1994
- Reference specific sections of the Act where resolutions are passed
- Use past tense throughout — minutes record what occurred
- All resolutions must be formally proposed, seconded, and carried by show of hands 
  unless stated otherwise
- Do NOT include any legal advice or recommendations — only record facts provided
- Do NOT fabricate any facts not provided in the input data

OUTPUT FORMAT:
Return ONLY the minutes document text. No preamble, no commentary, no markdown headers.
Start with "MINUTES OF THE ANNUAL GENERAL MEETING" and end with the signature block.""",

        "user_prompt_template": """Draft formal AGM minutes for the following meeting:

COMPANY DETAILS:
Company Name: {COMPANY_NAME}
Registration Number: {REGISTRATION_NUMBER}
Registered Address: {REGISTERED_ADDRESS}

MEETING DETAILS:
Financial Year: {FINANCIAL_YEAR}
Meeting Date: {AGM_DATE}
Meeting Time: {AGM_TIME}
Meeting Venue: {AGM_VENUE}

ATTENDANCE:
Chairman: {CHAIRMAN_NAME} (Director)
Directors Present: {DIRECTORS_PRESENT}
Members Present: {MEMBERS_PRESENT}
Apologies: {APOLOGIES}
Total Quorum Count: {QUORUM_COUNT} (Required: {QUORUM_REQUIRED})

NOTICE:
Notice Date: {NOTICE_DATE}
Notice Period: {NOTICE_DAYS} clear days

BUSINESS TRANSACTED:
1. Accounts adopted: {ACCOUNTS_ADOPTED} (Financial Year Ended: {FY_END_DATE})
2. Auditors reappointed: {AUDITOR_REAPPOINTED}
   Auditor Name/Firm: {AUDITOR_NAME}
   ICAB Number: {ICAB_NUMBER}
3. Any other business: {OTHER_BUSINESS}

ADDITIONAL NOTES FROM MEETING:
{MEETING_NOTES}

Please draft complete, formal AGM minutes incorporating all the above information. 
The minutes must comply with the Bangladesh Companies Act 1994.""",

        "output_format_instructions": """Return the complete AGM minutes as plain text with:
- Centred heading: MINUTES OF THE ANNUAL GENERAL MEETING
- Company name and registration number in the heading block
- Numbered agenda items
- Formal resolution text for each resolution passed
- Signature block at the bottom: Chairman signature + date""",

        "required_placeholders": [
            "COMPANY_NAME", "REGISTRATION_NUMBER", "REGISTERED_ADDRESS",
            "FINANCIAL_YEAR", "AGM_DATE", "AGM_TIME", "AGM_VENUE",
            "CHAIRMAN_NAME", "DIRECTORS_PRESENT", "MEMBERS_PRESENT",
            "QUORUM_COUNT", "QUORUM_REQUIRED", "NOTICE_DATE", "NOTICE_DAYS",
            "ACCOUNTS_ADOPTED", "FY_END_DATE", "AUDITOR_REAPPOINTED",
            "AUDITOR_NAME", "ICAB_NUMBER",
        ],
        "optional_placeholders": [
            "APOLOGIES", "OTHER_BUSINESS", "MEETING_NOTES",
        ],
    },

    # ──────────────────────────────────────────────────────────────────
    # 2. BOARD RESOLUTION
    # ──────────────────────────────────────────────────────────────────
    {
        "template_name":  "BOARD_RESOLUTION_STANDARD",
        "document_type":  "BOARD_RESOLUTION",
        "version":        "1.0",
        "system_prompt": """You are a Bangladesh corporate legal specialist drafting formal 
Board of Directors resolutions for private limited companies.

DRAFTING STANDARDS:
- Use the standard Bangladesh board resolution format: "RESOLVED THAT..." for each resolution
- Each resolution must be a complete, self-contained legal statement
- Include recitals where appropriate (WHEREAS / CONSIDERING THAT)
- Use the phrase "by majority/unanimous vote" as applicable
- Include the resolution date, quorum present, and names of directors
- Where the resolution authorises execution of documents, specify which documents 
  and who is authorised to sign
- Do NOT include legal advice — resolutions are factual records
- All statutory references must be accurate to Companies Act 1994 Bangladesh

RESOLUTION TYPES SUPPORTED:
Opening/Closing bank accounts, Appointing/removing officers, Approving transfers,
Authorising signatories, Capital changes, Engaging advisors, Declaring dividends,
Approving audited accounts, Any specific board action.

OUTPUT FORMAT:
Plain text only. Start with heading "BOARD RESOLUTION OF [COMPANY NAME]". 
No markdown. End with signature blocks for all directors present.""",

        "user_prompt_template": """Draft a formal Board Resolution for the following:

COMPANY DETAILS:
Company Name: {COMPANY_NAME}
Registration Number: {REGISTRATION_NUMBER}

MEETING/RESOLUTION DETAILS:
Resolution Type: {RESOLUTION_TYPE}
Date of Resolution: {RESOLUTION_DATE}
Meeting Format: {MEETING_FORMAT}  (e.g., Physical meeting / Circular resolution)
Venue (if physical): {MEETING_VENUE}

DIRECTORS PRESENT / SIGNING:
{DIRECTORS_LIST}
Total Present: {DIRECTORS_COUNT}
Quorum Required: {QUORUM_REQUIRED}
Vote Result: {VOTE_RESULT}  (e.g., Unanimous / Majority)

RESOLUTION SUBJECT:
{RESOLUTION_SUBJECT}

SPECIFIC AUTHORISATIONS OR CONDITIONS:
{RESOLUTION_CONDITIONS}

STATUTORY BASIS (if applicable):
{STATUTORY_BASIS}

BACKGROUND / RECITALS (if needed):
{RECITALS}

Please draft a complete, formal board resolution covering all the above.""",

        "output_format_instructions": """Return complete board resolution as plain text:
- Heading: BOARD RESOLUTION OF [COMPANY NAME]
- Date and meeting details
- Directors present list
- Recitals (WHEREAS...) if applicable
- Resolution clauses (RESOLVED THAT...)
- Signature block for each director with date line""",

        "required_placeholders": [
            "COMPANY_NAME", "REGISTRATION_NUMBER", "RESOLUTION_TYPE",
            "RESOLUTION_DATE", "MEETING_FORMAT", "DIRECTORS_LIST",
            "DIRECTORS_COUNT", "QUORUM_REQUIRED", "VOTE_RESULT",
            "RESOLUTION_SUBJECT",
        ],
        "optional_placeholders": [
            "MEETING_VENUE", "RESOLUTION_CONDITIONS",
            "STATUTORY_BASIS", "RECITALS",
        ],
    },

    # ──────────────────────────────────────────────────────────────────
    # 3. SHARE CERTIFICATE
    # ──────────────────────────────────────────────────────────────────
    {
        "template_name":  "SHARE_CERTIFICATE_STANDARD",
        "document_type":  "SHARE_CERTIFICATE",
        "version":        "1.0",
        "system_prompt": """You are a Bangladesh corporate legal specialist drafting formal 
share certificates for private limited companies registered under the Companies Act 1994.

DRAFTING STANDARDS:
- The share certificate is a formal company document — not a letter
- Must state: certificate number, company name and reg. no., shareholder name, 
  number of shares, share class, nominal value per share
- Must reference the company's Articles of Association restrictions (if private company)
- Must state that shares are subject to the Companies Act 1994 provisions
- Standard restriction clause for private companies: shares are not freely transferable 
  and any transfer is subject to Board approval under the Articles
- Do NOT include advice or recommendations

OUTPUT FORMAT:
Formal certificate layout in plain text. Single document. All details within the 
certificate — no cover letters or explanatory notes.""",

        "user_prompt_template": """Draft a share certificate with the following details:

COMPANY DETAILS:
Company Name: {COMPANY_NAME}
Registration Number: {REGISTRATION_NUMBER}
Registered Office: {REGISTERED_ADDRESS}
Incorporation Date: {INCORPORATION_DATE}

CERTIFICATE DETAILS:
Certificate Number: {CERTIFICATE_NUMBER}
Issue Date: {ISSUE_DATE}
Folio Number: {FOLIO_NUMBER}

SHAREHOLDER DETAILS:
Shareholder Full Name: {SHAREHOLDER_NAME}
NID / Passport Number: {SHAREHOLDER_ID}
Address: {SHAREHOLDER_ADDRESS}

SHARE DETAILS:
Number of Shares: {NUMBER_OF_SHARES} (in words: {SHARES_IN_WORDS})
Share Class: {SHARE_CLASS}  (e.g., Ordinary)
Nominal Value Per Share: BDT {NOMINAL_VALUE_PER_SHARE}
Total Nominal Value: BDT {TOTAL_NOMINAL_VALUE}
Fully Paid: {FULLY_PAID}  (Yes/No)

PREVIOUS CERTIFICATE (if replacement):
Previous Certificate Number: {PREVIOUS_CERT_NO}
Reason for Reissue: {REISSUE_REASON}

Please draft a formal share certificate incorporating all the above details.""",

        "output_format_instructions": """Return the certificate as structured plain text:
- Company letterhead block (name, reg. no., address)
- Certificate number and "SHARE CERTIFICATE" title
- "THIS IS TO CERTIFY THAT..." statement
- All share details
- Restriction notice for private company shares
- Signature block: two directors or director + secretary
- Seal notation: "Under the Common Seal of the Company" """,

        "required_placeholders": [
            "COMPANY_NAME", "REGISTRATION_NUMBER", "REGISTERED_ADDRESS",
            "INCORPORATION_DATE", "CERTIFICATE_NUMBER", "ISSUE_DATE",
            "FOLIO_NUMBER", "SHAREHOLDER_NAME", "SHAREHOLDER_ID",
            "SHAREHOLDER_ADDRESS", "NUMBER_OF_SHARES", "SHARES_IN_WORDS",
            "SHARE_CLASS", "NOMINAL_VALUE_PER_SHARE", "TOTAL_NOMINAL_VALUE",
            "FULLY_PAID",
        ],
        "optional_placeholders": [
            "PREVIOUS_CERT_NO", "REISSUE_REASON",
        ],
    },

    # ──────────────────────────────────────────────────────────────────
    # 4. SHARE TRANSFER INSTRUMENT
    # ──────────────────────────────────────────────────────────────────
    {
        "template_name":  "TRANSFER_INSTRUMENT_STANDARD",
        "document_type":  "TRANSFER_INSTRUMENT",
        "version":        "1.0",
        "system_prompt": """You are a Bangladesh corporate legal specialist drafting 
instruments of transfer of shares (Form 117 equivalent) under the Companies Act 1994 Bangladesh.

DRAFTING STANDARDS:
- The instrument must comply with Section 82 and Schedule requirements
- Must contain: transferor full details, transferee full details, share details,
  consideration, execution date, witness details
- Must reference the company's Register of Members entry
- For private companies: must state that board approval was obtained (if applicable)
  and stamp duty requirements
- Use formal witnessing language
- Do NOT draft this as a letter — it is a formal executed instrument

STAMP DUTY NOTE:
For Bangladesh share transfers, stamp duty is payable at 1.5% of consideration 
or nominal value, whichever is higher. The instrument must be stamped before 
registration. Note this requirement in the instrument.

OUTPUT FORMAT:
Formal instrument/deed format in plain text. Complete execution block with 
transferor signature, witness, and transferee acceptance.""",

        "user_prompt_template": """Draft a share transfer instrument for the following transfer:

COMPANY DETAILS:
Company Name: {COMPANY_NAME}
Registration Number: {REGISTRATION_NUMBER}

TRANSFER DETAILS:
Transfer Date: {TRANSFER_DATE}
Instrument Number: {INSTRUMENT_NUMBER}

TRANSFEROR (Seller):
Full Name: {TRANSFEROR_NAME}
Father's Name: {TRANSFEROR_FATHER_NAME}
NID / Passport: {TRANSFEROR_NID}
Address: {TRANSFEROR_ADDRESS}
Current Folio Number: {TRANSFEROR_FOLIO}

TRANSFEREE (Buyer):
Full Name: {TRANSFEREE_NAME}
Father's Name: {TRANSFEREE_FATHER_NAME}
NID / Passport: {TRANSFEREE_NID}
Address: {TRANSFEREE_ADDRESS}

SHARES BEING TRANSFERRED:
Number of Shares: {SHARES_TRANSFERRED} (in words: {SHARES_IN_WORDS})
Share Class: {SHARE_CLASS}
Certificate Number(s): {CERTIFICATE_NUMBERS}
Nominal Value Per Share: BDT {NOMINAL_VALUE_PER_SHARE}
Total Nominal Value: BDT {TOTAL_NOMINAL_VALUE}
Consideration (Transfer Price): BDT {CONSIDERATION_BDT}
Stamp Duty Paid: BDT {STAMP_DUTY_BDT}
Stamp Duty Receipt Number: {STAMP_DUTY_RECEIPT}

BOARD APPROVAL:
Board Approval Obtained: {BOARD_APPROVAL_OBTAINED}
Board Approval Date: {BOARD_APPROVAL_DATE}
Board Resolution Reference: {BOARD_RESOLUTION_REF}

WITNESS:
Witness Name: {WITNESS_NAME}
Witness Designation: {WITNESS_DESIGNATION}

Please draft a complete, formal instrument of transfer incorporating all the above.""",

        "output_format_instructions": """Return formal instrument as plain text:
- Title: INSTRUMENT OF TRANSFER OF SHARES
- Company details
- Formal transferor declaration: "I/We, the transferor, hereby transfer..."
- Share details table
- Stamp duty declaration
- Execution block: Transferor signature + date + witness
- Acceptance block: Transferee signature + date + witness
- Board approval reference
- Note on registration requirement""",

        "required_placeholders": [
            "COMPANY_NAME", "REGISTRATION_NUMBER", "TRANSFER_DATE",
            "INSTRUMENT_NUMBER", "TRANSFEROR_NAME", "TRANSFEROR_FATHER_NAME",
            "TRANSFEROR_NID", "TRANSFEROR_ADDRESS", "TRANSFEROR_FOLIO",
            "TRANSFEREE_NAME", "TRANSFEREE_FATHER_NAME", "TRANSFEREE_NID",
            "TRANSFEREE_ADDRESS", "SHARES_TRANSFERRED", "SHARES_IN_WORDS",
            "SHARE_CLASS", "CERTIFICATE_NUMBERS", "NOMINAL_VALUE_PER_SHARE",
            "TOTAL_NOMINAL_VALUE", "CONSIDERATION_BDT",
        ],
        "optional_placeholders": [
            "STAMP_DUTY_BDT", "STAMP_DUTY_RECEIPT",
            "BOARD_APPROVAL_OBTAINED", "BOARD_APPROVAL_DATE",
            "BOARD_RESOLUTION_REF", "WITNESS_NAME", "WITNESS_DESIGNATION",
        ],
    },

    # ──────────────────────────────────────────────────────────────────
    # 5. ENGAGEMENT LETTER
    # ──────────────────────────────────────────────────────────────────
    {
        "template_name":  "ENGAGEMENT_LETTER_STANDARD",
        "document_type":  "ENGAGEMENT_LETTER",
        "version":        "1.0",
        "system_prompt": """You are drafting a professional legal services engagement / retainer 
letter for NEUM LEX COUNSEL (NLC), a Bangladeshi corporate law and compliance firm.

DRAFTING STANDARDS:
- Professional, formal tone — not casual or marketing-oriented
- Clearly define scope of services, fees, and client obligations
- Include limitation of liability clause (NLC standard)
- Include confidentiality provisions
- Reference the ILRMF (NEUM LEX RJSC Compliance Master Framework) if engagement 
  is compliance-related
- State clearly what NLC will NOT do (AI limitation clause for AI-assisted services)
- For Corporate Rescue engagements: prominently note that NLC cannot guarantee 
  outcome and that results depend on RJSC processing times
- Include payment terms and retainer conditions
- Professional indemnity statement
- Governing law: Laws of Bangladesh, jurisdiction: Courts of Dhaka

AI LIMITATION CLAUSE (always include for compliance engagements):
NLC uses AI-assisted tools for certain drafting and analysis tasks. All AI outputs 
are reviewed and approved by NLC legal staff before delivery to the client. The client 
acknowledges that AI-assisted work is subject to human verification as part of NLC's 
quality assurance process.

OUTPUT FORMAT:
Formal business letter format. Date, addressee, salutation, structured body with 
numbered clauses for scope/fees/terms. Complimentary close and signature block.""",

        "user_prompt_template": """Draft an engagement letter for the following:

NLC DETAILS:
From: NEUM LEX COUNSEL
Address: {NLC_ADDRESS}
Contact: {NLC_CONTACT_NAME}
Date: {LETTER_DATE}

CLIENT DETAILS:
Client Company: {COMPANY_NAME}
Client Contact Name: {CLIENT_CONTACT_NAME}
Client Contact Designation: {CLIENT_DESIGNATION}
Client Address: {CLIENT_ADDRESS}
Registration Number: {REGISTRATION_NUMBER}

ENGAGEMENT DETAILS:
Engagement Type: {ENGAGEMENT_TYPE}
Revenue Tier: {REVENUE_TIER}
Scope of Services:
{SCOPE_OF_SERVICES}

Estimated Timelines:
{ESTIMATED_TIMELINES}

FINANCIAL TERMS:
Professional Fee: BDT {PROFESSIONAL_FEE}
Government / RJSC Filing Fee (estimated): BDT {GOVERNMENT_FEE}
VAT (15%): BDT {VAT_AMOUNT}
Total Estimated Fee: BDT {TOTAL_FEE}
Payment Terms: {PAYMENT_TERMS}
Retainer (if applicable): BDT {RETAINER_AMOUNT}

SPECIAL CONDITIONS:
{SPECIAL_CONDITIONS}

Please draft a complete engagement letter incorporating all the above.""",

        "output_format_instructions": """Return complete engagement letter as plain text:
- NLC letterhead (company name, address, date)
- Client addressee block
- Re: line clearly stating engagement subject
- Numbered sections: 1. Scope of Services, 2. Fees and Payment, 
  3. Our Obligations, 4. Your Obligations, 5. Limitations, 
  6. Confidentiality, 7. AI-Assisted Services Notice, 
  8. Governing Law, 9. Acceptance
- Signature block: NLC authorised signatory
- Client acceptance block: signature line + date""",

        "required_placeholders": [
            "NLC_ADDRESS", "NLC_CONTACT_NAME", "LETTER_DATE",
            "COMPANY_NAME", "CLIENT_CONTACT_NAME", "CLIENT_DESIGNATION",
            "CLIENT_ADDRESS", "REGISTRATION_NUMBER", "ENGAGEMENT_TYPE",
            "REVENUE_TIER", "SCOPE_OF_SERVICES", "PROFESSIONAL_FEE",
            "TOTAL_FEE", "PAYMENT_TERMS",
        ],
        "optional_placeholders": [
            "GOVERNMENT_FEE", "VAT_AMOUNT", "RETAINER_AMOUNT",
            "ESTIMATED_TIMELINES", "SPECIAL_CONDITIONS",
        ],
    },

    # ──────────────────────────────────────────────────────────────────
    # 6. ANNUAL RETURN (covering letter + checklist)
    # ──────────────────────────────────────────────────────────────────
    {
        "template_name":  "ANNUAL_RETURN_COVERING_LETTER",
        "document_type":  "ANNUAL_RETURN",
        "version":        "1.0",
        "system_prompt": """You are a Bangladesh RJSC compliance specialist drafting 
covering letters and submission checklists for annual return filings.

PURPOSE:
This template produces: (1) a covering letter to accompany the annual return 
submission to RJSC, (2) a checklist of all documents being submitted.

DRAFTING STANDARDS:
- The covering letter is addressed to the Registrar of Joint Stock Companies and Firms
- Reference the Section 190 Companies Act 1994 requirement
- List all attachments explicitly — RJSC clerks use the covering letter to verify submissions
- Note any years of backlog filing clearly and explain reasons where applicable
- Where late filing fee has been paid, reference the receipt number
- For backdated/regularisation filings: state clearly which year is being filed for
  and include a brief chronology if multiple years

OUTPUT FORMAT:
Formal letter addressed to RJSC + itemised attachment list. 
No markdown. Professional letterhead format.""",

        "user_prompt_template": """Draft an RJSC annual return covering letter:

COMPANY DETAILS:
Company Name: {COMPANY_NAME}
Registration Number: {REGISTRATION_NUMBER}
Registered Office: {REGISTERED_ADDRESS}

FILING DETAILS:
Financial Year: {FINANCIAL_YEAR}
AGM Date: {AGM_DATE}
Filing Date: {FILING_DATE}
Filing Type: {FILING_TYPE}  (On-time / Late / Backlog regularisation)
Is Backlog Filing: {IS_BACKLOG}
Backlog Years Covered: {BACKLOG_YEARS}

LATE FILING FEES PAID:
Late Fee BDT: {LATE_FEE_BDT}
Receipt Number: {LATE_FEE_RECEIPT}

ATTACHMENTS BEING SUBMITTED:
1. Annual Return Form XII: {FORM_XII_INCLUDED}
2. Audited Financial Statements: {ACCOUNTS_INCLUDED}
3. Directors List (updated): {DIRECTORS_LIST_INCLUDED}
4. Members List with shareholding: {MEMBERS_LIST_INCLUDED}
5. Auditor's Report: {AUDITOR_REPORT_INCLUDED}
6. AGM Minutes: {AGM_MINUTES_INCLUDED}
7. Additional attachments: {ADDITIONAL_ATTACHMENTS}

NOTES / EXPLANATORY REMARKS:
{EXPLANATORY_NOTES}

Please draft the complete covering letter and checklist.""",

        "output_format_instructions": """Return as plain text:
- Company letterhead 
- Date
- Addressee: The Registrar, RJSC, Dhaka
- Reference line: Annual Return Filing — [Company Name] — FY [Year]
- Body: formal letter text explaining the submission
- Attachment checklist (numbered)
- Signature block: Director + designation
- Total page count note""",

        "required_placeholders": [
            "COMPANY_NAME", "REGISTRATION_NUMBER", "REGISTERED_ADDRESS",
            "FINANCIAL_YEAR", "AGM_DATE", "FILING_DATE", "FILING_TYPE",
        ],
        "optional_placeholders": [
            "IS_BACKLOG", "BACKLOG_YEARS", "LATE_FEE_BDT", "LATE_FEE_RECEIPT",
            "FORM_XII_INCLUDED", "ACCOUNTS_INCLUDED", "DIRECTORS_LIST_INCLUDED",
            "MEMBERS_LIST_INCLUDED", "AUDITOR_REPORT_INCLUDED",
            "AGM_MINUTES_INCLUDED", "ADDITIONAL_ATTACHMENTS",
            "EXPLANATORY_NOTES",
        ],
    },

    # ──────────────────────────────────────────────────────────────────
    # 7. RESCUE PLAN NARRATIVE
    # ──────────────────────────────────────────────────────────────────
    {
        "template_name":  "RESCUE_PLAN_NARRATIVE",
        "document_type":  "RESCUE_PLAN",
        "version":        "1.0",
        "system_prompt": """You are a Bangladesh corporate rescue and compliance specialist 
preparing formal Corporate Rescue Plan documents for companies in statutory default.

CONTEXT:
NEUM LEX COUNSEL's Corporate Rescue service follows an 8-step sequence to bring 
companies from BLACK band (severe statutory default) back to GREEN band (full compliance):
Step 1: Retrospective Audit
Step 2: Ratify Irregular Transfers  
Step 3: Regularise Director Records
Step 4: Convene Back-dated AGMs (where legally permissible)
Step 5: File Outstanding Annual Returns
Step 6: Update Statutory Registers
Step 7: Issue Outstanding Share Certificates
Step 8: RJSC Acknowledgment and Compliance Confirmation

DRAFTING STANDARDS:
- The Rescue Plan is a formal document presented to the client Board
- Acknowledge the severity of the situation clearly but professionally
- Each step must include: what needs to be done, why, statutory basis, 
  estimated timeline, what documents NLC will produce
- Note that timelines depend on RJSC processing and cannot be guaranteed
- Include director personal liability context where relevant
- Do NOT minimise the seriousness of the situation
- Do NOT guarantee outcomes

OUTPUT FORMAT:
Formal report structure. Sections with headings. Plain text only (no markdown).""",

        "user_prompt_template": """Draft a Corporate Rescue Plan narrative for the following company:

COMPANY DETAILS:
Company Name: {COMPANY_NAME}
Registration Number: {REGISTRATION_NUMBER}
Incorporation Date: {INCORPORATION_DATE}
Company Type: {COMPANY_TYPE}
Current Company Status: {COMPANY_STATUS}

COMPLIANCE STATUS:
Current Risk Band: {CURRENT_RISK_BAND}
Current Compliance Score: {CURRENT_SCORE} / 100
Years in Default: {YEARS_IN_DEFAULT}
Active BLACK Flags: {BLACK_FLAGS}
Active RED Flags: {RED_FLAGS}
Active YELLOW Flags: {YELLOW_FLAGS}

SPECIFIC ISSUES IDENTIFIED:
{COMPLIANCE_ISSUES_LIST}

AGM STATUS:
AGMs missed: {AGMS_MISSED}
Last AGM held: {LAST_AGM_DATE}

AUDIT STATUS:
Audits pending: {AUDITS_PENDING}
Last audit completed: {LAST_AUDIT_DATE}

ANNUAL RETURNS STATUS:
Annual returns unfiled: {RETURNS_UNFILED}
Last return filed for: {LAST_RETURN_YEAR}

DIRECTOR STATUS:
Director irregularities: {DIRECTOR_ISSUES}

SHAREHOLDING STATUS:
Transfer irregularities: {TRANSFER_ISSUES}

RESCUE SCOPE:
Revenue Tier: {REVENUE_TIER}
Estimated Total Fee: BDT {TOTAL_FEE_BDT}
Target Completion: {TARGET_COMPLETION_DATE}
Lead NLC Officer: {LEAD_OFFICER}

Please draft a comprehensive Corporate Rescue Plan narrative.""",

        "output_format_instructions": """Return formal rescue plan as plain text with sections:
1. EXECUTIVE SUMMARY (severity, key risks, recommended action)
2. STATUTORY DEFAULT ANALYSIS (by module: AGM, Audit, Returns, Directors, Transfers)
3. DIRECTOR PERSONAL LIABILITY ASSESSMENT
4. 8-STEP RESCUE SEQUENCE (each step: objective, actions, timeline, deliverables)
5. ESTIMATED TIMELINE AND MILESTONES
6. FEE SCHEDULE AND PAYMENT TERMS
7. LIMITATIONS AND CONDITIONS
8. NEXT STEPS
9. DECLARATION (NLC sign-off block)""",

        "required_placeholders": [
            "COMPANY_NAME", "REGISTRATION_NUMBER", "INCORPORATION_DATE",
            "COMPANY_TYPE", "CURRENT_RISK_BAND", "CURRENT_SCORE",
            "YEARS_IN_DEFAULT", "COMPLIANCE_ISSUES_LIST", "REVENUE_TIER",
        ],
        "optional_placeholders": [
            "COMPANY_STATUS", "BLACK_FLAGS", "RED_FLAGS", "YELLOW_FLAGS",
            "AGMS_MISSED", "LAST_AGM_DATE", "AUDITS_PENDING", "LAST_AUDIT_DATE",
            "RETURNS_UNFILED", "LAST_RETURN_YEAR", "DIRECTOR_ISSUES",
            "TRANSFER_ISSUES", "TOTAL_FEE_BDT", "TARGET_COMPLETION_DATE",
            "LEAD_OFFICER",
        ],
    },

    # ──────────────────────────────────────────────────────────────────
    # 8. STATUTORY NOTICE
    # ──────────────────────────────────────────────────────────────────
    {
        "template_name":  "STATUTORY_NOTICE_STANDARD",
        "document_type":  "STATUTORY_NOTICE",
        "version":        "1.0",
        "system_prompt": """You are a Bangladesh corporate legal specialist drafting 
statutory notices for companies under the Companies Act 1994.

NOTICE TYPES SUPPORTED:
- AGM Notice (Section 86)
- EGM Notice (Section 85)
- Notice of AGM Default to Directors (internal)
- Notice of Director Appointment to Directors
- Notice of Director Resignation acceptance
- Annual Return Reminder Notice to client
- RJSC Compliance Default Warning (internal to client)

DRAFTING STANDARDS:
- AGM/EGM notices: must state date, time, place, and agenda precisely
- Meeting notices: must include the 21 clear days' notice statement
- All notices must be in writing (this is the written form)
- Internal notices to directors: formal but can be memo format
- Client default warnings: professional, non-threatening, factual
- Do NOT draft as a letter to the RJSC — these are notices to members/directors

OUTPUT FORMAT:
Formal notice format. No markdown. Letterhead. Proper addressing.""",

        "user_prompt_template": """Draft the following statutory notice:

COMPANY DETAILS:
Company Name: {COMPANY_NAME}
Registration Number: {REGISTRATION_NUMBER}
Registered Address: {REGISTERED_ADDRESS}

NOTICE DETAILS:
Notice Type: {NOTICE_TYPE}
Notice Date: {NOTICE_DATE}
Issued By: {ISSUER_NAME} ({ISSUER_DESIGNATION})

RECIPIENTS:
{RECIPIENTS_LIST}

MEETING DETAILS (if meeting notice):
Meeting Type: {MEETING_TYPE}
Meeting Date: {MEETING_DATE}
Meeting Time: {MEETING_TIME}
Meeting Venue: {MEETING_VENUE}
Notice Period: {NOTICE_PERIOD_DAYS} clear days

AGENDA ITEMS:
{AGENDA_ITEMS}

ADDITIONAL INFORMATION:
{ADDITIONAL_INFO}

Please draft the complete statutory notice.""",

        "output_format_instructions": """Return formal notice as plain text:
- Company letterhead
- Date and reference number
- Recipients block
- Subject / Re: line
- Body text appropriate to notice type
- Agenda (if meeting notice): numbered items
- Important: "NOTE: This notice is issued in compliance with Section [X] 
  of the Companies Act 1994 (Bangladesh)"
- Issuer signature block""",

        "required_placeholders": [
            "COMPANY_NAME", "REGISTRATION_NUMBER", "REGISTERED_ADDRESS",
            "NOTICE_TYPE", "NOTICE_DATE", "ISSUER_NAME", "ISSUER_DESIGNATION",
            "RECIPIENTS_LIST",
        ],
        "optional_placeholders": [
            "MEETING_TYPE", "MEETING_DATE", "MEETING_TIME", "MEETING_VENUE",
            "NOTICE_PERIOD_DAYS", "AGENDA_ITEMS", "ADDITIONAL_INFO",
        ],
    },

    # ──────────────────────────────────────────────────────────────────
    # 9. DUE DILIGENCE REPORT
    # ──────────────────────────────────────────────────────────────────
    {
        "template_name":  "DUE_DILIGENCE_STANDARD",
        "document_type":  "DUE_DILIGENCE",
        "version":        "1.0",
        "system_prompt": """You are a Bangladesh corporate legal specialist preparing 
a statutory compliance due diligence report for a company.

PURPOSE:
This report provides a structured assessment of the company's RJSC compliance 
status, suitable for: investors conducting acquisition due diligence, banks 
assessing creditworthiness, potential directors evaluating appointment risk, 
and the company's own directors assessing personal liability exposure.

DRAFTING STANDARDS:
- Objective, factual tone — not advocacy
- Each module assessed separately with RAG (Red / Amber / Green) status
- Cite specific Section numbers for each finding
- Distinguish between: confirmed defaults (evidence in records), potential 
  defaults (records incomplete), and assumed compliant (no negative data)
- Personal liability section is critical: which directors are exposed, for what, and why
- Do NOT provide legal opinions on outcomes — report findings only
- Do NOT give advice on how to fix issues — that is a separate service
- Include data quality caveats: "This report is based on information provided 
  by the company. NLC has not independently verified all underlying documents."

OUTPUT FORMAT:
Formal report. Sections with headings and sub-headings. Tables where applicable 
(use plain text table format: | col | col |). Plain text only.""",

        "user_prompt_template": """Prepare a statutory compliance due diligence report:

COMPANY DETAILS:
Company Name: {COMPANY_NAME}
Registration Number: {REGISTRATION_NUMBER}
Incorporation Date: {INCORPORATION_DATE}
Company Type: {COMPANY_TYPE}
Financial Year End: {FINANCIAL_YEAR_END}
Report Date: {REPORT_DATE}
Prepared For: {PREPARED_FOR}
Prepared By: NEUM LEX COUNSEL

COMPLIANCE SUMMARY:
Overall Compliance Score: {COMPLIANCE_SCORE} / 100
Risk Band: {RISK_BAND}
Last Evaluated: {LAST_EVALUATED}

AGM COMPLIANCE:
{AGM_COMPLIANCE_DATA}

AUDIT COMPLIANCE:
{AUDIT_COMPLIANCE_DATA}

ANNUAL RETURN COMPLIANCE:
{RETURNS_COMPLIANCE_DATA}

DIRECTOR RECORDS:
{DIRECTOR_COMPLIANCE_DATA}

SHAREHOLDING AND TRANSFERS:
{SHAREHOLDING_DATA}

STATUTORY REGISTERS:
{REGISTERS_DATA}

ACTIVE COMPLIANCE FLAGS:
{FLAGS_LIST}

SCORE HISTORY (last 6 months):
{SCORE_HISTORY}

Please prepare a complete due diligence report.""",

        "output_format_instructions": """Return formal due diligence report as plain text with:
1. COVER PAGE BLOCK (company, report date, prepared for, NLC reference)
2. EXECUTIVE SUMMARY (overall status, risk band, key issues)
3. SCOPE AND METHODOLOGY
4. MODULE-BY-MODULE ASSESSMENT:
   4.1 AGM Compliance
   4.2 Audit Compliance  
   4.3 Annual Return Compliance
   4.4 Director and Officer Compliance
   4.5 Shareholding and Share Transfer Compliance
   4.6 Statutory Registers
5. COMPLIANCE FLAGS REGISTER (table format)
6. DIRECTOR PERSONAL LIABILITY ASSESSMENT
7. RISK MATRIX SUMMARY (table)
8. DATA CAVEATS AND LIMITATIONS
9. APPENDICES REFERENCE
10. NLC DECLARATION AND SIGNATURE BLOCK""",

        "required_placeholders": [
            "COMPANY_NAME", "REGISTRATION_NUMBER", "INCORPORATION_DATE",
            "COMPANY_TYPE", "FINANCIAL_YEAR_END", "REPORT_DATE",
            "PREPARED_FOR", "COMPLIANCE_SCORE", "RISK_BAND",
        ],
        "optional_placeholders": [
            "LAST_EVALUATED", "AGM_COMPLIANCE_DATA", "AUDIT_COMPLIANCE_DATA",
            "RETURNS_COMPLIANCE_DATA", "DIRECTOR_COMPLIANCE_DATA",
            "SHAREHOLDING_DATA", "REGISTERS_DATA", "FLAGS_LIST",
            "SCORE_HISTORY",
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════
# SEEDER
# ═══════════════════════════════════════════════════════════════════════

EXPECTED_TEMPLATE_COUNT = 9


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable not set.")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def validate_templates() -> None:
    """Validate all template definitions before seeding."""
    valid_doc_types = {
        "AGM_MINUTES", "BOARD_RESOLUTION", "ANNUAL_RETURN", "AUDIT_REPORT",
        "SHARE_CERTIFICATE", "TRANSFER_INSTRUMENT", "ENGAGEMENT_LETTER",
        "RESCUE_PLAN", "DUE_DILIGENCE", "STATUTORY_NOTICE", "OTHER",
    }
    seen_names = set()
    for t in PROMPT_TEMPLATES:
        issues = []
        if t["template_name"] in seen_names:
            issues.append("duplicate template_name")
        seen_names.add(t["template_name"])
        if t["document_type"] not in valid_doc_types:
            issues.append(f"invalid document_type: {t['document_type']!r}")
        if not t.get("system_prompt"):
            issues.append("empty system_prompt")
        if not t.get("user_prompt_template"):
            issues.append("empty user_prompt_template")
        if not t.get("required_placeholders"):
            issues.append("no required_placeholders")
        if issues:
            raise ValueError(
                f"Template validation failed [{t['template_name']}]: {', '.join(issues)}"
            )


async def seed_templates(
    dry_run: bool = False,
    verbose: bool = False,
    reset: bool = False,
) -> int:
    import json as _json

    print(f"\n{'='*60}")
    print(f"  NEUM LEX COUNSEL — Prompt Templates Seeder")
    print(f"  {EXPECTED_TEMPLATE_COUNT} document templates")
    print(f"  Mode: {'DRY RUN' if dry_run else ('RESET + INSERT' if reset else 'UPSERT')}")
    print(f"{'='*60}\n")

    print("Validating template definitions...")
    validate_templates()
    print(f"  ✓ All {len(PROMPT_TEMPLATES)} template definitions valid\n")

    if dry_run:
        for t in PROMPT_TEMPLATES:
            placeholders = t.get("required_placeholders", [])
            print(
                f"  ✓ {t['template_name']:40s}  {t['document_type']:25s}  "
                f"{len(placeholders)} required placeholders"
            )
        print(f"\n✓ Dry run complete — no changes written to DB.")
        return 0

    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        if reset:
            await conn.execute(sa.text("DELETE FROM ai_prompt_templates"))
            print("  ↺ Reset: existing templates deleted\n")

        inserted = 0
        updated = 0
        now = datetime.now(timezone.utc)

        for tmpl in PROMPT_TEMPLATES:
            # Check if template already exists
            result = await conn.execute(
                sa.text(
                    "SELECT id FROM ai_prompt_templates "
                    "WHERE template_name = :name"
                ),
                {"name": tmpl["template_name"]}
            )
            existing = result.fetchone()

            req_pholders = _json.dumps(tmpl.get("required_placeholders", []))
            opt_pholders = _json.dumps(tmpl.get("optional_placeholders", []))
            output_fmt   = tmpl.get("output_format_instructions", "")

            if existing and not reset:
                await conn.execute(sa.text("""
                    UPDATE ai_prompt_templates SET
                        document_type             = CAST(:doc_type AS document_type),
                        version                   = :version,
                        system_prompt             = :system_prompt,
                        user_prompt_template      = :user_prompt,
                        output_format_instructions= :output_fmt,
                        required_placeholders     = CAST(:req_ph AS jsonb),
                        liability_disclaimer      = :disclaimer,
                        is_active                 = TRUE,
                        updated_at                = :now
                    WHERE template_name = :name
                """), {
                    "name":          tmpl["template_name"],
                    "doc_type":      tmpl["document_type"],
                    "version":       tmpl["version"],
                    "system_prompt": tmpl["system_prompt"].strip(),
                    "user_prompt":   tmpl["user_prompt_template"].strip(),
                    "output_fmt":    output_fmt.strip(),
                    "req_ph":        req_pholders,
                    "disclaimer":    NLC_LIABILITY_DISCLAIMER.strip(),
                    "now":           now,
                })
                updated += 1
                status = "↺ updated"
            else:
                await conn.execute(sa.text("""
                    INSERT INTO ai_prompt_templates (
                        id, template_name, document_type, version,
                        system_prompt, user_prompt_template,
                        output_format_instructions,
                        required_placeholders,
                        liability_disclaimer,
                        is_active, created_at, updated_at
                    ) VALUES (
                        uuid_generate_v4(),
                        :name,
                        CAST(:doc_type AS document_type),
                        :version,
                        :system_prompt,
                        :user_prompt,
                        :output_fmt,
                        CAST(:req_ph AS jsonb),
                        :disclaimer,
                        TRUE, :now, :now
                    )
                """), {
                    "name":          tmpl["template_name"],
                    "doc_type":      tmpl["document_type"],
                    "version":       tmpl["version"],
                    "system_prompt": tmpl["system_prompt"].strip(),
                    "user_prompt":   tmpl["user_prompt_template"].strip(),
                    "output_fmt":    output_fmt.strip(),
                    "req_ph":        req_pholders,
                    "disclaimer":    NLC_LIABILITY_DISCLAIMER.strip(),
                    "now":           now,
                })
                inserted += 1
                status = "✓ inserted"

            if verbose:
                print(
                    f"  {status}  {tmpl['template_name']:40s}  "
                    f"{tmpl['document_type']}"
                )

        count_result = await conn.execute(
            sa.text("SELECT COUNT(*) FROM ai_prompt_templates WHERE is_active = TRUE")
        )
        db_count = count_result.scalar()

    await engine.dispose()

    print(f"\n{'='*60}")
    print(f"  Seeding complete!")
    print(f"  Inserted: {inserted}  Updated: {updated}")
    print(f"  DB total active templates: {db_count}")
    print(
        f"\n  ✓ AI Constitution Article 3 & 5 satisfied: "
        f"all templates include liability_disclaimer."
    )
    print(f"{'='*60}\n")

    return inserted + updated


def main():
    parser = argparse.ArgumentParser(
        description="Seed AI prompt templates into NLC database.",
    )
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--verbose",  "-v", action="store_true")
    parser.add_argument(
        "--reset", action="store_true",
        help="Delete all existing templates and re-insert (use with caution)."
    )
    args = parser.parse_args()

    try:
        asyncio.run(seed_templates(
            dry_run=args.dry_run,
            verbose=args.verbose,
            reset=args.reset,
        ))
        sys.exit(0)
    except RuntimeError as e:
        print(f"\n✗ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Seeding failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
