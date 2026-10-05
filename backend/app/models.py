from __future__ import annotations
import datetime as dt

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def now():
    return dt.datetime.utcnow()


class Institute(Base):
    __tablename__ = "institutes"

    id = Column(Integer, primary_key=True)
    name = Column(String, default="Skill Bay Academy")
    tagline = Column(String, default="Enabling Life Skills")
    parent_org = Column(String, default="Kauvery Hospital")
    program_name = Column(String, default="Career & Competency Development Program (CCDP)")
    program_duration = Column(String, default="50 Days")
    # Editable Kauvery units & departments (JSON arrays)
    kauvery_units_json = Column(Text, nullable=True)
    departments_json = Column(Text, nullable=True)
    # Editable scoring weights
    skill_weight_pct = Column(Float, default=75.0)
    attendance_weight_pct = Column(Float, default=25.0)
    # Centralized thresholds & targets
    readiness_cutoff = Column(Float, default=55.0)
    readiness_target_pct = Column(Float, default=80.0)
    attendance_target_pct = Column(Float, default=85.0)
    score_benchmark = Column(Float, default=75.0)
    typing_target_wpm = Column(Float, default=30.0)
    tier_1_cutoff = Column(Float, default=80.0)
    tier_2_cutoff = Column(Float, default=60.0)
    tier_3_cutoff = Column(Float, default=40.0)
    fit_perfect_cutoff = Column(Float, default=75.0)
    fit_medium_cutoff = Column(Float, default=55.0)
    fit_low_cutoff = Column(Float, default=35.0)
    created_at = Column(DateTime, default=now)


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=now)

    batches = relationship("Batch", back_populates="course")
    students = relationship("Student", back_populates="course")


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))

    course = relationship("Course", back_populates="batches")
    students = relationship("Student", back_populates="batch")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    roll_number = Column(String, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String)
    phone = Column(String)
    photo_url = Column(String, nullable=True)

    course_id = Column(Integer, ForeignKey("courses.id"))
    batch_id = Column(Integer, ForeignKey("batches.id"))

    attendance_pct = Column(Float, default=0.0)
    attendance_status = Column(String, default="tracked")  # "tracked" or "N/A"
    attendance_reason = Column(String, nullable=True)
    overall_score = Column(Float, default=0.0)
    placement_ready = Column(Boolean, default=False)  # score-based qualification

    # Actual placement outcome (from placement sheet)
    is_placed = Column(Boolean, default=False)
    placement_company = Column(String, nullable=True)
    placement_designation = Column(String, nullable=True)
    placement_salary = Column(String, nullable=True)
    placement_salary_num = Column(Float, default=0.0)

    # Metric & Compliance columns
    typing_wpm = Column(Float, nullable=True)
    compliance_json = Column(Text, nullable=True)  # JSON for uniform/sizes

    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    course = relationship("Course", back_populates="students")
    batch = relationship("Batch", back_populates="students")
    scores = relationship(
        "StudentScore", back_populates="student", cascade="all, delete-orphan"
    )
    analysis_results = relationship(
        "AnalysisResult",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="desc(AnalysisResult.created_at)",
    )


class StudentScore(Base):
    """One row per (student, skill) — powers the skill radar & weak-skill heatmap."""

    __tablename__ = "student_scores"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    skill_id = Column(Integer, ForeignKey("skills.id"))
    score = Column(Float, default=0.0)  # normalized 0-100

    student = relationship("Student", back_populates="scores")
    skill = relationship("Skill")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))

    overall_score = Column(Float)
    placement_readiness_pct = Column(Float)
    strengths = Column(Text)  # JSON-encoded list
    weaknesses = Column(Text)  # JSON-encoded list
    recommended_roles = Column(Text)  # JSON-encoded list of {role, confidence}
    salary_range = Column(String)
    interview_readiness = Column(String)
    learning_roadmap = Column(Text)
    thirty_day_plan = Column(Text)
    recommended_certifications = Column(Text)  # JSON-encoded list
    ai_summary = Column(Text)
    ai_source = Column(String, default="local")  # "gemini" or "local"

    created_at = Column(DateTime, default=now)

    student = relationship("Student", back_populates="analysis_results")


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True)
    filename = Column(String)
    mode = Column(String)  # live | save | update
    student_count = Column(Integer, default=0)
    detected_columns = Column(Text)  # JSON list
    detected_skills = Column(Text)  # JSON list
    status = Column(String, default="processed")
    created_at = Column(DateTime, default=now)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True)
    action = Column(String)
    detail = Column(String)
    created_at = Column(DateTime, default=now)


class JobRoleModel(Base):
    __tablename__ = "job_roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    # JSON list of {"skill": "Communication Skills", "min_score": 15, "max_score": 25}
    required_skills = Column(Text, nullable=False, default="[]")
    min_score = Column(Float, default=50.0)          # overall score cutoff
    demand_level = Column(String, default="Medium")  # High / Medium / Selective
    openings = Column(Integer, default=0)            # number of open positions
    is_active = Column(Boolean, default=True)        # active/inactive toggle
    company_name = Column(String, nullable=True)     # optional partner company
    kauvery_unit = Column(String, nullable=True)     # Kauvery unit / branch (e.g. Trichy Tennur, Chennai Alwarpet)
    department = Column(String, nullable=True)       # Department (e.g. Patient Care, Front Office, Billing, IT)
    created_at = Column(DateTime, default=now)


class AIChatSession(Base):
    """Persists chat sessions for the SkillBay AI assistant."""

    __tablename__ = "ai_chat_sessions"

    id = Column(Integer, primary_key=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    messages = relationship(
        "AIChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AIChatMessage.created_at",
    )


class AIChatMessage(Base):
    """One row per message in a chat session."""

    __tablename__ = "ai_chat_messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("ai_chat_sessions.id"))
    role = Column(String, nullable=False)   # "user" | "assistant"
    content = Column(Text, nullable=False)
    source = Column(String, default="gemini")  # "gemini" | "local"
    model = Column(String, default="gemini-3.6-flash")
    created_at = Column(DateTime, default=now)

    session = relationship("AIChatSession", back_populates="messages")
