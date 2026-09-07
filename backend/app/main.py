from dotenv import load_dotenv
load_dotenv()  # loads backend/.env if present - must run before any os.getenv() calls elsewhere

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import init_db
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.api.admin_routes import router as admin_router

app = FastAPI(
    title="PostPulse API",
    description="ML-powered API predicting social-media content performance.",
    version="1.0.0",
)

# ALLOWED_ORIGINS: comma-separated list for production (e.g. your deployed
# frontend's URL). Falls back to localhost dev ports if unset, so local
# development keeps working with zero configuration.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175"
allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "PostPulse API - see /docs for API documentation."}
