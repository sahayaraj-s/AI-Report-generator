import os
import pytest
from app.database import SessionLocal
from app.models import Student, Batch, Course
from app.services.consolidator import consolidate_workbook
from app.routers.upload import (
    persist_consolidated_student,
    get_or_create,
    get_threshold_settings,
    compute_student_metrics,
)

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "tests", "fixtures", "synthetic_ccdp_30.xlsx")

def seed_database_if_empty():
    db = SessionLocal()
    try:
        count = db.query(Student).count()
        if count < 30 and os.path.exists(FIXTURE_PATH):
            batch = get_or_create(db, Batch, name="CCDP 2")
            course = get_or_create(db, Course, name="CCDP (Career & Competency Development Program)")
            students, _ = consolidate_workbook(
                FIXTURE_PATH,
                default_course=course.name,
                default_batch=batch.name,
            )
            cfg = get_threshold_settings(db)
            for s in students:
                s_computed = compute_student_metrics(s, cfg, db=db)
                persist_consolidated_student(db, s_computed, course.id, batch.id, overwrite=True)
            db.commit()
    finally:
        db.close()

@pytest.fixture(autouse=True)
def ensure_db_seeded():
    seed_database_if_empty()
    yield
