with open('app/main.py', 'rb') as f:
    lines = f.readlines()
sep = b'\r\n' if b'\r\n' in lines[0] else b'\n'

insert = [
    b'    # Auto-create admin user from env vars if not exists' + sep,
    b'    try:' + sep,
    b'        _ae = settings.ADMIN_EMAIL' + sep,
    b'        _ap = settings.ADMIN_PASSWORD' + sep,
    b'        if _ae and _ap:' + sep,
    b'            from sqlalchemy import select as _sel' + sep,
    b'            from app.models.user import User as _User' + sep,
    b'            from app.core.security import hash_password as _hp' + sep,
    b'            from app.models.database import AsyncSessionLocal as _ASL' + sep,
    b'            import uuid as _uuid' + sep,
    b'            async with _ASL() as _db:' + sep,
    b'                _ex = await _db.execute(_sel(_User).where(_User.email == _ae))' + sep,
    b'                if not _ex.scalar_one_or_none():' + sep,
    b'                    _db.add(_User(id=_uuid.uuid4(), email=_ae, password_hash=_hp(_ap),' + sep,
    b'                        full_name="NLC Super Admin", role="SUPER_ADMIN",' + sep,
    b'                        is_active=True, requires_2fa=False))' + sep,
    b'                    await _db.commit()' + sep,
    b'                    logger.info("admin_auto_created", email=_ae)' + sep,
    b'    except Exception as _e:' + sep,
    b'        logger.warning("admin_auto_create_failed", error=str(_e))' + sep,
]

new_lines = []
for line in lines:
    new_lines.append(line)
    if b'logger.info("db_connectivity_ok")' in line:
        new_lines.extend(insert)

with open('app/main.py', 'wb') as f:
    f.writelines(new_lines)
print('Done')
