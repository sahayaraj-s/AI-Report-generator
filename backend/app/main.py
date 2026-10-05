from __future__ import annotations
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import logging
from app.config import settings
from app.database import SessionLocal, engine, init_db
from app.models import Institute, JobRoleModel
from app.routers import admin, auth_router, dashboard, jobs, reports, students, upload, ai as ai_router
from app.services.job_roles import _get_default_kauvery_roles

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Skill Bay Academy — AI Placement Analytics API", version="2.0.0")

# Parse allowed origins from environment variable (comma-separated)
cors_origins_list = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if not cors_origins_list:
    cors_origins_list = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()

    if settings.dev_mode:
        logger.warning("=" * 64)
        logger.warning("  ⚠️  SECURITY WARNING: DEV_MODE is ENABLED! ⚠️")
        logger.warning("  Authentication is currently bypassed for testing.")
        logger.warning("  Ensure DEV_MODE=False is configured for all production deploys.")
        logger.warning("=" * 64)

    db = SessionLocal()
    try:
        inst = db.query(Institute).first()
        if not inst:
            db.add(Institute(
                name="Skill Bay Academy",
                tagline="Enabling Life Skills",
                parent_org="Kauvery Hospital",
                program_name="Career & Competency Development Program (CCDP)",
                program_duration="50 Days",
            ))
            db.commit()

        # Seed Kauvery Hospital roles if no roles exist
        if db.query(JobRoleModel).count() == 0:
            for r in _get_default_kauvery_roles():
                criteria_json = json.dumps([
                    {"skill": sc.skill, "min_score": sc.min_score, "max_score": sc.max_score}
                    for sc in r.skill_criteria
                ])
                db.add(JobRoleModel(
                    name=r.name,
                    required_skills=criteria_json,
                    min_score=r.min_score,
                    demand_level=r.demand_level,
                    openings=r.openings,
                    is_active=r.is_active,
                    company_name=r.company_name or "Kauvery Hospital",
                    kauvery_unit=r.kauvery_unit,
                    department=r.department,
                ))
            db.commit()
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "dev_mode": settings.dev_mode,
        "institute": "Skill Bay Academy",
        "parent_org": "Kauvery Hospital",
        "program": "CCDP (50 Days)",
    }


app.include_router(auth_router.router)
app.include_router(admin.router)
app.include_router(upload.router)
app.include_router(students.router)
app.include_router(dashboard.router)
app.include_router(jobs.router)
app.include_router(reports.router)
app.include_router(ai_router.router)
