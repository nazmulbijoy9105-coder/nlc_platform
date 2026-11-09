"""Regression tests for signed administrative notification migration writes."""
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = (
    "alembic/versions/0058_suppress_unreleased_rule_notifications.py",
    "alembic/versions/0074_legal_release_quarantine.py",
)


@pytest.mark.parametrize("relative_path", MIGRATIONS)
def test_notification_suppression_uses_verified_transaction_local_admin(relative_path):
    source = (ROOT / relative_path).read_text(encoding="utf-8")

    identity_setup = source.index(
        "set_config('app.current_user_id', 'ADMIN', TRUE)"
    )
    notification_update = source.index("UPDATE public.notifications")
    assert identity_setup < notification_update

    assert "FROM nlc_private.rls_signing_key" in source
    assert "public.hmac(" in source
    assert "convert_to('ADMIN', 'UTF8')" in source
    assert "set_config(\n                'app.current_user_signature'" in source
    assert "length(stored_secret) < 32" in source

    # The signed authority is explicitly cleared after the protected write.
    clear_identity = source.index(
        "set_config('app.current_user_id', '', TRUE)",
        notification_update,
    )
    clear_signature = source.index(
        "set_config('app.current_user_signature', '', TRUE)",
        notification_update,
    )
    assert notification_update < clear_identity
    assert notification_update < clear_signature

    # Never solve the migration conflict by disabling the security trigger.
    assert "DISABLE TRIGGER" not in source.upper()
