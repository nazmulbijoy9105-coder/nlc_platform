from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from app.api.auth import get_current_user
# Import from your actual database location
from app.models.database import get_db

router = APIRouter()

async def require_admin(current_user=Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

class DashboardStats(BaseModel):
    total_users: int
    total_cases: int
    total_rules: int
    active_cases: int

class UserListItem(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(admin=Depends(require_admin), db=Depends(get_db)):
    from sqlalchemy import select, func
    from app.models.user import User
    
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_cases = 0
    total_rules = 0
    active_cases = 0

    try:
        from app.models.rescue import RescueCase
        total_cases = (await db.execute(select(func.count(RescueCase.id)))).scalar() or 0
        active_cases = (await db.execute(select(func.count(RescueCase.id)).where(RescueCase.status == "active"))).scalar() or 0
    except ImportError: pass

    try:
        from app.models.rules import Rule
        total_rules = (await db.execute(select(func.count(Rule.id)))).scalar() or 0
    except ImportError: pass

    return DashboardStats(total_users=total_users, total_cases=total_cases, total_rules=total_rules, active_cases=active_cases)

@router.get("/users", response_model=list[UserListItem])
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin=Depends(require_admin),
    db=Depends(get_db),
):
    from sqlalchemy import select
    from app.models.user import User

    query = select(User).order_by(User.id.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    users = result.scalars().all()
    return [
        UserListItem(id=u.id, email=u.email, first_name=u.first_name, last_name=u.last_name, role=u.role, is_active=u.is_active)
        for u in users
    ]


