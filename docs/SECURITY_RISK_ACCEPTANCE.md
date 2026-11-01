# Security Risk Acceptance — Known Vulnerabilities

## Accepted Risks (as of 2026-11-02)

| Package | Version | Vulnerability | Risk | Mitigation |
|---------|---------|--------------|------|------------|
| starlette | 0.41.3 | Multiple CVEs | Medium | FastAPI 0.115.5 caps at <0.42; upgrade planned |
| python-jose | 3.5.0 | PYSEC-2026-4298 | Low | No upstream fix; consider PyJWT migration |
| ecdsa | 0.19.2 | PYSEC-2026-1325 | Low | Used only for legacy JWT verification |

## Upgrade Plan
- Q1 2027: FastAPI 0.118+ + starlette 0.49+ (dedicated sprint)
- Q2 2027: Migrate python-jose to PyJWT
