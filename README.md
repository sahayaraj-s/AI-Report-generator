# AI Placement Dashboard — Skill Bay Academy

An AI-powered placement analytics platform: upload a student sheet, get
automatic scoring, job-role matching, and AI-generated placement reports.

This is a working MVP covering the core flow end-to-end — not a mockup.
Backend and frontend were both built, installed, and test-run during
development (sample 10-student sheet → upload → scoring → dashboard →
PDF report, all verified working).

## Run it locally (2 terminals, no external accounts required)

```bash
# Terminal 1
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

venv\Scripts\python.exe run.py
uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm install
cp .env.example .env
npm run dev
```
venv\Scripts\python.exe run.py 
npm run dev

Open `http://localhost:5173`. Try uploading an Excel/CSV sheet with a `Name`
column plus any numeric skill columns (e.g. `Python`, `SQL`, `Communication`)
— everything downstream (scoring, job matching, AI summary, PDF) runs for
real on whatever you upload.

## What's real right now vs. what needs your credentials

Real and working today: upload parsing/validation, the scoring engine, the
15-role job-matching rule engine, AI report generation (local generator by
default, or live Gemini once you add a key), student directory, student
profiles with skill radar, PDF report export, dashboard analytics.

Needs your own accounts to go live (this sandbox has no network access to
any of these, so they're wired in code but untested against real services):
a Firebase project (Authentication + your Postgres/Data Connect instance),
a Gemini API key, and Vercel/Render for deployment. Both READMEs below walk
through exactly what to set.

- `backend/README.md` — API setup, Firebase/Postgres/Gemini wiring
- `frontend/README.md` — UI setup, Firebase web config

## Scope note

The original brief covers a much larger feature set (recruiter search, AI
chatbot, full reports center, settings, bulk ops, landing page, dark/light
toggle). We agreed to build the core MVP first — auth, upload, dashboard,
student directory, and AI analysis — which is what's here. The same
patterns (routers + services on the backend, Layout/Card/Badge components
on the frontend) extend cleanly to the rest whenever you're ready for the
next phase.

## Branding

Colors were sampled directly from the Skill Bay Academy logo rather than
using the orange/plum palette from the original Stitch export:

| Token | Hex | Use |
|---|---|---|
| Maroon | `#8B1D55` | Primary actions, active nav |
| Purple | `#72398C` | Secondary accents |
| Pink | `#DE4F73` | Highlights, positive deltas |
| Yellow | `#EFBC19` | Warnings, in-progress states |
