from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# 1. Normalize database URL
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# 2. If SQLite with relative path, anchor to backend directory explicitly
if db_url.startswith("sqlite:///./") or db_url == "sqlite:///placement.db":
    backend_dir = Path(__file__).resolve().parent.parent
    db_file = backend_dir / "placement.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

engine_kwargs = {"pool_pre_ping": True}
if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Dialect-aware self-migration: SQLite PRAGMA only runs on sqlite
    if engine.dialect.name == "sqlite":
        try:
            with engine.connect() as conn:
                # 1. Check job_roles columns
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
                        conn.execute(text("ALTER TABLE job_roles ADD COLUMN min_score FLOAT DEFAULT 50.0"))
                    if "kauvery_unit" not in existing_cols:
                        conn.execute(text("ALTER TABLE job_roles ADD COLUMN kauvery_unit VARCHAR DEFAULT 'Kauvery Hospital - Trichy (Tennur)'"))
                    if "department" not in existing_cols:
                        conn.execute(text("ALTER TABLE job_roles ADD COLUMN department VARCHAR DEFAULT 'Hospital Administration & Operations'"))

                # 2. Check institutes columns
                res_inst = conn.execute(text("PRAGMA table_info(institutes)"))
                inst_cols = {row[1] for row in res_inst.fetchall()}
                if inst_cols:
                    if "parent_org" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN parent_org VARCHAR DEFAULT 'Kauvery Hospital'"))
                    if "program_name" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN program_name VARCHAR DEFAULT 'Career & Competency Development Program (CCDP)'"))
                    if "program_duration" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN program_duration VARCHAR DEFAULT '50 Days'"))
                    if "kauvery_units_json" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN kauvery_units_json TEXT"))
                    if "departments_json" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN departments_json TEXT"))
                    if "skill_weight_pct" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN skill_weight_pct FLOAT DEFAULT 75.0"))
                    if "attendance_weight_pct" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN attendance_weight_pct FLOAT DEFAULT 25.0"))
                    if "readiness_cutoff" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN readiness_cutoff FLOAT DEFAULT 55.0"))
                    if "readiness_target_pct" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN readiness_target_pct FLOAT DEFAULT 80.0"))
                    if "attendance_target_pct" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN attendance_target_pct FLOAT DEFAULT 85.0"))
                    if "score_benchmark" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN score_benchmark FLOAT DEFAULT 75.0"))
                    if "typing_target_wpm" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN typing_target_wpm FLOAT DEFAULT 30.0"))
                    if "tier_1_cutoff" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN tier_1_cutoff FLOAT DEFAULT 80.0"))
                    if "tier_2_cutoff" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN tier_2_cutoff FLOAT DEFAULT 60.0"))
                    if "tier_3_cutoff" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN tier_3_cutoff FLOAT DEFAULT 40.0"))
                    if "fit_perfect_cutoff" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN fit_perfect_cutoff FLOAT DEFAULT 75.0"))
                    if "fit_medium_cutoff" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN fit_medium_cutoff FLOAT DEFAULT 55.0"))
                    if "fit_low_cutoff" not in inst_cols:
                        conn.execute(text("ALTER TABLE institutes ADD COLUMN fit_low_cutoff FLOAT DEFAULT 35.0"))

                # 3. Check students columns
                res_stud = conn.execute(text("PRAGMA table_info(students)"))
                stud_cols = {row[1] for row in res_stud.fetchall()}
                if stud_cols:
                    if "attendance_status" not in stud_cols:
                        conn.execute(text("ALTER TABLE students ADD COLUMN attendance_status VARCHAR DEFAULT 'tracked'"))
                    if "attendance_reason" not in stud_cols:
                        conn.execute(text("ALTER TABLE students ADD COLUMN attendance_reason VARCHAR"))
                    if "is_placed" not in stud_cols:
                        conn.execute(text("ALTER TABLE students ADD COLUMN is_placed BOOLEAN DEFAULT 0"))
                    if "placement_company" not in stud_cols:
                        conn.execute(text("ALTER TABLE students ADD COLUMN placement_company VARCHAR"))
                    if "placement_designation" not in stud_cols:
                        conn.execute(text("ALTER TABLE students ADD COLUMN placement_designation VARCHAR"))
                    if "placement_salary" not in stud_cols:
                        conn.execute(text("ALTER TABLE students ADD COLUMN placement_salary VARCHAR"))
                    if "placement_salary_num" not in stud_cols:
                        conn.execute(text("ALTER TABLE students ADD COLUMN placement_salary_num FLOAT DEFAULT 0.0"))
                    if "typing_wpm" not in stud_cols:
                        conn.execute(text("ALTER TABLE students ADD COLUMN typing_wpm FLOAT"))
                    if "compliance_json" not in stud_cols:
                        conn.execute(text("ALTER TABLE students ADD COLUMN compliance_json TEXT"))

                # 4. Check ai_chat_messages columns
                res_msg = conn.execute(text("PRAGMA table_info(ai_chat_messages)"))
                msg_cols = {row[1] for row in res_msg.fetchall()}
                if msg_cols:
                    if "source" not in msg_cols:
                        conn.execute(text("ALTER TABLE ai_chat_messages ADD COLUMN source VARCHAR DEFAULT 'gemini'"))
                    if "model" not in msg_cols:
                        conn.execute(text("ALTER TABLE ai_chat_messages ADD COLUMN model VARCHAR DEFAULT 'gemini-3.6-flash'"))

                conn.commit()
        except Exception as e:
            print("SQLite auto-migration notice:", e)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
