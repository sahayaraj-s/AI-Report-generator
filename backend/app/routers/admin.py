from __future__ import annotations
import json
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnalysisResult, ActivityLog, Batch, Course, Institute, JobRoleModel, Skill, Student, StudentScore, Upload
from app.services.job_roles import KAUVERY_UNITS, DEPARTMENTS, _get_default_kauvery_roles
from app.services.upload_processing import _is_non_skill_column, extract_skill_meta
from app.services import scoring, job_roles as job_roles_svc
from app.services.ai_service import generate_ai_report
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
def get_admin_settings(db: Session = Depends(get_db)):
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
        "placement_readiness_threshold": 55,
        "skill_weight_pct": skill_w,
        "attendance_weight_pct": att_w,
        "kauvery_units": _parse_units(institute),
        "departments": _parse_departments(institute),
    }


@router.post("/settings")
def update_admin_settings(payload: dict = Body(...), db: Session = Depends(get_db)):
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

    db.commit()
    db.refresh(institute)
    return {"message": "Settings updated successfully", "status": "success"}


@router.get("/notifications")
def get_notifications(db: Session = Depends(get_db)):
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
async def clean_legacy_skills(db: Session = Depends(get_db)):
    """
    Cleans up any legacy non-skill entries from skills table and student_scores
    (e.g., 'Parents No.', 'Age', 'Personal No.', 'Contact No.') and recalculates
    clean CCDP scores and analysis for all students.
    """
    # 1. Delete non-skills
    all_skills = db.query(Skill).all()
    deleted_count = 0
    valid_skills = []

    for s in all_skills:
        if _is_non_skill_column(s.name) or s.name.strip().lower() in ("total", "marks", "grade", "gpa"):
            db.query(StudentScore).filter_by(skill_id=s.id).delete()
            db.delete(s)
            deleted_count += 1
        else:
            valid_skills.append(s)

    db.commit()

    # 2. Group valid skills by clean canonical name
    from collections import defaultdict
    canonical_groups = defaultdict(list)
    for s in db.query(Skill).all():
        clean_name, _ = extract_skill_meta(s.name)
        canonical_groups[clean_name].append(s)

    for clean_name, group in canonical_groups.items():
        primary_skill = group[0]
        # Temporary unique rename to prevent collisions
        primary_skill.name = f"__canonical_{primary_skill.id}__"
        db.flush()

        for duplicate_skill in group[1:]:
            dup_scores = db.query(StudentScore).filter_by(skill_id=duplicate_skill.id).all()
            for sc in dup_scores:
                existing_sc = db.query(StudentScore).filter_by(
                    student_id=sc.student_id, skill_id=primary_skill.id
                ).first()
                if existing_sc:
                    existing_sc.score = max(existing_sc.score, sc.score)
                    db.delete(sc)
                else:
                    sc.skill_id = primary_skill.id
            db.delete(duplicate_skill)
            deleted_count += 1

    db.commit()

    # Now set final clean names
    for clean_name, group in canonical_groups.items():
        primary_skill = db.query(Skill).get(group[0].id)
        if primary_skill:
            primary_skill.name = clean_name
    db.commit()

    # 3. Recalculate scores and analysis for all existing students
    institute = _get_or_create_institute(db)
    skill_w = (institute.skill_weight_pct or 75.0) / 100.0
    att_w = (institute.attendance_weight_pct or 25.0) / 100.0

    students = db.query(Student).all()
    recalculated_count = 0

    for st in students:
        scores_raw = db.query(StudentScore).filter_by(student_id=st.id).all()
        skill_scores = {}
        for sr in scores_raw:
            score_val = sr.score
            if score_val <= 10.0 and score_val > 0:
                score_val = score_val * 10.0
            sr.score = round(min(max(score_val, 0.0), 100.0), 1)
            skill_scores[sr.skill.name] = sr.score

        st.overall_score = scoring.overall_score(skill_scores, st.attendance_pct, skill_w, att_w)
        top_roles = job_roles_svc.match_job_roles(skill_scores, st.overall_score, db=db)
        top_conf = top_roles[0]["confidence"] if top_roles else 0.0
        readiness = scoring.placement_readiness_pct(st.overall_score, st.attendance_pct, top_conf)
        st.placement_ready = readiness >= 55.0

        strengths, weaknesses = scoring.strengths_and_weaknesses(skill_scores)
        ai_report = await generate_ai_report(st.name, st.overall_score, strengths, weaknesses, top_roles)

        analysis = (
            db.query(AnalysisResult)
            .filter_by(student_id=st.id)
            .order_by(AnalysisResult.created_at.desc())
            .first()
        )
        if not analysis:
            analysis = AnalysisResult(student_id=st.id)
            db.add(analysis)

        analysis.overall_score = st.overall_score
        analysis.placement_readiness_pct = readiness
        analysis.strengths = json.dumps(strengths)
        analysis.weaknesses = json.dumps(weaknesses)
        analysis.recommended_roles = json.dumps(top_roles)
        analysis.salary_range = scoring.predict_salary_band(st.overall_score)
        analysis.interview_readiness = scoring.interview_readiness_label(st.overall_score)
        analysis.learning_roadmap = ai_report["learning_roadmap"]
        analysis.thirty_day_plan = ai_report["thirty_day_plan"]
        analysis.recommended_certifications = json.dumps(ai_report["recommended_certifications"])
        analysis.ai_summary = ai_report["ai_summary"]
        analysis.ai_source = ai_report["ai_source"]

        recalculated_count += 1

    db.commit()
    return {
        "message": f"Purged {deleted_count} non-skill columns. Recalculated {recalculated_count} student profiles.",
        "deleted_skills": deleted_count,
        "recalculated_students": recalculated_count,
    }


@router.post("/seed-kauvery-roles")
def seed_kauvery_roles(db: Session = Depends(get_db)):
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
def clear_all_data(db: Session = Depends(get_db)):
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
