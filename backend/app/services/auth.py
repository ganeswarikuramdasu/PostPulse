"""
auth.py

Password hashing (bcrypt), JWT access tokens (python-jose), and FastAPI
dependencies for getting the current authenticated / verified user.

SECRET_KEY MUST be set via environment variable in any real deployment -
the default here is only for zero-config local development and is NOT safe
to use in production (see backend/.env.example).
"""
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from jwt import PyJWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.db import get_db, User

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

_INSECURE_DEFAULT_SECRET = "dev-only-insecure-secret-change-me-in-production"
if SECRET_KEY == _INSECURE_DEFAULT_SECRET:
    import warnings
    warnings.warn(
        "SECRET_KEY is using the insecure default value. This is fine for local "
        "development but MUST be changed before any real deployment - anyone who "
        "knows this default can forge valid login tokens for any user. Set SECRET_KEY "
        "in backend/.env (generate one with: python -c \"import secrets; print(secrets.token_hex(32))\").",
        stacklevel=1,
    )

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _prepare_password_bytes(password: str) -> bytes:
    # bcrypt has a hard 72-BYTE limit and raises ValueError above it (not a
    # silent truncation in current bcrypt versions) - a password with
    # multi-byte UTF-8 characters can exceed 72 bytes well under 72
    # characters. Truncate explicitly and consistently in both hash and
    # verify so this never raises for the user and hashing/verification
    # stay symmetric.
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare_password_bytes(password), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare_password_bytes(password), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_verified_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before using this feature.",
        )
    return user
