import json
import os
import pytest
from app.services.llm_manager import answer_offline_fallback
from app.database import SessionLocal

EVAL_PATH = os.path.join(os.path.dirname(__file__), "ai_eval_cases.json")

def load_eval_cases():
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_eval_cases_structure():
    cases = load_eval_cases()
    assert len(cases) >= 40, f"Expected at least 40 eval cases, got {len(cases)}"
    for c in cases:
        assert "id" in c
        assert "category" in c
        assert "query" in c

def test_offline_fallback_never_dumps_batch_summary():
    """
    Offline deterministic responder must NEVER dump the entire batch summary as default.
    When query is unrecognized or out of scope, it should suggest questions or state its scope.
    """
    db = SessionLocal()
    try:
        # 1. Greeting
        greeting_resp = answer_offline_fallback("hi", db)
        assert "SkillBay AI" in greeting_resp
        assert "Here are some questions you can ask me" in greeting_resp

        # 2. Tanglish / typos
        typo_resp = answer_offline_fallback("midium score students", db)
        assert len(typo_resp) > 0

        # 3. Unrecognized query
        unrec_resp = answer_offline_fallback("recipe for chocolate cake", db)
        assert "batch summary" not in unrec_resp.lower()
        assert "questions" in unrec_resp.lower() or "not find" in unrec_resp.lower()

    finally:
        db.close()

@pytest.mark.parametrize("case", load_eval_cases()[:10])
def test_eval_cases_sample(case):
    # Verify that query is non-empty and has expected keywords
    assert len(case["query"]) > 0
    assert len(case.get("expected_keywords", [])) > 0
