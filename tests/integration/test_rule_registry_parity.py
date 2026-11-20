"""Database/API/engine rule-registry parity against the seeded integration database."""
import pytest
from sqlalchemy import select, text

from app.models.rules import LegalRule
from tools.audit_rule_parity import get_engine_rules, get_seed_rules


pytestmark = [pytest.mark.integration]

# SEED-01 governance contract (scripts/seed_rules.py): the seeder inserts
# missing catalogue IDs and never touches the activation state of existing
# rows. Migration 0115 quarantined the legacy INC-001 identity in the
# append-only legal_rule_identity_archive and deliberately deferred canonical
# INC-001 activation to a future evidence-backed migration, so the seeded
# database must hold the catalogue MINUS the identity-quarantined IDs as
# active. The archive is the authoritative registry; if this query returns
# nothing on a FORCE-RLS connection, the parity assertions below must fail
# loudly rather than silently expect the full catalogue.
QUARANTINED_IDS_SQL = (
    "SELECT DISTINCT legacy_rule_id FROM legal_rule_identity_archive "
    "WHERE disposition = 'QUARANTINED_LEGACY_IDENTITY'"
)


@pytest.mark.asyncio
async def test_rule_registry_matches_engine_seed_database_and_super_admin_api(
    api_client, super_admin_headers, db
):
    engine_ids = get_engine_rules()
    seed_ids = get_seed_rules()
    db_result = await db.execute(
        select(LegalRule.rule_id).where(LegalRule.is_active.is_(True))
    )
    database_ids = set(db_result.scalars().all())

    quarantined_ids = set((await db.execute(text(QUARANTINED_IDS_SQL))).scalars())
    assert quarantined_ids, (
        "legal_rule_identity_archive returned no quarantined identities; "
        "this connection cannot see the append-only archive (FORCE RLS, no "
        "policy) so rule-activation parity cannot be asserted safely"
    )
    expected_active = seed_ids - quarantined_ids

    response = await api_client.get("/api/v1/rules?is_active=true", headers=super_admin_headers)
    assert response.status_code == 200, response.text
    api_ids = {item["rule_id"] for item in response.json()}

    assert engine_ids == seed_ids
    assert database_ids == expected_active
    assert api_ids == database_ids
