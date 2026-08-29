from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.db import get_db, User, PredictionHistory
from app.schemas.auth import UserOut, AdminUserUpdate
from app.services.auth import get_current_admin_user
from typing import List

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(get_current_admin_user)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: AdminUserUpdate, db: Session = Depends(get_db),
                 admin: User = Depends(get_current_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == admin.id and payload.is_admin is False:
        raise HTTPException(status_code=400, detail="You can't remove your own admin access.")

    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.plan is not None:
        if payload.plan not in ("free", "pro"):
            raise HTTPException(status_code=400, detail="plan must be 'free' or 'pro'.")
        user.plan = payload.plan
    if payload.is_verified is not None:
        user.is_verified = payload.is_verified

    db.commit()
    db.refresh(user)
    return user


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), _admin: User = Depends(get_current_admin_user)):
    total_users = db.query(func.count(User.id)).scalar()
    verified_users = db.query(func.count(User.id)).filter(User.is_verified == True).scalar()  # noqa: E712
    pro_users = db.query(func.count(User.id)).filter(User.plan == "pro").scalar()
    total_predictions = db.query(func.count(PredictionHistory.id)).scalar()
    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "pro_users": pro_users,
        "total_predictions": total_predictions,
    }
