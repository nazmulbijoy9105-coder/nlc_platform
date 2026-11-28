---
name: company-applicability-analysis
description: Determine whether a Bangladesh company-law compliance rule applies to a particular company, event and date. Use for private limited company obligations, exceptions, thresholds, filing events and company-specific compliance assessments.
---

# Company applicability analysis

## Objective
Prevent a generic statutory checklist from being treated as universally applicable to every private limited company.

## Required inputs
Company type and status; incorporation and relevant event dates; articles/constitution facts where relevant; share capital and membership facts; industry or regulated status; event facts; source versions; and user-provided evidence provenance. Identify missing inputs.

## Method
1. Define the company population and legal as-of date.
2. Identify the operative provision and verify commencement/amendments through primary legal research.
3. Translate the provision into a transparent applicability predicate.
4. Identify exceptions, thresholds, exclusions, triggering events, deadlines and dependencies on articles or shareholder resolutions.
5. Distinguish legal obligation, RJSC filing requirement, good governance practice and contractual/internal policy.
6. Evaluate only when required facts are present and validated.
7. Return APPLIES, DOES_NOT_APPLY, CONDITIONAL or INSUFFICIENT_FACTS with reasons and source links.
8. Preserve uncertainty and refer interpretive ambiguity to independent counsel.

## Output
Rule ID; company facts used; facts missing; as-of date; applicability state; predicate; exception analysis; statutory source; filing consequence; deadline basis; evidence required; unresolved issues; counsel review status.

## Safety
No default-to-applies behavior. No penalty or score deduction from missing or unverified facts. Do not infer facts from company name, industry stereotype, OCR or an uploaded document alone. RJSC filing status is not a complete measure of legal compliance.
