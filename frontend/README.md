# AI Placement Dashboard — Frontend

React 19 + Vite + Tailwind. Branded for Skill Bay Academy using colors sampled
directly from the logo (maroon `#8B1D55`, purple `#72398C`, pink `#DE4F73`,
yellow `#EFBC19`), laid out to match the Stitch UI design (dark, glassmorphism
sidebar + card dashboard).

## Quick start (no Firebase account needed yet)

```bash
npm install
cp .env.example .env       # VITE_DEV_MODE=true — works immediately
npm run dev
```

Open `http://localhost:5173`. With `VITE_DEV_MODE=true` you're auto-logged-in
as a mock admin (the Google/email buttons still render but aren't required),
so you can exercise the whole app before creating a Firebase project. Make
sure the backend is running at `http://localhost:8000` (see `../backend/README.md`).

## Going to production

1. Create Web app credentials in your Firebase project (Project Settings →
   General → Your apps), fill in every `VITE_FIREBASE_*` value in `.env`.
2. Set `VITE_DEV_MODE=false`.
3. Point `VITE_API_BASE_URL` at your deployed backend (e.g. Render URL).
4. `npm run build` → deploy the `dist/` folder (e.g. to Vercel).

## Pages implemented

- `Login` — Google + email/password (real Firebase Auth calls once configured)
- `DashboardOverview` — stat cards, course/skill charts, monthly progress, weak-skill heatmap, recent uploads
- `UploadStudentData` — drag-and-drop, live preview, all 3 analysis modes
- `StudentsDirectory` — search, filter, sort, paginate, delete, PDF download
- `StudentProfile` — skill radar, AI summary, strengths/weaknesses, job-role match, salary prediction, roadmap, 30-day plan, PDF download

## Not built yet

Recruiter search, AI chatbot widget, Reports Center, Settings, dark/light
theme toggle (currently dark-only), the marketing landing page. Same
component patterns used here (Layout/Sidebar/Card/Badge) extend cleanly to
these — this just wasn't in the agreed first-MVP scope.
