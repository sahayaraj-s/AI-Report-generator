"""
import_ccdp2.py - CCDP 2 Batch Importer
=======================================
Reads Students Complete Details - CCDP 2(1).xlsx using loader.py and metrics.py.
Populates the database with verified students, scores, and analysis results.

Usage:
  venv\\Scripts\\python.exe import_ccdp2.py
"""
import sys
import os
import json
import logging

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

from app.database import SessionLocal, engine, Base
from app.models import (
    Course, Batch, Skill, Student, StudentScore,
    AnalysisResult, Upload, ActivityLog
)
from loader import load_all_sheets, validate_students
from metrics import build_full_metrics

EXCEL_CANDIDATES = [
    os.path.join(os.path.dirname(ROOT), "Students Complete Details - CCDP 2(1).xlsx"),
    os.path.join(os.path.dirname(ROOT), "Students Complete Details - CCDP 2.xlsx"),
    os.path.join(ROOT, "Students Complete Details - CCDP 2(1).xlsx"),
    os.path.join(ROOT, "Students Complete Details - CCDP 2.xlsx"),
]

COURSE_NAME = "CCDP (Career & Competency Development Program)"
BATCH_NAME = "CCDP 2"


def find_excel_file():
    for p in EXCEL_CANDIDATES:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"Could not find CCDP 2 Excel file in: {EXCEL_CANDIDATES}")


def main():
    excel_path = find_excel_file()
    print(f"\n{'='*70}")
    print(f"IMPORTING CCDP 2 DATA: {os.path.basename(excel_path)}")
    print(f"{'='*70}\n")

    # 1. Load data via loader.py
    loader_result = load_all_sheets(excel_path, os.path.basename(excel_path))
    students_raw = loader_result["students"]
    dq_warnings = loader_result["dq_warnings"]

    # 2. Validation gate
    validate_students(students_raw, expected_count=30, dq_warnings=dq_warnings)

    # 3. Compute derived metrics
    metrics_bundle = build_full_metrics(loader_result)
    per_student = metrics_bundle["per_student"]
    class_avg_overall = metrics_bundle["class_avg_overall_pct"]
    class_avg_subj = metrics_bundle["class_avg_pct_per_subject"]
    class_skill_avgs = metrics_bundle["class_skill_averages"]

    print(f"[METRICS] Computed metrics for {len(per_student)} students.")
    print(f"[METRICS] Class Average Overall Score: {class_avg_overall}%")

    # 4. Database sync
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("[DB] Clearing previous CCDP 2 records...")
    # Delete existing batch students
    existing_batch = db.query(Batch).filter(Batch.name == BATCH_NAME).first()
    if existing_batch:
        student_ids = [s.id for s in db.query(Student).filter(Student.batch_id == existing_batch.id).all()]
        if student_ids:
            db.query(StudentScore).filter(StudentScore.student_id.in_(student_ids)).delete(synchronize_session=False)
            db.query(AnalysisResult).filter(AnalysisResult.student_id.in_(student_ids)).delete(synchronize_session=False)
            db.query(Student).filter(Student.id.in_(student_ids)).delete(synchronize_session=False)
        db.delete(existing_batch)
        db.commit()

    # Create/Find Course
    course = db.query(Course).filter(Course.name == COURSE_NAME).first()
    if not course:
        course = Course(name=COURSE_NAME)
        db.add(course)
        db.flush()

    # Create Batch
    batch = Batch(name=BATCH_NAME, course_id=course.id)
    db.add(batch)
    db.flush()

    # Upsert all skills
    all_skill_names = set()
    for srec in per_student.values():
        all_skill_names.update(srec["assessment_scores"].keys())
        all_skill_names.update(srec["skill_scores"].keys())

    skill_objs = {}
    for sname in all_skill_names:
        clean_name = sname.replace("\n", " ").strip()
        sk = db.query(Skill).filter(Skill.name == clean_name).first()
        if not sk:
            sk = Skill(name=clean_name)
            db.add(sk)
            db.flush()
        skill_objs[sname] = sk

    print(f"[DB] Upserted {len(skill_objs)} skill categories.")

    # 5. Insert students
    inserted_count = 0
    for cn, rec in sorted(per_student.items(), key=lambda x: x[1]["class_rank"]):
        prof = rec["profile"]
        name = rec["display_name"]
        roll = prof.get("Enrolment No.") or prof.get("enrolment no") or prof.get("Roll No") or ""
        email = prof.get("Email id") or prof.get("email") or ""
        phone = prof.get("Personal No.") or prof.get("personal no") or prof.get("phone") or ""
        if isinstance(phone, float):
            phone = str(int(phone))

        overall_pct = rec["overall_pct"]
        att_pct = rec["attendance_pct"]
        is_placed = rec.get("placement") is not None
        placement_ready = is_placed or (overall_pct >= 60.0 and att_pct >= 80.0)

        student = Student(
            name=name,
            roll_number=str(roll).strip(),
            email=str(email).strip(),
            phone=str(phone).strip(),
            course_id=course.id,
            batch_id=batch.id,
            attendance_pct=att_pct,
            overall_score=overall_pct,
            placement_ready=placement_ready,
        )
        db.add(student)
        db.flush()

        # Add StudentScores
        for subj, score_val in rec["assessment_scores"].items():
            if isinstance(score_val, (int, float)):
                sk = skill_objs.get(subj)
                if sk:
                    mx = rec["max_marks"].get(subj, 100.0)
                    norm_score = round((score_val / mx) * 100, 1) if mx > 0 else score_val
                    db.add(StudentScore(student_id=student.id, skill_id=sk.id, score=norm_score))

        for skill_name, skill_val in rec["skill_scores"].items():
            if isinstance(skill_val, (int, float)):
                sk = skill_objs.get(skill_name)
                if sk:
                    norm_score = round((skill_val / 10.0) * 100, 1)
                    db.add(StudentScore(student_id=student.id, skill_id=sk.id, score=norm_score))

        # Recommended roles & Analysis
        recommended_roles = []
        placement = rec.get("placement")
        if placement and placement.get("Designation"):
            recommended_roles.append({
                "role": placement["Designation"],
                "company": placement.get("Organization", ""),
                "confidence": 95,
                "fit_tier": "Perfect Match",
                "notes": f"Actual placement: {placement['Designation']} at {placement.get('Organization', '')}"
            })
        else:
            if overall_pct >= 75:
                recommended_roles.append({"role": "Hospital Front Office Executive", "confidence": 88, "fit_tier": "Perfect Match"})
            elif overall_pct >= 60:
                recommended_roles.append({"role": "Customer Care Associate", "confidence": 75, "fit_tier": "Medium Fit"})
            else:
                recommended_roles.append({"role": "Operations Support Trainee", "confidence": 62, "fit_tier": "Medium Fit"})

        analysis = AnalysisResult(
            student_id=student.id,
            overall_score=overall_pct,
            placement_readiness_pct=overall_pct,
            strengths=json.dumps(rec.get("strengths", [])),
            weaknesses=json.dumps(rec.get("weaknesses", [])),
            recommended_roles=json.dumps(recommended_roles),
            salary_range=placement.get("salary_display") if placement else "Rs. 10,000 - 15,000 / month",
            interview_readiness="Ready for Placement" if placement_ready else "Needs Practice",
            ai_summary=(
                f"{name} achieved an overall assessment score of {overall_pct}% "
                f"(Rank #{rec['class_rank']} of {rec['class_size']}) with {att_pct}% attendance. "
                + (f"Placed as {placement.get('Designation', 'Trainee')}"
                   + (f" at {placement['Organization']}" if placement.get("Organization") else "")
                   + (f" ({placement['salary_display']})" if placement.get("salary_display") else "")
                   + "." if placement else "Currently open for hospital and healthcare placement opportunities.")
            ),
            ai_source="grounded_metrics",
        )
        db.add(analysis)
        inserted_count += 1
        print(f"  [#{rec['class_rank']:2d}] {name:30s} | Score: {overall_pct:5.1f}% | Att: {att_pct:5.1f}% | Ready: {placement_ready} | Placed: {is_placed}")

    # Log upload & activity
    db.add(Upload(
        filename=os.path.basename(excel_path),
        mode="save",
        student_count=inserted_count,
        detected_columns=json.dumps(list(all_skill_names)),
        detected_skills=json.dumps(list(all_skill_names)),
        status="processed",
    ))
    db.add(ActivityLog(
        action="upload:import_ccdp2",
        detail=f"CCDP 2 batch imported: {inserted_count} students with verified metrics",
    ))
    db.commit()

    print(f"\n{'='*70}")
    print(f"[SUCCESS] Successfully imported {inserted_count} students into '{BATCH_NAME}'")
    print(f"[SUMMARY] Class Average: {class_avg_overall}% (Target: 71.1%)")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
