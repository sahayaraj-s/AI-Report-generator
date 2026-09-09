from __future__ import annotations
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal, engine, init_db
from app.models import Institute, JobRoleModel
from app.routers import admin, auth_router, dashboard, jobs, reports, students, upload, ai as ai_router
from app.services.job_roles import _get_default_kauvery_roles

app = FastAPI(title="Skill Bay Academy — AI Placement Analytics API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.on_event("startup")
def on_startup():
    init_db()
    # Auto-migrate SQLite schema
    try:
        with engine.connect() as conn:
            # Check job_roles columns
            result = conn.execute(text("PRAGMA table_info(job_roles)"))
            existing_cols = {row[1] for row in result.fetchall()}
            if existing_cols:
                if "company_name" not in existing_cols:
                    conn.execute(text("ALTER TABLE job_roles ADD COLUMN company_name VARCHAR"))
                if "openings" not in existing_cols:
                    conn.execute(text("ALTER TABLE job_roles ADD COLUMN openings INTEGER DEFAULT 0"))
                if "is_active" not in existing_cols:
                    conn.execute(text("ALTER TABLE job_roles ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                if "demand_level" not in existing_cols:
                    conn.execute(text("ALTER TABLE job_roles ADD COLUMN demand_level VARCHAR DEFAULT 'Medium'"))
                if "min_score" not in existing_cols:
                    conn.execute(text("ALTER TABLE job_roles ADD COLUMN min_score FLOAT DEFAULT 0.0"))
                if "kauvery_unit" not in existing_cols:
                    conn.execute(text("ALTER TABLE job_roles ADD COLUMN kauvery_unit VARCHAR DEFAULT 'Kauvery Hospital - Trichy (Tennur)'"))
                if "department" not in existing_cols:
                    conn.execute(text("ALTER TABLE job_roles ADD COLUMN department VARCHAR DEFAULT 'Hospital Administration & Operations'"))

            # Check institutes columns
            res_inst = conn.execute(text("PRAGMA table_info(institutes)"))
            inst_cols = {row[1] for row in res_inst.fetchall()}
            if inst_cols:
                if "parent_org" not in inst_cols:
                    conn.execute(text("ALTER TABLE institutes ADD COLUMN parent_org VARCHAR DEFAULT 'Kauvery Hospital'"))
                if "program_name" not in inst_cols:
                    conn.execute(text("ALTER TABLE institutes ADD COLUMN program_name VARCHAR DEFAULT 'Career & Competency Development Program (CCDP)'"))
                if "program_duration" not in inst_cols:
                    conn.execute(text("ALTER TABLE institutes ADD COLUMN program_duration VARCHAR DEFAULT '50 Days'"))

            conn.commit()
    except Exception as e:
        print("Auto-migration notice:", e)

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
