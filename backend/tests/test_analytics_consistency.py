import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Course, Batch
from app.routers.upload import persist_consolidated_student
from app.services.consolidator import consolidate_workbook
from app.services.analytics import (
    compute_analytics,
    compute_analytics_from_records,
    get_cohort_summary,
    list_students,
)

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic_ccdp_30.xlsx")

def test_cross_consumer_analytics_consistency():
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    try:
        # Load the 30 consolidated students from fixture
        consolidated_students, _ = consolidate_workbook(FIXTURE_PATH)
        assert len(consolidated_students) == 30

        # Seed the isolated database with the fixture students
        course = Course(name="CCDP")
        batch = Batch(name="CCDP 2")
        db.add(course)
        db.add(batch)
        db.commit()
        db.refresh(course)
        db.refresh(batch)

        for s in consolidated_students:
            persist_consolidated_student(db, s, course.id, batch.id)
        db.commit()

        # Consumer 1: Upload Live Preview (compute_analytics_from_records)
        preview_res = compute_analytics_from_records(consolidated_students, db=db)
        n_preview = preview_res["total_students"]
        avg_preview = preview_res["average_score"]
        ready_preview = preview_res["placement_ready"]
        placed_preview = preview_res["placed_count"]

        # Consumer 2: Dashboard & Reports (compute_analytics on DB)
        db_res = compute_analytics(db=db)
        n_db = db_res["total_students"]
        avg_db = db_res["average_score"]
        ready_db = db_res["placement_ready"]
        placed_db = db_res["placed_count"]

        # Consumer 3: AI Chat Tool: get_cohort_summary
        chat_summary = get_cohort_summary(db=db)
        n_chat = chat_summary["total_students"]
        avg_chat = chat_summary["average_score"]
        ready_chat = chat_summary["placement_ready_count"]
        placed_chat = chat_summary["placed_count"]

        # Consumer 4: AI Chat Tool: list_students
        chat_list = list_students(db=db, limit=100)
        n_chat_list = chat_list["total"]

        # Assert identical student count across all consumers
        assert n_preview == n_db == n_chat == n_chat_list == 30, (
            f"Counts diverged: Preview={n_preview}, DB={n_db}, Chat={n_chat}, List={n_chat_list}"
        )

        # Assert identical class average
        assert avg_preview == avg_db == avg_chat == 76.0, (
            f"Averages diverged: Preview={avg_preview}, DB={avg_db}, Chat={avg_chat}"
        )

        # Assert identical placement ready count
        assert ready_preview == ready_db == ready_chat == 27, (
            f"Readiness counts diverged: Preview={ready_preview}, DB={ready_db}, Chat={ready_chat}"
        )

        # Assert identical confirmed placed count
        assert placed_preview == placed_db == placed_chat == 27, (
            f"Placed counts diverged: Preview={placed_preview}, DB={placed_db}, Chat={placed_chat}"
        )

    finally:
        db.close()

