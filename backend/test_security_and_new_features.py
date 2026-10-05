"""
test_security_and_new_features.py
Validates:
1. Protected endpoints return 401 without bearer token when DEV_MODE=False.
2. /api/health stays public without token.
3. Upload size limit enforces 25 MB maximum and returns HTTP 413.
4. File extension validation enforces .xlsx, .xls, .csv and returns HTTP 400.
5. CSV formula injection escaping prefixes single quote (') on risky characters.
6. Role auto-detection (/api/jobs/roles/auto-detect) returns HTTP 200 with suggestions.
"""
from __future__ import annotations
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.routers.reports import sanitize_csv_cell

client = TestClient(app)


def test_auth_protection_401():
    """Verify that unauthenticated requests to protected endpoints return 401."""
    original_dev_mode = settings.dev_mode
    try:
        # Enforce production auth mode
        settings.dev_mode = False

        # 1. /api/health MUST stay public
        resp_health = client.get("/api/health")
        assert resp_health.status_code == 200, f"Expected 200 for public health endpoint, got {resp_health.status_code}"

        # 2. Admin endpoints must reject unauthenticated calls
        assert client.get("/api/admin/settings").status_code == 401
        assert client.post("/api/admin/clear-data").status_code == 401

        # 3. Jobs endpoints must reject unauthenticated calls
        assert client.get("/api/jobs/roles").status_code == 401
        assert client.post("/api/jobs/roles/auto-detect", json={"detected_skills": []}).status_code == 401

        # 4. AI endpoints must reject unauthenticated calls
        assert client.post("/api/ai/chat", json={"query": "hello"}).status_code == 401
        assert client.get("/api/ai/sessions").status_code == 401
        assert client.get("/api/ai/templates").status_code == 401

        # 5. Students & reports endpoints must reject unauthenticated calls
        assert client.get("/api/students").status_code == 401
        assert client.get("/api/reports/batch/csv").status_code == 401

        print("  [PASS] test_auth_protection_401: All protected endpoints returned 401; /api/health returned 200.")
    finally:
        settings.dev_mode = original_dev_mode


def test_upload_size_limit_413():
    """Verify that uploads exceeding 25 MB return HTTP 413."""
    original_dev_mode = settings.dev_mode
    try:
        settings.dev_mode = True

        # Generate a dummy stream exceeding 25 MB (25 MB + 1024 bytes)
        oversized_data = b"x" * (25 * 1024 * 1024 + 1024)

        resp = client.post(
            "/api/upload/preview",
            files={"file": ("oversized.csv", io.BytesIO(oversized_data), "text/csv")},
            headers={"Authorization": "Bearer dev-mock-token"},
        )
        assert resp.status_code == 413, f"Expected HTTP 413 for >25MB upload, got {resp.status_code}: {resp.text}"
        assert "exceeds maximum upload limit" in resp.text.lower() or "413" in str(resp.status_code)
        print("  [PASS] test_upload_size_limit_413: >25MB upload rejected with HTTP 413.")
    finally:
        settings.dev_mode = original_dev_mode


def test_invalid_upload_extension_400():
    """Verify that uploading files other than .xlsx, .xls, .csv returns HTTP 400."""
    original_dev_mode = settings.dev_mode
    try:
        settings.dev_mode = True

        resp = client.post(
            "/api/upload/preview",
            files={"file": ("malicious.exe", io.BytesIO(b"fake binary"), "application/octet-stream")},
            headers={"Authorization": "Bearer dev-mock-token"},
        )
        assert resp.status_code == 400, f"Expected HTTP 400 for .exe file, got {resp.status_code}"
        print("  [PASS] test_invalid_upload_extension_400: Non-spreadsheet file rejected with HTTP 400.")
    finally:
        settings.dev_mode = original_dev_mode


def test_csv_formula_injection_escaping():
    """Verify that dangerous CSV formula trigger characters are prefixed with a single quote."""
    # Dangerous trigger characters: =, +, -, @, \t, \r
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-10") == "'-10"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("\tmalicious_tab") == "'\tmalicious_tab"
    assert sanitize_csv_cell("\rcarriage_return") == "'\rcarriage_return"

    # Safe characters should not be modified
    assert sanitize_csv_cell("Aarav Sharma") == "Aarav Sharma"
    assert sanitize_csv_cell("CS001") == "CS001"
    assert sanitize_csv_cell(85.5) == 85.5
    assert sanitize_csv_cell(None) == ""

    print("  [PASS] test_csv_formula_injection_escaping: All formula injection triggers correctly escaped with single quote.")


def test_auto_detect_roles_endpoint_200():
    """Verify that POST /api/jobs/roles/auto-detect returns HTTP 200 without NameError."""
    original_dev_mode = settings.dev_mode
    try:
        settings.dev_mode = True

        payload = {
            "detected_skills": ["Python", "SQL", "Communication Skills", "Advanced Excel"]
        }
        resp = client.post(
            "/api/jobs/roles/auto-detect",
            json=payload,
            headers={"Authorization": "Bearer dev-mock-token"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "suggested_roles" in data, "Response missing suggested_roles key"
        assert isinstance(data["suggested_roles"], list), "suggested_roles must be a list"
        print(f"  [PASS] test_auto_detect_roles_endpoint_200: Successfully returned 200 with {len(data['suggested_roles'])} suggested roles.")
    finally:
        settings.dev_mode = original_dev_mode


def run_all_security_tests():
    print("=" * 60)
    print(" RUNNING SECURITY & NEW FEATURE VERIFICATION SUITE")
    print("=" * 60)
    test_auth_protection_401()
    test_upload_size_limit_413()
    test_invalid_upload_extension_400()
    test_csv_formula_injection_escaping()
    test_auto_detect_roles_endpoint_200()
    print("=" * 60)
    print(" ALL SECURITY & NEW FEATURE TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_security_tests()
