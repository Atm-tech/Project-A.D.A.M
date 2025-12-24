from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.user import AppUser
from app.models.outlet import Outlet

router = APIRouter()


@router.post(
    "/login",
    summary="Login with hardcoded demo users",
)
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(AppUser).filter(AppUser.username == username).first()
    if not user or user.password != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {
        "username": user.username,
        "role": user.role,
        "outlet_id": user.outlet_id,
    }


@router.post(
    "/register",
    summary="Request a new user account (pending approval)",
)
def register(
    full_name: str = Form(...),
    username: str = Form(...),
    phone: str = Form(...),
    outlet_id: int = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    if password != confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match.")
    existing = db.query(AppUser).filter(AppUser.username == username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists.")
    if phone:
        existing_phone = db.query(AppUser).filter(AppUser.phone == phone).first()
        if existing_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone already registered.")
    outlet = db.query(Outlet).filter(Outlet.outlet_id == outlet_id).first()
    if not outlet:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outlet not found.")
    user = AppUser(
        full_name=full_name,
        username=username,
        phone=phone,
        password=password,
        role="user",
        status="pending",
        outlet_id=None,
        requested_outlet_id=outlet_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "pending", "user_id": user.user_id}


@router.get(
    "/pending",
    summary="List pending users (admin view)",
)
def list_pending(db: Session = Depends(get_db)):
    users = db.query(AppUser).filter(AppUser.status == "pending").all()
    return users


@router.post(
    "/approve",
    summary="Approve or reject a pending user (admin)",
)
def approve_user(
    user_id: int = Form(...),
    approve: bool = Form(...),
    role: str = Form(default="user"),
    approved_by: str = Form(default="admin"),
    db: Session = Depends(get_db),
):
    user = db.query(AppUser).filter(AppUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not pending.")
    if approve:
        user.status = "active"
        user.role = role
        user.outlet_id = user.requested_outlet_id
        user.approved_by = approved_by
        user.approved_at = datetime.utcnow()
    else:
        user.status = "rejected"
    db.commit()
    db.refresh(user)
    return {"status": user.status, "user_id": user.user_id, "role": user.role}


@router.post(
    "/reset-password",
    summary="Reset a user's password (admin)",
)
def reset_password(
    user_id: int = Form(...),
    new_password: str = Form(...),
    approved_by: str = Form(default="admin"),
    db: Session = Depends(get_db),
):
    user = db.query(AppUser).filter(AppUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.password = new_password
    user.approved_by = approved_by
    user.approved_at = datetime.utcnow()
    db.commit()
    return {"status": "ok", "user_id": user.user_id}
