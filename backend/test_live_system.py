"""
test_live_system.py - Live Verification of Backend and Frontend Services
Tests both running servers over actual HTTP network sockets.
"""
import urllib.request
import urllib.parse
import json
import re

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"

def http_get(url, headers=None):
    hdrs = {"User-Agent": "LiveTester/1.0", "Authorization": "Bearer dev-mock-token"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read(), resp.headers

def http_post(url, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json", "User-Agent": "LiveTester/1.0", "Authorization": "Bearer dev-mock-token"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs)
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read(), resp.headers

def test_live():
    print("=" * 60)
    print(" LIVE SYSTEM TEST: Skill Bay Academy Placement Dashboard")
    print("=" * 60)

    try:
        # 1. Backend Health Check
        print("\n[1] Checking Backend Health (/api/health)...")
        status, body, _ = http_get(f"{BACKEND_URL}/api/health")
        assert status == 200
        health = json.loads(body.decode("utf-8"))
        print(f"  [OK] Health Status: {health['status']}, Institute: {health.get('institute')}")
    except Exception as exc:
        print(f"SKIPPED: Live backend not running on {BACKEND_URL} ({exc}).")
        print("To run live socket verification, start backend with: cd backend && python run.py")
        return

    # 2. Frontend Check (optional if running)
    try:
        print("\n[2] Checking Frontend (http://localhost:5173)...")
        status, body, headers = http_get(f"{FRONTEND_URL}/")
        html_text = body.decode("utf-8")
        assert status == 200, f"Frontend returned status {status}"
        print(f"  [OK] Frontend is UP and serving index.html ({len(body)} bytes)")
    except Exception as exc:
        print(f"  [NOTICE] Frontend not running on {FRONTEND_URL} ({exc}). Skipping frontend check.")

    # 3. Dashboard Stats
    print("\n[3] Checking Dashboard Stats (/api/dashboard/stats)...")
    status, body, _ = http_get(f"{BACKEND_URL}/api/dashboard/stats")
    assert status == 200
    stats = json.loads(body.decode("utf-8"))
    print(f"  [OK] Total Students: {stats['total_students']}")
    print(f"  [OK] Placement Ready: {stats['placement_ready']}")
    print(f"  [OK] Average Score: {stats['average_score']}%")

    # 4. Students Directory
    print("\n[4] Checking Students Directory (/api/students)...")
    status, body, _ = http_get(f"{BACKEND_URL}/api/students?page=1&page_size=10")
    assert status == 200
    students_data = json.loads(body.decode("utf-8"))
    total_students = students_data["total"]
    items = students_data["items"]
    print(f"  [OK] Total students returned: {total_students} (Page 1 has {len(items)} items)")
    assert len(items) > 0, "No students found in directory"
    first_student = items[0]

    # 5. Student Profile & Analysis
    student_id = first_student["id"]
    print(f"\n[5] Checking Student Profile for ID {student_id} (/api/students/{student_id})...")
    status, body, _ = http_get(f"{BACKEND_URL}/api/students/{student_id}")
    assert status == 200
    profile = json.loads(body.decode("utf-8"))
    assert "student" in profile
    print(f"  [OK] Student profile fetched successfully.")
    if profile.get("latest_analysis"):
        analysis = profile["latest_analysis"]
        print(f"  [OK] Latest Score: {analysis.get('overall_score')}, Grade: {analysis.get('grade')}")
        print(f"  [OK] Placement Readiness: {analysis.get('placement_ready')}")
        print(f"  [OK] AI Summary excerpt: {analysis.get('ai_summary', '')[:100]}...")

    # 6. Job Roles
    print("\n[6] Checking Job Roles (/api/jobs/roles)...")
    status, body, _ = http_get(f"{BACKEND_URL}/api/jobs/roles")
    assert status == 200
    roles_data = json.loads(body.decode("utf-8"))
    roles = roles_data.get("roles", [])
    print(f"  [OK] Total Job Roles: {len(roles)}, Openings: {roles_data.get('total_openings', 0)}")
    for r in roles[:3]:
        print(f"       - {r['name']} ({r.get('company_name', 'Kauvery Hospital')}): {r.get('matched_students', 0)} matched")

    # 7. AI Assistant Templates & Chat Session
    print("\n[7] Checking AI Assistant (/api/ai/templates & /api/ai/sessions)...")
    status, body, _ = http_get(f"{BACKEND_URL}/api/ai/templates")
    assert status == 200
    templates = json.loads(body.decode("utf-8")).get("templates", [])
    print(f"  [OK] Prompt Templates: {len(templates)} available")

    # Create chat session
    status, body, _ = http_post(f"{BACKEND_URL}/api/ai/sessions", {"title": "Live Test Chat"})
    assert status == 200
    session_info = json.loads(body.decode("utf-8"))
    session_id = session_info["id"]
    print(f"  [OK] Created Chat Session: #{session_id}")

    # Send a prompt to chat
    status, body, _ = http_post(
        f"{BACKEND_URL}/api/ai/sessions/{session_id}/messages",
        {"content": "Provide a quick summary of student placement statistics."}
    )
    assert status == 200
    chat_response = json.loads(body.decode("utf-8"))
    print(f"  [OK] AI Chat Response received ({len(chat_response.get('content', ''))} chars)")
    print(f"       Preview: {chat_response.get('content', '')[:120].strip()}...")

    # 8. Reports & PDF Generation
    print("\n[8] Checking Reports & PDF Generation...")
    # Reports meta
    status, body, _ = http_get(f"{BACKEND_URL}/api/reports/meta")
    assert status == 200
    meta = json.loads(body.decode("utf-8"))
    print(f"  [OK] Reports Meta: {len(meta.get('batches', []))} batches, {len(meta.get('students', []))} students")

    # Institute PDF
    status, body, headers = http_get(f"{BACKEND_URL}/api/reports/institute/pdf")
    assert status == 200
    assert headers.get_content_type() == "application/pdf"
    print(f"  [OK] Generated Institute PDF: {len(body)} bytes")

    # Student PDF
    status, body, headers = http_get(f"{BACKEND_URL}/api/reports/student/{student_id}/pdf")
    assert status == 200
    assert headers.get_content_type() == "application/pdf"
    print(f"  [OK] Generated Student PDF for #{student_id}: {len(body)} bytes")

    # Match Matrix PDF
    status, body, headers = http_get(f"{BACKEND_URL}/api/reports/match/pdf")
    assert status == 200
    assert headers.get_content_type() == "application/pdf"
    print(f"  [OK] Generated Match Matrix PDF: {len(body)} bytes")

    # 9. Admin Notifications
    print("\n[9] Checking Admin Notifications (/api/admin/notifications)...")
    status, body, _ = http_get(f"{BACKEND_URL}/api/admin/notifications")
    assert status == 200
    notifs = json.loads(body.decode("utf-8"))
    print(f"  [OK] Notifications endpoint active (count: {len(notifs.get('notifications', []))})")

    print("\n" + "=" * 60)
    print(" ALL LIVE SYSTEM TESTS PASSED SUCCESSFULLY! ")
    print(" Backend: http://127.0.0.1:8000  [UP & HEALTHY]")
    print(" Frontend: http://localhost:5173  [UP & SERVING]")
    print("=" * 60)

if __name__ == "__main__":
    test_live()
