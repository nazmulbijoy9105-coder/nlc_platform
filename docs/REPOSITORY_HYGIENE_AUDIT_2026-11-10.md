# Repository Hygiene Audit — 10 November 2026

**Scope:** Read-only Git tree inventory of the six accessible NLC-related repositories on their `main` branches.  
**Purpose:** Identify likely accidental, generated, duplicated or obsolete files for a later reviewed cleanup.  
**Safety:** No file was deleted, moved, renamed or executed as part of this audit.

## 1. Repository inventory

| Repository | Tracked files | Directories | Initial result |
|---|---:|---:|---|
| `nlc_platform` | 498 | 42 | Several likely one-off artifacts and duplicate files; requires reference-aware review. |
| `nlc_frontend` | 59 | 34 | Two empty root-level files with package-like names; inspect before cleanup. |
| `Nlc_Compliance-B` | 69 | 13 | No obvious backup/temp/build artifacts in tree inventory. |
| `Nlc_Compliance-F` | 24 | 12 | No obvious backup/temp/build artifacts in tree inventory. |
| `NLC_CompanyLaw-Research-B` | 11 | 1 | Small research/backend prototype; no obvious generated artifacts. |
| `-NLC_CompanyLaw-Research-F` | 9 | 1 | Small research/frontend prototype; no obvious generated artifacts. |

All six tree responses were complete (not truncated). This is a tracked-file inventory, not proof that a file is unused at runtime. GitHub code search is not a complete dependency or deployment reference graph.

## 2. High-confidence duplicate / stray candidates

| Repository / path | Evidence | Suggested disposition |
|---|---|---|
| `nlc_platform/tools/diagnostics/nlc_verify_D0-D16 (1).sh` | Same Git blob SHA and byte content as `nlc_platform/tools/diagnostics/nlc_verify_D0-D16.sh`. The duplicate suffix is not used by the script itself. | Candidate to delete after confirming no external operator documentation points to the suffixed filename. Keep the canonical unsuffixed script. |
| `nlc_platform/render.yaml.tmp` | 49-byte placeholder: “Updated worker env vars will be merged by hand”; no code-search references found. | Candidate to delete. It is not a deployment manifest; canonical Render files remain separate. |
| `nlc_frontend/eslint` | Empty file (zero bytes); not a valid ESLint config. | Candidate to delete after checking no external workflow uses this exact path. |
| `nlc_frontend/nlc-frontend@1.0.0` | Empty file (zero bytes); looks like an accidental package-name artifact. | Candidate to delete after checking no external workflow uses this exact path. |

## 3. Likely one-off patch scripts — do not execute as current maintenance tools

These root-level `nlc_platform` scripts have no code-search references by filename and appear to be historical local patch helpers:

- `_fix.py`
- `_fix_header_position.py`
- `_minimal_fixer.py`
- `_patch_utf8_and_bugfix.py`
- `phase1_quick_wins.py`

The first four rewrite headers/encoding in root verification scripts. `phase1_quick_wins.py` attempts to rewrite tests, rule-state enums, company service logic and filing transitions using text patterns and historical line assumptions. It is not a safe production maintenance command and must not be run without a fresh diff review and isolated tests.

**Suggested disposition:** mark as historical, move to a dated audit archive, or delete only after confirming no external operator workflow depends on them. Do not execute them during cleanup.

## 4. Generated audit evidence and historical backups — preserve pending retention decision

The `nlc_platform` root contains multiple JSON snapshots (`co.json`, `co2.json`, `db.json`, `hi.json`, `ra.json`, `ra2.json`, `ri.json`, `rl.json`, `ti.json`, `tm.json`) with generated timestamps and absolute Windows recovery-clone paths. Search results show some are referenced in historical audit outputs. They may be stale, but they are evidence artefacts; do not delete until their provenance and retention value are resolved.

Also preserve pending review:
- `legal_audit/backup/NLC_RECOVERY_CLONES__nlc_platform_clean__app__rule_engine__engine.py.20261030_005441.bak` — historical engine backup.
- `db_rules.txt` — explicitly documented historical database dump used by parity/audit scripts.
- `NLC_RESEARCH_EVIDENCE_CORE.txt` — historical evidence transcript containing repository-state and audit context.
- `app/static/rjsc_forms/minutes_1st_meeting.pdf` and `docs/rjsc_forms/minutes_1st_meeting.pdf` — byte-identical PDFs. The app/static copy may be runtime-served; do not remove either until route/static references and documentation intent are checked.

These are not ordinary build caches. Preserve chain-of-custody where relevant.

## 5. Diagnostic utility and operational files — retain unless proven obsolete

- `docs/redis_check.py` is a standalone Redis connectivity diagnostic. It performs PING plus SET/GET/DELETE against a short-lived key. It has no in-repository references; it should be documented as a manual diagnostic and never run against production without explicit approval.
- `tools/diagnostics/nlc_verify_D0-D16.sh` contains hard-coded Windows recovery-clone paths and historical line-number checks. Retain the canonical script only if still useful; refresh its assumptions before relying on it.
- Backup workflows under `.github/workflows/disabled/` are intentionally disabled by their path. Do not enable or delete them without verifying the current backup architecture and ownership.
- `scripts/backup_to_s3.sh`, `scripts/verify_backup.py` and backup documentation are operational controls, not junk.

## 6. Prototype repositories

The four smaller repositories (`Nlc_Compliance-B`, `Nlc_Compliance-F`, `NLC_CompanyLaw-Research-B`, `-NLC_CompanyLaw-Research-F`) contain small, coherent backend/frontend or research prototypes. No obvious temp, backup, build-output or duplicate-blob groups were found in their tracked-file trees. Their small size is not evidence that they are unused. Before archiving any, check repository activity, deployment references, README purpose, open PRs and whether the current NLC architecture imports or depends on them.

## 7. Cleanup execution plan

1. Search CI, deployment manifests, README/runbooks, scripts and code for every proposed candidate path.
2. Check commit history and last-modified context; identify whether files are relied on by local operator procedures not visible in code search.
3. Separate disposable artifacts from legal/audit evidence and operational recovery material.
4. Submit a dedicated cleanup PR with only high-confidence deletions and tests/build checks.
5. Keep archival evidence under a documented retention policy; do not mix cleanup with legal rule changes or production migrations.

## 8. Current disposition

**No deletion is authorized or performed.** The highest-confidence cleanup candidates are the duplicate suffixed shell script, the placeholder `render.yaml.tmp`, and the two empty frontend root files. One-off patch scripts are likely obsolete but need operator-workflow confirmation. Historical legal/database/audit artefacts remain preserved.

A complete reference-aware audit still requires inspecting all package/build/deployment manifests, code imports, dynamic path loads, workflow scripts, commit history, deployment references and operator runbooks for every candidate. This report records the first complete tree inventory and targeted reference checks; it does not claim that every file in every repository has been proven unused.
