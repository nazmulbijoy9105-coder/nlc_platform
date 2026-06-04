from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models.database import get_db_for_user

router = APIRouter()


async def require_admin(current_user=Depends(get_current_user)):
    role = current_user.role if hasattr(current_user, "role") else current_user.get("role", "")
    if str(role) not in ("SUPER_ADMIN", "ADMIN_STAFF"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user




@router.get("/dashboard")
async def admin_dashboard(
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db_for_user),
):
    from sqlalchemy import select
    from app.models.company import Company
    activities = []
    try:
        r = await db.execute(select(Company).where(Company.last_evaluated_at.isnot(None)).order_by(Company.last_evaluated_at.desc()).limit(5))
        for co in r.scalars().all():
            score = co.current_compliance_score or co.compliance_score or 0
            activities.append({"id": str(co.id), "message": f"Evaluation for {co.name or co.company_name or 'Unknown'} - Score: {score}/100", "actor": "Rule Engine", "created_at": co.last_evaluated_at.isoformat() if co.last_evaluated_at else "", "type": "EVALUATION" if score >= 50 else "VIOLATION"})
    except Exception:
        pass
    try:
        from app.models.filings import Filing
        r = await db.execute(select(Filing).order_by(Filing.created_at.desc()).limit(5))
        for fl in r.scalars().all():
            activities.append({"id": str(fl.id), "message": f"{fl.filing_type or 'Filing'} created", "actor": "System", "created_at": fl.created_at.isoformat() if hasattr(fl, 'created_at') and fl.created_at else "", "type": "FILING"})
    except Exception:
        pass
    try:
        from app.models.documents import GeneratedDocument
        r = await db.execute(select(GeneratedDocument).order_by(GeneratedDocument.created_at.desc()).limit(5))
        for doc in r.scalars().all():
            activities.append({"id": str(doc.id), "message": f"Document '{doc.title or 'Untitled'} - {doc.status or 'DRAFT'}", "actor": "AI Assistant", "created_at": doc.created_at.isoformat() if hasattr(doc, 'created_at') and doc.created_at else "", "type": "DOCUMENT"})
    except Exception:
        pass
    activities.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return activities[:15]

class UserListItem(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    class Config:
        from_attributes = True

class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    password: str

class UserCreateResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    class Config:
        from_attributes = True


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db_for_user),
):
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    )
    users = result.scalars().all()
    return [UserListItem(id=str(u.id), email=u.email, full_name=u.full_name, role=str(u.role), is_active=u.is_active) for u in users]


@router.post("/users", response_model=UserCreateResponse, status_code=201)
async def create_user(
    body: UserCreateRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db_for_user),
):
    from sqlalchemy import select
    from app.models.user import User
    from app.models.enums import UserRole
    import bcrypt

    valid_roles = {r.value for r in UserRole}
    if body.role not in valid_roles:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {sorted(valid_roles)}")
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = User(email=body.email, full_name=body.full_name, role=UserRole(body.role), password_hash=hashed, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserCreateResponse(id=str(user.id), email=user.email, full_name=user.full_name, role=str(user.role), is_active=user.is_active)


@router.patch("/users/{user_id}/deactivate", status_code=200)
async def deactivate_user(user_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db_for_user)):
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.user import User
    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid user ID")
    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    current_id = str(admin.id) if hasattr(admin, "id") else admin.get("id", "")
    if str(uid) == current_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    user.is_active = False
    await db.commit()
    return {"id": user_id, "is_active": False}


@router.patch("/users/{user_id}/reactivate", status_code=200)
async def reactivate_user(user_id: str, admin=Depends(require_admin), db: AsyncSession = Depends(get_db_for_user)):
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.user import User
    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid user ID")
    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await db.commit()
    return {"id": user_id, "is_active": True}
