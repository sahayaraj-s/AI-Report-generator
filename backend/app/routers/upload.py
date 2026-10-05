from __future__ import annotations
import json
from typing import Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import ActivityLog, AnalysisResult, Batch, Course, Institute, Skill, Student, StudentScore, Upload
from app.services.consolidator import consolidate_workbook
from app.services.analytics import compute_analytics_from_records, compute_student_metrics, get_threshold_settings
from app.services import scoring
from app.services.job_roles import match_job_roles
from app.services.pipeline import get_or_create

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_EXTENSIONS = (".xlsx", ".xls", ".csv")
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB
CHUNK_SIZE = 64 * 1024  # 64 KB chunks


async def read_file_with_limit(file: UploadFile, max_size: int = MAX_UPLOAD_SIZE) -> bytes:
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum upload limit of {max_size // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def persist_consolidated_student(
    db: Session,
    s_dict: dict,
    course_id: int,
    batch_id: int,
    overwrite: bool = True,
) -> tuple[Student, bool]:
    """
    Idempotent persistence for one consolidated student record.
    """
    existing = None
    if s_dict.get("roll_number"):
        existing = db.query(Student).filter_by(roll_number=str(s_dict["roll_number"]).strip()).first()
    if not existing and s_dict.get("email"):
        existing = db.query(Student).filter_by(email=str(s_dict["email"]).strip()).first()
    if not existing and s_dict.get("name") and batch_id:
        existing = db.query(Student).filter_by(name=str(s_dict["name"]).strip(), batch_id=batch_id).first()

    if existing and not overwrite:
        return existing, False

    student = existing or Student()
    student.name = str(s_dict.get("name") or s_dict.get("display_name") or "Unknown Student").strip()
    student.roll_number = str(s_dict.get("roll_number")).strip() if s_dict.get("roll_number") else None
    student.email = str(s_dict.get("email")).strip() if s_dict.get("email") else None
    student.phone = str(s_dict.get("phone")).strip() if s_dict.get("phone") else None
    student.course_id = course_id
    student.batch_id = batch_id
    student.attendance_pct = s_dict.get("attendance_pct")
    student.attendance_status = s_dict.get("attendance_status", "tracked")
    student.attendance_reason = s_dict.get("attendance_reason")
    student.overall_score = float(s_dict.get("overall_score") or 0.0)
    student.placement_ready = bool(s_dict.get("placement_ready", False))

    student.is_placed = bool(s_dict.get("is_placed", False))
    student.placement_company = s_dict.get("placement_company")
    student.placement_designation = s_dict.get("placement_designation")
    student.placement_salary = s_dict.get("placement_salary")
    student.placement_salary_num = float(s_dict.get("placement_salary_num") or 0.0)

    student.typing_wpm = s_dict.get("typing_wpm")
    student.compliance_json = json.dumps(s_dict.get("compliance") or {})

    if not existing:
        db.add(student)
    db.flush()

    # Genuine skills scores
    db.query(StudentScore).filter_by(student_id=student.id).delete()
    for skill_name, score in (s_dict.get("skill_scores") or {}).items():
        skill = get_or_create(db, Skill, name=skill_name)
        db.add(StudentScore(student_id=student.id, skill_id=skill.id, score=score))

    # AnalysisResult record
    strengths, weaknesses = scoring.strengths_and_weaknesses(s_dict.get("skill_scores") or {})
    role_matches = match_job_roles(s_dict.get("skill_scores") or {}, student.overall_score, db=db)
    top_role_name = role_matches[0]["role"] if role_matches else "Healthcare Operations"

    analysis = AnalysisResult(
        student_id=student.id,
        overall_score=student.overall_score,
        placement_readiness_pct=float(s_dict.get("placement_readiness_pct") or 0.0),
        strengths=json.dumps(strengths),
        weaknesses=json.dumps(weaknesses),
        recommended_roles=json.dumps(role_matches),
        salary_range=scoring.predict_salary_band(student.overall_score),
        interview_readiness=scoring.interview_readiness_label(student.overall_score),
        learning_roadmap="Focus on core clinical/technical competency and practical workplace communication.",
        thirty_day_plan="Weekly assessment and targeted role mock interviews.",
        recommended_certifications=json.dumps(["Kauvery Clinical Documentation Specialist", "Basic Life Support"]),
        ai_summary=f"{student.name} demonstrates an overall competency score of {student.overall_score}%. Best matching role: {top_role_name}.",
        ai_source="SkillBay Analytics v2",
    )
    db.add(analysis)
    return student, True


@router.post("/preview")
async def preview_upload(
    file: UploadFile = File(...),
    course_name: str = Form(default="CCDP (Career & Competency Development Program)"),
    batch_name: str = Form(default="CCDP 2"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Session-only Live Preview.
    Guarantees:
    - Exactly consolidated students (no multi-sheet row explosion).
    - Writes ZERO rows to the database.
    - Groups columns by class (skill, metric, compliance, derived, administrative/PII).
    - Returns identical stats/readiness to the dashboard.
    """
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(400, "Only .xlsx, .xls, or .csv files are accepted")

    raw = await read_file_with_limit(file)
    try:
        consolidated_students, consolidation_report = consolidate_workbook(
            raw,
            default_course=course_name,
            default_batch=batch_name,
        )
    except Exception as exc:
        raise HTTPException(400, f"Could not process workbook: {exc}")

    # Compute analytics from records with DB settings (0 DB writes)
    computed = compute_analytics_from_records(consolidated_students, db=db)

    cols_by_class = consolidation_report.get("columns_by_class", {})
    detected_skills = cols_by_class.get("skill", [])
    compliance_cols = cols_by_class.get("compliance", [])
    metric_cols = cols_by_class.get("metric", [])
    derived_cols = cols_by_class.get("derived", [])
    admin_cols = cols_by_class.get("administrative/PII", [])

    all_detected_cols = []
    for cls_cols in cols_by_class.values():
        all_detected_cols.extend(cls_cols)
    all_detected_cols = sorted(list(set(all_detected_cols)))

    warnings = [
        f"{n['title']}: {n['detail']}"
        for n in consolidation_report.get("data_quality_notes", [])
    ]

    return {
        "upload_id": None,  # Explicitly None to confirm session-only with 0 DB writes
        "filename": file.filename,
        "student_count": len(consolidated_students),
        "detected_batch": batch_name,
        "detected_course": course_name,
        "detected_columns": all_detected_cols,
        "detected_skills": detected_skills,
        "compliance_columns": compliance_cols,
        "metric_columns": metric_cols,
        "derived_columns": derived_cols,
        "excluded_columns": sorted(list(set(derived_cols + admin_cols))),
        "columns_by_class": cols_by_class,
        "sheets_summary": consolidation_report.get("sheets", []),
        "consolidation_report": consolidation_report,
        "data_quality_notes": consolidation_report.get("data_quality_notes", []),
        "file_size_kb": round(len(raw) / 1024, 1),
        "warnings": warnings,
        "students": computed["students"],
        "kpis": {
            "total_students": computed["total_students"],
            "average_score": computed["average_score"],
            "placement_ready_count": computed["placement_ready"],
            "placement_ready_pct": computed["placement_ready_pct"],
            "placed_count": computed["placed_count"],
            "placed_pct": computed["placed_pct"],
            "average_attendance": computed["average_attendance"],
            "score_tier_distribution": computed["score_tier_distribution"],
            "typing_stats": computed["typing_stats"],
            "target_metrics": computed["target_metrics"],
        },
    }


@router.post("/process")
async def process_upload(
    file: UploadFile = File(...),
    mode: str = Form(...),  # "live" | "save" | "update"
    course_name: str = Form(default="CCDP (Career & Competency Development Program)"),
    batch_name: str = Form(default="CCDP 2"),
    overwrite: bool = Form(default=False),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Processes the uploaded workbook.
    - If mode == "live": returns preview session data (0 DB writes).
    - If mode in ("save", "update"): saves consolidated students idempotently into DB.
    """
    if mode not in ("live", "save", "update"):
        raise HTTPException(400, "mode must be one of: live, save, update")
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(400, "Only .xlsx, .xls, or .csv files are accepted")

    raw = await read_file_with_limit(file)
    final_course = course_name.strip() or "CCDP (Career & Competency Development Program)"
    final_batch = batch_name.strip() or "CCDP 2"

    try:
        consolidated_students, consolidation_report = consolidate_workbook(
            raw,
            default_course=final_course,
            default_batch=final_batch,
        )
    except Exception as exc:
        raise HTTPException(400, f"Could not process workbook: {exc}")

    # Compute student metrics using consolidated pipeline
    cfg = get_threshold_settings(db)
    computed_records = [
        compute_student_metrics(s, cfg, db=db)
        for s in consolidated_students
    ]

    computed_analytics = compute_analytics_from_records(computed_records, db=db)

    cols_by_class = consolidation_report.get("columns_by_class", {})
    detected_skills = cols_by_class.get("skill", [])

    if mode == "live":
        # Purely session-only: writes nothing to DB
        return {
            "mode": mode,
            "filename": file.filename,
            "student_count": len(computed_records),
            "sheets_summary": consolidation_report.get("sheets", []),
            "consolidation_report": consolidation_report,
            "columns_by_class": cols_by_class,
            "warnings": [
                f"{n['title']}: {n['detail']}"
                for n in consolidation_report.get("data_quality_notes", [])
            ],
            "students": computed_analytics["students"],
            "kpis": {
                "total_students": computed_analytics["total_students"],
                "average_score": computed_analytics["average_score"],
                "placement_ready_count": computed_analytics["placement_ready"],
                "placement_ready_pct": computed_analytics["placement_ready_pct"],
                "placed_count": computed_analytics["placed_count"],
                "placed_pct": computed_analytics["placed_pct"],
                "average_attendance": computed_analytics["average_attendance"],
                "score_tier_distribution": computed_analytics["score_tier_distribution"],
                "typing_stats": computed_analytics["typing_stats"],
            },
        }

    # Save / Update mode
    course = get_or_create(db, Course, name=final_course)
    batch = db.query(Batch).filter_by(name=final_batch, course_id=course.id).first()
    if not batch:
        batch = Batch(name=final_batch, course_id=course.id)
        db.add(batch)
        db.flush()

    saved, skipped = 0, 0
    allow_overwrite = (mode == "update" and overwrite) or mode == "save" or mode == "update"

    for s_dict in computed_records:
        _, was_written = persist_consolidated_student(
            db=db,
            s_dict=s_dict,
            course_id=course.id,
            batch_id=batch.id,
            overwrite=allow_overwrite,
        )
        if was_written:
            saved += 1
        else:
            skipped += 1

    upload_row = Upload(
        filename=file.filename,
        mode=mode,
        student_count=len(computed_records),
        detected_columns=json.dumps(detected_skills),
        detected_skills=json.dumps(detected_skills),
        status="processed",
    )
    db.add(upload_row)
    db.add(ActivityLog(
        action=f"upload:{mode}",
        detail=f"{file.filename} (Batch: {final_batch}) — {saved} saved, {skipped} skipped",
    ))
    db.commit()

    return {
        "mode": mode,
        "filename": file.filename,
        "student_count": len(computed_records),
        "saved": saved,
        "skipped": skipped,
        "batch": final_batch,
        "course": final_course,
        "sheets_summary": consolidation_report.get("sheets", []),
        "consolidation_report": consolidation_report,
        "columns_by_class": cols_by_class,
        "warnings": [
            f"{n['title']}: {n['detail']}"
            for n in consolidation_report.get("data_quality_notes", [])
        ],
        "kpis": {
            "total_students": computed_analytics["total_students"],
            "average_score": computed_analytics["average_score"],
            "placement_ready_count": computed_analytics["placement_ready"],
            "placement_ready_pct": computed_analytics["placement_ready_pct"],
            "placed_count": computed_analytics["placed_count"],
            "placed_pct": computed_analytics["placed_pct"],
            "average_attendance": computed_analytics["average_attendance"],
        },
    }
