# Dependency License Policy

**Project:** NLC Platform  
**Project license:** Proprietary — All rights reserved  
**Owner decision recorded:** 2026-11-27

## 1. Separate project and dependency licensing

NLC Platform is proprietary software. The project's proprietary status does
not change the license terms of third-party dependencies, and acceptance of a
dependency license does not grant a license to NLC Platform.

Each dependency must be assessed under its own applicable license and any
relevant notice, attribution, source-disclosure, offer, or redistribution
obligations.

## 2. Explicitly approved dependency licenses

The following license families are approved for use, subject to retaining and
providing applicable license texts, copyright notices, attribution, and
NOTICE materials when required:

- MIT.
- BSD-2-Clause and BSD-3-Clause.
- Apache-2.0.
- ISC.
- Unlicense.
- Python Software Foundation License (PSFL), including Defusedxml.

The project owner expressly accepts PSFL-licensed dependencies. This approval
is intentional and is not an unresolved or unknown-license exception. The
specific PSFL version and its notice obligations must still be observed.

The CI allowlist is intentionally narrower than this explanatory list where
metadata is ambiguous or compound. A package whose metadata cannot be
unambiguously mapped to an approved license expression remains blocked until
the expression is reviewed and represented exactly in the checker.

## 3. Requires case-by-case written review

The following categories are not approved by default and block release until
the exact license, use, distribution model, and obligations have been reviewed
and the decision is recorded:

- LGPL.
- MPL.
- EPL.
- GPL.
- AGPL.
- SSPL.
- BUSL.
- Dual-licensed, custom, source-available, or other non-standard terms.
- Public-domain or compound expressions that the checker cannot safely
  interpret.
- Unknown, missing, conflicting, or unverified license metadata.

A dependency in this category must be replaced, excluded, or expressly approved
in a dated project-owner/legal-review record before it can be allowlisted.
Scanner labels alone are not a legal determination.

## 4. Evidence and release controls

For each release dependency audit, retain:

1. The dependency inventory, including package name and version.
2. The detected license identifier and source used to verify it.
3. Applicable license and NOTICE texts for distributed dependencies.
4. Written approvals and conditions for dependencies requiring case-by-case
   review.
5. A record of unresolved, unknown, or disallowed findings and their disposition.

Unknown or unapproved licenses are release blockers. A passing scanner result
does not waive notice or attribution obligations.

## 5. Change control

Changes to accepted license categories, or exceptions for a particular
dependency, require a documented decision by the project owner or an expressly
authorized legal reviewer. Record the dependency, version, license, rationale,
conditions, approver, and decision date in the relevant release evidence.

This policy does not provide legal advice and does not replace review of the
actual license texts or applicable law.
