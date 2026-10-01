import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.dependencies import get_db, get_db_for_user

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
            score = co.current_compliance_score or co.compliance_score or 0  # type: ignore[attr-defined]
            activities.append({"id": str(co.id), "message": f"Evaluation for {co.name or co.company_name or 'Unknown'} - Score: {score}/100", "actor": "Rule Engine", "created_at": co.last_evaluated_at.isoformat() if co.last_evaluated_at else "", "type": "EVALUATION" if score >= 50 else "VIOLATION"})  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        from app.models.filings import Filing  # type: ignore[attr-defined]
        r = await db.execute(select(Filing).order_by(Filing.created_at.desc()).limit(5))
        for fl in r.scalars().all():
            activities.append({"id": str(fl.id), "message": f"{fl.filing_type or 'Filing'} created", "actor": "System", "created_at": fl.created_at.isoformat() if hasattr(fl, 'created_at') and fl.created_at else "", "type": "FILING"})  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        from app.models.documents import GeneratedDocument  # type: ignore[attr-defined]
        r = await db.execute(select(GeneratedDocument).order_by(GeneratedDocument.created_at.desc()).limit(5))
        for doc in r.scalars().all():
            activities.append({"id": str(doc.id), "message": f"Document '{doc.title or 'Untitled'} - {doc.status or 'DRAFT'}", "actor": "AI Assistant", "created_at": doc.created_at.isoformat() if hasattr(doc, 'created_at') and doc.created_at else "", "type": "DOCUMENT"})  # type: ignore[attr-defined]
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

    from app.models.enums import UserRole
    from app.models.user import User

    valid_roles = {r.value for r in UserRole}
    if body.role not in valid_roles:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {sorted(valid_roles)}")
    caller = getattr(admin, "role", None)
    caller = str(getattr(caller, "value", caller))
    if body.role == "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="SUPER_ADMIN cannot be created via API")
    if body.role == "ADMIN_STAFF" and caller != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Only SUPER_ADMIN can create admin staff")
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    # Validate password strength
    is_strong, msg = validate_password_strength(body.password)
    if not is_strong:
        raise HTTPException(status_code=422, detail=msg)
    hashed = hash_password(body.password)
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


import csv
import io

from fastapi.responses import StreamingResponse

from app.core.security import hash_password, validate_password_strength


@router.get("/activity-logs/export")
async def export_activity_logs(
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db_for_user),
    days: int = 30,
):
    """Export activity logs as CSV for auditors."""
    from sqlalchemy import text
    result = await db.execute(
        text(f"SELECT user_id, company_id, action, resource_type, resource_id, description, ip_address, logged_at FROM user_activity_logs WHERE logged_at >= NOW() - INTERVAL '{days} days' ORDER BY logged_at DESC LIMIT 10000")
    )
    rows = result.fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "company_id", "action", "resource_type", "resource_id", "description", "ip_address", "logged_at"])
    for row in rows:
        writer.writerow([str(v) if v else "" for v in row])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=activity_logs_{days}days.csv"}
    )


@router.post("/cron/evaluate-all")
async def cron_evaluate_all(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Cron-triggered evaluation of all active companies.
    
    Protected by CRON_SECRET env var. Use with cron-job.org or GitHub Actions.
    Example: curl -X POST URL/api/v1/admin/cron/evaluate-all -H "X-Cron-Secret: your_secret"
    """
    import os
    # CRON_SECRET is optional — if not set, endpoint is open (for free tier)
    cron_secret = os.environ.get("CRON_SECRET", "")
    if cron_secret:
        provided = request.headers.get("X-Cron-Secret", "")
        if provided != cron_secret:
            raise HTTPException(status_code=403, detail="Invalid cron secret")
    
    try:
        from sqlalchemy import text
        result = await db.execute(text("SELECT id FROM companies WHERE is_active = true"))
        company_ids = [str(row[0]) for row in result.fetchall()]
    except Exception as e:
        return {"status": "error", "detail": f"DB query failed: {str(e)[:100]}", "timestamp": int(time.time())}
    
    evaluated = 0
    errors = 0
    results = []
    for company_id in company_ids:
        try:
            from app.services.compliance_service import ComplianceService
            svc = ComplianceService(db)
            result = await svc.evaluate_company(company_id)  # type: ignore
            evaluated += 1
            results.append({
                "company_id": str(company_id),
                "score": result.get("score", 0),  # type: ignore[attr-defined]
                "risk_band": str(result.get("risk_band", "—")),  # type: ignore[attr-defined]
            })
        except Exception as e:
            errors += 1
            results.append({"company_id": str(company_id), "error": str(e)[:100]})
    
    # Explicit commit — flush() in service pushes to DB but doesn't commit
    await db.commit()
    
    return {
        "status": "complete",
        "total_companies": len(company_ids),
        "evaluated": evaluated,
        "errors": errors,
        "results": results[:5],  # Show first 5 results
        "timestamp": int(time.time()),
    }


@router.get("/cron/health")
async def cron_health():
    """Simple health endpoint for cron-job.org (GET request, no auth)."""
    import time
    return {"status": "ok", "service": "nlc-platform", "time": int(time.time())}
