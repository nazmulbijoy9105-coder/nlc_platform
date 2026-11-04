"""Database/API/engine rule-registry parity against the seeded integration database."""
import pytest
from sqlalchemy import select

from app.models.rules import LegalRule
from tools.audit_rule_parity import get_engine_rules, get_seed_rules


pytestmark = [pytest.mark.integration]


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

    response = await api_client.get("/api/v1/rules", headers=super_admin_headers)
    assert response.status_code == 200, response.text
    api_ids = {item["rule_id"] for item in response.json()}

    assert engine_ids == seed_ids
    assert database_ids == seed_ids
    assert api_ids == database_ids
