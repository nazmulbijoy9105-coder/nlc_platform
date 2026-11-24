# Security Remediation Status

Updated: 2026-11-22

This document records the remediation state for the dependency and application
security findings tracked in the security/remediate-12-findings pull request.

## Remediated in this branch

| Finding | Change |
|---|---|
| Starlette range-header / related advisories | Upgrade FastAPI to 0.165.0 and Starlette to 1.10.0. The FastAPI release line requires a newer Starlette baseline; retain the exact pins together and verify the resolved dependency graph in CI. |
| python-jose / ECDSA Minerva | Replace python-jose with PyJWT 2.15.1; update token implementation and the direct token test import; remove the direct ecdsa pin. Token type, expiry, algorithm allow-list, JTI, refresh and temporary-token behavior remain enforced by the application. |
| Brotli | Upgrade the direct Brotli dependency to 1.2.1. |
| Pillow | Upgrade Pillow to 13.0.0 for the reported Pillow package advisories. **Residual platform-specific issue:** upstream Pillow 13.0.0 wheels were reported to bundle Brotli 1.2.0 in pillow.libs. The direct Brotli pin does not replace that bundled copy. The NLC Dockerfile uses CPython 3.11, while the currently documented community-rebuilt wheel is CPython 3.12/Linux x86_64 only; do not install that incompatible third-party artifact. Keep this gate open until an upstream Pillow release or a separately built, reviewed CPython 3.11 wheel is verified to contain the upstream Brotli fix and passes Pillow's tests. |
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

## Accepted residual risk — Pillow's bundled Brotli decoder

Pillow 13.0.0 wheels may bundle Brotli 1.2.0 under `pillow.libs/`. The direct
`brotli==1.2.1` pin does not replace or patch that private decoder. The
vulnerable decoder is reached through FreeType's WOFF2 font decompression path.
The application source currently has no direct `PIL` imports, which reduces
the apparent direct exposure; it does **not** establish that the decoder is
unreachable. Indirect consumers (including WeasyPrint and the OCR dependency
stack) have not yet been fully audited for Pillow use or untrusted WOFF2 input.

**Decision:** provisionally accept this residual risk until an upstream Pillow
wheel with the fixed bundled decoder is available, or a reviewed CPython 3.11
wheel is built from the 13.0.0 sdist against Brotli 1.2.1. Do not treat the
separate Brotli package pin as closure evidence. Keep the finding open and do
not deploy on the strength of the top-level pin alone.

**Closure gate — record evidence against the exact production wheel/image:**

```sh
# Inspect the wheel before installation.
unzip -l pillow-*.whl | grep -E 'pillow.libs/libbrotli(dec|common)'

# Or inspect the installed Pillow payload in the built image.
python - <<'PY'
from pathlib import Path
import re
import PIL

libdir = Path(PIL.__file__).resolve().parent.parent / "pillow.libs"
matches = sorted(
    p.name for p in libdir.glob("libbrotli*")
    if "brotlidec" in p.name or "brotlicommon" in p.name
)
print("\n".join(matches))
assert matches, "No bundled Brotli libraries found; inspect the wheel/build linkage"
for name in matches:
    version = re.search(r"\.so\.(\d+\.\d+\.\d+)$", name)
    assert version and tuple(map(int, version.group(1).split("."))) >= (1, 2, 1), name
assert any("brotlidec" in name for name in matches), "Bundled decoder library missing"
assert any("brotlicommon" in name for name in matches), "Bundled common library missing"
PY
```

Retain the wheel SHA-256, Python/platform tag, Pillow build provenance, the
Brotli version evidence, and Pillow's full test-suite result with the CI
artifact. For a custom wheel, also record that the CPython 3.11/Linux target
matches the production image. Re-run this gate against the final image rather
than relying only on a locally inspected wheel.

## Findings requiring verification before closure

1. **Pillow's bundled Brotli copy:** inspect the actual wheel installed in the
   production image. A top-level `brotli==1.2.1` does not patch a private
   `pillow.libs/libbrotli*` copy. The closure procedure and provisional
   residual-risk decision are recorded above.
2. **Full dependency graph:** run `pip-audit -r requirements.txt` against the
   resolved production environment and retain the machine-readable report.
3. **Compatibility:** run the complete backend suite against the upgraded
   FastAPI/Starlette, filelock, Pillow, and other dependency versions before
   deployment. Do not deploy this branch based only on successful resolution.
4. **Defusedxml license classifier:** the reported item is a license-identification
   finding, not by itself a demonstrated exploitable security vulnerability.
   Confirm the package's actual license metadata and the project's license policy.
5. **Tornado:** upgraded to 6.6.1. This is required because 6.5.10 remains
   affected by the October/November 2026 RedirectHandler open-redirect and related
   advisories; 6.6.1 includes the subsequent triple-slash redirect fix.

No production deployment, test-suite pass, or clean vulnerability scan is claimed
by this document. Closure requires recorded CI and production-artifact evidence.
