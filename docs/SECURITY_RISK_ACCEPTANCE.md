# Security Remediation Status

Updated: 2026-11-26

This document records the remediation state for the dependency and application
security findings tracked in the security/remediate-12-findings pull request.

## Remediated in this branch

| Finding | Change |
|---|---|
| Starlette range-header / related advisories | Upgrade FastAPI to 0.165.0 and Starlette to 1.10.0. The FastAPI release line requires a newer Starlette baseline; retain the exact pins together and verify the resolved dependency graph in CI. |
| python-jose / ECDSA Minerva | Replace python-jose with PyJWT 2.15.1; update token implementation and the direct token test import; remove the direct ecdsa pin. Token type, expiry, algorithm allow-list, JTI, refresh and temporary-token behavior remain enforced by the application. |
| Brotli | Upgrade the direct Brotli dependency to 1.2.1. |
| Pillow | Production CPython 3.11/Linux x86_64 now pins the reviewed custom Pillow 13.0.0 wheel built from the upstream sdist with bundled Brotli 1.2.1. The exact wheel SHA-256, build provenance and Pillow test-suite evidence are recorded below. The official PyPI Pillow 13.0.0 wheel remains unsuitable for production because it bundles Brotli 1.2.0. |
| certifi | Upgrade to 2026.11.20. |
| fsspec | Upgrade to 2026.9.0. |
| virtualenv | Upgrade to 21.15.11. |
| GitPython | Upgrade to 3.2.1. |
| dnspython | Upgrade to 2.9.2. |
| pyasn1 | Upgrade to 0.6.5. |
| soupsieve | Upgrade to 4.1.3. |
| filelock | Upgrade to 4.2.12. |

## Application-level remediation

- Verification subprocess calls use an argument vector, explicitly disable shell
  interpretation, close inherited file descriptors, disable stdin, and execute
  only allow-listed scripts resolved inside the trusted scripts directory.
  Invalid text from subprocess output or UTF-8 report files is recorded as a
  failed verification instead of aborting consolidated report generation.
- The Alembic seed migration binds every inserted value through SQLAlchemy
  parameters; rule strings are no longer interpolated into SQL.
- The fallback PDF HTML renderer escapes title and document content before
  interpolation. The Jinja template path continues to use autoescaping.
- Deployment curl guidance reads the bearer token from an environment variable
  instead of embedding a token in the command.

## Pillow bundled Brotli remediation evidence

The production target no longer installs the official PyPI Pillow 13.0.0 Linux
wheel. It installs a reviewed CPython 3.11/Linux x86_64 wheel built from the
verified Pillow 13.0.0 sdist with only Pillow's Brotli build dependency changed
from 1.2.0 to 1.2.1.

- Release: [NLC Pillow 13.0.0 / Brotli 1.2.1 CPython 3.11 wheel](https://github.com/nazmulbijoy9105-coder/nlc_platform/releases/tag/nlc-pillow-13.0.0-brotli1.2.1-cp311-wheel0480)
- Asset: \`pillow-13.0.0-1brotli121-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl\`
- SHA-256: \`90fea45cb80408dbaa03a0aee58d0e8de01e936e423fd6f645441712e49676d9\`
- Pillow sdist SHA-256: \`cdcd1ba258178f7356d74170c9a81ba4eab6a5d55748bc402a5a2a6fe6be3510\`
- Pillow wheel-recipe source commit: \`293218ad059d994baf1777d882911bed6a49704a\`
- Pillow test-images commit: \`073ab5ff1895abf8cf5c8d797c1066ed394ce207\`
- Build tag: \`1brotli121\`; target tags: CPython 3.11, manylinux 2.27/2.28, x86_64.
- The build used Pillow's \`cibuildwheel\` recipe and its \`pyproject.toml\` test command; the full Pillow wheel test suite passed.
- The artifact's \`pillow.libs\` contains both Brotli decoder and common libraries at SONAME 1.2.1. An independent load of the bundled decoder returned \`BrotliDecoderVersion() == (1, 2, 1)\`.

The release is a reviewed compatibility wheel, not an upstream Pillow release.
The direct \`brotli==1.2.1\` requirement remains useful for other dependencies but
is not treated as a patch for Pillow's private libraries. The production
requirements marker selects the custom wheel only for CPython 3.11/Linux
x86_64; non-production developer platforms retain upstream Pillow 13.0.0.
Those fallback platforms must not be used as production deployment targets.

**Runtime closure gate:** the Dockerfile checks the installed Pillow version,
requires both bundled Brotli libraries with SONAME >= 1.2.1, loads the bundled
decoder, and checks its runtime version API. A Docker build fails closed if
the custom wheel is absent, incompatible, or replaced by the vulnerable
upstream wheel. This check runs in the final runtime-base image, not only in
the wheel-builder environment.

Retain the release asset, SHA-256, build provenance, Pillow test-suite result,
and final Docker image CI result as closure evidence. Any change to the
production Python version, architecture, or manylinux compatibility target
requires a separately reviewed wheel and updated hash before deployment.

## Findings requiring verification before closure

1. **Pillow's bundled Brotli copy:** the production target is pinned to the reviewed CPython 3.11/Linux x86_64 wheel. CI #5780 built the final runtime image and verified both bundled Brotli libraries and the loaded decoder are 1.2.1. Other production platforms remain blocked until separately reviewed.
   Evidence: [final-image and runtime verification](security-evidence/2026-11-26-security-closure.md).
   Status: CLOSED
2. **Full dependency graph:** `pip-audit 2.10.1` resolved and audited 222 dependencies from `requirements.txt` on CPython 3.11/Linux x86_64 against both PyPI and OSV. Both machine-readable reports contain zero vulnerable dependencies and zero known vulnerabilities.
   Evidence: [dependency audit reports, hashes and environment](security-evidence/2026-11-26-security-closure.md).
   Status: CLOSED
3. **Compatibility:** CI #5780 on main commit `8913f52d122ea8c7d28f5797122cccc0d224e55a` passed the complete unit and integration test jobs after installing `requirements.txt`, plus lint and Docker runtime smoke.
   Evidence: [backend compatibility verification](security-evidence/2026-11-26-security-closure.md).
   Status: CLOSED
4. **Defusedxml license classifier:** the actual `defusedxml==0.7.1` wheel metadata declares PSFL and the OSI-approved Python Software Foundation License classifier. However, the repository has no root LICENSE file, project license declaration, or separate dependency-license policy. The package metadata is verified; NLC policy acceptance is not. Obtain explicit project-owner confirmation before closure.
   Evidence: [Defusedxml license metadata and policy review](security-evidence/2026-11-26-security-closure.md).
   Status: OPEN
5. **Tornado:** the resolved dependency graph confirms `tornado==6.6.1`; both PyPI and OSV audits report no known vulnerabilities for the resolved graph.
   Evidence: [resolved Tornado version and advisory results](security-evidence/2026-11-26-security-closure.md).
   Status: CLOSED

The Python dependency audit is clean against both PyPI and OSV for the resolved 222-package graph; this is not a whole-system scan and does not replace operating-system or bundled-native-library verification. Pillow's bundled Brotli payload and the upgraded backend compatibility suite have separate passing final-image and CI evidence. Defusedxml's PSFL metadata is verified, but project license-policy approval remains open. Production release must remain blocked until item 4 is explicitly resolved.
