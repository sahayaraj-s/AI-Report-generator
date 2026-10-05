import os
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal
from app.models import Student, StudentScore, Upload
from app.auth import get_current_admin
from app.services.consolidator import consolidate_workbook

client = TestClient(app)

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic_ccdp_30.xlsx")

@pytest.fixture(autouse=True)
def auth_override():
    app.dependency_overrides[get_current_admin] = lambda: {"username": "admin", "role": "admin"}
    yield
    app.dependency_overrides.pop(get_current_admin, None)

def test_consolidate_workbook_returns_exactly_30():
    students, report = consolidate_workbook(FIXTURE_PATH)
    assert len(students) == 30, f"Expected 30 consolidated students, got {len(students)}"
    assert report["total_consolidated_students"] == 30
    assert len(report["sheets"]) >= 4

    # Assert genuine skills vs compliance separation
    first_st = students[0]
    assert "Basic English" in first_st["skill_scores"]
    assert "Shirt" not in first_st["skill_scores"]
    assert "Shoe Size" not in first_st["skill_scores"]
    assert "Tie" not in first_st["skill_scores"]
    assert "Trouser" not in first_st["skill_scores"]
    assert "Total" not in first_st["skill_scores"]
    assert "Typing Speed" not in first_st["skill_scores"]
    assert "Shirt" in first_st["compliance"]

def test_preview_writes_zero_rows_to_database():
    db = SessionLocal()
    initial_uploads = db.query(Upload).count()
    initial_students = db.query(Student).count()
    initial_scores = db.query(StudentScore).count()
    db.close()

    with open(FIXTURE_PATH, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/upload/preview",
        files={"file": ("synthetic_ccdp_30.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"course_name": "CCDP", "batch_name": "CCDP 2"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["student_count"] == 30
    assert data["upload_id"] is None

    # Assert 0 DB rows were written!
    db = SessionLocal()
    after_uploads = db.query(Upload).count()
    after_students = db.query(Student).count()
    after_scores = db.query(StudentScore).count()
    db.close()

    assert after_uploads == initial_uploads, "Upload preview must not write to uploads table"
    assert after_students == initial_students, "Upload preview must not write to students table"
    assert after_scores == initial_scores, "Upload preview must not write to student_scores table"

def test_upload_invalid_extension_rejected():
    fake_file = io.BytesIO(b"fake executable content")
    response = client.post(
        "/api/upload/preview",
        files={"file": ("malicious.exe", fake_file, "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Only .xlsx, .xls, or .csv" in response.json()["detail"]

def test_upload_oversized_file_rejected():
    # 26 MB chunk to exceed the 25 MB limit
    oversized = io.BytesIO(b"0" * (26 * 1024 * 1024))
    response = client.post(
        "/api/upload/preview",
        files={"file": ("oversized.xlsx", oversized, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 413
    assert "exceeds maximum upload limit" in response.json()["detail"]
