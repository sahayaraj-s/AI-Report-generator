"""
End-to-end automated test suite for AI Placement Dashboard API.
"""
import os
import sys
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_full_flow():
    print("--- STEP 1: Uploading sample_students.csv ---")
    csv_path = os.path.join(os.path.dirname(__file__), "..", "sample_students.csv")
    assert os.path.exists(csv_path), "sample_students.csv not found"

    with open(csv_path, "rb") as f:
        resp = client.post(
            "/api/upload/process",
            files={"file": ("sample_students.csv", f, "text/csv")},
            data={"mode": "save", "course_name": "B.Tech CSE", "batch_name": "2021-2025", "overwrite": "true"}
        )
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    data = resp.json()
    print("Upload result:", data)
    assert data["student_count"] > 0
    assert "saved" in data

    print("\n--- STEP 2: Checking Dashboard Stats ---")
    resp = client.get("/api/dashboard/stats")
    assert resp.status_code == 200, f"Dashboard stats failed: {resp.text}"
    stats = resp.json()
    print("Dashboard stats summary:", {
        "total_students": stats["total_students"],
        "placement_ready": stats["placement_ready"],
        "average_score": stats["average_score"],
        "top_performer": stats["top_performer"],
    })
    assert stats["total_students"] > 0

    print("\n--- STEP 3: Checking Job Roles Endpoint ---")
    resp = client.get("/api/jobs/roles")
    assert resp.status_code == 200, f"Job roles failed: {resp.text}"
    roles_data = resp.json()
    print("Job roles summary:", {
        "total_roles": roles_data["total_roles"],
        "total_students": roles_data["total_students"],
        "matched_roles": [r["name"] for r in roles_data["roles"] if r["matched_students"] > 0]
    })
    assert roles_data["total_roles"] >= 0

    print("\n--- STEP 4: Fetching Students Directory ---")
    resp = client.get("/api/students")
    assert resp.status_code == 200, f"Students directory failed: {resp.text}"
    students_list = resp.json()
    print(f"Total students in directory: {students_list['total']}")
    assert len(students_list["items"]) > 0

    first_student_id = students_list["items"][0]["id"]

    print(f"\n--- STEP 5: Fetching Student Profile (ID: {first_student_id}) ---")
    resp = client.get(f"/api/students/{first_student_id}")
    assert resp.status_code == 200, f"Student profile failed: {resp.text}"
    profile = resp.json()
    print("Student name:", profile["student"]["name"])
    print("AI Summary:", profile["latest_analysis"]["ai_summary"])
    assert profile["latest_analysis"] is not None

    print(f"\n--- STEP 6: Downloading PDF Report for Student (ID: {first_student_id}) ---")
    resp = client.get(f"/api/reports/student/{first_student_id}/pdf")
    assert resp.status_code == 200, f"PDF report download failed: {resp.text}"
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 1000
    print("PDF size bytes:", len(resp.content))

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    test_full_flow()
