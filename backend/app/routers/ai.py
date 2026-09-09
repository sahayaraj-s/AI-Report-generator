"""
SkillBay AI chat router — powers the Mini Chatbot and the dedicated SkillBay AI page.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AIChatSession, AIChatMessage
from app.services.ai_service import generate_chat_response

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ─── Chat (stateless) ────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """
    Stateless chat endpoint — takes query + history, returns AI response.
    Used by Mini Chatbot.
    """
    query = (payload.get("query") or payload.get("content") or "").strip()
    if not query:
        raise HTTPException(400, "Query is required")
    history = payload.get("history", [])

    response = await generate_chat_response(query, history, db)
    return {"response": response, "query": query, "content": response}


# ─── Chat Sessions (persisted) ────────────────────────────────────────────────

@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
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
):
    """
    Create a new chat session. If query is provided, generates AI response and persists it.
    If query is not provided, returns a newly created empty session.
    """
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

    # Load history
    history = [
        {"role": m.role, "content": m.content}
        for m in session.messages
    ]

    # Generate AI response
    response = await generate_chat_response(query, history, db)

    # Persist messages
    db.add(AIChatMessage(session_id=session.id, role="user", content=query))
    db.add(AIChatMessage(session_id=session.id, role="assistant", content=response))
    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "session_id": session.id,
        "title": session.title,
        "session_title": session.title,
        "response": response,
        "query": query,
        "content": response,
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get all messages in a session."""
    session = db.query(AIChatSession).get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "id": session.id,
        "title": session.title,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in session.messages
        ],
    }


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    session = db.query(AIChatSession).get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    user_text = (payload.get("content") or payload.get("query") or "").strip()
    if not user_text:
        raise HTTPException(400, "Message content is required")

    history = [
        {"role": m.role, "content": m.content}
        for m in session.messages
    ]

    assistant_text = await generate_chat_response(user_text, history, db)

    user_msg = AIChatMessage(session_id=session_id, role="user", content=user_text)
    assistant_msg = AIChatMessage(session_id=session_id, role="assistant", content=assistant_text)
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
        "created_at": assistant_msg.created_at.isoformat(),
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
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
def get_templates():
    return {"templates": PROMPT_TEMPLATES}
