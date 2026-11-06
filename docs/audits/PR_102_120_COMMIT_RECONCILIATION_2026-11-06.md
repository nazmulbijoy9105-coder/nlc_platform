# PR #102–#120 commit and file reconciliation — 6 November 2026

## Scope and method

This ledger compares GitHub PR metadata, changed-file lists, merge destinations and selected current-main files. It is a **path-level reconciliation**, not a complete patch-ID proof for every commit.

Important limits:
- PR #102, #105, #114, #117 and #118 exceed the GitHub commits endpoint's first-page limit of 100; the endpoint response used for this pass was capped at 100 commits for those PRs. PR metadata gives the full commit count, but this document does not claim every SHA was individually classified.
- A file appearing in both an unmerged and merged PR does not prove every change in that file was incorporated. It is a candidate for content/diff review, not proof of commit equivalence.
- A merged PR is only merged into its declared base. PR #120's base was the #107 feature branch, not main.
- Do not cherry-pick whole branches by commit count. The migration graph, current file content, legal provenance and regression tests control the decision.

## PR inventory

| PR | Commits | Files | GitHub state | Mainline disposition |
|---:|---:|---:|---|---|
| #102 | 158 | 19 | Closed, not merged | AGM evidence branch was superseded/partly ported through #103/#113 and the later #117/#118 consolidation. Its old 0045/0048 migration filenames are not in the current migration tree. |
| #103 | 26 | 12 | Merged 3 Nov | Mainline AGM/filing changes incorporated; later AGM unknown-default and provenance work superseded parts of the branch. |
| #104 | 19 | 10 | Closed, not merged | Stale schema-reconcile/CI branch. Do not restore its competing 0045 migration. |
| #105 | 428 | 68 | Closed, not merged | Large Articles verification, hard-copy evidence, signed RLS and tenant isolation branch. Articles endpoint/migrations are absent from mainline; full-document S3 upload design conflicts with the hard-copy/no-upload policy. |
| #106 | 9 | 7 | Closed, not merged | AGM notice and worker changes were subsequently touched by #113; its standalone security tenant-boundary test path remains a candidate for porting after review. |
| #107 | 77 | 22 | Closed, not merged | Signed-RLS feature branch. The exact 0049/0051 branch migrations and Articles API are not the mainline implementation; #118 introduced a different signed-identity migration path. |
| #108 | — | — | GitHub 404 | PR metadata is unavailable; do not infer its content or disposition. |
| #109 | 1 | 1 | Closed, not merged | Workflow specification only. It establishes the hard-copy/no-full-document-upload constraint; it is not a working backend workflow. |
| #110 | 1 | 0 | Merged 4 Nov | Merge-record PR only; no changed files. |
| #111 | 8 | 5 | Closed, not merged | Legal rule source corrections are not safely recoverable by branch merge. Current branch re-reconciles AGM/charge citations and adds evidence gates; standalone reconciliation test remains a candidate. |
| #112 | 10 | 2 | Closed, not merged | Dashboard/company-service changes were subsequently touched by #113. No unique changed path relative to merged PR file sets; exact patch equivalence is not asserted. |
| #113 | 9 | 7 | Merged 4 Nov | Mainline dashboard tenant scoping and AGM unknown-default changes incorporated. |
| #114 | 170 | 38 | Closed, not merged | Legal remediation work overlaps the later #117/#118 consolidation by changed-file path. No wholesale cherry-pick. |
| #115 | 69 | 25 | Closed, not merged | Legal engine/evidence changes overlap #117/#118 paths. Review individual propositions and tests; do not treat branch closure as merge. |
| #116 | 17 | 10 | Closed, not merged | PDF/score-gate work overlaps #117/#118 paths. Current PDF release gate and reconciliation tests must be evaluated on current main, not copied from this branch. |
| #117 | 364 | 97 | Merged 5 Nov | Mainline P0 consolidation. Its migration chain is the source to reconcile, not the older competing migration files from #102/#105/#107/#119. |
| #118 | 242 | 89 | Merged 5 Nov | Mainline release-gate and runtime database-role consolidation. Current code is the basis for the PR #125 remediation. |
| #119 | 3 | 2 | Closed, not merged | Do not port its competing 0048 merge migration. Its Dockerfile changes are not proof of a deployable release. |
| #120 | 3 | 2 | Merged into #107 branch | **Not merged into main.** ActivityService exception-propagation behavior is present in the current mainline service file by direct comparison; the branch-specific integration test path is not established as mainline coverage. |

## Candidate path deltas that must not be lost

These paths were changed by unmerged PRs but were not changed by the merged PR file sets (#103, #113, #117, #118). This is a **candidate list**, not proof that every behavior is absent from current code.

### PR #102
- `alembic/versions/0045_agm_evidence_nullability.py`
- `alembic/versions/0048_merge_agm_evidence_heads.py`
- `db_rules.txt`
- `docs/LAWYER_PENDING_REVIEW.md`

Disposition: old migration filenames are superseded by the current 0045–0057 graph; do not cherry-pick. Reconcile any legal/test findings individually.

### PR #104
- `alembic/versions/0045_schema_reconcile_agm.py`
- `alembic/versions/20261029_0103_b10c91ac6860_add_rescue_generation_error_to_companies.py`

Disposition: competing 0045 migration is not to be restored. The rescue-generation migration is present in the current tree; verify its exact current revision/parent rather than reapplying the PR copy.

### PR #105
- `alembic/versions/0046_schema_reconcile_agm.py`
- `alembic/versions/0047_aud003_review_state.py`
- `alembic/versions/0048_articles_verification.py`
- `alembic/versions/0049_tenant_rls_hardening.py`
- `alembic/versions/0050_agm_evidence_verification.py`
- `alembic/versions/0051_signed_rls_identity_validation.py`
- `app/api/articles.py`
- `tests/integration/test_articles_verification.py`
- `tests/integration/test_auth_rls_flows.py`
- `tests/integration/test_tenant_isolation.py`
- `tests/integration/test_tenant_rls_runtime_role.py`
- `canonical_architecture/applicability_model.py`
- `docs/RULE_IDENTITY_BUG_REPORT.md`
- `docs/LEGAL_RECONCILIATION_CHECKLIST.csv`
- `basis_audit.csv`

Disposition: Articles endpoint and its migration path are not the current mainline implementation. The original upload-oriented design must not be restored. Frontend PR #33 disables the unsafe PDF upload interface; a backend NLC-only physical-examination record workflow remains unimplemented. Reconcile rule identity findings and missing tests separately.

### PR #106
- `tests/unit/test_security_tenant_boundaries.py`

Disposition: candidate regression test. Mainline has later dashboard isolation tests, but this exact test file was not in the merged PR path set. Review and port only if it adds distinct negative cross-tenant cases.

### PR #107
- `alembic/versions/0044_webhook_schema_reconcile.py`
- `alembic/versions/0049_tenant_rls_hardening.py`
- `alembic/versions/0051_signed_rls_identity_validation.py`
- `app/api/articles.py`
- `tests/integration/test_articles_verification.py`
- `tests/integration/test_auth_rls_flows.py`
- `tests/integration/test_e2e_flow.py`
- `tests/integration/test_tenant_rls_runtime_role.py`

Disposition: old migration chain is superseded by #118's signed-identity design and PR #125's 0050 role preflight. Do not cherry-pick. Port any distinct runtime/tenant-negative tests after checking current `tests/integration/test_rls_hardening.py`.

### PR #109
- `docs/COMPANY_INFORMATION_DECLARATION_WORKFLOW.md`

Disposition: workflow specification only. Use its hard-copy/no-upload constraint; do not describe it as a completed feature.

### PR #111
- `tests/unit/test_legal_corpus_reconciliation.py`

Disposition: candidate legal regression test. Engine, canonical rule and seed files were changed by the PR, but the current PR #125 branch has separately reworked the AGM and charge legal gates. Review test assertions against current law and current engine before porting.

### PR #120
- `tests/integration/test_tenant_rls_runtime_role.py`

Disposition: the ActivityService code fix is present in mainline; this exact test path is not proven to be. Existing RLS integration tests cover signed identity and append-only activity insertion, but compare test assertions before declaring equivalence.

### PR #119
- `alembic/versions/0048_merge_agm_evidence_heads.py`

Disposition: competing migration merge; do not port. Preserve the single current migration head.

## Current follow-up work on PR #125

PR #125 is the active backend remediation branch. It contains the role-provisioning preflight, legal-score and notification release gates, rule/applicability corrections, production runtime-role guard, charge evidence requirements and regression tests. The exact current head must pass unit, integration, canonical-integrity, two-clean-PostgreSQL-upgrade and Docker-smoke jobs before merge.

## Current follow-up work on frontend PR #33

PR #33 is an open draft on `nlc_frontend`. It removes the Articles PDF file input and upload action, replacing them with a hard-copy examination notice. Its frontend CI passed on head `6b5478989326e22e3716ab8a1688729e82ccbe88`. It is a safety stop only; it does not implement the missing backend examination record.

## Release decision

- Do not merge any unmerged historical PR as a whole.
- Do not restore duplicate/parallel migration files.
- Do not restore full MOA/AOA or original RJSC-document upload.
- Do not release legal scores, RED/BLACK customer findings, rescue triggers or legal notifications until named independent Bangladesh counsel approves the rule and scoring proposition.
- No production migration, database-role alteration or Render deployment was performed during this reconciliation.
