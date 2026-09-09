# AI Placement Dashboard — Backend

FastAPI + SQLAlchemy backend for Skill Bay Academy's placement analytics dashboard.

## What's real vs. what you still need to plug in

Everything in this backend is fully implemented and tested — Excel/CSV parsing,
the scoring engine, the 15-role job-matching rule engine, AI report generation,
PDF export, and every API route. It runs today, with zero external accounts,
on SQLite and a local report generator.

To go to production you need to supply three things, none of which this
sandbox could reach to test live:

1. **A Postgres database** (your own, or Firebase Data Connect's managed
   Cloud SQL Postgres) — just set `DATABASE_URL`.
2. **A Firebase project** with Authentication enabled (Google + Email/Password
   providers) — download the service account JSON and set
   `FIREBASE_SERVICE_ACCOUNT_JSON`.
3. **A Gemini API key** (optional) — without it, AI summaries/roadmaps are
   generated locally from the real computed scores, which is fully
   functional, just not LLM-authored prose.

## Quick start (no external accounts needed)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # DEV_MODE=true, SQLite — works immediately
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs.

`DEV_MODE=true` (the default) makes every request act as a logged-in admin,
so you can test the whole app before setting up Firebase.

## Going to production

1. Set `DEV_MODE=false` in `.env`.
2. Firebase Console → Project Settings → Service Accounts → Generate new
   private key. Paste the full JSON (as one line) into
   `FIREBASE_SERVICE_ACCOUNT_JSON`.
3. Set `DATABASE_URL` to your Postgres connection string, e.g.
   `postgresql://user:password@host:5432/dbname`. Tables are created
   automatically on startup — no separate migration step for this MVP schema.
4. Add `GEMINI_API_KEY` to switch on live Gemini-authored reports.
5. Deploy (e.g. Render): `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

## Project layout

```
app/
  main.py              FastAPI app, CORS, startup DB init
  config.py            Settings (reads .env)
  database.py          SQLAlchemy engine/session
  models.py            ORM models (institutes, students, skills, analysis_results, uploads, ...)
  schemas.py           Pydantic response shapes
  auth.py              Firebase token verification + DEV_MODE bypass
  routers/
    upload.py          Preview + process (live / save / update)
    students.py         List/search/filter/sort/paginate, profile, update, delete
    dashboard.py        Aggregate stats + chart data
    reports.py          PDF generation (ReportLab)
    auth_router.py       /api/auth/me
  services/
    upload_processing.py   Column/skill detection from messy real-world sheets
    scoring.py              Normalization, overall score, readiness, salary band
    job_roles.py             15-role rule engine
    ai_service.py             Gemini call with local fallback
    pipeline.py                Orchestrates parsing → scoring → AI → persistence
```

## What's in this MVP vs. the full original spec

Built: auth (Firebase + dev bypass), upload (all 3 modes), student CRUD +
search/filter/sort/pagination, dashboard aggregate stats, AI analysis
pipeline (scoring, job-role matching, salary/interview prediction, roadmap),
PDF report export.

Not built yet (next phase — say the word and I'll pick these up): recruiter
search page/table, the floating AI chatbot, a dedicated Reports Center for
batch/course/institute-level PDFs, Settings page, bulk operations, activity
log viewer, the marketing landing page. None of these are hard given the
foundation here — they're mostly new routers + pages following the same
patterns as what's already built.
