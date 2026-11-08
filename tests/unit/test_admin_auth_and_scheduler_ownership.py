"""Regression tests for admin identity freshness and scheduler ownership."""

import inspect

import pytest


def test_admin_router_uses_database_backed_current_user():
    from app.api import admin as admin_api
    from app.core import dependencies as core_dependencies

    assert admin_api.get_current_user is core_dependencies.get_current_user

    dependency = inspect.signature(admin_api.require_admin).parameters[
        "current_user"
    ].default
    assert dependency.dependency is core_dependencies.get_current_user

    super_admin_dependency = inspect.signature(
        admin_api.require_super_admin
    ).parameters["current_user"].default
    assert super_admin_dependency.dependency is core_dependencies.get_current_user


@pytest.mark.asyncio
async def test_legacy_scheduler_is_disabled_by_default(monkeypatch):
    import app.tasks.scheduler as scheduler_module

    monkeypatch.delenv("ENABLE_SCHEDULER", raising=False)
    monkeypatch.setattr(
        scheduler_module,
        "create_scheduler",
        lambda: pytest.fail("legacy APScheduler must remain disabled by default"),
    )
    monkeypatch.setattr(scheduler_module, "scheduler", None)

    await scheduler_module.start_scheduler()

    assert scheduler_module.scheduler is None
