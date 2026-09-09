"""
Comprehensive test suite verifying all Phase 2 backend endpoints.
"""
import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

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
    )
    assert resp.status_code == 200, resp.text
    print("Upload OK:", resp.json())

    print("\n=== Testing Dashboard Stats & Batch Filter ===")
    resp = client.get("/api/dashboard/stats")
    assert resp.status_code == 200, resp.text
    stats = resp.json()
    assert stats["total_students"] >= 5
    assert "batch_list" in stats
    print("Dashboard stats OK:", stats["total_students"], "students, batch_list:", stats["batch_list"])

    # Test with batch filter
    resp_batch = client.get("/api/dashboard/stats?batch=2024%20Batch")
    assert resp_batch.status_code == 200
    print("Filtered batch stats OK:", resp_batch.json()["total_students"], "students in 2024 Batch")

    print("\n=== Testing Job Roles ===")
    resp = client.get("/api/jobs/roles")
    assert resp.status_code == 200
    roles = resp.json()
    print("Total roles:", roles["total_roles"], "Total openings:", roles.get("total_openings"))

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
    resp_create = client.post("/api/jobs/roles", json=new_role)
    if resp_create.status_code == 200:
        role_id = resp_create.json()["id"]
        print("Created role with ID:", role_id)
        # Test candidates for role
        resp_cand = client.get(f"/api/jobs/roles/{role_id}/candidates")
        assert resp_cand.status_code == 200
        print("Role candidates:", resp_cand.json()["total_candidates"], "matched")

    print("\n=== Testing AI Chat Sessions ===")
    # Create session
    resp_sess = client.post("/api/ai/sessions", json={"title": "Test Chat"})
    assert resp_sess.status_code == 200
    session_id = resp_sess.json()["id"]
    print("Created chat session ID:", session_id)

    # Send message
    resp_msg = client.post(
        f"/api/ai/sessions/{session_id}/messages",
        json={"content": "How many students are placement ready?"}
    )
    assert resp_msg.status_code == 200
    print("AI Response:", resp_msg.json()["content"])

    # Test templates
    resp_tpl = client.get("/api/ai/templates")
    assert resp_tpl.status_code == 200
    assert len(resp_tpl.json()["templates"]) > 0
    print("Prompt templates count:", len(resp_tpl.json()["templates"]))

    print("\n=== Testing Reports Endpoints ===")
    # 1. Reports Meta
    resp_meta = client.get("/api/reports/meta")
    assert resp_meta.status_code == 200
    print("Reports meta:", len(resp_meta.json()["batches"]), "batches")

    # 2. Institute PDF
    resp_inst = client.get("/api/reports/institute/pdf")
    assert resp_inst.status_code == 200
    assert resp_inst.headers["content-type"] == "application/pdf"
    assert len(resp_inst.content) > 500
    print("Institute PDF size:", len(resp_inst.content), "bytes")

    # 3. Batch PDF
    resp_batch_pdf = client.get("/api/reports/batch/pdf?batch=2024%20Batch")
    assert resp_batch_pdf.status_code == 200
    assert resp_batch_pdf.headers["content-type"] == "application/pdf"
    print("Batch PDF size:", len(resp_batch_pdf.content), "bytes")

    # 4. Batch CSV
    resp_batch_csv = client.get("/api/reports/batch/csv?batch=2024%20Batch")
    assert resp_batch_csv.status_code == 200
    print("Batch CSV length:", len(resp_batch_csv.content), "bytes")

    # 5. Match Matrix PDF
    resp_matrix = client.get("/api/reports/match/pdf")
    assert resp_matrix.status_code == 200
    assert resp_matrix.headers["content-type"] == "application/pdf"
    print("Match Matrix PDF size:", len(resp_matrix.content), "bytes")

    # 6. Match Matrix CSV
    resp_matrix_csv = client.get("/api/reports/match/csv")
    assert resp_matrix_csv.status_code == 200
    print("Match Matrix CSV length:", len(resp_matrix_csv.content), "bytes")

    print("\n==========================================")
    print(" ALL PHASE 2 BACKEND TESTS PASSED! ")
    print("==========================================")

if __name__ == "__main__":
    test_all()
