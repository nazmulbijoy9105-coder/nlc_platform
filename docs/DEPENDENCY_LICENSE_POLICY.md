# Dependency license policy

## Project license

NLC Platform is proprietary software. The project owner declares the project
license in the root `LICENSE` file and `pyproject.toml`; dependency licenses
do not change the project's license.

## Explicitly approved dependency licenses

The CI allowlist currently approves only:

- MIT
- BSD 2-Clause
- BSD 3-Clause
- Apache License 2.0
- ISC

The CI gate compares each installed distribution's declared license metadata
against an explicit alias list. Unknown, empty, compound, or unrecognized
license strings fail closed and require review rather than being silently
accepted.

## Pending owner decisions

- **Python Software Foundation License (PSFL/PSF): NOT APPROVED pending an
  explicit project-owner decision and notice review.** In particular,
  `defusedxml` must not pass the automated gate merely because PSFL is absent
  from a denylist.
- LGPL, GPL, AGPL, MPL, SSPL, BUSL, and other copyleft/source-available terms
  are not approved by default. A dependency using one requires documented
  written approval before it is added to the allowlist.
- Public-domain, dual-license, custom, missing, or ambiguous metadata must be
  reviewed and mapped to an exact approved expression; it is not implicitly
  permitted.

## Change control

To approve another license, the project owner must update this document and
`scripts/check_dependency_licenses.py` in the same reviewed pull request,
record the rationale and applicable notice/attribution obligations, and
confirm the dependency's actual license text. CI must remain fail-closed for
all licenses not explicitly listed.
