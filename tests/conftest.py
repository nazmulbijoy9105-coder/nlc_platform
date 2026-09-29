import pytest
import os

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )

def pytest_collection_modifyitems(config, items):
    if os.getenv("CI"):
        skip_integration = pytest.mark.skip(reason="Requires database in CI")
        for item in items:
            if "integration" in str(item.fspath):
                item.add_marker(skip_integration)
