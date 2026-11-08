#!/usr/bin/env bash
# Apply canonical registry fix: admit INC-005, INC-006, CAP-003 into STATUTORY_RULE_REGISTRY
set -euo pipefail
FILE="canonical_architecture/statutory_rules.py"
if [[ ! -f "$FILE" ]]; then
  echo "Run from nlc_platform repo root (file missing: $FILE)" >&2
  exit 1
fi
python3 - <<'PY'
from pathlib import Path
path = Path("canonical_architecture/statutory_rules.py")
text = path.read_text(encoding="utf-8")
old = (
    '    if list(d["evidence_required"]) != ["DOCUMENTARY_EVIDENCE"]:\n'
    "        return None\n"
)
if old not in text:
    if "Admit both placeholder DOCUMENTARY_EVIDENCE" in text:
        print("Already fixed")
        raise SystemExit(0)
    raise SystemExit("Expected DOCUMENTARY_EVIDENCE gate not found — aborting")
new = (
    "    # Admit both placeholder DOCUMENTARY_EVIDENCE stubs and fully specified\n"
    "    # multi-item evidence lists (INC-005, INC-006, CAP-003). The previous\n"
    "    # DOCUMENTARY_EVIDENCE-only gate silently dropped those three rules and\n"
    "    # left STATUTORY_RULE_REGISTRY at 82 while the engine exposes 85.\n"
)
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Patched", path)
PY

echo "Verify:"
python3 -c "
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
print('count', len(STATUTORY_RULE_REGISTRY))
print('INC-005', 'INC-005' in STATUTORY_RULE_REGISTRY)
print('INC-006', 'INC-006' in STATUTORY_RULE_REGISTRY)
print('CAP-003', 'CAP-003' in STATUTORY_RULE_REGISTRY)
"
