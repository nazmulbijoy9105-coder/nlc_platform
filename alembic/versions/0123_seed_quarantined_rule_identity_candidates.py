"""Seed quarantined canonical identity candidates without legal/history attribution.

Revision ID: 0123_seed_quarantined_rule_identity_candidates
Revises: 0122_rls_staff_scope_and_score_history

This migration gives every registered engine rule a stable UUID candidate. It
does not resolve legal equivalence, assign effective dates, create revisions,
activate identities, alter legal_rules, or rewrite historical findings.
"""
from alembic import op

revision = "0123_seed_quarantined_rule_identity_candidates"
down_revision = "0122_rls_staff_scope_and_score_history"
branch_labels = None
depends_on = None

_RULE_IDS = (
    "INC-001",
    "INC-003",
    "INC-004",
    "INC-005",
    "INC-006",
    "AUD-001",
    "AUD-002",
    "AUD-003",
    "AUD-004",
    "AGM-001",
    "AGM-002",
    "AGM-003",
    "AGM-004",
    "AGM-005",
    "AGM-006",
    "AR-001",
    "AR-002",
    "AR-003",
    "AR-004",
    "DIR-001",
    "DIR-002",
    "DIR-003",
    "DIR-004",
    "SH-001",
    "SH-002",
    "SH-003",
    "TR-001",
    "TR-002",
    "TR-003",
    "TR-004",
    "TR-005",
    "TR-006",
    "REG-001",
    "REG-002",
    "REG-003",
    "OFF-001",
    "CAP-001",
    "CAP-002",
    "CAP-003",
    "CAP-004",
    "TAX-001",
    "TAX-002",
    "ESC-001",
    "ESC-002",
    "ESC-003",
    "AGM-007",
    "AUD-005",
    "BNK-001",
    "BNK-002",
    "BNK-003",
    "BSEC-001",
    "BSEC-002",
    "BSEC-003",
    "BSEC-004",
    "CHG-001",
    "DEF-001",
    "DEF-002",
    "DIR-005",
    "DIR-006",
    "ESC-004",
    "ESC-005",
    "FX-001",
    "LBR-001",
    "LBR-002",
    "LBR-003",
    "STR-001",
    "STR-002",
    "STR-003",
    "TAX-003",
    "TAX-004",
    "TL-001",
    "TL-002",
    "VAT-002",
    "VAT-003",
    "BOD-001",
    "BOD-002",
    "BOD-003",
    "ACC-001",
    "ACC-002",
    "ACC-003",
    "DIR-007",
    "DIR-008",
    "DIR-010",
    "MEM-001",
    "INC-007",
)


def upgrade() -> None:
    # Migration-owner-only policies make the data seed explicit even when
    # FORCE ROW LEVEL SECURITY is enabled. Runtime and audit roles remain read-only.
    op.execute("""
        DO $policy$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_migration_owner') THEN
                EXECUTE 'DROP POLICY IF EXISTS legal_rule_identities_migration_owner_all ON public.legal_rule_identities';
                EXECUTE 'CREATE POLICY legal_rule_identities_migration_owner_all '
                    || 'ON public.legal_rule_identities FOR ALL TO nlc_migration_owner '
                    || 'USING (current_user = ''nlc_migration_owner'') '
                    || 'WITH CHECK (current_user = ''nlc_migration_owner'')';

                EXECUTE 'DROP POLICY IF EXISTS legal_rule_aliases_migration_owner_all ON public.legal_rule_aliases';
                EXECUTE 'CREATE POLICY legal_rule_aliases_migration_owner_all '
                    || 'ON public.legal_rule_aliases FOR ALL TO nlc_migration_owner '
                    || 'USING (current_user = ''nlc_migration_owner'') '
                    || 'WITH CHECK (current_user = ''nlc_migration_owner'')';

                EXECUTE 'DROP POLICY IF EXISTS legal_rule_revisions_migration_owner_all ON public.legal_rule_revisions';
                EXECUTE 'CREATE POLICY legal_rule_revisions_migration_owner_all '
                    || 'ON public.legal_rule_revisions FOR ALL TO nlc_migration_owner '
                    || 'USING (current_user = ''nlc_migration_owner'') '
                    || 'WITH CHECK (current_user = ''nlc_migration_owner'')';
            END IF;
        END
        $policy$
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_rule_identity_candidate_basis
        ON public.legal_rule_identities (creation_basis)
        WHERE creation_basis LIKE 'NLC_ENGINE_RULE_ID_CANDIDATE:%'
    """)

    op.execute("""
        WITH candidates(rule_id) AS (
            VALUES
            ('INC-001'),
            ('INC-003'),
            ('INC-004'),
            ('INC-005'),
            ('INC-006'),
            ('AUD-001'),
            ('AUD-002'),
            ('AUD-003'),
            ('AUD-004'),
            ('AGM-001'),
            ('AGM-002'),
            ('AGM-003'),
            ('AGM-004'),
            ('AGM-005'),
            ('AGM-006'),
            ('AR-001'),
            ('AR-002'),
            ('AR-003'),
            ('AR-004'),
            ('DIR-001'),
            ('DIR-002'),
            ('DIR-003'),
            ('DIR-004'),
            ('SH-001'),
            ('SH-002'),
            ('SH-003'),
            ('TR-001'),
            ('TR-002'),
            ('TR-003'),
            ('TR-004'),
            ('TR-005'),
            ('TR-006'),
            ('REG-001'),
            ('REG-002'),
            ('REG-003'),
            ('OFF-001'),
            ('CAP-001'),
            ('CAP-002'),
            ('CAP-003'),
            ('CAP-004'),
            ('TAX-001'),
            ('TAX-002'),
            ('ESC-001'),
            ('ESC-002'),
            ('ESC-003'),
            ('AGM-007'),
            ('AUD-005'),
            ('BNK-001'),
            ('BNK-002'),
            ('BNK-003'),
            ('BSEC-001'),
            ('BSEC-002'),
            ('BSEC-003'),
            ('BSEC-004'),
            ('CHG-001'),
            ('DEF-001'),
            ('DEF-002'),
            ('DIR-005'),
            ('DIR-006'),
            ('ESC-004'),
            ('ESC-005'),
            ('FX-001'),
            ('LBR-001'),
            ('LBR-002'),
            ('LBR-003'),
            ('STR-001'),
            ('STR-002'),
            ('STR-003'),
            ('TAX-003'),
            ('TAX-004'),
            ('TL-001'),
            ('TL-002'),
            ('VAT-002'),
            ('VAT-003'),
            ('BOD-001'),
            ('BOD-002'),
            ('BOD-003'),
            ('ACC-001'),
            ('ACC-002'),
            ('ACC-003'),
            ('DIR-007'),
            ('DIR-008'),
            ('DIR-010'),
            ('MEM-001'),
            ('INC-007')
        )
        INSERT INTO public.legal_rule_identities (
            jurisdiction,
            obligation_key,
            identity_status,
            creation_basis,
            created_by
        )
        SELECT
            'BD',
            NULL,
            'QUARANTINED',
            'NLC_ENGINE_RULE_ID_CANDIDATE:' || candidates.rule_id,
            'migration:0123_seed_quarantined_rule_identity_candidates'
        FROM candidates
        ON CONFLICT DO NOTHING
    """)

    # Only the 84 non-colliding active legacy rows receive unresolved aliases.
    # INC-001 is intentionally not aliased: its historical section-9 row was
    # quarantined and must not be attributed to the engine's section-23 candidate.
    op.execute("""
        INSERT INTO public.legal_rule_aliases (
            canonical_rule_id,
            source_namespace,
            historical_rule_id,
            resolution_status,
            mapping_basis
        )
        SELECT
            identity.id,
            'nlc_platform.legal_rules',
            substring(
                identity.creation_basis
                from length('NLC_ENGINE_RULE_ID_CANDIDATE:') + 1
            ),
            'UNRESOLVED',
            'Identifier-only candidate linkage; no statutory equivalence, revision, '
            || 'or historical finding attribution is asserted.'
        FROM public.legal_rule_identities identity
        JOIN public.legal_rules legacy
          ON legacy.rule_id = substring(
              identity.creation_basis
              from length('NLC_ENGINE_RULE_ID_CANDIDATE:') + 1
          )
         AND legacy.is_active IS TRUE
        WHERE identity.creation_basis LIKE 'NLC_ENGINE_RULE_ID_CANDIDATE:%'
          AND legacy.rule_id <> 'INC-001'
          AND legacy.rule_id <> 'INC-002'
        ON CONFLICT (
            source_namespace, historical_rule_id, canonical_rule_id
        ) DO NOTHING
    """)

    op.execute("""
        DO $validate$
        DECLARE
            identity_rows bigint;
            alias_rows bigint;
            unresolved_alias_rows bigint;
            non_quarantined_rows bigint;
            active_rule_ids bigint;
            candidate_revision_rows bigint;
        BEGIN
            SELECT count(*) INTO identity_rows
              FROM public.legal_rule_identities
             WHERE creation_basis LIKE 'NLC_ENGINE_RULE_ID_CANDIDATE:%';
            IF identity_rows <> 85 THEN
                RAISE EXCEPTION
                    'Expected 85 quarantined identity candidates, found %',
                    identity_rows;
            END IF;

            SELECT count(DISTINCT rule_id) INTO active_rule_ids
              FROM public.legal_rules
             WHERE is_active IS TRUE
               AND rule_id <> 'INC-001'
               AND rule_id <> 'INC-002';
            IF active_rule_ids <> 84 THEN
                RAISE EXCEPTION
                    'Expected 84 non-colliding active legal rule IDs, found %',
                    active_rule_ids;
            END IF;

            SELECT count(*) INTO alias_rows
              FROM public.legal_rule_aliases
             WHERE source_namespace = 'nlc_platform.legal_rules';
            IF alias_rows <> 84 THEN
                RAISE EXCEPTION
                    'Expected 84 unresolved identifier aliases, found %',
                    alias_rows;
            END IF;

            SELECT count(*) INTO unresolved_alias_rows
              FROM public.legal_rule_aliases
             WHERE source_namespace = 'nlc_platform.legal_rules'
               AND resolution_status = 'UNRESOLVED';
            IF unresolved_alias_rows <> 84 THEN
                RAISE EXCEPTION
                    'Expected 84 unresolved aliases, found %',
                    unresolved_alias_rows;
            END IF;

            SELECT count(*) INTO non_quarantined_rows
              FROM public.legal_rule_identities
             WHERE creation_basis LIKE 'NLC_ENGINE_RULE_ID_CANDIDATE:%'
               AND identity_status <> 'QUARANTINED';
            IF non_quarantined_rows <> 0 THEN
                RAISE EXCEPTION
                    'Identity candidate seed unexpectedly activated % rows',
                    non_quarantined_rows;
            END IF;

            SELECT count(*) INTO candidate_revision_rows
              FROM public.legal_rule_revisions revision
              JOIN public.legal_rule_identities identity
                ON identity.id = revision.canonical_rule_id
             WHERE identity.creation_basis LIKE 'NLC_ENGINE_RULE_ID_CANDIDATE:%';
            IF candidate_revision_rows <> 0 THEN
                RAISE EXCEPTION
                    'Identity candidate seed must not invent effective-dated revisions';
            END IF;
        END
        $validate$
    """)

    # Read-only audit views expose aggregate identity and full tenant-table RLS
    # inventory without granting the audit role access to tenant/legal rows.
    op.execute("""
        CREATE VIEW audit.canonical_identity_parity AS
        SELECT
            count(*) FILTER (
                WHERE creation_basis LIKE 'NLC_ENGINE_RULE_ID_CANDIDATE:%'
            )::integer AS candidate_identity_rows,
            count(*) FILTER (
                WHERE creation_basis LIKE 'NLC_ENGINE_RULE_ID_CANDIDATE:%'
                  AND identity_status = 'QUARANTINED'
            )::integer AS quarantined_candidate_identity_rows,
            count(*) FILTER (
                WHERE creation_basis LIKE 'NLC_ENGINE_RULE_ID_CANDIDATE:%'
                  AND identity_status = 'ACTIVE'
            )::integer AS active_candidate_identity_rows,
            (
                SELECT count(*)::integer
                FROM public.legal_rule_aliases
                WHERE source_namespace = 'nlc_platform.legal_rules'
            ) AS candidate_alias_rows,
            (
                SELECT count(*)::integer
                FROM public.legal_rule_aliases
                WHERE source_namespace = 'nlc_platform.legal_rules'
                  AND resolution_status = 'UNRESOLVED'
            ) AS unresolved_candidate_alias_rows,
            (
                SELECT count(*)::integer
                FROM public.legal_rule_aliases
                WHERE source_namespace = 'nlc_platform.legal_rules'
                  AND resolution_status = 'RESOLVED'
            ) AS resolved_candidate_alias_rows,
            (
                SELECT count(*)::integer
                FROM public.legal_rule_revisions revision
                JOIN public.legal_rule_identities identity
                  ON identity.id = revision.canonical_rule_id
                WHERE identity.creation_basis LIKE 'NLC_ENGINE_RULE_ID_CANDIDATE:%'
            ) AS candidate_revision_rows
        FROM public.legal_rule_identities
    """)

    op.execute("""
        CREATE VIEW audit.tenant_rls_parity AS
        WITH inventory AS (
            SELECT
                c.relname AS table_name,
                c.relrowsecurity AS rls_enabled,
                c.relforcerowsecurity AS force_rls,
                count(p.policyname)::integer AS policy_count
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a
              ON a.attrelid = c.oid
             AND a.attname = 'company_id'
             AND NOT a.attisdropped
            LEFT JOIN pg_policies p
              ON p.schemaname = n.nspname
             AND p.tablename = c.relname
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
            GROUP BY c.relname, c.relrowsecurity, c.relforcerowsecurity
        )
        SELECT
            count(*)::integer AS tenant_company_id_tables,
            count(*) FILTER (
                WHERE rls_enabled AND force_rls AND policy_count > 0
            )::integer AS tenant_rls_forced_tables,
            count(*) FILTER (
                WHERE NOT rls_enabled OR NOT force_rls OR policy_count = 0
            )::integer AS tenant_rls_missing_tables,
            (
                count(*) > 0
                AND count(*) FILTER (
                    WHERE NOT rls_enabled OR NOT force_rls OR policy_count = 0
                ) = 0
            ) AS tenant_rls_inventory_complete,
            coalesce(
                jsonb_agg(
                    jsonb_build_object(
                        'table_name', table_name,
                        'rls_enabled', rls_enabled,
                        'force_rls', force_rls,
                        'policy_count', policy_count
                    )
                    ORDER BY table_name
                ),
                '[]'::jsonb
            ) AS table_inventory
        FROM inventory
    """)

    for view in ("canonical_identity_parity", "tenant_rls_parity"):
        op.execute(
            f"REVOKE ALL ON TABLE audit.{view} FROM PUBLIC, nlc_app_role"
        )
        op.execute(
            f"GRANT SELECT ON TABLE audit.{view} TO nlc_ci_audit_role"
        )


def downgrade() -> None:
    raise RuntimeError(
        "0123 is forward-only: candidate identity records are immutable audit data; "
        "retire or supersede them through a separately reviewed forward migration."
    )
