# NLC security closure evidence — 2026-11-26

## Full dependency audit

**Audit outcome: PASS — zero package advisories.**

- Workflow: [Full dependency security audit, run #4](https://github.com/nazmulbijoy9105-coder/nlc_platform/actions/runs/45866008549)
- Audit tool: `pip-audit 2.10.1`
- Environment: CPython 3.11.18, Linux x86_64
- Input: `requirements.txt`, SHA-256 `958a651f4196b57624288acdd9e901c424668330a49ede74b63df9e5ae80fe3e`
- Collection mode: `pip-audit --strict -r requirements.txt`; both PyPI and OSV advisory services were queried.
- Result: **222 resolved dependencies, zero vulnerable dependencies, zero known vulnerabilities** from each advisory source.
- The unpinned `apscheduler>=3.11.0` requirement resolved to `3.11.3` in this graph.

The raw JSON reports are retained in the run's machine-readable artifact. The artifact is ID `15139453869`, SHA-256 `16796efac40b60b7ef54fe506d41a8728462c375a96a671be35d2af46960ab84`, with expiry 2027-02-24. The PyPI and OSV report files each have SHA-256 `7732fdfbf1c4b6baf3d9715a034e84edd4bed3c87a3f8c83a79d0fe9406aacf0`. The structured summary is committed in [2026-11-26-dependency-audit-summary.json](2026-11-26-dependency-audit-summary.json).

Resolved security-sensitive versions from both reports:

| Package | Resolved version |
|---|---:|
| Pillow | 13.0.0 |
| Tornado | 6.6.1 |
| FastAPI | 0.165.0 |
| Starlette | 1.10.0 |
| filelock | 4.2.12 |
| Defusedxml | 0.7.1 |

This is a Python package advisory audit. It does not independently audit operating-system packages or private native libraries bundled inside wheels; the Pillow Brotli payload is separately checked in the final Docker image below.

## Pillow bundled Brotli and final image

- Exact main CI run: [CI #5780](https://github.com/nazmulbijoy9105-coder/nlc_platform/actions/runs/45862898579)
- Commit: `8913f52d122ea8c7d28f5797122cccc0d224e55a`
- Result: all four jobs passed — unit tests, integration tests, lint, and Docker runtime smoke.
- Docker runtime job: `140058230737`; the Docker image build and both container smoke steps passed.
- Build output verified:
  - `libbrotlidec-05408f95.so.1.2.1`
  - `libbrotlicommon-53534446.so.1.2.1`
  - Loaded `BrotliDecoderVersion()`: `(1, 2, 1)`

The guard executes in the `runtime-base` stage inherited by the API, worker, and beat images. The production target remains CPython 3.11/Linux x86_64; other platforms remain blocked unless separately reviewed.

## Backend compatibility

The same CI #5780 run used `pip install -r requirements.txt` in the unit and integration jobs. Both complete backend test jobs passed against the upgraded dependency set, as did the final Docker runtime smoke. This closes the compatibility verification item for the exact main commit above.

## Defusedxml license metadata — policy approval still open

The downloaded `defusedxml==0.7.1` wheel metadata reports:

- `License: PSFL`
- `License :: OSI Approved :: Python Software Foundation License`

The wheel and metadata digests are recorded in [2026-11-26-defusedxml-license-metadata.json](2026-11-26-defusedxml-license-metadata.json).

**Policy decision is not established.** Repository inspection found no root `LICENSE` file, no `project.license` declaration in `pyproject.toml`, and no separate dependency-license policy document. The metadata establishes the package's declared license, but does not establish NLC's approval policy. A project owner must confirm that PSFL-licensed dependencies are acceptable (or record the applicable policy) before this item can be marked CLOSED.

## Release interpretation

Items 1, 2, 3, and 5 have the evidence recorded above. Item 4 remains OPEN pending explicit license-policy confirmation. The security-acceptance gate must therefore continue to block production release. No production migration or deployment is authorized or claimed by this evidence.
