from __future__ import annotations
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import Upload
from app.services.analytics import AnalyticsFilters, compute_analytics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats(
    batch: str = Query(default=""),
    course: str = Query(default=""),
    performance_tier: str = Query(default=""),
    readiness: str = Query(default=""),
    placed: str = Query(default=""),
    search: str = Query(default=""),
    min_score: float | None = Query(default=None),
    max_score: float | None = Query(default=None),
    min_attendance: float | None = Query(default=None),
    sort_by: str = Query(default="overall_score"),
    sort_dir: str = Query(default="desc"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Power BI-grade aggregate stats powered by the single source of truth analytics service.
    Zero synthetic curves or fabricated data.
    """
    filters = AnalyticsFilters(
        batch=batch.strip(),
        course=course.strip(),
        tier=performance_tier.strip(),
        readiness=readiness.strip(),
        placed=placed.strip(),
        search=search.strip(),
        min_score=min_score,
        max_score=max_score,
        min_attendance=min_attendance,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    data = compute_analytics(db=db, filters=filters)

    recent_uploads = (
        db.query(Upload).order_by(Upload.created_at.desc()).limit(5).all()
    )
    recent_uploads_out = [
        {
            "filename": u.filename,
            "mode": u.mode,
            "student_count": u.student_count,
            "status": u.status,
            "created_at": u.created_at.isoformat() if u.created_at else "",
        }
        for u in recent_uploads
    ]

    data["recent_uploads"] = recent_uploads_out
    return data
