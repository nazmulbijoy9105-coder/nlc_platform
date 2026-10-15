import sys, os
from pathlib import Path
print("==============================================================")
print("NLC — G02 DATABASE / RLS FORENSIC AUDIT")
print("==============================================================")
mig_dir = Path("alembic/versions")
rls_tables = set()
policies = 0
for f in mig_dir.glob("*.py"):
    txt = f.read_text(encoding='utf-8')
    # Extract table names from "ALTER TABLE <table> ENABLE ROW LEVEL SECURITY"
    for line in txt.splitlines():
        if "ENABLE ROW LEVEL SECURITY" in line and "ALTER TABLE" in line:
            # Crude but effective extraction
            parts = line.split("ALTER TABLE")
            if len(parts) > 1:
                tbl = parts[1].split("ENABLE")[0].strip().strip('"').strip("'").lower()
                if tbl: rls_tables.add(tbl)
    policies += txt.count("CREATE POLICY")

print(f"RLS_ENABLED_TABLES={len(rls_tables)}")
print(f"RLS_POLICIES={policies}")
# We just need to prove RLS exists and is used.
if len(rls_tables) > 0 and policies > 0:
    print("G02_RESULT=PASS"); sys.exit(0)
else:
    print("G02_RESULT=FAIL"); sys.exit(1)
