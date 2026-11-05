"""PostgreSQL persistence contract for evidence-only severity."""
import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_not_evaluated_is_a_persistable_severity_enum_value(db):
    result = await db.execute(
        text("SELECT 'NOT_EVALUATED'::severity_level::text")
    )
    assert result.scalar_one() == "NOT_EVALUATED"
