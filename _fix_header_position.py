#!/usr/bin/env python3
import re
import ast
from pathlib import Path

TARGETS = [
    "verify_rls.py",
    "verify_tenant_isolation.py",
    "verify_transfer_mapping.py",
    "verify_rule_integrity.py",
    "verify_rescue_lifecycle.py",
    "verify_rjsc_api.py",
    "verify_db_ops.py",
    "verify_commercial.py",
    "verify_historical.py",
    "run_all_verifications.py",
]

HEADER_RE = re.compile(
    r"^import sys\n"
    r"try:\n"
    r"    sys\.stdout\.reconfigure\(encoding=['\"][^'\"]+['\"],\s*errors=['\"][^'\"]+['\"]\)\n"
    r"    sys\.stderr\.reconfigure\(encoding=['\"][^'\"]+['\"],\s*errors=['\"][^'\"]+['\"]\)\n"
    r"except Exception:\n"
    r"    pass\n",
    re.MULTILINE,
)

NEW_HEADER = (
    "import sys\n"
    "try:\n"
    '    sys.stdout.reconfigure(encoding="utf-8", errors="replace")\n'
    '    sys.stderr.reconfigure(encoding="utf-8", errors="replace")\n'
    "except Exception:\n"
    "    pass\n"
)


def find_insertion_point(text):
    lines = text.split("\n")
    i = 0
    if i < len(lines) and lines[i].startswith("#!"):
        i += 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i < len(lines) and (lines[i].startswith('"""') or lines[i].startswith("'''")):
        if lines[i].count('"""') >= 2 or lines[i].count("'''") >= 2:
            i += 1
        else:
            quote = '"""' if lines[i].startswith('"""') else "'''"
            i += 1
            while i < len(lines) and quote not in lines[i]:
                i += 1
            i += 1
    while i < len(lines) and re.match(r"^from\s+__future__\s+import\s+", lines[i]):
        i += 1
    while i < len(lines) and (lines[i].strip() == "" or lines[i].lstrip().startswith("#")):
        i += 1
    while i < len(lines):
        if re.match(r"^(import\s+\w|from\s+\w)", lines[i]):
            return i
        i += 1
    return len(lines)


def fix_file(path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return (False, f"could not read: {exc}")
    original = text
    matches = list(HEADER_RE.finditer(text))
    if matches:
        for m in reversed(matches):
            text = text[:m.start()] + text[m.end():]
    insert_at = find_insertion_point(text)
    if insert_at is None:
        return (False, "no insertion point found")
    lines = text.split("\n")
    lines.insert(insert_at, NEW_HEADER.rstrip("\n"))
    text = "\n".join(lines)
    if text == original:
        return (False, "no changes needed")
    try:
        path.write_text(text, encoding="utf-8")
    except Exception as exc:
        return (False, f"could not write: {exc}")
    return (True, f"removed {len(matches)} broken header(s), inserted 1 correct header at line {insert_at + 1}")


print("=== Smart UTF-8 Header Fixer ===")
print(f"Operating on: {Path.cwd()}")
print()
fixed_count = 0
for name in TARGETS:
    p = Path(name)
    if not p.exists():
        print(f"[SKIP] {name}: not found")
        continue
    changed, msg = fix_file(p)
    if changed:
        try:
            ast.parse(p.read_text(encoding="utf-8"))
            print(f"[OK ] {name}: {msg}, syntax OK")
            fixed_count += 1
        except SyntaxError as exc:
            print(f"[ERR] {name}: {msg}, BUT syntax still bad: {exc}")
    else:
        print(f"[--] {name}: {msg}")
print()
print(f"Total: {fixed_count} files fixed.")
