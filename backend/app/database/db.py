"""
db.py

Uses SQLAlchemy so the same code works against Supabase / PostgreSQL (production),
MySQL (local dev), and SQLite (automatic local fallback when DATABASE_URL
isn't set, so the project still runs with zero database setup).

Supported DATABASE_URL forms (auto-normalized where a driver isn't named):
  - Supabase / PostgreSQL: postgresql+psycopg2://... or postgres://... or postgresql://...
  - MySQL (local dev):     mysql://...   -> mysql+pymysql://...
  - SQLite (zero setup):   sqlite:///./postpulse.db

Requires the matching driver in backend/requirements.txt: `psycopg2-binary`
(Postgres/Supabase) and/or `pymysql` (MySQL). See README "Database Choice".
"""
import os
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or "sqlite:///./postpulse.db"

# Cloud database providers hand out connection strings in a few common
# shapes; SQLAlchemy needs the driver named explicitly. Normalize automatically
# so pasting a provider's URL straight into DATABASE_URL just works:
#   mysql://...        -> mysql+pymysql://...
#   postgres://...     -> postgresql+psycopg2://...
#   postgresql://...   -> postgresql+psycopg2://...
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine_kwargs = {"connect_args": connect_args, "pool_pre_ping": True}
if not DATABASE_URL.startswith("sqlite"):
    # pool_recycle avoids "MySQL server has gone away" errors in production,
    # where a managed MySQL instance (or a load balancer in front of it) can
    # silently close idle connections after a timeout shorter than the
    # pool's default idle lifetime. 280s stays safely under the common
    # 300s/8h default wait_timeout most managed MySQL providers set.
    engine_kwargs["pool_recycle"] = 280
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "5"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "10"))

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    plan = Column(String(20), default="free", nullable=False)  # "free" | "pro" - foundation for future paid tiers
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    predictions = relationship("PredictionHistory", back_populates="user")


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)


class PredictionHistory(Base):
    __tablename__ = "prediction_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable for backwards compat
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    content_type = Column(String(50))
    creator_category = Column(String(50))
    account_type = Column(String(20))
    input_json = Column(Text)

    performance_score = Column(Float)
    performance_category = Column(String(20))
    expected_views = Column(Integer)
    expected_engagement_rate = Column(Float)
    result_json = Column(Text)

    user = relationship("User", back_populates="predictions")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
