"""
llm_manager.py - Modern Gemini GenAI Manager & Tool Calling Engine
===================================================================
Uses the official google-genai SDK:
- Dynamic model discovery via models.list
- Automatic fallback chain with degraded / offline status reporting
- First-class function calling (read-only tools grounded on app.services.analytics)
- Streaming via Server-Sent Events (SSE)
- Multimodal support (Images, PDF, table preview)
- Deterministic offline fallback (never dumps batch summary as default)
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import time
from typing import Any, AsyncGenerator, Callable
import pandas as pd

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError

from app.config import settings
from app.services import analytics
from app.services.analytics import AnalyticsFilters

log = logging.getLogger(__name__)

# Cache for available models
_MODELS_CACHE: list[dict] = []
_LAST_MODELS_FETCH: float = 0.0
_STATUS: dict = {
    "mode": "offline",
    "model": "local",
    "last_error": None,
    "available_models": [],
}

PROMPT_FILE = os.path.join(
    os.path.dirname(__file__), "prompts", "skillbay_system.md"
)


def load_system_prompt() -> str:
    if os.path.exists(PROMPT_FILE):
        try:
            with open(PROMPT_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            log.warning("Could not read skillbay_system.md: %s", e)
    return (
        "You are SkillBay AI, the intelligent placement assistant for Skill Bay Academy. "
        "Strict rule: Every number, name, rank, and salary must come from a tool call in this turn. "
        "Never invent student records or hallucinate scores."
    )


def get_genai_client() -> genai.Client | None:
    api_key = settings.gemini_api_key.strip()
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        log.warning("Failed to initialize genai.Client: %s", e)
        return None


def refresh_available_models() -> list[dict]:
    global _MODELS_CACHE, _LAST_MODELS_FETCH, _STATUS
    now = time.time()
    if _MODELS_CACHE and (now - _LAST_MODELS_FETCH) < 300.0:
        return _MODELS_CACHE

    client = get_genai_client()
    if not client:
        _STATUS = {
            "mode": "offline",
            "model": "local",
            "last_error": "No GEMINI_API_KEY configured",
            "available_models": [],
        }
        return []

    try:
        models_list = client.models.list()
        discovered = []
        for m in models_list:
            actions = m.supported_actions or []
            if "generateContent" in actions:
                m_id = m.name.replace("models/", "") if m.name else ""
                # Filter out retired models
                if any(m_id.startswith(p) for p in ("gemini-1.5", "gemini-2.0")):
                    continue
                if m_id == "gemini-2.5-flash-image":
                    continue

                discovered.append({
                    "id": m_id,
                    "name": m.display_name or m_id,
                    "description": m.description or "",
                })

        _MODELS_CACHE = discovered
        _LAST_MODELS_FETCH = now
        _STATUS["available_models"] = [m["id"] for m in discovered]
        _STATUS["mode"] = "gemini"
        _STATUS["model"] = settings.gemini_model_default
        _STATUS["last_error"] = None
        return discovered
    except Exception as e:
        log.warning("models.list failed: %s", e)
        _STATUS["mode"] = "degraded"
        _STATUS["last_error"] = str(e)
        return []


def get_ai_status() -> dict:
    refresh_available_models()
    return dict(_STATUS)


def resolve_working_model(requested_model: str | None = None) -> tuple[str, bool]:
    """
    Resolves requested model against fallback chain. Returns (model_name, is_fallback).
    """
    refresh_available_models()
    available = set(_STATUS.get("available_models", []))

    chain = []
    if requested_model:
        chain.append(requested_model)
    chain.extend([
        settings.gemini_model_default,
        settings.gemini_model_fast,
        settings.gemini_model_deep,
    ])
    for fb in settings.gemini_fallbacks.split(","):
        fb_s = fb.strip()
        if fb_s and fb_s not in chain:
            chain.append(fb_s)

    for m in chain:
        if available and m in available:
            is_fallback = (requested_model is not None and m != requested_model)
            return m, is_fallback

    # Default to first non-retired fallback
    return settings.gemini_model_default, True


# ---------------------------------------------------------------------------
# Tool Factory bound to DB Session
# ---------------------------------------------------------------------------

def create_chat_tools(db: Any) -> list[Callable]:
    """
    Returns Pydantic/function-calling tools grounded strictly in app.services.analytics.
    All tools return clean, minimal JSON dicts without PII.
    """

    def get_cohort_summary(batch: str = "", course: str = "") -> dict:
        """Get high-level summary of the batch: total students, readiness count, placement count, average score."""
        filters = AnalyticsFilters(batch=batch, course=course)
        return analytics.get_cohort_summary(db, filters)

    def list_students(
        batch: str = "",
        tier: str = "",
        readiness: str = "",
        placed: str = "",
        search: str = "",
        sort_by: str = "overall_score",
        sort_dir: str = "desc",
        limit: int = 15,
        offset: int = 0,
        rank: int = 0,
    ) -> dict:
        """List students with scores, tier, readiness, rank, and role fit."""
        filters = AnalyticsFilters(
            batch=batch,
            tier=tier,
            readiness=readiness,
            placed=placed,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        res = analytics.list_students(db, filters, limit=limit, offset=offset)
        if rank > 0:
            for s in res["students"]:
                if s.get("rank") == rank:
                    return {"total": 1, "students": [s]}
        return res

    def get_student_profile(student_name_or_id: str) -> dict:
        """Get comprehensive profile, strengths, weaknesses, role matches and scores for a specific student."""
        prof = analytics.get_student_profile(db, student_name_or_id)
        if not prof:
            return {"error": f"No student matching '{student_name_or_id}' found in records."}
        return prof

    def compare_students(student_names: list[str]) -> list[dict]:
        """Compare 2 or more students side-by-side."""
        return analytics.compare_students(db, student_names)

    def get_skill_stats(skill_name: str = "") -> dict:
        """Get cohort performance, averages, gaps and remediation needs for skills."""
        return analytics.get_skill_stats(db, skill=skill_name)

    def get_attendance_stats(batch: str = "") -> dict:
        """Get attendance averages, tracked counts, and attendance distribution."""
        filters = AnalyticsFilters(batch=batch)
        return analytics.get_attendance_stats(db, filters)

    def get_typing_stats(batch: str = "") -> dict:
        """Get typing speed stats: average WPM, min, max, target, and top typists."""
        filters = AnalyticsFilters(batch=batch)
        return analytics.get_typing_stats(db, filters)

    def get_placement_stats(group_by: str = "company", batch: str = "") -> dict:
        """Get placement statistics: total placed, unplaced students, packages, and recruiter breakdown."""
        filters = AnalyticsFilters(batch=batch)
        return analytics.get_placement_stats(db, group_by=group_by, filters=filters)

    def get_job_role_matches(student_name: str = "", role: str = "") -> dict:
        """Match students with hospital job roles, or list qualified students for a role."""
        return analytics.get_job_role_matches(db, student_ref=student_name, role=role)

    def get_unit_fulfillment(batch: str = "") -> list[dict]:
        """Get Kauvery Hospital unit fulfillment matrix and department openings."""
        filters = AnalyticsFilters(batch=batch)
        return analytics.get_unit_fulfillment(db, filters)

    def build_chart(kind: str = "bar", metric: str = "tier", limit: int = 10) -> dict:
        """Build a visual chart spec for the UI (e.g. tier distribution, radar, funnel, histogram)."""
        return analytics.build_chart(db, kind=kind, metric=metric, limit=limit)

    return [
        get_cohort_summary,
        list_students,
        get_student_profile,
        compare_students,
        get_skill_stats,
        get_attendance_stats,
        get_typing_stats,
        get_placement_stats,
        get_job_role_matches,
        get_unit_fulfillment,
        build_chart,
    ]


# ---------------------------------------------------------------------------
# Multimodal Attachment Processor
# ---------------------------------------------------------------------------

MAGIC_BYTES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def validate_and_convert_attachment(
    filename: str, raw_bytes: bytes
) -> types.Part | str | None:
    if len(raw_bytes) > 20 * 1024 * 1024:
        raise ValueError(f"File '{filename}' exceeds maximum size of 20 MB.")

    mime_type = "application/octet-stream"
    for header, m in MAGIC_BYTES.items():
        if raw_bytes.startswith(header):
            mime_type = m
            break

    if filename.lower().endswith(".pdf") or mime_type == "application/pdf":
        return types.Part.from_bytes(data=raw_bytes, mime_type="application/pdf")

    if mime_type.startswith("image/"):
        return types.Part.from_bytes(data=raw_bytes, mime_type=mime_type)

    # Spreadsheet: extract compact text preview for LLM
    if filename.lower().endswith((".xlsx", ".xls", ".csv")):
        try:
            if filename.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(raw_bytes))
            else:
                df = pd.read_excel(io.BytesIO(raw_bytes))
            summary_txt = (
                f"[Uploaded Spreadsheet: {filename}]\n"
                f"Rows: {len(df)}, Columns: {list(df.columns)}\n"
                f"Sample Top 5 Rows:\n{df.head(5).to_string(index=False)}"
            )
            return summary_txt
        except Exception as e:
            return f"[Uploaded Spreadsheet: {filename} (Error parsing preview: {e})]"

    return None


# ---------------------------------------------------------------------------
# Local Deterministic Fallback Responder
# ---------------------------------------------------------------------------

def answer_offline_fallback(query: str, db: Any) -> str:
    """
    Grounded deterministic responder used ONLY when Gemini is completely unreachable.
    Never dumps the batch summary by default.
    """
    q = query.lower().strip()
    data = analytics.compute_analytics(db)
    students = data["students"]

    # 1. Greetings
    if re.match(r"^(hi|hello|hey|good\s+morning|good\s+afternoon|vanakkam)", q):
        return (
            "Hello! I am **SkillBay AI**, your placement intelligence assistant for Skill Bay Academy (Kauvery Hospital CCDP).\n\n"
            "Here are some questions you can ask me:\n"
            "- *Who are the top performers in the batch?*\n"
            "- *Which students need critical remediation?*\n"
            "- *Show placement statistics and recruiter offers.*\n"
            "- *What are our lowest-scoring skills?*\n"
            "- *Summarize a specific student's profile.*"
        )

    # 2. Specific student lookup
    for s in students:
        s_name = s["name"].lower()
        first_token = s_name.split()[0]
        if s_name in q or (len(first_token) >= 4 and first_token in q):
            p = analytics.get_student_profile(db, s["id"])
            if p:
                att_str = f"{p['attendance_pct']:.1f}%" if p['attendance_pct'] is not None else "N/A"
                comp_name = p['placement_company'] or 'Partner'
                sal_disp = p['placement_salary'] or ''
                p_status = f"Placed at {comp_name} ({sal_disp})" if p['is_placed'] else "Not placed yet"
                return (
                    f"### {p['name']} (Rank #{p['rank']})\n"
                    f"- **Overall CCDP Score:** {p['overall_score']:.1f}/100 ({p['tier']})\n"
                    f"- **Placement Readiness:** {p['placement_readiness_pct']:.1f}% ({'✓ Qualified' if p['placement_ready'] else '⚠ Needs Training'})\n"
                    f"- **Training Attendance:** {att_str}\n"
                    f"- **Best Fit Role:** **{p['best_role']}** ({p['fit_tier']})\n"
                    f"- **Placement Status:** {p_status}\n\n"
                    f"💡 *Ask: 'What are {p['name']}'s strengths?' or 'Generate 30-day plan for {p['name']}'.*"
                )

    # 3. Specific rank query (e.g. "30th", "10 rank", "rank 1")
    rank_m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*rank\b|\brank\s*#?(\d{1,2})\b|\b(\d{1,2})(?:st|nd|rd|th)\b", q)
    if rank_m:
        val = next(v for v in rank_m.groups() if v is not None)
        rk = int(val)
        for s in students:
            if s.get("rank") == rk:
                return (
                    f"**Rank #{rk}: {s['name']}**\n"
                    f"- Overall Score: **{s['overall_score']:.1f}%** ({s['tier_short']})\n"
                    f"- Readiness: **{s['placement_readiness_pct']:.1f}%**\n"
                    f"- Best Role: **{s['best_role']}**\n"
                    f"- Status: {'Placed' if s['is_placed'] else 'Seeking placement'}"
                )

    # 4. Low score / remediation query
    if any(k in q for k in ["low", "struggling", "remediation", "tier 4", "needs prep", "support"]):
        tier4 = [s for s in students if s["tier_code"] == "tier_4"]
        if not tier4:
            return "No students in the current batch fall into Tier 4 (Critical Remediation)."
        lines = [
            f"### Students Needing Remediation ({len(tier4)} candidates):",
            "| Rank | Student Name | Overall Score | Weak Areas |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for s in tier4[:8]:
            weak = ", ".join(s["weaknesses"][:2]) if s["weaknesses"] else "General"
            lines.append(f"| #{s['rank']} | **{s['name']}** | {s['overall_score']:.1f}% | {weak} |")
        return "\n".join(lines)

    # 5. Medium score query (typo tolerant: "midium", "medium")
    if any(k in q for k in ["medium", "midium", "tier 2", "tier 3", "average score students"]):
        mid = [s for s in students if s["tier_code"] in ("tier_2", "tier_3")]
        lines = [
            f"### Medium Score Candidates ({len(mid)} students in Tier 2 & 3):",
            "| Rank | Student Name | Overall Score | Best Fit Role |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for s in mid[:8]:
            lines.append(f"| #{s['rank']} | **{s['name']}** | {s['overall_score']:.1f}% | {s['best_role']} |")
        return "\n".join(lines)

    # 6. Top performers
    if any(k in q for k in ["top", "high", "best", "distinction", "rank 1", "yaar top"]):
        top = sorted(students, key=lambda s: s["overall_score"], reverse=True)[:5]
        lines = [
            "### Top Performing Candidates:",
            "| Rank | Student Name | Overall Score | Readiness | Best Fit Role |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for s in top:
            lines.append(f"| #{s['rank']} | **{s['name']}** | {s['overall_score']:.1f}% | {s['placement_readiness_pct']:.1f}% | {s['best_role']} |")
        return "\n".join(lines)

    # 7. Placement & Company query
    if any(k in q for k in ["placed", "placement", "unplaced", "company", "salary", "package", "hamsa", "joy alukkas"]):
        placed = [s for s in students if s["is_placed"]]
        unplaced = [s for s in students if not s["is_placed"]]
        if "unplaced" in q:
            lines = [f"### Unplaced Students ({len(unplaced)} of {len(students)}):"]
            for s in unplaced[:8]:
                lines.append(f"- **{s['name']}** (Score: {s['overall_score']:.1f}%, Rank #{s['rank']})")
            return "\n".join(lines)
        return (
            f"### Placement Overview\n"
            f"- **Placed Students:** **{len(placed)}** of {len(students)} ({data['placed_pct']}%) \n"
            f"- **Top Recruiter:** {data['company_breakdown'][0]['company'] if data['company_breakdown'] else 'Kauvery Hospital'}\n"
            f"- **Seeking Placement:** {len(unplaced)} students\n\n"
            f"Ask for specific recruiters like 'Who is placed at Hamsa?' or 'Show highest salaries'."
        )

    # 8. Genuine "I don't know" fallback — NEVER dump batch summary
    return (
        "I could not find records matching your question in the current cohort dataset.\n\n"
        "Here are examples of questions I can answer accurately:\n"
        "- *'Who scored in the top 10?'*\n"
        "- *'Which students are placed at Kauvery Hospital?'*\n"
        "- *'What are the class averages for communication and technical skills?'*\n"
        "- *'Show student at rank 30.'*\n"
        "- *'Who needs remediation?'*"
    )


# ---------------------------------------------------------------------------
# Core Generation & Streaming Orchestrator
# ---------------------------------------------------------------------------

async def generate_chat_turn(
    query: str,
    history: list[dict],
    db: Any,
    model_override: str | None = None,
    attachments: list[tuple[str, bytes]] | None = None,
    effort: str = "quick",
) -> AsyncGenerator[dict, None]:
    """
    Async generator yielding SSE event dictionaries:
    - {"event": "tool_status", "data": {"status": "...", "tool": "..."}}
    - {"event": "token", "data": {"text": "..."}}
    - {"event": "chart", "data": {...}}
    - {"event": "done", "data": {"source": "gemini|local", "model": "..."}}
    - {"event": "error", "data": {"message": "..."}}
    """
    client = get_genai_client()
    target_model, is_fallback = resolve_working_model(model_override)

    if not client:
        # Offline mode
        resp = answer_offline_fallback(query, db)
        yield {"event": "token", "data": {"text": resp}}
        yield {"event": "done", "data": {"source": "local", "model": "offline-fallback", "degraded": True}}
        return

    tools = create_chat_tools(db)
    system_instruction = load_system_prompt()

    # Configure thinking level based on effort
    thinking_budget = 0 if effort == "quick" else (1024 if effort == "detailed" else 2048)

    # Prepare multimodal parts
    user_parts: list[Any] = []
    if attachments:
        for fname, raw_b in attachments:
            try:
                p = validate_and_convert_attachment(fname, raw_b)
                if p:
                    user_parts.append(p)
            except Exception as e:
                yield {"event": "token", "data": {"text": f"*(Attachment notice: {e})*\n\n"}}

    user_parts.append(query)

    # Build chat history
    formatted_history = []
    for h in history[-10:]:
        role = "user" if h.get("role") == "user" else "model"
        formatted_history.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=h.get("content", ""))]
        ))

    # Try streaming with Gemini tool calling
    retry_count = 0
    max_retries = 2
    active_model = target_model

    while retry_count <= max_retries:
        try:
            chat = client.chats.create(
                model=active_model,
                history=formatted_history,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools,
                    temperature=0.2,
                )
            )

            # Send message with streaming
            stream = chat.send_message_stream(user_parts)
            has_tokens = False

            for chunk in stream:
                # Inspect for tool execution
                if hasattr(chunk, "candidates") and chunk.candidates:
                    cand = chunk.candidates[0]
                    if cand.content and cand.content.parts:
                        for p in cand.content.parts:
                            if hasattr(p, "function_call") and p.function_call:
                                fn_name = getattr(p.function_call, "name", "tool")
                                yield {
                                    "event": "tool_status",
                                    "data": {"status": f"Querying {fn_name.replace('_', ' ')}...", "tool": fn_name},
                                }

                if chunk.text:
                    has_tokens = True
                    yield {"event": "token", "data": {"text": chunk.text}}

            yield {
                "event": "done",
                "data": {
                    "source": "gemini",
                    "model": active_model,
                    "degraded": is_fallback,
                }
            }
            return

        except (ClientError, APIError, ServerError, Exception) as exc:
            err_str = str(exc)
            log.warning("Gemini stream turn error on model %s: %s", active_model, err_str)
            retry_count += 1

            # Fall back to alternative models in chain
            if "404" in err_str or "not found" in err_str.lower() or "503" in err_str:
                if active_model == target_model:
                    active_model = settings.gemini_model_fast
                    is_fallback = True
                    await asyncio.sleep(0.5)
                    continue

            # If all retries fail, fall back gracefully to deterministic responder
            log.info("Falling back to local grounded deterministic responder.")
            local_resp = answer_offline_fallback(query, db)
            yield {"event": "token", "data": {"text": local_resp}}
            yield {
                "event": "done",
                "data": {
                    "source": "local",
                    "model": "offline-fallback",
                    "degraded": True,
                    "reason": err_str[:120],
                }
            }
            return
