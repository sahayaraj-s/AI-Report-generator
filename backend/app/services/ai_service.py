"""
AI narrative generation for Skill Bay Academy (Kauvery Hospital CCDP).
Provides tailored student summaries, 50-day preparation roadmaps, and certifications
for Kauvery Hospital units and corporate partner placement.
"""
from __future__ import annotations
import json
import httpx
from app.config import settings


def _local_roadmap(weaknesses: list, top_roles: list) -> str:
    role_txt = top_roles[0]["role"] if top_roles else "Kauvery Hospital Placement"
    lines = []
    if weaknesses:
        for w in weaknesses[:3]:
            lines.append(f"- Strengthen **{w}**: daily 45-min targeted practice sessions + practical case scenario drills.")
    if role_txt:
        lines.append(f"- Prepare for **{role_txt}**: align with Kauvery Hospital unit workflow and core department competencies.")
    if not lines:
        lines.append("- Maintain strong CCDP performance: complete advanced mock interviews and clinical/corporate scenario assessments.")
    return "\n".join(lines)


def _local_thirty_day_plan(weaknesses: list, strengths: list, top_roles: list) -> str:
    focus = weaknesses[0] if weaknesses else (strengths[0] if strengths else "Communication & Soft Skills")
    role_txt = top_roles[0]["role"] if top_roles else "Kauvery Hospital Placement"
    skill_gaps = top_roles[0].get("skill_gaps", []) if top_roles else []
    gap_txt = ", ".join(g["skill"] for g in skill_gaps[:2]) if skill_gaps else focus
    return (
        f"Week 1: Core Foundation — Intensive review of **{gap_txt}** with live trainer feedback.\n"
        f"Week 2: Applied Competency — Practical department roleplay & case assignments for **{role_txt}**.\n"
        f"Week 3: Assessment Readiness — Timed aptitude drills, MS Office MIS exercises, and resume alignment.\n"
        f"Week 4: Placement Preparation — Kauvery Hospital unit mock interviews & final placement clearance."
    )


def _local_certifications(top_roles: list) -> list:
    cert_map = {
        "Patient Care Coordinator": "Hospital Patient Relations & NABH Service Standards",
        "Front Office & Helpdesk Executive": "Healthcare Front Office & Customer Experience (CX)",
        "Billing & Health Insurance Executive": "Medical Billing, Cashless & TPA Claims Processing",
        "Hospital Operations Trainee": "Healthcare Operations & Hospital Administration",
        "Healthcare IT & Systems Assistant": "Healthcare Information Systems & EMR Management",
        "Medical Records / Quality Assistant": "Medical Record Technology (MRD) & Healthcare Quality",
        "Pharmacy & Supply Chain Assistant": "Hospital Pharmacy Supply Chain & Inventory Control",
        "Customer Experience Executive": "Corporate Customer Service & Business Communication",
        "Data & Analytics Trainee": "Advanced Excel & Healthcare Data Analytics",
        "General Management Trainee": "Skill Bay Academy CCDP Leadership & Professional Excellence",
    }
    out = []
    for r in top_roles[:2]:
        cert = cert_map.get(r.get("role", ""))
        if cert:
            out.append(cert)
    return out or [
        "Skill Bay Academy CCDP Professional Excellence",
        "Kauvery Hospital Service & Communication Standards"
    ]


def generate_local_report(
    student_name: str,
    overall: float,
    strengths: list,
    weaknesses: list,
    top_roles: list,
) -> dict:
    role_txt = top_roles[0]["role"] if top_roles else "Kauvery Hospital Placement"
    fit_tier = top_roles[0].get("fit_tier", "") if top_roles else ""
    unit_txt = top_roles[0].get("kauvery_unit", "Kauvery Hospital") if top_roles else "Kauvery Hospital"
    skill_gaps = top_roles[0].get("skill_gaps", []) if top_roles else []
    gap_detail = ""
    if skill_gaps:
        gap_parts = [f"{g['skill']} (achieved {g['achieved']}, needs {g['required']})" for g in skill_gaps[:2]]
        gap_detail = f" Focus areas for {role_txt}: {'; '.join(gap_parts)}."

    summary = (
        f"{student_name} achieved an overall CCDP score of {overall}/100"
        + (f" -- **{fit_tier}** for **{role_txt}** at {unit_txt}" if fit_tier else f", best-fit role: **{role_txt}**")
        + "."
        + (f" Key strengths: {', '.join(strengths[:2])}." if strengths else "")
        + (f" Recommended training focus: {', '.join(weaknesses[:2])}." if weaknesses else "")
        + gap_detail
    )
    return {
        "ai_summary": summary,
        "learning_roadmap": _local_roadmap(weaknesses, top_roles),
        "thirty_day_plan": _local_thirty_day_plan(weaknesses, strengths, top_roles),
        "recommended_certifications": _local_certifications(top_roles),
        "ai_source": "local",
    }


async def generate_gemini_report(
    student_name: str,
    overall: float,
    strengths: list,
    weaknesses: list,
    top_roles: list,
) -> dict:
    role_txt = top_roles[0]["role"] if top_roles else "Kauvery Hospital Placement"
    fit_tier = top_roles[0].get("fit_tier", "") if top_roles else ""
    unit_txt = top_roles[0].get("kauvery_unit", "Kauvery Hospital") if top_roles else "Kauvery Hospital"
    skill_gaps = top_roles[0].get("skill_gaps", []) if top_roles else []

    prompt = (
        f"You are the Lead Placement Evaluator for Skill Bay Academy (an initiative of Kauvery Hospital) "
        f"evaluating candidates from the 50-day Career & Competency Development Program (CCDP).\n"
        f"Write a clean JSON object (no markdown, no backticks, no commentary) with keys:\n"
        f"- \"ai_summary\": 2-3 concise sentences highlighting candidate's overall readiness, best fit role ({role_txt} at {unit_txt}), and fit tier ({fit_tier}).\n"
        f"- \"learning_roadmap\": 3-4 bullet lines as one string with \\n, focused on closing skill gaps for Kauvery hospital/corporate roles.\n"
        f"- \"thirty_day_plan\": 4 week-by-week lines as one string with \\n, providing an actionable 30-day preparation sprint.\n"
        f"- \"recommended_certifications\": a JSON array of 1-3 professional certificates relevant to healthcare operations and {role_txt}.\n\n"
        f"Candidate: {student_name}\n"
        f"Overall CCDP Score: {overall}/100\n"
        f"Strengths: {strengths}\n"
        f"Weaknesses: {weaknesses}\n"
        f"Top Role Match: {role_txt} ({fit_tier}) at {unit_txt}\n"
        f"Skill Gaps: {json.dumps(skill_gaps)}"
    )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    if not settings.gemini_api_key or not settings.gemini_api_key.startswith("AIza"):
        return generate_local_report(student_name, overall, strengths, weaknesses, top_roles)

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip().strip("`").replace("json\n", "", 1)
            parsed = json.loads(text)
            parsed["ai_source"] = "gemini"
            return parsed
    except Exception:
        return generate_local_report(student_name, overall, strengths, weaknesses, top_roles)


async def generate_ai_report(
    student_name: str,
    overall: float,
    strengths: list,
    weaknesses: list,
    top_roles: list,
) -> dict:
    if settings.gemini_api_key and settings.gemini_api_key.startswith("AIza"):
        return await generate_gemini_report(student_name, overall, strengths, weaknesses, top_roles)
    return generate_local_report(student_name, overall, strengths, weaknesses, top_roles)


async def generate_chat_response(query: str, history: list, db) -> str:
    """Generate chat response for the SkillBay AI assistant."""
    from app.services.chat_service import build_context_snapshot, generate_chat_response as _chat
    context = build_context_snapshot(db)
    return await _chat(history, context, query)
