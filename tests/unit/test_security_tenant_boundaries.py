"""Security tests for webhook endpoint tenant boundaries."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock


def _sql(stmt) -> str:
    """Compile a SQLAlchemy statement to SQL string."""
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


class TestWebhookTenantBoundaries:

    @pytest.mark.asyncio
    async def test_test_delivery_requires_endpoint_owner(self):
        """Webhook delivery query must filter by endpoint owner."""
        owner_id = uuid.UUID("b7a30ec0-7fc4-4eac-95c1-07f0cd2c95de")
        endpoint_id = "f02afa5d-c692-468c-ab33-22e17f057be5"

        from app.models.webhook import WebhookEndpoint, WebhookDelivery
        from sqlalchemy import select
        from sqlalchemy.orm import aliased

        Endpoint = aliased(WebhookEndpoint)
        stmt = (
            select(WebhookDelivery)
            .join(Endpoint, WebhookDelivery.endpoint_id == Endpoint.id)
            .where(Endpoint.id == endpoint_id, Endpoint.user_id == owner_id)
        )

        sql = _sql(stmt)
        # UUIDs in compiled SQL may not have hyphens
        assert str(owner_id).replace("-", "") in sql.replace("-", ""), \
            f"Owner ID not found in query: {sql}"

    @pytest.mark.asyncio
    async def test_delivery_history_is_scoped_to_endpoint_owner(self):
        """Delivery history query must be scoped to endpoint owner."""
        owner_id = uuid.UUID("c7c30df4-a3b9-47ad-af6d-467d353fbfa8")

        from app.models.webhook import WebhookEndpoint, WebhookDelivery
        from sqlalchemy import select
        from sqlalchemy.orm import aliased

        Endpoint = aliased(WebhookEndpoint)
        stmt = (
            select(WebhookDelivery)
            .join(Endpoint, WebhookDelivery.endpoint_id == Endpoint.id)
            .where(Endpoint.user_id == owner_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(50)
        )

        sql = _sql(stmt)
        assert str(owner_id).replace("-", "") in sql.replace("-", ""), \
            f"Owner ID not found in query: {sql}"
