"""Regression checks for migration 0006 rule ownership and downgrade safety."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "alembic" / "versions" / "0006_seed_v3_rules.py"


def test_rule_seed_uses_parameterized_insert_and_tracks_only_inserted_rows():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "ALTER COLUMN rule_type TYPE VARCHAR(50) USING rule_type::text" in source
    assert "DROP TYPE IF EXISTS rule_type" in source
    assert "INSERT INTO legal_rules" in source
    assert "ON CONFLICT (rule_id) DO NOTHING" in source
    assert "RETURNING rule_id" in source
    assert "connection.execute(insert_rule, params)" in source
    assert "if inserted_rule_id is not None:" in source
    assert "track_insert" in source
    assert "connection.execute(track_insert, {\"rule_id\": inserted_rule_id})" in source


def test_downgrade_deletes_only_migration_owned_rules_and_restores_enum_safely():
    source = MIGRATION.read_text(encoding="utf-8")
    downgrade = source.split("def downgrade():", maxsplit=1)[1]

    assert "DELETE FROM legal_rules" in downgrade
    assert "SELECT rule_id FROM _nlc_migration_0006_seeded_rule_ids" in downgrade
    assert "op.drop_table(\"_nlc_migration_0006_seeded_rule_ids\")" in downgrade
    assert "WHERE rule_type NOT IN" in downgrade
    assert "CREATE TYPE rule_type AS ENUM" in downgrade
    assert "ALTER COLUMN rule_type TYPE rule_type" in downgrade
    assert "            $$;" in downgrade
    assert "DELETE FROM legal_rules WHERE rule_id IN (" not in downgrade
