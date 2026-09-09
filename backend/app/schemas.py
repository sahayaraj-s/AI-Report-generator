from __future__ import annotations
import datetime as dt

from pydantic import BaseModel, ConfigDict


class SkillScoreOut(BaseModel):
    skill: str
    score: float


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    roll_number: str | None = None
    name: str
    email: str | None = None
    phone: str | None = None
    photo_url: str | None = None
    course: str | None = None
    batch: str | None = None
    attendance_pct: float
    overall_score: float
    placement_ready: bool
    updated_at: dt.datetime


class StudentListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[StudentOut]


class RoleMatchOut(BaseModel):
    role: str
    confidence: float
    matched_skills: list[str]


class AnalysisResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    overall_score: float
    placement_readiness_pct: float
    strengths: list[str]
    weaknesses: list[str]
    recommended_roles: list[RoleMatchOut]
    salary_range: str
    interview_readiness: str
    learning_roadmap: str
    thirty_day_plan: str
    recommended_certifications: list[str]
    ai_summary: str
    ai_source: str
    created_at: dt.datetime


class StudentProfileOut(BaseModel):
    student: StudentOut
    skill_scores: list[SkillScoreOut]
    latest_analysis: AnalysisResultOut | None = None


class DashboardStatsOut(BaseModel):
    total_students: int
    placement_ready: int
    placement_ready_pct: float
    need_training: int
    need_training_critical: int
    need_training_moderate: int
    average_score: float
    average_attendance: float
    top_performer: str | None
    recruiters_partnered: int
    ai_accuracy_pct: float
    skill_distribution: list[dict]
    course_comparison: list[dict]
    monthly_progress: list[dict]
    weak_skill_heatmap: list[dict]
    recent_uploads: list[dict]


class UploadPreviewOut(BaseModel):
    upload_id: int
    filename: str
    student_count: int
    detected_columns: list[str]
    detected_skills: list[str]
    file_size_kb: float
    warnings: list[str]
