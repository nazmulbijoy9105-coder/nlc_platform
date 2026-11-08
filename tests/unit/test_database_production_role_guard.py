"""Production cannot disable the least-privilege runtime database role guard."""
import os
import subprocess
import sys


def test_production_rejects_explicitly_disabling_rls_runtime_role_guard():
    env = os.environ.copy()
    env.pop("APP_DATABASE_URL", None)
    env["ENVIRONMENT"] = "production"
    env["REQUIRE_RLS_APP_ROLE"] = "false"
    env["DATABASE_URL"] = "postgresql://user:password@localhost/test"

    result = subprocess.run(
        [sys.executable, "-c", "import app.models.database"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "REQUIRE_RLS_APP_ROLE cannot be disabled in production" in result.stderr
