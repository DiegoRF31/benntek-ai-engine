from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.infrastructure.models.user_model import User
from app.api.auth import require_role
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix= "/admin",
    tags=["Admin"]
)

@router.get("/users")
def get_all_users(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    query = db.query(User).filter(
    User.tenant_id == current_user.tenant_id
)

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.all()

    return {
    "users": [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active
        }
        for u in users
    ]
}

@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    updates: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    user = db.query(User).filter(
    User.id == user_id,
    User.tenant_id == current_user.tenant_id
).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in updates.items():
        if hasattr(user, key):
            setattr(user, key, value)

    db.commit()
    db.refresh(user)

    return {"message": "User updated"}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    user = db.query(User).filter(
    User.id == user_id,
    User.tenant_id == current_user.tenant_id
).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"message": "User deleted"}