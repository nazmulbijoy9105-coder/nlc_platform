"""Regression tests for commercial conversion-funnel aggregation."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.commercial_service import EngagementService


@pytest.mark.asyncio
async def test_conversion_funnel_consumes_query_result_once():
    rows = [
        SimpleNamespace(engagement_status="IDENTIFIED", count=4, value=Decimal("400.00")),
        SimpleNamespace(engagement_status="CONFIRMED", count=2, value=Decimal("300.00")),
        SimpleNamespace(engagement_status="COMPLETED", count=1, value=Decimal("100.00")),
    ]
    result = SimpleNamespace(all=lambda: rows)
    db = SimpleNamespace(execute=AsyncMock(return_value=result))

    response = await EngagementService(db).get_conversion_funnel()

    assert response["stages"] == {
        "IDENTIFIED": {"count": 4, "value": Decimal("400.00")},
        "CONFIRMED": {"count": 2, "value": Decimal("300.00")},
        "COMPLETED": {"count": 1, "value": Decimal("100.00")},
    }
    assert response["conversion_identified_to_confirmed"] == 50.0
    assert response["conversion_confirmed_to_completed"] == 50.0
    db.execute.assert_awaited_once()
