# Free-tier Neon backup

This workflow creates a PostgreSQL custom-format dump from the direct Neon production endpoint, checks the archive TOC and the three required evidence-table entries with `scripts/verify_backup.py`, encrypts the dump with GPG AES-256, and uploads only the encrypted archive plus its SHA-256 file as a GitHub Actions artifact.

## Required repository secrets

In GitHub: **Settings → Secrets and variables → Actions → New repository secret**.

1. `NLC_BACKUP_DATABASE_URL`: a direct Neon PostgreSQL connection URL, not a pooler URL, with `sslmode=require`. Use a dedicated backup login with only the required schema USAGE and table/sequence SELECT grants, plus BYPASSRLS so pg_dump can read every tenant's RLS-protected rows. Do not grant INSERT/UPDATE/DELETE/DDL or ownership. BYPASSRLS is still highly sensitive because it can read all tenant data; restrict the credential to this workflow and rotate it if exposed. Do not use the runtime role or the currently misconfigured migration login. Do not paste this value into chat or commit it.
2. `NLC_BACKUP_ENCRYPTION_PASSPHRASE`: a randomly generated passphrase of at least 24 characters. Store a separate copy offline (password manager or encrypted offline record). GitHub cannot recover it for you. Without it, the downloaded archive is unusable.

Do not use the runtime application's overly privileged credentials if a dedicated read-only backup login can be provisioned.

## Operation and limits

- Runs daily at 02:17 UTC and can also be started manually from **Actions → Free-tier encrypted Neon backup → Run workflow**.
- The workflow fails closed if either secret is missing, the URL is pooled/non-TLS, the archive check fails, or the encrypted file exceeds 100 MB.
- Only the encrypted archive and checksum are uploaded. The plaintext dump is removed from the runner after encryption.
- Artifacts expire after **3 days**. GitHub Free currently includes 500 MB of Actions artifact storage shared with GitHub Packages; this workflow caps each encrypted dump at 100 MB but cannot reserve storage against other repository artifacts.
- This is a short-retention convenience copy, **not a durable independent backup**. Download each artifact promptly and store it offline or in another independently controlled location. Do not assume GitHub's artifact retention is a legal-record archive.
- The workflow does not modify production data or run migrations.

## Download and verify

Download both files from the workflow run's Artifacts section. Keep the checksum and encrypted archive together.

```bash
sha256sum -c nlc-production-YYYYMMDDTHHMMSSZ.dump.gpg.sha256
gpg --output nlc-production-YYYYMMDDTHHMMSSZ.dump --decrypt nlc-production-YYYYMMDDTHHMMSSZ.dump.gpg
pg_restore --list nlc-production-YYYYMMDDTHHMMSSZ.dump
python3 scripts/verify_backup.py nlc-production-YYYYMMDDTHHMMSSZ.dump
```

Enter the passphrase locally when GPG prompts. Never put it on a command line or in a shell history.

## Restore gate

A readable archive is not a successful recovery. Restore only to a disposable, isolated Neon branch/database, never production, and verify schema, row counts, foreign keys, indexes, grants, RLS policies, tenant isolation, and application compatibility. The current three evidence tables are known to be empty in production; this workflow preserves the current state but cannot recreate historical rows that were already lost before the dump.
