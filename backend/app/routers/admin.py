from __future__ import annotations
import json
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnalysisResult, ActivityLog, Batch, Course, Institute, JobRoleModel, Skill, Student, StudentScore, Upload
from app.services.job_roles import KAUVERY_UNITS, DEPARTMENTS, _get_default_kauvery_roles
from app.services.upload_processing import _is_non_skill_column, extract_skill_meta
from app.services import scoring, job_roles as job_roles_svc
from app.auth import get_current_admin
from app.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _get_or_create_institute(db: Session) -> Institute:
    institute = db.query(Institute).first()
    if not institute:
        institute = Institute(
            name="Skill Bay Academy",
            tagline="Enabling Life Skills",
            parent_org="Kauvery Hospital",
            program_name="Career & Competency Development Program (CCDP)",
            program_duration="50 Days",
        )
        db.add(institute)
        db.commit()
        db.refresh(institute)
    return institute


def _parse_units(institute: Institute) -> list[str]:
    if institute.kauvery_units_json:
        try:
            return json.loads(institute.kauvery_units_json)
        except Exception:
            pass
    return list(KAUVERY_UNITS)


def _parse_departments(institute: Institute) -> list[str]:
    if institute.departments_json:
        try:
            return json.loads(institute.departments_json)
        except Exception:
            pass
    return list(DEPARTMENTS)


@router.get("/settings")
def get_admin_settings(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    institute = _get_or_create_institute(db)
    skill_w = institute.skill_weight_pct if institute.skill_weight_pct is not None else 75.0
    att_w = institute.attendance_weight_pct if institute.attendance_weight_pct is not None else 25.0

    return {
        "institute_name": institute.name,
        "tagline": institute.tagline,
        "parent_org": institute.parent_org or "Kauvery Hospital",
        "program_name": institute.program_name or "Career & Competency Development Program (CCDP)",
        "program_duration": institute.program_duration or "50 Days",
        "gemini_model": settings.gemini_model,
        "gemini_api_key_configured": bool(settings.gemini_api_key),
        "kauvery_first_preference": True,
        "placement_readiness_threshold": institute.readiness_cutoff if institute.readiness_cutoff is not None else 55.0,
        "readiness_cutoff": institute.readiness_cutoff if institute.readiness_cutoff is not None else 55.0,
        "readiness_target_pct": institute.readiness_target_pct if institute.readiness_target_pct is not None else 80.0,
        "attendance_target_pct": institute.attendance_target_pct if institute.attendance_target_pct is not None else 85.0,
        "score_benchmark": institute.score_benchmark if institute.score_benchmark is not None else 75.0,
        "typing_target_wpm": institute.typing_target_wpm if institute.typing_target_wpm is not None else 30.0,
        "tier_1_cutoff": institute.tier_1_cutoff if institute.tier_1_cutoff is not None else 80.0,
        "tier_2_cutoff": institute.tier_2_cutoff if institute.tier_2_cutoff is not None else 60.0,
        "tier_3_cutoff": institute.tier_3_cutoff if institute.tier_3_cutoff is not None else 40.0,
        "fit_perfect_cutoff": institute.fit_perfect_cutoff if institute.fit_perfect_cutoff is not None else 75.0,
        "fit_medium_cutoff": institute.fit_medium_cutoff if institute.fit_medium_cutoff is not None else 55.0,
        "fit_low_cutoff": institute.fit_low_cutoff if institute.fit_low_cutoff is not None else 35.0,
        "skill_weight_pct": skill_w,
        "attendance_weight_pct": att_w,
        "kauvery_units": _parse_units(institute),
        "departments": _parse_departments(institute),
    }


@router.post("/settings")
def update_admin_settings(payload: dict = Body(...), db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    institute = _get_or_create_institute(db)

    if "institute_name" in payload:
        institute.name = payload["institute_name"]
    if "tagline" in payload:
        institute.tagline = payload["tagline"]
    if "parent_org" in payload:
        institute.parent_org = payload["parent_org"]
    if "program_name" in payload:
        institute.program_name = payload["program_name"]
    if "program_duration" in payload:
        institute.program_duration = payload["program_duration"]

    # Editable units & departments
    if "kauvery_units" in payload:
        units = [u.strip() for u in payload["kauvery_units"] if str(u).strip()]
        institute.kauvery_units_json = json.dumps(units)
    if "departments" in payload:
        depts = [d.strip() for d in payload["departments"] if str(d).strip()]
        institute.departments_json = json.dumps(depts)

    # Editable scoring weights
    if "skill_weight_pct" in payload or "attendance_weight_pct" in payload:
        sw = float(payload.get("skill_weight_pct", institute.skill_weight_pct or 75.0))
        aw = float(payload.get("attendance_weight_pct", institute.attendance_weight_pct or 25.0))
        if abs((sw + aw) - 100.0) > 0.5:
            raise HTTPException(status_code=400, detail="Skill weight + Attendance weight must sum to 100%.")
        institute.skill_weight_pct = round(sw, 1)
        institute.attendance_weight_pct = round(aw, 1)

    # Editable threshold settings
    for field_name in (
        "readiness_cutoff", "readiness_target_pct", "attendance_target_pct",
        "score_benchmark", "typing_target_wpm", "tier_1_cutoff", "tier_2_cutoff",
        "tier_3_cutoff", "fit_perfect_cutoff", "fit_medium_cutoff", "fit_low_cutoff"
    ):
        if field_name in payload and payload[field_name] is not None:
            try:
                setattr(institute, field_name, float(payload[field_name]))
            except (ValueError, TypeError):
                pass

    if "placement_readiness_threshold" in payload and payload["placement_readiness_threshold"] is not None:
        try:
            institute.readiness_cutoff = float(payload["placement_readiness_threshold"])
        except (ValueError, TypeError):
            pass

    db.commit()
    db.refresh(institute)
    return {"message": "Settings updated successfully", "status": "success"}


@router.get("/notifications")
def get_notifications(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Returns recent activity for the dashboard notification bell."""
    uploads = (
        db.query(Upload)
        .order_by(Upload.created_at.desc())
        .limit(8)
        .all()
    )
    logs = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(5)
        .all()
    )

    notifications = []
    for u in uploads:
        notifications.append({
            "id": f"upload_{u.id}",
            "type": "upload",
            "title": f"Batch uploaded: {u.filename or 'Excel File'}",
            "body": f"{u.student_count} students · {u.mode or 'save'} mode",
            "time": u.created_at.isoformat() if u.created_at else None,
        })
    for log in logs:
        notifications.append({
            "id": f"log_{log.id}",
            "type": "activity",
            "title": log.action or "System Activity",
            "body": log.detail or "",
            "time": log.created_at.isoformat() if log.created_at else None,
        })

    # Sort all by time desc
    notifications.sort(key=lambda x: x["time"] or "", reverse=True)
    return {"notifications": notifications[:10], "total": len(notifications)}


@router.post("/clean-legacy-skills")
async def clean_legacy_skills(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """
    Cleans up any legacy non-skill entries from skills table and student_scores
    (e.g., Shirt, Trouser, Tie, Shoe Size, Total, Typing Speed, phone numbers, age)
    and recalculates clean CCDP scores and analysis for all students using analytics.
    """
    from app.services.column_classifier import classify_column
    from app.services.analytics import compute_student_metrics, get_threshold_settings, load_students_from_db

    all_skills = db.query(Skill).all()
    deleted_count = 0

    for s in all_skills:
        c_class = classify_column(s.name)
        is_invalid = s.name.startswith("Unnamed:") or c_class != "skill" or s.name.strip().lower() in ("total", "marks", "grade", "gpa")
        if is_invalid:
            # If it's a compliance or metric column, preserve data in student fields
            scores = db.query(StudentScore).filter_by(skill_id=s.id).all()
            for sc in scores:
                st = db.query(Student).get(sc.student_id)
                if st:
                    if c_class == "compliance":
                        comp = json.loads(st.compliance_json or "{}")
                        comp[s.name] = str(sc.score)
                        st.compliance_json = json.dumps(comp)
                    elif c_class == "metric":
                        if sc.score > 0 and (st.typing_wpm is None or st.typing_wpm == 0):
                            st.typing_wpm = sc.score

            db.query(StudentScore).filter_by(skill_id=s.id).delete()
            db.delete(s)
            deleted_count += 1

    db.commit()

    # Recalculate scores and analysis for all existing students
    cfg = get_threshold_settings(db)
    students = db.query(Student).all()
    recalculated_count = 0

    for st in students:
        scores_raw = db.query(StudentScore).filter_by(student_id=st.id).all()
        skill_scores = {sr.skill.name: sr.score for sr in scores_raw if classify_column(sr.skill.name) == "skill"}

        raw_data = {
            "id": st.id,
            "name": st.name,
            "roll_number": st.roll_number,
            "email": st.email,
            "phone": st.phone,
            "course": st.course.name if st.course else None,
            "batch": st.batch.name if st.batch else None,
            "skill_scores": skill_scores,
            "attendance_pct": st.attendance_pct,
            "attendance_status": st.attendance_status,
            "attendance_reason": st.attendance_reason,
            "is_placed": st.is_placed,
            "placement_company": st.placement_company,
            "placement_designation": st.placement_designation,
            "placement_salary": st.placement_salary,
            "placement_salary_num": st.placement_salary_num,
            "typing_wpm": st.typing_wpm,
            "compliance": json.loads(st.compliance_json or "{}"),
        }

        computed = compute_student_metrics(raw_data, cfg, db=db)
        st.overall_score = computed["overall_score"]
        st.placement_ready = computed["placement_ready"]

        # Update AnalysisResult
        analysis = (
            db.query(AnalysisResult)
            .filter_by(student_id=st.id)
            .order_by(AnalysisResult.created_at.desc())
            .first()
        )
        if not analysis:
            analysis = AnalysisResult(student_id=st.id)
            db.add(analysis)

        analysis.overall_score = computed["overall_score"]
        analysis.placement_readiness_pct = computed["placement_readiness_pct"]
        analysis.strengths = json.dumps(computed["strengths"])
        analysis.weaknesses = json.dumps(computed["weaknesses"])
        analysis.recommended_roles = json.dumps(computed["role_matches"])
        analysis.salary_range = scoring.predict_salary_band(computed["overall_score"])
        analysis.interview_readiness = scoring.interview_readiness_label(computed["overall_score"])

        recalculated_count += 1

    db.commit()
    return {
        "message": f"Purged {deleted_count} non-skill columns. Recalculated {recalculated_count} student profiles.",
        "deleted_skills": deleted_count,
        "recalculated_students": recalculated_count,
    }


@router.post("/seed-kauvery-roles")
def seed_kauvery_roles(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Pre-seeds standard Kauvery Hospital placement roles."""
    defaults = _get_default_kauvery_roles()
    seeded = 0
    for r in defaults:
        existing = db.query(JobRoleModel).filter(JobRoleModel.name.ilike(r.name)).first()
        if not existing:
            criteria_json = json.dumps([
                {"skill": sc.skill, "min_score": sc.min_score, "max_score": sc.max_score}
                for sc in r.skill_criteria
            ])
            db.add(JobRoleModel(
                name=r.name,
                required_skills=criteria_json,
                min_score=r.min_score,
                demand_level=r.demand_level,
                openings=r.openings,
                is_active=r.is_active,
                company_name=r.company_name or "Kauvery Hospital",
                kauvery_unit=r.kauvery_unit or "Kauvery Hospital - Trichy (Tennur)",
                department=r.department or "Hospital Administration & Operations",
            ))
            seeded += 1
    db.commit()
    return {"message": f"Seeded {seeded} Kauvery Hospital placement roles.", "seeded_count": seeded}


@router.post("/clear-data")
def clear_all_data(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """
    Wipes all student records, scores, analysis results, courses, batches, and uploads
    to start with a clean state.
    """
    db.query(StudentScore).delete()
    db.query(AnalysisResult).delete()
    db.query(Student).delete()
    db.query(Batch).delete()
    db.query(Course).delete()
    db.query(Upload).delete()
    db.query(ActivityLog).delete()
    db.commit()

    return {"message": "All student data and uploads have been cleared successfully."}


@router.post("/clean-test-data")
def clean_test_data(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """
    Deletes all mock/test data (e.g. 2024 Batch, 2025 Batch, test sample uploads),
    preserving the real CCDP 2 student cohort.
    """
    # Find test batches (anything not named CCDP 2)
    test_batches = db.query(Batch).filter(Batch.name != "CCDP 2").all()
    test_batch_ids = [b.id for b in test_batches]

    # Students belonging to test batches or without a batch
    test_students = db.query(Student).filter(
        (Student.batch_id.in_(test_batch_ids)) | (Student.batch_id.is_(None))
    ).all()
    test_student_ids = [s.id for s in test_students]

    if test_student_ids:
        db.query(StudentScore).filter(StudentScore.student_id.in_(test_student_ids)).delete(synchronize_session=False)
        db.query(AnalysisResult).filter(AnalysisResult.student_id.in_(test_student_ids)).delete(synchronize_session=False)
        db.query(Student).filter(Student.id.in_(test_student_ids)).delete(synchronize_session=False)

    for b in test_batches:
        db.delete(b)

    # Delete test courses (anything not containing CCDP)
    test_courses = db.query(Course).filter(~Course.name.contains("CCDP")).all()
    for c in test_courses:
        db.delete(c)

    # Delete test uploads (sample.csv, sample_students.csv)
    test_uploads = db.query(Upload).filter(
        Upload.filename.in_(["sample.csv", "sample_students.csv"])
    ).all()
    for u in test_uploads:
        db.delete(u)

    db.add(ActivityLog(action="clean_test_data", detail=f"Cleaned {len(test_student_ids)} test students and {len(test_batches)} test batches"))
    db.commit()

    return {
        "message": f"Successfully purged {len(test_student_ids)} test students, {len(test_batches)} test batches, and test uploads. CCDP 2 cohort is fully preserved.",
        "deleted_students": len(test_student_ids),
        "deleted_batches": len(test_batches),
    }
