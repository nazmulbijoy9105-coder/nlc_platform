# Dependency License Policy

**Project:** NLC Platform  
**Project license:** Proprietary — All rights reserved  
**Policy status:** Project-owner decision recorded  
**Scope:** Third-party packages and other dependencies incorporated into, distributed with, or used to build or operate NLC Platform.

## 1. Separate project and dependency licensing

NLC Platform is proprietary software. The project's proprietary status does not
change the license terms of third-party dependencies, and acceptance of a
dependency license does not grant a license to NLC Platform.

Each dependency must be assessed under its own applicable license and any
relevant notice, attribution, source-disclosure, offer, or redistribution
obligations.

## 2. Explicit acceptance of PSFL

The project owner explicitly accepts dependencies distributed under the
**Python Software Foundation License (PSFL)**, subject to the terms of the
specific PSFL version applicable to each dependency.

PSFL acceptance is intentional and is not an unresolved or unknown-license
exception. Before redistributing a PSFL-licensed dependency, the project must
retain and provide the applicable license text, copyright notices, and other
required notices in the manner required by that license.

## 3. License categories

The following categories guide dependency review. Classification must be
verified against the actual license text and the way the dependency is used;
an SPDX identifier or scanner label alone is not a legal determination.

### Generally acceptable, subject to notice compliance

- Python Software Foundation License (PSFL), explicitly accepted above.
- MIT.
- BSD-2-Clause and BSD-3-Clause.
- Apache-2.0.
- ISC.
- Other permissive licenses approved in writing by the project owner or
  designated legal reviewer.

Required copyright, attribution, license, and NOTICE materials must be
preserved where applicable.

### Requires case-by-case written review before release

- LGPL.
- MPL.
- EPL.
- Other weak-copyleft, reciprocal, source-available, dual-licensed, or
  non-standard licenses.

Review must consider the exact license version, linking and modification
model, distribution method, source and notice obligations, and compatibility
with the proprietary product. Approval and any conditions must be recorded.

### Not accepted without express project-owner and legal approval

- GPL.
- AGPL.
- SSPL.
- Unknown, missing, conflicting, or unverified licenses.
- Any license whose terms or restrictions have not been reviewed sufficiently
  to determine whether use and distribution are compatible with the product.

A dependency in this category blocks release until the issue is resolved,
replaced, excluded, or expressly approved in a documented decision.

## 4. Evidence and release controls

For each release dependency audit, retain:

1. The dependency-audit output, including package name and version.
2. The detected license identifier and the source used to verify it.
3. Relevant license and NOTICE texts for distributed dependencies.
4. Written approvals and conditions for dependencies requiring case-by-case
   review.
5. A record of unresolved, unknown, or disallowed findings and their disposition.

A scanner's classification is evidence for review, not project-owner approval.
A passing scanner result does not waive notice or attribution obligations.

Unknown or unapproved licenses are release blockers. PSFL findings are
acceptable under this policy when the applicable PSFL terms and notice
obligations are met. This document is the project's written record of that
PSFL acceptance for dependency-license review and security-closure evidence.

## 5. Changes to this policy

Changes to accepted license categories, or exceptions for a particular
dependency, require a documented decision by the project owner or an expressly
authorized legal reviewer. Record the dependency, version, license, rationale,
conditions, approver, and decision date in the relevant release evidence.

This policy does not provide legal advice and does not replace review of the
actual license texts or applicable law.
