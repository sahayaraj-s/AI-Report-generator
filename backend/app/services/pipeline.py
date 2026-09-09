from __future__ import annotations
import json
import pandas as pd
from sqlalchemy.orm import Session

from app.models import AnalysisResult, Batch, Course, Skill, Student, StudentScore
from app.services import scoring, job_roles as job_roles_svc
from app.services.ai_service import generate_ai_report


def get_or_create(db: Session, model, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    instance = model(**kwargs)
    db.add(instance)
    db.flush()
    return instance


async def build_student_records(
    df: pd.DataFrame,
    meta_columns: dict,
    skill_columns_meta: dict,
    default_course: str = "CCDP (Career & Competency Development Program)",
    default_batch: str = "CCDP 1",
    skill_weight: float = 0.75,
    att_weight: float = 0.25,
):
    """
    Pure computation step (no DB writes): returns a list of dicts, one per
    student row, with normalized scores and AI analysis computed.
    """
    records = []
    for idx, row in df.iterrows():
        name = str(row.get(meta_columns.get("name", ""), "")).strip()
        if not name or name.lower() == "nan":
            continue

        # Extract normalized skill scores using each column's specific scale
        skill_scores = {}
        for raw_col, meta in skill_columns_meta.items():
            clean_name = meta["clean_name"]
            scale = meta["scale"]
            raw_val = row.get(raw_col, 0)
            score_100 = scoring.normalize_score(raw_val, scale)
            # If multiple columns map to same clean skill, take highest or average
            if clean_name in skill_scores:
                skill_scores[clean_name] = round((skill_scores[clean_name] + score_100) / 2.0, 1)
            else:
                skill_scores[clean_name] = score_100

        # Attendance parsing
        attendance_raw = row.get(meta_columns.get("attendance", ""), None)
        try:
            attendance_pct = float(attendance_raw) if attendance_raw is not None else 75.0
            if attendance_pct <= 1.0 and attendance_pct > 0.0:
                attendance_pct *= 100.0
        except (TypeError, ValueError):
            attendance_pct = 75.0
        attendance_pct = round(max(0.0, min(attendance_pct, 100.0)), 1)

        # Batch resolution: explicit column > sheet metadata > default
        row_batch = None
        if "batch" in meta_columns and row.get(meta_columns["batch"]):
            val = str(row[meta_columns["batch"]]).strip()
            if val and val.lower() != "nan":
                row_batch = val
        if not row_batch and "_detected_batch" in row:
            row_batch = str(row["_detected_batch"]).strip()
        if not row_batch:
            row_batch = default_batch or "CCDP 1"

        # Course resolution
        row_course = None
        if "course" in meta_columns and row.get(meta_columns["course"]):
            val = str(row[meta_columns["course"]]).strip()
            if val and val.lower() != "nan":
                row_course = val
        if not row_course:
            row_course = default_course or "CCDP (Career & Competency Development Program)"

        overall = scoring.overall_score(skill_scores, attendance_pct, skill_weight, att_weight)
        top_roles = job_roles_svc.match_job_roles(skill_scores, overall)
        top_role_confidence = top_roles[0]["confidence"] if top_roles else 0.0
        readiness = scoring.placement_readiness_pct(overall, attendance_pct, top_role_confidence)
        strengths, weaknesses = scoring.strengths_and_weaknesses(skill_scores)

        ai_report = await generate_ai_report(name, overall, strengths, weaknesses, top_roles)

        records.append(
            {
                "name": name,
                "roll_number": str(row.get(meta_columns.get("roll_number", ""), "")).strip() or None,
                "email": str(row.get(meta_columns.get("email", ""), "")).strip() or None,
                "phone": str(row.get(meta_columns.get("phone", ""), "")).strip() or None,
                "course": row_course,
                "batch": row_batch,
                "attendance_pct": attendance_pct,
                "overall_score": overall,
                "placement_ready": readiness >= 55.0,
                "placement_readiness_pct": readiness,
                "skill_scores": skill_scores,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "recommended_roles": top_roles,
                "salary_range": scoring.predict_salary_band(overall),
                "interview_readiness": scoring.interview_readiness_label(overall),
                "ai_summary": ai_report["ai_summary"],
                "learning_roadmap": ai_report["learning_roadmap"],
                "thirty_day_plan": ai_report["thirty_day_plan"],
                "recommended_certifications": ai_report["recommended_certifications"],
                "ai_source": ai_report["ai_source"],
            }
        )

    return records


def persist_student_record(db: Session, record: dict, default_course: str, default_batch: str, overwrite: bool):
    course_name = record["course"] or default_course or "CCDP (Career & Competency Development Program)"
    batch_name = record["batch"] or default_batch or "CCDP 1"

    course = get_or_create(db, Course, name=course_name)
    batch = db.query(Batch).filter_by(name=batch_name, course_id=course.id).first()
    if not batch:
        batch = Batch(name=batch_name, course_id=course.id)
        db.add(batch)
        db.flush()

    existing = None
    if record["roll_number"]:
        existing = db.query(Student).filter_by(roll_number=record["roll_number"]).first()
    if not existing and record["email"]:
        existing = db.query(Student).filter_by(email=record["email"]).first()
    if not existing and record["name"] and batch.id:
        existing = db.query(Student).filter_by(name=record["name"], batch_id=batch.id).first()

    if existing and not overwrite:
        return existing, False  # skipped

    student = existing or Student()
    student.name = record["name"]
    student.roll_number = record["roll_number"]
    student.email = record["email"]
    student.phone = record["phone"]
    student.course_id = course.id
    student.batch_id = batch.id
    student.attendance_pct = record["attendance_pct"]
    student.overall_score = record["overall_score"]
    student.placement_ready = record["placement_ready"]

    if not existing:
        db.add(student)
    db.flush()

    # Replace skill scores for this student
    db.query(StudentScore).filter_by(student_id=student.id).delete()
    for skill_name, score in record["skill_scores"].items():
        skill = get_or_create(db, Skill, name=skill_name)
        db.add(StudentScore(student_id=student.id, skill_id=skill.id, score=score))

    analysis = AnalysisResult(
        student_id=student.id,
        overall_score=record["overall_score"],
        placement_readiness_pct=record["placement_readiness_pct"],
        strengths=json.dumps(record["strengths"]),
        weaknesses=json.dumps(record["weaknesses"]),
        recommended_roles=json.dumps(record["recommended_roles"]),
        salary_range=record["salary_range"],
        interview_readiness=record["interview_readiness"],
        learning_roadmap=record["learning_roadmap"],
        thirty_day_plan=record["thirty_day_plan"],
        recommended_certifications=json.dumps(record["recommended_certifications"]),
        ai_summary=record["ai_summary"],
        ai_source=record["ai_source"],
    )
    db.add(analysis)

    return student, True  # saved/updated
