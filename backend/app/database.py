from __future__ import annotations
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Auto-migrate missing SQLite columns on existing databases
    if settings.database_url.startswith("sqlite"):
        try:
            with engine.connect() as conn:
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
                    conn.commit()
        except Exception as e:
            print("Auto-migration notice:", e)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
