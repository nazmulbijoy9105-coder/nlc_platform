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
- Python Software Foundation License (PSFL), including Defusedxml and the Python License, Version 2 (SPDX Python-2.0).
- CMU License (SPDX MIT-CMU).
- Tcl/Tk License (TCL).

The project owner expressly accepts PSFL-licensed dependencies, the permissive CMU License, and the Tcl/Tk License. This approval
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

## 5. Current dependency dispositions (2026-11-27)

| Package / version | Detected license | Decision | Release treatment |
|---|---|---|---|
| PyMuPDF 1.27.1 | AGPL-3.0 or Artifex commercial | Removed from runtime and development requirement sets after repository search found no application import or use. No AGPL/commercial acceptance is granted. | Not installed by the application; reintroduction requires a new review. |
| pypdfium2 5.5.0 | BSD-3-Clause / Apache-2.0 plus PDFium bundled dependency licenses | Present in the resolved inventory and now explicitly version-pinned; no package/bundle approval is recorded. | Release blocker until the exact wheel's bundled PDFium notices and all included licenses are reviewed and approved, or the dependency is removed from the resolved install. |
| greenlet 3.3.1 | MIT AND Python-2.0 | Approved under the existing MIT and PSFL approvals; retain both sets of applicable notices. | Allowlisted as an explicitly reviewed compound expression. |
| certifi 2026.11.20 | MPL-2.0 | Not approved; no package-specific written approval is recorded. | Release blocker while present in the installed runtime inventory. |
| Pillow 13.0.0 | MIT-CMU | Approved as the distinct CMU License under the owner decision above; preserve notices and the no-endorsement condition. | Allowed when the license text and notices are retained. |
| chardet 6.0.0.post1 | LGPL-2.1-or-later | Direct pin removed after repository search found no application import. No LGPL approval is granted. | If installed transitively, remains a release blocker pending replacement or written review. |
| pyphen 0.17.2 | GPL-2.0-or-later OR LGPL-2.1-or-later OR MPL-1.1 | Not approved; its tri-license alternatives require an explicit choice and review of the selected terms and included dictionaries. | Release blocker while present in the installed runtime inventory. |
| python-bidi 0.6.7 | LGPL | Not approved; no package-specific written approval is recorded. | Release blocker while present in the installed runtime inventory. |
| tqdm 4.67.3 | MPL-2.0 AND MIT | Present in the resolved inventory and now explicitly version-pinned. The distribution contains MPL-covered files as well as MIT-covered files; no MPL approval is granted. | Release blocker pending replacement or written project-owner/legal approval of the MPL obligations. |
| ujson 6.0.0 | BSD-3-Clause AND TCL | Direct pin removed after repository search found no application import. BSD-3-Clause and Tcl/Tk License are explicitly approved; retain both notices and verify bundled double-conversion notices in the installed distribution. | Allowed only if the actual inventory and bundled notices match this reviewed expression; unknown bundled licenses still block. |

Removal decisions above are based on the absence of repository references, not on a licence exception. Transitive packages remain in scope: removing a direct pin does not resolve a package that is still installed through another dependency. Re-run the inventory after every dependency change and review the actual resolved package set.

## 6. Change control

Changes to accepted license categories, or exceptions for a particular
dependency, require a documented decision by the project owner or an expressly
authorized legal reviewer. Record the dependency, version, license, rationale,
conditions, approver, and decision date in the relevant release evidence.

This policy does not provide legal advice and does not replace review of the
actual license texts or applicable law.
