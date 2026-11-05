"""Explicit, one-time Super Admin provisioning.

This command replaces unsafe automatic admin creation/password syncing during
API startup. It is dry-run by default and never prints credentials.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.models.database import AsyncSessionLocal, set_admin_context
from app.models.enums import UserRole
from app.models.user import User


async def provision(*, apply: bool, reset_password: bool) -> int:
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    full_name = os.environ.get("ADMIN_FULL_NAME", "NLC Super Admin").strip()

    if not email or not password:
        raise RuntimeError("Set ADMIN_EMAIL and ADMIN_PASSWORD in the secure environment")
    if len(password) < 16:
        raise RuntimeError("ADMIN_PASSWORD must be at least 16 characters")
    if "@" not in email:
        raise RuntimeError("ADMIN_EMAIL must be a valid email address")

    async with AsyncSessionLocal() as db:
        await set_admin_context(db)
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing is not None and existing.role != UserRole.SUPER_ADMIN:
            raise RuntimeError(
                "The email already belongs to a non-Super-Admin account; "
                "refusing automatic role promotion"
            )

        if existing is None:
            print(f"Plan: create Super Admin account for {email}")
            if apply:
                db.add(
                    User(
                        id=uuid.uuid4(),
                        email=email,
                        full_name=full_name,
                        password_hash=hash_password(password),
                        role=UserRole.SUPER_ADMIN,
                        is_active=True,
                        totp_enabled=False,
                    )
                )
        elif reset_password:
            print(f"Plan: reset password for existing Super Admin {email}")
            if apply:
                existing.password_hash = hash_password(password)
                existing.failed_login_attempts = 0
                existing.locked_until = None
                existing.is_active = True
        else:
            print(f"Super Admin {email} already exists; no changes requested")
            return 0

        if apply:
            await db.commit()
            print("Super Admin provisioning committed")
        else:
            print("DRY RUN: no database changes made; pass --apply to commit")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision the initial NLC Super Admin (dry-run by default)"
    )
    parser.add_argument("--apply", action="store_true", help="commit the requested change")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="reset an existing Super Admin password; requires --apply",
    )
    args = parser.parse_args()
    if args.reset_password and not args.apply:
        parser.error("--reset-password requires --apply")
    try:
        asyncio.run(provision(apply=args.apply, reset_password=args.reset_password))
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
