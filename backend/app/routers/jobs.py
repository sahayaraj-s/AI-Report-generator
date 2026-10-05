from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_admin
from app.models import Student, AnalysisResult, JobRoleModel
from app.services.job_roles import (
    get_all_job_roles, get_active_job_roles,
    get_role_candidates, _parse_skill_criteria, auto_detect_roles_from_skills,
    KAUVERY_UNITS, DEPARTMENTS, JobRole
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    """Return all defined job roles with Kauvery Hospital Units, Departments, structured skills, and match stats."""
    job_roles = get_all_job_roles(db)
    analysis_rows = db.query(AnalysisResult).order_by(AnalysisResult.created_at.desc()).all()

    role_student_map: dict[str, set[int]] = {}
    role_tier_map: dict[str, dict] = {}

    for ar in analysis_rows:
        if ar.recommended_roles:
            try:
                roles_data = json.loads(ar.recommended_roles) if isinstance(ar.recommended_roles, str) else ar.recommended_roles
            except Exception:
                roles_data = []
            if isinstance(roles_data, list):
                for rr in roles_data:
                    if isinstance(rr, dict):
                        role_name = rr.get("role", "")
                        if role_name:
                            role_student_map.setdefault(role_name, set()).add(ar.student_id)
                            tier = rr.get("fit_tier", "")
                            if role_name not in role_tier_map:
                                role_tier_map[role_name] = {"Perfect Match": 0, "Medium Fit": 0, "Low Fit": 0}
                            if tier in role_tier_map[role_name]:
                                role_tier_map[role_name][tier] += 1

    total_students = db.query(Student).count()
    active_roles = db.query(JobRoleModel).filter(JobRoleModel.is_active.is_(True)).count()
    total_openings = db.query(JobRoleModel).filter(JobRoleModel.is_active.is_(True)).all()
    total_openings_count = sum(r.openings or 0 for r in total_openings)

    roles = []
    for jr in job_roles:
        matched_ids = role_student_map.get(jr.name, set())
        tier_breakdown = role_tier_map.get(jr.name, {"Perfect Match": 0, "Medium Fit": 0, "Low Fit": 0})

        skill_criteria_out = []
        for sc in jr.skill_criteria:
            skill_criteria_out.append({
                "skill": sc.skill,
                "min_score": sc.min_score,
                "max_score": sc.max_score,
                "benchmark_pct": sc.benchmark_pct,
            })

        roles.append({
            "id": jr.id,
            "name": jr.name,
            "required_skills": jr.required_skills,
            "skill_criteria": skill_criteria_out,
            "min_score": jr.min_score,
            "demand_level": jr.demand_level,
            "openings": jr.openings,
            "is_active": jr.is_active,
            "company_name": jr.company_name or "Kauvery Hospital",
            "kauvery_unit": jr.kauvery_unit or "Kauvery Hospital - Trichy (Tennur)",
            "department": jr.department or "Hospital Administration & Operations",
            "matched_students": len(matched_ids),
            "tier_breakdown": tier_breakdown,
        })

    return {
        "total_roles": len(roles),
        "active_roles": active_roles,
        "total_students": total_students,
        "total_openings": total_openings_count,
        "kauvery_units": KAUVERY_UNITS,
        "departments": DEPARTMENTS,
        "roles": roles,
    }


@router.post("/roles")
def create_role(payload: dict = Body(...), db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    name = payload.get("name", "").strip()
    skill_criteria = payload.get("skill_criteria", [])
    required_skills_raw = payload.get("required_skills", [])
    demand_level = payload.get("demand_level", "High")
    openings = int(payload.get("openings", 1))
    is_active = bool(payload.get("is_active", True))
    company_name = payload.get("company_name", "Kauvery Hospital")
    kauvery_unit = payload.get("kauvery_unit", "Kauvery Hospital - Trichy (Tennur)")
    department = payload.get("department", "Patient Care & Customer Relations")
    min_score = float(payload.get("min_score", 0.0))

    if not name:
        raise HTTPException(400, "Role name is required")

    if skill_criteria:
        skills_json = json.dumps(skill_criteria)
    elif required_skills_raw:
        normalized = []
        for s in required_skills_raw:
            if isinstance(s, str):
                normalized.append({"skill": s, "min_score": 15.0, "max_score": 25.0})
            elif isinstance(s, dict):
                normalized.append(s)
        skills_json = json.dumps(normalized)
    else:
        # Default criteria if none supplied
        skills_json = json.dumps([{"skill": "Communication Skills", "min_score": 15.0, "max_score": 25.0}])

    existing = db.query(JobRoleModel).filter(JobRoleModel.name.ilike(name)).first()
    if existing:
        raise HTTPException(400, f"Role '{name}' already exists")

    new_role = JobRoleModel(
        name=name,
        required_skills=skills_json,
        min_score=min_score,
        demand_level=demand_level,
        openings=openings,
        is_active=is_active,
        company_name=company_name,
        kauvery_unit=kauvery_unit,
        department=department,
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    criteria = _parse_skill_criteria(new_role.required_skills)
    return {
        "id": new_role.id,
        "name": new_role.name,
        "skill_criteria": [{"skill": sc.skill, "min_score": sc.min_score, "max_score": sc.max_score, "benchmark_pct": sc.benchmark_pct} for sc in criteria],
        "required_skills": [sc.skill for sc in criteria],
        "min_score": new_role.min_score,
        "demand_level": new_role.demand_level,
        "openings": new_role.openings,
        "is_active": new_role.is_active,
        "company_name": new_role.company_name,
        "kauvery_unit": new_role.kauvery_unit,
        "department": new_role.department,
    }


@router.put("/roles/{role_id}")
def update_role(role_id: int, payload: dict = Body(...), db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    role = db.query(JobRoleModel).get(role_id)
    if not role:
        raise HTTPException(404, "Role not found")

    if "name" in payload:
        role.name = payload["name"].strip()
    if "demand_level" in payload:
        role.demand_level = payload["demand_level"]
    if "openings" in payload:
        role.openings = int(payload["openings"])
    if "is_active" in payload:
        role.is_active = bool(payload["is_active"])
    if "company_name" in payload:
        role.company_name = payload["company_name"]
    if "kauvery_unit" in payload:
        role.kauvery_unit = payload["kauvery_unit"]
    if "department" in payload:
        role.department = payload["department"]
    if "min_score" in payload:
        role.min_score = float(payload["min_score"])
    if "skill_criteria" in payload:
        role.required_skills = json.dumps(payload["skill_criteria"])
    elif "required_skills" in payload:
        raw = payload["required_skills"]
        normalized = []
        for s in raw:
            if isinstance(s, str):
                normalized.append({"skill": s, "min_score": 15.0, "max_score": 25.0})
            elif isinstance(s, dict):
                normalized.append(s)
        role.required_skills = json.dumps(normalized)

    db.commit()
    db.refresh(role)
    criteria = _parse_skill_criteria(role.required_skills)
    return {
        "id": role.id,
        "name": role.name,
        "skill_criteria": [{"skill": sc.skill, "min_score": sc.min_score, "max_score": sc.max_score, "benchmark_pct": sc.benchmark_pct} for sc in criteria],
        "required_skills": [sc.skill for sc in criteria],
        "min_score": role.min_score,
        "demand_level": role.demand_level,
        "openings": role.openings,
        "is_active": role.is_active,
        "company_name": role.company_name,
        "kauvery_unit": role.kauvery_unit,
        "department": role.department,
    }


@router.patch("/roles/{role_id}/toggle")
def toggle_role_active(role_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    role = db.query(JobRoleModel).get(role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    role.is_active = not role.is_active
    db.commit()
    return {"id": role.id, "name": role.name, "is_active": role.is_active}


@router.delete("/roles/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    role = db.query(JobRoleModel).get(role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    db.delete(role)
    db.commit()
    return {"deleted": True, "id": role_id}


@router.get("/roles/{role_id}/candidates")
def role_candidates(role_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    """Get students matched to this role classified by fit tier."""
    db_role = db.query(JobRoleModel).get(role_id)
    if not db_role:
        raise HTTPException(404, "Role not found")

    criteria = _parse_skill_criteria(db_role.required_skills or "[]")
    role = JobRole(
        id=db_role.id,
        name=db_role.name,
        skill_criteria=criteria,
        min_score=db_role.min_score or 0.0,
        demand_level=db_role.demand_level or "Medium",
        openings=db_role.openings or 0,
        is_active=db_role.is_active if db_role.is_active is not None else True,
        company_name=db_role.company_name or "Kauvery Hospital",
        kauvery_unit=db_role.kauvery_unit or "Kauvery Hospital - Trichy (Tennur)",
        department=db_role.department or "Hospital Administration & Operations",
    )

    candidates = get_role_candidates(role, db)

    perfect = [c for c in candidates if c["fit_tier"] == "Perfect Match"]
    medium = [c for c in candidates if c["fit_tier"] == "Medium Fit"]
    low = [c for c in candidates if c["fit_tier"] == "Low Fit"]

    return {
        "role_id": role_id,
        "role_name": db_role.name,
        "company_name": role.company_name,
        "kauvery_unit": role.kauvery_unit,
        "department": role.department,
        "openings": db_role.openings,
        "total_candidates": len(candidates),
        "perfect_match": len(perfect),
        "medium_fit": len(medium),
        "low_fit": len(low),
        "candidates": candidates,
    }


@router.post("/roles/auto-detect")
def auto_detect_roles(payload: dict = Body(...), admin: dict = Depends(get_current_admin)):
    detected_skills = payload.get("detected_skills", [])
    suggested = auto_detect_roles_from_skills(detected_skills)
    return {"suggested_roles": suggested}
