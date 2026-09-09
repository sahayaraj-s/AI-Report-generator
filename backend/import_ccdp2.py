"""
One-shot importer for 'Students Complete Details - CCDP 2.xlsx'
Run: python backend/import_ccdp2.py
"""
import sys
import os
import json
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import openpyxl
import pandas as pd

# ─── Setup Django-style path ────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from app.database import SessionLocal, engine
from app import models
from app.models import (
    Base, Course, Batch, Skill, Student, StudentScore,
    AnalysisResult, Upload, ActivityLog,
    StudentScore as SS,
)
from app.services import scoring, job_roles as job_roles_svc
from app.services.ai_service import generate_ai_report

EXCEL_PATH = os.path.join(os.path.dirname(ROOT), "Students Complete Details - CCDP 2.xlsx")
BATCH_NAME = "CCDP 2"
COURSE_NAME = "CCDP (Career & Competency Development Program)"


def parse_assessment(wb):
    """Parse Assessment sheet. Row 1 = col names, Row 2 = scales, Row 3+ = data."""
    ws = wb["Assessment"]
    rows = list(ws.iter_rows(values_only=True))
    col_names = rows[0]  # (S.No, Name, RolePlay, BasicComp, ...)
    scale_row = rows[1]  # (None, None, 'Out of 20', 'Out of 50', ...)

    # Build skill -> scale map
    skills = {}
    for i, col in enumerate(col_names):
        if col is None or col in ("S.No", "Name", "Total"):
            continue
        scale_str = scale_row[i] if i < len(scale_row) else None
        scale = 100.0
        if scale_str and isinstance(scale_str, str):
            import re
            m = re.search(r"(\d+)", scale_str)
            if m:
                scale = float(m.group(1))
        skills[i] = {"name": str(col).strip(), "scale": scale}

    # Parse student data
    student_map = {}  # name -> {skill_name: score_0_to_100}
    for row in rows[2:]:
        name = row[1]
        if not name or not isinstance(name, str):
            continue
        name = name.strip()
        if not name:
            continue
        scores = {}
        for i, meta in skills.items():
            val = row[i] if i < len(row) else None
            if val is not None:
                try:
                    numeric = float(val)
                    normalized = round((numeric / meta["scale"]) * 100, 1)
                    normalized = max(0.0, min(100.0, normalized))
                    scores[meta["name"]] = normalized
                except Exception:
                    pass
        student_map[name] = scores
    return student_map


def parse_skill_matrix(wb):
    """Parse Skill Matrix sheet (Out of 10 scores)."""
    ws = wb["Skill Matrix"]
    rows = list(ws.iter_rows(values_only=True))
    col_names = rows[0]

    skill_map = {}
    for i, col in enumerate(col_names):
        if col is None or col in ("S.No", "Name"):
            continue
        name = str(col).strip().replace("\n", " ")
        # Exclude non-skill columns
        if "typing" in name.lower() or "wpm" in name.lower():
            continue
        skill_map[i] = name

    student_scores = {}
    for row in rows[1:]:
        name = row[1]
        if not name or not isinstance(name, str):
            continue
        name = name.strip()
        scores = {}
        for i, skill_name in skill_map.items():
            val = row[i] if i < len(row) else None
            if val is not None:
                try:
                    numeric = float(val)
                    normalized = round((numeric / 10.0) * 100, 1)
                    normalized = max(0.0, min(100.0, normalized))
                    scores[skill_name] = normalized
                except Exception:
                    pass
        student_scores[name] = scores
    return student_scores


def parse_attendance(wb):
    """Parse Attendance sheet. Row 1 = category, Row 2 = headers (S.No, Name, dates...), Row 3+ = data."""
    ws = wb["Attendance"]
    rows = list(ws.iter_rows(values_only=True))
    # Find the header row (has 'Name' in it)
    header_row_idx = 1
    for idx, row in enumerate(rows):
        if row[1] == "Name" or (row[1] is not None and str(row[1]).strip().lower() == "name"):
            header_row_idx = idx
            break

    student_attendance = {}
    for row in rows[header_row_idx + 1:]:
        name = row[1]
        if not name or not isinstance(name, str):
            continue
        name = name.strip()
        # Count P and A
        day_values = [v for v in row[2:] if v in ("P", "A", "p", "a", "L", "l")]
        total = len(day_values)
        present = sum(1 for v in day_values if str(v).upper() in ("P",))
        pct = round((present / total) * 100, 1) if total > 0 else 0.0
        student_attendance[name] = pct
    return student_attendance


def parse_students_details(wb):
    """Parse Students Details for name, email, phone, roll number."""
    ws = wb["Students Details"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]

    col_map = {}
    for i, col in enumerate(header):
        if col is None:
            continue
        lc = str(col).strip().lower()
        if lc == "name":
            col_map["name"] = i
        elif "enrol" in lc:
            col_map["roll"] = i
        elif "email" in lc:
            col_map["email"] = i
        elif lc == "personal no.":
            col_map["phone"] = i

    students = {}
    for row in rows[1:]:
        name_val = row[col_map["name"]] if "name" in col_map else None
        if not name_val or not isinstance(name_val, str):
            continue
        name = name_val.strip()
        students[name] = {
            "roll": str(row[col_map["roll"]]).strip() if "roll" in col_map else "",
            "email": str(row[col_map["email"]]).strip() if "email" in col_map else "",
            "phone": str(int(row[col_map["phone"]])) if "phone" in col_map and row[col_map["phone"]] else "",
        }
    return students


def canonical_skill_name(raw: str) -> str:
    """Map raw skill column names to canonical CCDP skill names."""
    lc = raw.strip().lower()
    if "communication" in lc:
        return "Communication Skills"
    if "analytical" in lc or "aptitude" in lc:
        return "Analytical Skills"
    if "leadership" in lc:
        return "Leadership Skills"
    if "creativity" in lc or "innovation" in lc:
        return "Creativity & Innovation"
    if "technical" in lc:
        return "Technical Skills"
    if "soft skill" in lc or "role play" in lc:
        return "Soft Skills"
    if "ms word" in lc or "word" in lc:
        return "MS Word"
    if "ms excel" in lc or "excel" in lc:
        return "MS Excel"
    if "basic computer" in lc or "computer" in lc:
        return "MS Office & IT"
    if "basic english" in lc or "english" in lc:
        return "Verbal Ability"
    if "business writing" in lc or "writing" in lc:
        return "Business Writing"
    if "hospital administration" in lc or "banking" in lc:
        return "Healthcare Domain"
    return raw.strip().title()


async def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("[CLEAR] Clearing existing student data...")
    db.query(StudentScore).delete()
    db.query(AnalysisResult).delete()
    db.query(Student).delete()
    db.query(Batch).delete()
    db.query(Course).delete()
    db.query(Upload).delete()
    db.query(ActivityLog).delete()
    db.commit()
    print("[OK] Cleared.")

    print(f"[LOAD] Loading: {EXCEL_PATH}")
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

    # Parse all sheets
    print("[PARSE] Parsing Assessment scores...")
    assessment_scores = parse_assessment(wb)
    print(f"   -> {len(assessment_scores)} students from Assessment")

    print("[PARSE] Parsing Skill Matrix...")
    skill_matrix_scores = parse_skill_matrix(wb)
    print(f"   -> {len(skill_matrix_scores)} students from Skill Matrix")

    print("[PARSE] Parsing Attendance...")
    attendance_map = parse_attendance(wb)
    print(f"   -> {len(attendance_map)} students from Attendance")

    print("[PARSE] Parsing Student Details...")
    student_details = parse_students_details(wb)
    print(f"   -> {len(student_details)} students from Student Details")

    # All student names
    all_names = set(assessment_scores.keys()) | set(skill_matrix_scores.keys()) | set(attendance_map.keys())
    print(f"\n[INFO] Total unique students: {len(all_names)}")

    # Create course & batch
    course = db.query(Course).filter(Course.name == COURSE_NAME).first()
    if not course:
        course = Course(name=COURSE_NAME)
        db.add(course)
        db.flush()

    batch = db.query(Batch).filter(Batch.name == BATCH_NAME, Batch.course_id == course.id).first()
    if not batch:
        batch = Batch(name=BATCH_NAME, course_id=course.id)
        db.add(batch)
        db.flush()

    # Collect all canonical skill names
    all_skill_names = set()
    for name in all_names:
        for raw_skill in (assessment_scores.get(name) or {}).keys():
            all_skill_names.add(canonical_skill_name(raw_skill))
        for raw_skill in (skill_matrix_scores.get(name) or {}).keys():
            all_skill_names.add(canonical_skill_name(raw_skill))

    # Upsert Skill rows
    skill_objs = {}
    for sname in all_skill_names:
        s = db.query(Skill).filter(Skill.name == sname).first()
        if not s:
            s = Skill(name=sname)
            db.add(s)
            db.flush()
        skill_objs[sname] = s

    db.commit()

    print("\n[IMPORT] Importing students...")
    saved_count = 0
    for name in sorted(all_names):
        details = student_details.get(name, {})
        att_pct = attendance_map.get(name, 85.0)

        # Merge skill scores
        merged_scores = {}  # canonical_name -> score (0-100)
        for raw_skill, score in (assessment_scores.get(name) or {}).items():
            canon = canonical_skill_name(raw_skill)
            merged_scores[canon] = max(merged_scores.get(canon, 0), score)
        for raw_skill, score in (skill_matrix_scores.get(name) or {}).items():
            canon = canonical_skill_name(raw_skill)
            merged_scores[canon] = max(merged_scores.get(canon, 0), score)

        # Calculate overall score
        overall = scoring.overall_score(merged_scores, att_pct)

        # Create Student
        student = Student(
            name=name,
            roll_number=details.get("roll", ""),
            email=details.get("email", ""),
            phone=details.get("phone", ""),
            course_id=course.id,
            batch_id=batch.id,
            attendance_pct=att_pct,
            overall_score=overall,
        )
        db.add(student)
        db.flush()

        # Add StudentScore rows
        for canon_name, score_val in merged_scores.items():
            skill_obj = skill_objs.get(canon_name)
            if skill_obj:
                ss = StudentScore(student_id=student.id, skill_id=skill_obj.id, score=score_val)
                db.add(ss)

        # Job matching
        top_roles = job_roles_svc.match_job_roles(merged_scores, overall, db=db)
        top_conf = top_roles[0]["confidence"] if top_roles else 0.0
        readiness = scoring.placement_readiness_pct(overall, att_pct, top_conf)
        student.placement_ready = readiness >= 55.0

        # AI analysis
        strengths, weaknesses = scoring.strengths_and_weaknesses(merged_scores)
        ai_report = await generate_ai_report(name, overall, strengths, weaknesses, top_roles)

        analysis = AnalysisResult(
            student_id=student.id,
            overall_score=overall,
            placement_readiness_pct=readiness,
            strengths=json.dumps(strengths),
            weaknesses=json.dumps(weaknesses),
            recommended_roles=json.dumps(top_roles),
            salary_range=scoring.predict_salary_band(overall),
            interview_readiness=scoring.interview_readiness_label(overall),
            learning_roadmap=ai_report["learning_roadmap"],
            thirty_day_plan=ai_report["thirty_day_plan"],
            recommended_certifications=json.dumps(ai_report["recommended_certifications"]),
            ai_summary=ai_report["ai_summary"],
            ai_source=ai_report["ai_source"],
        )
        db.add(analysis)
        saved_count += 1
        print(f"  [OK] {name:30s} | Score: {overall:5.1f} | Attendance: {att_pct}% | Ready: {student.placement_ready}")

    # Log upload
    db.add(Upload(
        filename="Students Complete Details - CCDP 2.xlsx",
        mode="save",
        student_count=saved_count,
        detected_columns=json.dumps(list(all_skill_names)),
        detected_skills=json.dumps(list(all_skill_names)),
        status="processed",
    ))
    db.add(ActivityLog(
        action="upload:save",
        detail=f"CCDP 2 batch imported — {saved_count} students from Excel"
    ))
    db.commit()
    print(f"\n[DONE] {saved_count} students imported into '{BATCH_NAME}'.")
    db.close()


if __name__ == "__main__":
    asyncio.run(main())
