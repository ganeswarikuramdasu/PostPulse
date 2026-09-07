import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.db import get_db, User, EmailVerificationToken
from app.schemas.auth import UserRegister, UserLogin, UserOut, TokenResponse, MessageResponse
from app.services.auth import (
    hash_password, verify_password, create_access_token,
    generate_verification_token, get_current_user,
)
from app.services.email_service import send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])

# The first account to register with this email is automatically promoted to
# admin - a simple, no-manual-DB-editing bootstrap mechanism. Set this in
# backend/.env. If unset, no auto-promotion happens (first admin must be
# created manually - see README "Admin Access").
ADMIN_BOOTSTRAP_EMAIL = os.getenv("ADMIN_BOOTSTRAP_EMAIL", "").lower().strip()
AUTO_VERIFY_USERS = os.getenv("AUTO_VERIFY_USERS", "false").lower().strip() in ("1", "true", "yes")


@router.post("/register", response_model=MessageResponse)
def register(payload: UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    is_admin = bool(ADMIN_BOOTSTRAP_EMAIL) and payload.email.lower() == ADMIN_BOOTSTRAP_EMAIL

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        is_verified=AUTO_VERIFY_USERS,
        is_admin=is_admin,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent requests can both pass the existence check above
        # before either commits - the unique constraint on email is the
        # real guard; this just turns that race into a clean 400 instead
        # of a raw 500 from an unhandled IntegrityError.
        db.rollback()
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    db.refresh(user)

    if AUTO_VERIFY_USERS:
        return {"message": "Account created successfully. You can log in now."}


    token = generate_verification_token()
    verification = EmailVerificationToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(verification)
    db.commit()

    # Email is sent in the background AFTER the response returns, so the
    # register request completes immediately regardless of how long the email
    # send takes. This prevents the "registration failed" timeout that
    # happened before (the frontend's 15s axios timeout would fire while the
    # account was actually being created, then a retry would hit
    # "already exists").
    background_tasks.add_task(send_verification_email, user.email, token)

    return {"message": "Account created. Check your email for a verification link."}


@router.get("/verify-email", response_model=MessageResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    record = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == token).first()
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or unknown verification token.")

    user = db.query(User).filter(User.id == record.user_id).first()

    if record.used:
        # Already consumed. If the account ended up verified, treat a repeated
        # (e.g. double-clicked) link as a harmless success instead of a confusing
        # failure - the user clearly got the email and the link worked.
        if user and user.is_verified:
            return {"message": "Your email is already verified. You can log in now."}
        raise HTTPException(status_code=400, detail="This verification link has already been used.")

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This verification link has expired. Please register again.")

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_verified = True
    record.used = True
    db.commit()

    return {"message": "Email verified. You can now log in."}


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in. Check your inbox (and spam folder) for the verification link.",
        )

    token = create_access_token(user.id)
    return {"access_token": token, "user": UserOut.model_validate(user)}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(payload: UserLogin, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Reuses UserLogin's email field only; still requires the correct password
    # so this can't be used to spam arbitrary email addresses.
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if user.is_verified:
        return {"message": "This account is already verified."}

    token = generate_verification_token()
    verification = EmailVerificationToken(
        user_id=user.id, token=token, expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db.add(verification)
    db.commit()
    background_tasks.add_task(send_verification_email, user.email, token)
    return {"message": "Verification email resent."}
