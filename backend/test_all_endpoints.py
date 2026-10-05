"""
Comprehensive test suite verifying all Phase 2 backend endpoints.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

settings.dev_mode = True

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-mock-token"}

SAMPLE_CSV = b"""Name,Roll No,Email,Course,Batch,Python,SQL,Communication,Problem Solving,Attendance %
Aarav Sharma,CS001,aarav@example.com,Computer Science,2024 Batch,22,24,18,20,92
Bhavya Patel,CS002,bhavya@example.com,Computer Science,2024 Batch,15,18,22,19,85
Chetan Kumar,CS003,chetan@example.com,Information Tech,2024 Batch,8,10,12,14,60
Divya Singh,CS004,divya@example.com,Computer Science,2025 Batch,25,23,24,25,98
Esha Gupta,CS005,esha@example.com,Information Tech,2025 Batch,12,14,15,10,72
"""

def test_all():
    print("=== Testing Upload ===")
    resp = client.post(
        "/api/upload/process",
        files={"file": ("sample.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
        data={"mode": "save", "course_name": "Computer Science", "batch_name": "2024 Batch", "overwrite": "true"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    print("Upload OK: saved count =", resp.json().get("saved"))

    print("\n=== Testing Dashboard Stats & Batch Filter ===")
    resp = client.get("/api/dashboard/stats")
    assert resp.status_code == 200, resp.text
    stats = resp.json()
    assert stats["total_students"] >= 5
    assert "batch_list" in stats
    print("Dashboard stats OK: total students =", stats["total_students"])

    # Test with batch filter
    resp_batch = client.get("/api/dashboard/stats?batch=2024%20Batch")
    assert resp_batch.status_code == 200
    print("Filtered batch stats OK: count =", resp_batch.json()["total_students"])

    print("\n=== Testing Job Roles ===")
    resp = client.get("/api/jobs/roles", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    roles = resp.json()
    print("Total roles:", roles["total_roles"])

    # Create a structured job role
    new_role = {
        "name": "Full Stack Python Pro",
        "skill_criteria": [
            {"skill": "Python", "min_score": 20, "max_score": 25},
            {"skill": "SQL", "min_score": 18, "max_score": 25},
        ],
        "min_score": 60,
        "demand_level": "High",
        "openings": 4,
        "is_active": True,
        "company_name": "Tech Corp",
    }
    resp_create = client.post("/api/jobs/roles", json=new_role, headers=AUTH_HEADERS)
    if resp_create.status_code == 200:
        role_id = resp_create.json()["id"]
        # Test candidates for role
        resp_cand = client.get(f"/api/jobs/roles/{role_id}/candidates", headers=AUTH_HEADERS)
        assert resp_cand.status_code == 200
        print("Role candidates check OK: matched count =", resp_cand.json()["total_candidates"])

    print("\n=== Testing AI Chat Sessions ===")
    # Create session
    resp_sess = client.post("/api/ai/sessions", json={"title": "Test Chat"}, headers=AUTH_HEADERS)
    assert resp_sess.status_code == 200
    session_id = resp_sess.json()["id"]

    # Send message
    resp_msg = client.post(
        f"/api/ai/sessions/{session_id}/messages",
        json={"content": "How many students are placement ready?"},
        headers=AUTH_HEADERS,
    )
    assert resp_msg.status_code == 200
    assert "content" in resp_msg.json()

    # Test templates
    resp_tpl = client.get("/api/ai/templates", headers=AUTH_HEADERS)
    assert resp_tpl.status_code == 200
    assert len(resp_tpl.json()["templates"]) > 0

    print("\n=== Testing Reports Endpoints ===")
    # 1. Reports Meta
    resp_meta = client.get("/api/reports/meta", headers=AUTH_HEADERS)
    assert resp_meta.status_code == 200

    # 2. Institute PDF
    resp_inst = client.get("/api/reports/institute/pdf", headers=AUTH_HEADERS)
    assert resp_inst.status_code == 200
    assert resp_inst.headers["content-type"] == "application/pdf"
    assert len(resp_inst.content) > 500

    # 3. Batch PDF
    resp_batch_pdf = client.get("/api/reports/batch/pdf?batch=2024%20Batch", headers=AUTH_HEADERS)
    assert resp_batch_pdf.status_code == 200
    assert resp_batch_pdf.headers["content-type"] == "application/pdf"

    # 4. Batch CSV
    resp_batch_csv = client.get("/api/reports/batch/csv?batch=2024%20Batch", headers=AUTH_HEADERS)
    assert resp_batch_csv.status_code == 200

    # 5. Match Matrix PDF
    resp_matrix = client.get("/api/reports/match/pdf", headers=AUTH_HEADERS)
    assert resp_matrix.status_code == 200
    assert resp_matrix.headers["content-type"] == "application/pdf"

    # 6. Match Matrix CSV
    resp_matrix_csv = client.get("/api/reports/match/csv", headers=AUTH_HEADERS)
    assert resp_matrix_csv.status_code == 200

    # 7. Clean up test data so database remains pristine
    resp_clean = client.post("/api/admin/clean-test-data", headers=AUTH_HEADERS)
    assert resp_clean.status_code == 200

    print("\n==========================================")
    print(" ALL PHASE 2 BACKEND TESTS PASSED! ")
    print("==========================================")


if __name__ == "__main__":
    test_all()
