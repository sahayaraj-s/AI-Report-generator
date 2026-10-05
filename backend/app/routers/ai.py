"""
SkillBay AI chat router — powers the Mini Chatbot and the dedicated SkillBay AI page.
Features:
- GET /api/ai/status (honest mode, model, last_error)
- GET /api/ai/models (available models from models.list)
- POST /api/ai/chat (stateless)
- POST /api/ai/chat/stream (SSE streaming with token, tool_status, done, error)
- Persisted sessions with source + model labels
- Multimodal attachment parsing (PNG/JPG/WEBP, PDF, XLSX/CSV preview)
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import AIChatMessage, AIChatSession
from app.services.llm_manager import (
    generate_chat_turn,
    get_ai_status,
    refresh_available_models,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _parse_attachments(payload: dict) -> list[tuple[str, bytes]]:
    raw_list = payload.get("attachments") or []
    out = []
    for att in raw_list:
        fname = att.get("name", "upload")
        data = att.get("data", "")
        if data:
            if "," in data:
                data = data.split(",", 1)[1]
            try:
                raw_b = base64.b64decode(data)
                out.append((fname, raw_b))
            except Exception as e:
                log.warning("Failed to decode attachment %s: %s", fname, e)
    return out


# ─── Status & Model Discovery ────────────────────────────────────────────────

@router.get("/status")
def ai_status(admin: dict = Depends(get_current_admin)):
    """Honest status of the AI engine: mode ('gemini' | 'degraded' | 'offline'), model, last_error."""
    return get_ai_status()


@router.get("/models")
def list_models(admin: dict = Depends(get_current_admin)):
    """Returns active models supporting generateContent discovered via models.list."""
    models = refresh_available_models()
    return {"models": models}


# ─── Chat (stateless) ────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    """
    Stateless chat endpoint — takes query + history + optional attachments,
    returns aggregated AI response with source and model.
    """
    query = (payload.get("query") or payload.get("content") or "").strip()
    if not query:
        raise HTTPException(400, "Query is required")

    history = payload.get("history", [])
    model_override = payload.get("model")
    effort = payload.get("effort", "quick")
    attachments = _parse_attachments(payload)

    tokens = []
    source = "gemini"
    active_model = "gemini-3.6-flash"

    async for item in generate_chat_turn(
        query=query,
        history=history,
        db=db,
        model_override=model_override,
        attachments=attachments,
        effort=effort,
    ):
        evt = item.get("event")
        data = item.get("data", {})
        if evt == "token":
            tokens.append(data.get("text", ""))
        elif evt == "done":
            source = data.get("source", source)
            active_model = data.get("model", active_model)

    full_resp = "".join(tokens)
    return {
        "response": full_resp,
        "content": full_resp,
        "query": query,
        "source": source,
        "model": active_model,
    }


# ─── Chat Streaming (SSE) ────────────────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    """
    SSE streaming endpoint emitting:
    - event: tool_status -> {"status": "Querying student profile...", "tool": "get_student_profile"}
    - event: token -> {"text": "chunk"}
    - event: done -> {"source": "gemini|local", "model": "..."}
    - event: error -> {"message": "..."}
    """
    query = (payload.get("query") or payload.get("content") or "").strip()
    if not query:
        raise HTTPException(400, "Query is required")

    history = payload.get("history", [])
    model_override = payload.get("model")
    effort = payload.get("effort", "quick")
    attachments = _parse_attachments(payload)

    async def event_generator():
        try:
            async for item in generate_chat_turn(
                query=query,
                history=history,
                db=db,
                model_override=model_override,
                attachments=attachments,
                effort=effort,
            ):
                evt = item.get("event", "token")
                d = json.dumps(item.get("data", {}))
                yield f"event: {evt}\ndata: {d}\n\n"
        except Exception as e:
            err_data = json.dumps({"message": str(e)})
            yield f"event: error\ndata: {err_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Chat Sessions (persisted) ────────────────────────────────────────────────

@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    """List all chat sessions for the SkillBay AI page sidebar."""
    sessions = db.query(AIChatSession).order_by(AIChatSession.updated_at.desc()).limit(50).all()
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "message_count": len(s.messages),
            }
            for s in sessions
        ]
    }


@router.post("/sessions")
async def create_session_and_chat(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    query = (payload.get("query") or payload.get("content") or "").strip()
    session_id = payload.get("session_id", None)
    title = payload.get("title", "").strip()

    if session_id:
        session = db.query(AIChatSession).get(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
    else:
        session_title = title or (query[:60] + ("…" if len(query) > 60 else "") if query else "New Chat")
        session = AIChatSession(title=session_title)
        db.add(session)
        db.flush()

    if not query:
        db.commit()
        db.refresh(session)
        return {
            "id": session.id,
            "session_id": session.id,
            "title": session.title,
            "session_title": session.title,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    history = [{"role": m.role, "content": m.content} for m in session.messages]
    model_override = payload.get("model")
    effort = payload.get("effort", "quick")
    attachments = _parse_attachments(payload)

    tokens = []
    source = "gemini"
    active_model = "gemini-3.6-flash"

    async for item in generate_chat_turn(
        query=query,
        history=history,
        db=db,
        model_override=model_override,
        attachments=attachments,
        effort=effort,
    ):
        if item.get("event") == "token":
            tokens.append(item.get("data", {}).get("text", ""))
        elif item.get("event") == "done":
            source = item.get("data", {}).get("source", source)
            active_model = item.get("data", {}).get("model", active_model)

    response_text = "".join(tokens)

    db.add(AIChatMessage(session_id=session.id, role="user", content=query, source="user", model=""))
    db.add(AIChatMessage(session_id=session.id, role="assistant", content=response_text, source=source, model=active_model))
    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "session_id": session.id,
        "title": session.title,
        "session_title": session.title,
        "response": response_text,
        "query": query,
        "content": response_text,
        "source": source,
        "model": active_model,
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    """Get all messages in a session."""
    session = db.query(AIChatSession).get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "id": session.id,
        "title": session.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "source": getattr(m, "source", "gemini"),
                "model": getattr(m, "model", "gemini-3.6-flash"),
                "created_at": m.created_at.isoformat(),
            }
            for m in session.messages
        ],
    }


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    session = db.query(AIChatSession).get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    user_text = (payload.get("content") or payload.get("query") or "").strip()
    if not user_text:
        raise HTTPException(400, "Message content is required")

    history = [{"role": m.role, "content": m.content} for m in session.messages]
    model_override = payload.get("model")
    effort = payload.get("effort", "quick")
    attachments = _parse_attachments(payload)

    tokens = []
    source = "gemini"
    active_model = "gemini-3.6-flash"

    async for item in generate_chat_turn(
        query=user_text,
        history=history,
        db=db,
        model_override=model_override,
        attachments=attachments,
        effort=effort,
    ):
        if item.get("event") == "token":
            tokens.append(item.get("data", {}).get("text", ""))
        elif item.get("event") == "done":
            source = item.get("data", {}).get("source", source)
            active_model = item.get("data", {}).get("model", active_model)

    assistant_text = "".join(tokens)

    user_msg = AIChatMessage(session_id=session_id, role="user", content=user_text, source="user", model="")
    assistant_msg = AIChatMessage(session_id=session_id, role="assistant", content=assistant_text, source=source, model=active_model)
    db.add(user_msg)
    db.add(assistant_msg)

    if session.title == "New Chat" and len(session.messages) <= 2:
        session.title = user_text[:60] + ("…" if len(user_text) > 60 else "")

    db.commit()
    db.refresh(assistant_msg)

    return {
        "id": assistant_msg.id,
        "role": "assistant",
        "content": assistant_text,
        "response": assistant_text,
        "source": source,
        "model": active_model,
        "created_at": assistant_msg.created_at.isoformat(),
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    session = db.query(AIChatSession).get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    db.delete(session)
    db.commit()
    return {"deleted": True, "id": session_id}


# ─── Prompt Templates ────────────────────────────────────────────────────────

PROMPT_TEMPLATES = [
    {"id": "batch_audit", "label": "Batch Performance Audit", "prompt": "Give me a full performance audit of all students in the current batch. Include top performers, students needing training, skill gaps, and placement readiness."},
    {"id": "top_candidates", "label": "Top Candidates for Placement", "prompt": "Who are the top 10 candidates ready for placement right now? Show their scores, best-fit roles, and suitability percentages."},
    {"id": "skill_gap", "label": "Skill Gap Analysis", "prompt": "What are the most common skill gaps across all students? Which skills have the lowest average scores and need urgent focus?"},
    {"id": "role_match", "label": "Job Role Matching Summary", "prompt": "Summarize how well students match our active job roles. For each role, tell me how many students are Perfect Match, Medium Fit, or Low Fit."},
    {"id": "interview_prep", "label": "Interview Readiness Report", "prompt": "Which students are interview-ready right now? Which ones need 2-4 weeks of prep? Give me a breakdown with names and recommended actions."},
    {"id": "batch_compare", "label": "Compare Batches", "prompt": "Compare the performance of all batches. Which batch has the highest average score and placement readiness? Where are the biggest differences?"},
    {"id": "low_performers", "label": "Students Needing Support", "prompt": "Identify students who are struggling (score below 50). What are their main weaknesses and what personalized support plan would you recommend?"},
    {"id": "openings_match", "label": "Match Students to Openings", "prompt": "We have active job openings. Which students best match which roles based on their skills and scores? Give me a prioritized shortlist."},
]

@router.get("/templates")
def get_templates(admin: dict = Depends(get_current_admin)):
    return {"templates": PROMPT_TEMPLATES}
