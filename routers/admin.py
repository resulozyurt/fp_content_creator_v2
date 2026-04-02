from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from services.db import get_db, User
from middleware.auth import get_current_admin_user

router = APIRouter(prefix="/api/admin", tags=["Admin Panel"])

# --- Response & Request Models for Admin ---
class UserAdminResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    balance: float

    class Config:
        from_attributes = True

class RoleUpdateRequest(BaseModel):
    role: str

# --- Admin Endpoints ---

@router.get("/users", response_model=List[UserAdminResponse])
def get_all_users(db: Session = Depends(get_db), admin_user: User = Depends(get_current_admin_user)):
    """Fetches all users from the database. Requires ADMIN role."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users

@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, request: RoleUpdateRequest, db: Session = Depends(get_db), admin_user: User = Depends(get_current_admin_user)):
    """Updates a user's role (e.g., from 'user' to 'admin')."""
    if request.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role specified.")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Prevent the admin from demoting themselves by accident
    if user.id == admin_user.id and request.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot demote your own admin account.")

    user.role = request.role
    db.commit()
    return {"status": "success", "message": f"User role successfully updated to {request.role}"}

@router.put("/users/{user_id}/toggle-status")
def toggle_user_status(user_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_current_admin_user)):
    """Toggles a user's active status (Ban / Unban)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    # Prevent the admin from banning themselves
    if user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="You cannot ban your own account.")

    user.is_active = not user.is_active
    db.commit()
    
    status_text = "activated" if user.is_active else "banned"
    return {"status": "success", "message": f"User account has been {status_text}."}