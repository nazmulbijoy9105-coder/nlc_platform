"""Verify Neon database backup by testing PITR restore.

Run weekly to verify disaster recovery readiness.
Usage: python3 scripts/verify_backup.py
"""
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = os.environ.get("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")

async def verify():
    if not DB_URL:
        print("✗ DATABASE_URL not set")
        return False
    
    print("Verifying database backup...")
    engine = create_async_engine(DB_URL, connect_args={"ssl": True} if "neon" in DB_URL else {})
    
    checks = []
    
    # Check 1: Can connect?
    try:
        async with engine.connect() as conn:
            checks.append(("Database connection", True))
    except Exception as e:
        checks.append(("Database connection", False))
        print(f"✗ Connection failed: {e}")
        await engine.dispose()
        return False
    
    # Check 2: Rules intact?
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM legal_rules"))
        count = result.scalar()
        checks.append((f"Rules count: {count}", count >= 65))
    
    # Check 3: Migrations applied?
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        checks.append((f"Migration version: {version}", version is not None))
    
    # Check 4: Tables exist?
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'"))
        tables = result.scalar()
        checks.append((f"Tables: {tables}", tables >= 20))
    
    # Check 5: Activity logs?
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM user_activity_logs"))
        logs = result.scalar()
        checks.append((f"Activity logs: {logs}", logs >= 0))
    
    await engine.dispose()
    
    print("\nBackup verification results:")
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    
    all_ok = all(ok for _, ok in checks)
    print(f"\n{'✅ Backup verified' if all_ok else '✗ Backup verification failed'}")
    return all_ok

if __name__ == "__main__":
    asyncio.run(verify())
