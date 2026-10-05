import pytest
from app.database import SessionLocal
from app.services.analytics import get_cohort_summary, list_students, get_student_profile

BANNED_PII_FIELDS = {
    "phone", "mobile", "mobile_number", "contact",
    "aadhaar", "aadhaar_number", "address", "dob",
    "date_of_birth", "father_name", "mother_name", "parent_details",
    "parent_name", "parent_phone"
}

def test_tools_never_return_banned_pii():
    db = SessionLocal()
    try:
        # 1. list_students
        students_res = list_students(db=db, limit=50)
        assert students_res["total"] > 0
        for s in students_res["students"]:
            for key in s.keys():
                assert key.lower() not in BANNED_PII_FIELDS, f"Banned PII field '{key}' found in list_students!"

        # 2. get_student_profile
        first_student = students_res["students"][0]
        profile = get_student_profile(db=db, student_ref=first_student["name"])
        assert profile is not None
        for key in profile.keys():
            assert key.lower() not in BANNED_PII_FIELDS, f"Banned PII field '{key}' found in get_student_profile!"

        # 3. get_cohort_summary
        summary = get_cohort_summary(db=db)
        for key in summary.keys():
            assert key.lower() not in BANNED_PII_FIELDS, f"Banned PII field '{key}' found in get_cohort_summary!"

    finally:
        db.close()
