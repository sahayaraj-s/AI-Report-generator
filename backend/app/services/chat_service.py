"""
Chat service for the SkillBay AI assistant.

Builds a live DB context snapshot and routes queries to Gemini (if configured)
or a local keyword-based responder that returns real data — not lorem-ipsum.
"""
from __future__ import annotations
import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    JobRoleModel,
    Skill,
    Student,
    StudentScore,
    Upload,
)


# ---------------------------------------------------------------------------
# Context snapshot
# ---------------------------------------------------------------------------

def build_context_snapshot(db: Session) -> dict:
    """
    Query the DB once and return a compact dict that is injected into every
    AI prompt as live, accurate context.
    """
    total_students = db.query(Student).count()
    placement_ready = db.query(Student).filter(Student.placement_ready.is_(True)).count()
    placement_ready_pct = round((placement_ready / total_students) * 100, 1) if total_students else 0.0
    avg_score = db.query(func.avg(Student.overall_score)).scalar() or 0.0
    avg_attendance = db.query(func.avg(Student.attendance_pct)).scalar() or 0.0

    # Top performers
    top_students = (
        db.query(Student)
        .order_by(Student.overall_score.desc())
        .limit(3)
        .all()
    )
    top_performers = [{"name": s.name, "score": s.overall_score} for s in top_students]

    # Weak skills (bottom 4 by avg score)
    skill_rows = (
        db.query(Skill.name, func.avg(StudentScore.score))
        .join(StudentScore, StudentScore.skill_id == Skill.id)
        .group_by(Skill.name)
        .order_by(func.avg(StudentScore.score).asc())
        .limit(4)
        .all()
    )
    weak_skills = [{"skill": name, "avg_score": round(avg or 0, 1)} for name, avg in skill_rows]

    # Active job roles + openings
    active_roles = (
        db.query(JobRoleModel)
        .filter(JobRoleModel.is_active.is_(True))
        .all()
    )
    total_openings = sum(r.openings or 0 for r in active_roles)
    role_names = [r.name for r in active_roles]

    # Recent uploads
    recent_upload_count = db.query(Upload).count()
    last_upload = db.query(Upload).order_by(Upload.created_at.desc()).first()
    last_upload_info = (
        f"{last_upload.filename} ({last_upload.student_count} students)"
        if last_upload else "None"
    )

    # Critical (below 40 score)
    critical_count = db.query(Student).filter(Student.overall_score < 40).count()

    return {
        "total_students": total_students,
        "placement_ready": placement_ready,
        "placement_ready_pct": placement_ready_pct,
        "need_training": total_students - placement_ready,
        "critical_students": critical_count,
        "avg_score": round(avg_score, 1),
        "avg_attendance": round(avg_attendance, 1),
        "top_performers": top_performers,
        "weak_skills": weak_skills,
        "active_roles": role_names,
        "total_openings": total_openings,
        "total_uploads": recent_upload_count,
        "last_upload": last_upload_info,
    }


def build_system_prompt(context: dict) -> str:
    top = ", ".join(f"{p['name']} ({p['score']}/100)" for p in context["top_performers"]) or "N/A"
    weak = ", ".join(f"{w['skill']} (avg {w['avg_score']})" for w in context["weak_skills"]) or "N/A"
    roles = ", ".join(context["active_roles"]) or "None configured"

    return (
        "You are SkillBay AI, the placement intelligence assistant for Skill Bay Academy. "
        "Answer placement officers' questions concisely and accurately using the live database snapshot below. "
        "Use markdown formatting: bold for numbers, bullet lists for enumerations, tables for comparisons. "
        "Never fabricate data — if you don't know, say so and suggest what report to run.\n\n"
        f"**Live DB Snapshot:**\n"
        f"- Total students: **{context['total_students']}**\n"
        f"- Placement ready: **{context['placement_ready']}** ({context['placement_ready_pct']}%)\n"
        f"- Need training: **{context['need_training']}** (critical below 40: {context['critical_students']})\n"
        f"- Average score: **{context['avg_score']}/100** · Avg attendance: **{context['avg_attendance']}%**\n"
        f"- Top performers: {top}\n"
        f"- Weakest skills: {weak}\n"
        f"- Active job roles ({len(context['active_roles'])}): {roles}\n"
        f"- Total openings: **{context['total_openings']}**\n"
        f"- Total uploads processed: {context['total_uploads']} · Last upload: {context['last_upload']}\n"
    )


# ---------------------------------------------------------------------------
# Local keyword-based responder (no API key needed)
# ---------------------------------------------------------------------------

def _local_chat_response(query: str, context: dict) -> str:
    q = query.lower()

    if any(w in q for w in ["placement ready", "how many ready", "ready students", "placement-ready"]):
        return (
            f"**{context['placement_ready']} students** are currently placement-ready "
            f"({context['placement_ready_pct']}% of {context['total_students']} total)."
        )

    if any(w in q for w in ["need training", "not ready", "struggling", "low performers", "critical"]):
        return (
            f"**{context['need_training']} students** need training. "
            f"Of these, **{context['critical_students']}** are critical (overall score < 40)."
        )

    if any(w in q for w in ["top performer", "best student", "highest score", "topper"]):
        if context["top_performers"]:
            lines = "\n".join(f"- **{p['name']}** — {p['score']}/100" for p in context["top_performers"])
            return f"**Top performers:**\n{lines}"
        return "No students have been analyzed yet."

    if any(w in q for w in ["weak skill", "skill gap", "lowest skill", "poor skill", "needs improvement"]):
        if context["weak_skills"]:
            lines = "\n".join(f"- **{w['skill']}** — avg {w['avg_score']}/100" for w in context["weak_skills"])
            return f"**Weakest skills across all students:**\n{lines}\n\nConsider targeted workshops for these areas."
        return "No skill data available yet — upload a student sheet first."

    if any(w in q for w in ["job role", "openings", "active role", "hiring", "vacancy", "vacancies"]):
        if context["active_roles"]:
            roles = ", ".join(context["active_roles"])
            return (
                f"There are **{len(context['active_roles'])} active job roles** "
                f"with **{context['total_openings']} total openings**.\n\n"
                f"Roles: {roles}\n\n"
                f"Go to the **Job Roles** page to see matched candidates per role."
            )
        return "No active job roles are configured yet. Add roles in the **Job Roles** page."

    if any(w in q for w in ["average score", "avg score", "mean score", "overall average"]):
        return f"The **average overall score** across all students is **{context['avg_score']}/100**."

    if any(w in q for w in ["attendance", "absent", "present"]):
        return f"The **average attendance** across all students is **{context['avg_attendance']}%**."

    if any(w in q for w in ["upload", "last upload", "data uploaded", "how many students"]):
        return (
            f"**{context['total_students']} students** are in the database from "
            f"**{context['total_uploads']} upload(s)**. Last upload: {context['last_upload']}."
        )

    if any(w in q for w in ["summary", "overview", "report", "status"]):
        top_name = context["top_performers"][0]["name"] if context["top_performers"] else "N/A"
        weak_skill = context["weak_skills"][0]["skill"] if context["weak_skills"] else "N/A"
        return (
            f"**Placement Dashboard Summary:**\n"
            f"- Students: **{context['total_students']}** total, "
            f"**{context['placement_ready']}** ready ({context['placement_ready_pct']}%)\n"
            f"- Avg score: **{context['avg_score']}/100** · Avg attendance: **{context['avg_attendance']}%**\n"
            f"- Top performer: **{top_name}**\n"
            f"- Biggest skill gap: **{weak_skill}**\n"
            f"- Active roles: **{len(context['active_roles'])}** with **{context['total_openings']}** openings\n\n"
            f"Use the **Reports** page to download a full PDF audit."
        )

    # Fallback
    return (
        f"I have access to your live placement data. Here's a quick summary:\n\n"
        f"**{context['total_students']} students** · "
        f"**{context['placement_ready_pct']}% placement-ready** · "
        f"**Avg score {context['avg_score']}/100**\n\n"
        f"Try asking about: placement readiness, top performers, weak skills, job role openings, "
        f"attendance, or a full summary."
    )


# ---------------------------------------------------------------------------
# Gemini-powered chat
# ---------------------------------------------------------------------------

async def _gemini_chat(system_prompt: str, messages: list, user_message: str) -> str:
    """
    Call Gemini with a system instruction + conversation history.
    Returns the assistant's reply text.
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )

    # Build contents array: alternating user/model turns
    contents = []
    for msg in messages[-10:]:  # Keep last 10 messages for context window
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 800, "temperature": 0.4},
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def generate_chat_response(
    messages: list,
    context: dict,
    user_message: str,
) -> str:
    """
    Returns the AI assistant's response string.
    Tries Gemini first; falls back to local responder on any failure.
    """
    system_prompt = build_system_prompt(context)

    if settings.gemini_api_key:
        try:
            return await _gemini_chat(system_prompt, messages, user_message)
        except Exception:
            pass  # Fall through to local

    return _local_chat_response(user_message, context)
