# Dependency license policy

**Owner decision recorded:** 2026-11-27

## Accepted open-source families

NLC may depend on packages under the following license families without further
per-package legal review, provided the dependency is required for the product
and is inventoried in the release `pip-audit` / license report:

- MIT, BSD (2/3-clause), Apache-2.0, ISC, Unlicense, CC0
- **PSFL** (Python Software Foundation License), including `defusedxml` and other
  packages that declare `License: PSFL` / OSI Python Software Foundation License
- MPL-2.0 for non-copyleft-viral use as shipped upstream

## Explicit acceptance: Defusedxml / PSFL

Finding 4 (Defusedxml license classifier) is **accepted**:

- Package: `defusedxml==0.7.1` (or the pin in `requirements.txt`)
- Declared license: PSFL (verified via wheel metadata)
- Project policy: PSFL is an accepted dependency license for NLC
- Root project license: MIT (`LICENSE`)

No additional commercial license is required for PSFL packages under this policy.

## Disallowed without written exception

- AGPL, SSPL, BUSL, and other strongly reciprocal / source-available commercial
  licenses that would force product source disclosure or incompatible terms

Exceptions require a dated note in this file and security-closure evidence.

## Release gate

Production release continues to require:

1. Live `pip-audit` with zero known vulnerabilities
2. Structural security-closure document with all items `Status: CLOSED`
3. This policy file present for PSFL/Defusedxml closure evidence
