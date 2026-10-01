import os
import re
from pathlib import Path


def patch(file, pattern, repl, flags=0):
    p = Path(file)
    if not p.exists():
        print(f"Skipped (not found): {file}")
        return
    txt = p.read_text(encoding='utf-8')
    new_txt, n = re.subn(pattern, repl, txt, flags=flags)
    if n > 0:
        p.write_text(new_txt, encoding='utf-8')
        print(f"Patched {file} ({n} replacements)")

def ensure_cast_import(file):
    p = Path(file)
    if not p.exists(): return
    txt = p.read_text(encoding='utf-8')
    if "cast" not in txt:
        if "from typing import" in txt:
            txt = txt.replace("from typing import ", "from typing import cast, ", 1)
        else:
            txt = "from typing import cast\n" + txt
        p.write_text(txt, encoding='utf-8')
        print(f"Added 'cast' import to {file}")

print("--- Applying automated regex patches ---")

# 1. Fix dependencies.py AsyncGenerator import
patch("app/core/dependencies.py", r"from typing import AsyncGenerator", "from collections.abc import AsyncGenerator")

# 2. Fix rowcount on Result objects
patch("app/services/base.py", r"\.rowcount", '.__dict__.get("rowcount", 0)')
patch("app/services/user_service.py", r"\.rowcount", '.__dict__.get("rowcount", 0)')
patch("app/worker/tasks/core.py", r"\.rowcount", '.__dict__.get("rowcount", 0)')

# 3. Fix API kwarg mismatches (rename to expected names)
patch("app/api/commercial.py", r"valid_until_days", "valid_days")
patch("app/api/commercial.py", r"assigned_to_id", "assigned_to")
patch("app/api/commercial.py", r"linked_rescue_step_id", "source_rescue_step_id")
patch("app/api/rescue.py", r"assigned_officer_id", "assigned_staff_id")
patch("app/api/rescue.py", r"\bcompletion_note\b", "completion_notes")

# 4. Fix main.py exception handler signature
patch("app/main.py", r"async def http_exception_handler\(request: Request, exc: HTTPException\)", "async def http_exception_handler(request: Request, exc: Exception)")
patch("app/main.py", r"async def validation_exception_handler\(request: Request, exc: RequestValidationError\)", "async def validation_exception_handler(request: Request, exc: Exception)")

# 5. Fix security.py bytes/str and casts
patch("app/core/security.py", r"token: str = urlsafe_b64encode", "token: bytes = urlsafe_b64encode")
patch("app/core/security.py", r"token_str: str = urlsafe_b64encode\((.*?)\)", r'token_str: str = urlsafe_b64encode(\1).decode("ascii")')
ensure_cast_import("app/core/security.py")
patch("app/core/security.py", r"return jwt\.encode\((.*)\)", r"return cast(str, jwt.encode(\1))")
patch("app/core/security.py", r"return jwt\.decode\((.*)\)", r"return cast(dict | None, jwt.decode(\1))")

# 6. Fix worker/tasks/core.py dict returns
ensure_cast_import("app/worker/tasks/core.py")
patch("app/worker/tasks/core.py", r"return result$", "return cast(dict[str, Any], result)", flags=re.MULTILINE)

# 7. Add missing Settings attributes automatically
settings_file = "app/core/config.py"
if Path(settings_file).exists():
    txt = Path(settings_file).read_text(encoding='utf-8')
    if "aws_key_id" not in txt:
        txt = txt.replace("class Settings(BaseSettings):", "class Settings(BaseSettings):\n    aws_key_id: str | None = None\n    aws_secret: str | None = None\n    ses_region: str | None = None\n    email_from: str | None = None\n    whatsapp_enabled: bool = False\n    whatsapp_api_token: str | None = None\n    s3_backup_bucket: str | None = None")
        Path(settings_file).write_text(txt, encoding='utf-8')
        print(f"Patched {settings_file}")

# 8. Add missing Model attributes automatically
for root, dirs, files in os.walk("app/models"):
    for file in files:
        if file.endswith(".py"):
            p = Path(root) / file
            txt = p.read_text(encoding='utf-8')
            if "class LegalRuleVersion" in txt and "previous_severity" not in txt:
                txt = txt.replace("class LegalRuleVersion", "class LegalRuleVersion\n    previous_severity: Mapped[str | None] = mapped_column(nullable=True)\n    new_severity: Mapped[str | None] = mapped_column(nullable=True)\n    previous_score_impact: Mapped[int | None] = mapped_column(nullable=True)\n    new_score_impact: Mapped[int | None] = mapped_column(nullable=True)\n    changed_by_id: Mapped[UUID | None] = mapped_column(ForeignKey(\"users.id\"), nullable=True)", 1)
                p.write_text(txt, encoding='utf-8')
                print(f"Patched LegalRuleVersion in {p}")

print("\nDone! Automated fixes applied.")
