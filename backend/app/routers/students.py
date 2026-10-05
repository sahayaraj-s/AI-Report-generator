import json

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import ActivityLog, AnalysisResult, Batch, Course, Student, StudentScore

router = APIRouter(prefix="/api/students", tags=["students"])


def _student_out(s: Student) -> dict:
    # Get best fit role from latest analysis
    latest_analysis = None
    if s.analysis_results:
        latest_analysis = s.analysis_results[0]

    best_role = None
    fit_tier = None
    if latest_analysis and latest_analysis.recommended_roles:
        try:
            roles = json.loads(latest_analysis.recommended_roles)
            if roles:
                best_role = roles[0].get("role")
                fit_tier = roles[0].get("fit_tier")
        except Exception:
            pass

    return {
        "id": s.id,
        "roll_number": s.roll_number,
        "name": s.name,
        "email": s.email,
        "phone": s.phone,
        "photo_url": s.photo_url,
        "course": s.course.name if s.course else None,
        "batch": s.batch.name if s.batch else None,
        "attendance_pct": s.attendance_pct,
        "overall_score": s.overall_score,
        "placement_ready": s.placement_ready,
        "best_role": best_role,
        "fit_tier": fit_tier,
        "updated_at": s.updated_at,
    }


@router.get("/batches")
def list_batches(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Return all distinct batches for filter dropdowns."""
    batches = db.query(Batch).all()
    return {
        "batches": [
            {"id": b.id, "name": b.name, "course": b.course.name if b.course else None}
            for b in batches
        ]
    }


@router.get("")
def list_students(
    search: str = Query(default=""),
    course: str = Query(default=""),
    batch: str = Query(default=""),
    placement_ready: bool | None = Query(default=None),
    min_score: float | None = Query(default=None),
    sort_by: str = Query(default="name"),
    sort_dir: str = Query(default="asc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    q = db.query(Student)

    if search:
        like = f"%{search}%"
        q = q.filter(or_(Student.name.ilike(like), Student.roll_number.ilike(like), Student.email.ilike(like)))
    if course:
        q = q.join(Course).filter(Course.name == course)
    if batch:
        q = q.join(Batch).filter(Batch.name == batch)
    if placement_ready is not None:
        q = q.filter(Student.placement_ready == placement_ready)
    if min_score is not None:
        q = q.filter(Student.overall_score >= min_score)

    total = q.count()

    sort_col = {
        "name": Student.name,
        "overall_score": Student.overall_score,
        "attendance_pct": Student.attendance_pct,
        "updated_at": Student.updated_at,
    }.get(sort_by, Student.name)
    sort_col = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    q = q.order_by(sort_col)

    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_student_out(s) for s in items],
    }


@router.get("/{student_id}")
def get_student_profile(student_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(404, "Student not found")

    skill_scores = db.query(StudentScore).filter_by(student_id=student.id).all()
    latest = (
        db.query(AnalysisResult)
        .filter_by(student_id=student.id)
        .order_by(AnalysisResult.created_at.desc())
        .first()
    )

    latest_out = None
    if latest:
        latest_out = {
            "id": latest.id,
            "overall_score": latest.overall_score,
            "placement_readiness_pct": latest.placement_readiness_pct,
            "strengths": json.loads(latest.strengths or "[]"),
            "weaknesses": json.loads(latest.weaknesses or "[]"),
            "recommended_roles": json.loads(latest.recommended_roles or "[]"),
            "salary_range": latest.salary_range,
            "interview_readiness": latest.interview_readiness,
            "learning_roadmap": latest.learning_roadmap,
            "thirty_day_plan": latest.thirty_day_plan,
            "recommended_certifications": json.loads(latest.recommended_certifications or "[]"),
            "ai_summary": latest.ai_summary,
            "ai_source": latest.ai_source,
            "created_at": latest.created_at,
        }

    return {
        "student": _student_out(student),
        "skill_scores": [{"skill": ss.skill.name, "score": ss.score} for ss in skill_scores],
        "latest_analysis": latest_out,
    }


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    name = student.name
    try:
        db.query(StudentScore).filter(StudentScore.student_id == student_id).delete(synchronize_session=False)
        db.query(AnalysisResult).filter(AnalysisResult.student_id == student_id).delete(synchronize_session=False)
        db.delete(student)
        db.add(ActivityLog(action="delete_student", detail=f"Deleted student {name} (ID: {student_id})"))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to delete student: {str(e)}")
    return {"deleted": True, "id": student_id, "name": name}


@router.post("/bulk-delete")
def bulk_delete_students(payload: dict, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Delete multiple students by ID list."""
    ids = payload.get("ids", [])
    if not ids:
        raise HTTPException(400, "No student IDs provided")
    try:
        int_ids = [int(sid) for sid in ids]
        db.query(StudentScore).filter(StudentScore.student_id.in_(int_ids)).delete(synchronize_session=False)
        db.query(AnalysisResult).filter(AnalysisResult.student_id.in_(int_ids)).delete(synchronize_session=False)
        deleted = db.query(Student).filter(Student.id.in_(int_ids)).delete(synchronize_session=False)
        db.add(ActivityLog(action="bulk_delete_students", detail=f"Bulk deleted {deleted} students (IDs: {int_ids})"))
        db.commit()
        return {"deleted": deleted, "ids": int_ids}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to bulk delete students: {str(e)}")


@router.patch("/{student_id}")
def update_student(student_id: int, payload: dict, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    for field in ("name", "email", "phone", "roll_number"):
        if field in payload:
            setattr(student, field, payload[field])
    db.commit()
    return _student_out(student)
