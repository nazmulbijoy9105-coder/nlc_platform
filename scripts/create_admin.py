"""
Run once on Render via: python scripts/create_admin.py
Creates SUPER_ADMIN user from ADMIN_EMAIL + ADMIN_PASSWORD env vars.
"""
import asyncio, os, uuid, datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from passlib.context import CryptContext

async def main():
    db_url = os.environ["DATABASE_URL"]
    email = os.environ["ADMIN_EMAIL"]
    password = os.environ["ADMIN_PASSWORD"]

    engine = create_async_engine(db_url)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd.hash(password)
    uid = str(uuid.uuid4())
    now = datetime.datetime.utcnow()

    async with Session() as session:
        await session.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, role, is_active, requires_2fa, created_at, updated_at)
            VALUES (:id, :email, :pw, :name, :role, true, false, :now, :now)
            ON CONFLICT (email) DO UPDATE SET password_hash=:pw, role=:role, is_active=true
        """), {"id": uid, "email": email, "pw": hashed,
               "name": "NLC Super Admin", "role": "SUPER_ADMIN", "now": now})
        await session.commit()
        print(f"Admin created: {email}")
    await engine.dispose()

asyncio.run(main())
