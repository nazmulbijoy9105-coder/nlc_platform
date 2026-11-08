# Registry fix branch (fix/canonical-registry-inc005-cap003-20261108)

## Problem
`_legacy_rule()` dropped any rule whose evidence_required was not exactly
`["DOCUMENTARY_EVIDENCE"]`. That silently excluded INC-005, INC-006, CAP-003
and left STATUTORY_RULE_REGISTRY at 82 vs engine 85.

## Status of this branch
- `scripts/apply_registry_fix.sh` — run from repo root to patch the gate.
- `canonical_architecture/statutory_rules.py` was briefly overwritten during
  tool upload; restore it from parent then apply the script:

```bash
git fetch origin
git checkout fix/canonical-registry-inc005-cap003-20261108
git checkout c6840d26ebd043c984d8120b6460c58b32615d15 -- canonical_architecture/statutory_rules.py
bash scripts/apply_registry_fix.sh
git add canonical_architecture/statutory_rules.py
git commit -m "fix: admit multi-evidence legacy rules into STATUTORY_RULE_REGISTRY"
git push
```

Or on any branch that still has the gate:

```bash
bash scripts/apply_registry_fix.sh
```
