from pathlib import Path


def test_production_tenant_smoke_is_get_only_and_does_not_print_bearer_tokens():
    source = Path("scripts/production_readonly_tenant_smoke.py").read_text(encoding="utf-8")

    assert 'method="GET"' in source
    for forbidden in ('method="POST"', 'method="PUT"', 'method="PATCH"', 'method="DELETE"'):
        assert forbidden not in source

    assert 'Authorization' in source
    assert "print(client_token)" not in source
    assert "print(staff_token)" not in source
    assert "print(admin_token)" not in source
    assert "NLC_PROD_CLIENT_BEARER" in source
    assert "NLC_PROD_STAFF_BEARER" in source
    assert "NLC_PROD_SUPER_ADMIN_BEARER" in source
