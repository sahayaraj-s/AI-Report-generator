# Deployment Guide — Skill Bay Academy AI Placement Dashboard

This document provides complete, production-ready deployment instructions for the **Skill Bay Academy / Kauvery Hospital CCDP** platform.

---

## Architecture Overview

- **Frontend**: React 19 + Vite 5 SPA (Tailwind CSS, TanStack Query, Recharts, Lucide).
- **Backend**: FastAPI + SQLAlchemy 2.0 + ReportLab + Firebase Admin SDK + Google Gemini AI.
- **Database**: PostgreSQL (Neon, Supabase, Render, or Docker).
- **Authentication**: Firebase Auth (Admin SDK on backend with Bearer token verification).

---

## Option A: Serverless Cloud (Recommended)
### Vercel (Frontend) + Render (Backend) + Neon / Supabase (PostgreSQL)

```
[ Browser / Client ]
       │
       ├── (Static Assets / SPA) ──► Vercel (frontend)
       │
       └── (API / Reports / AI)  ──► Render (FastAPI Backend)
                                          │
                                          ├──► Neon / Supabase (PostgreSQL)
                                          ├──► Firebase Admin (Auth Verification)
                                          └──► Google Gemini API (AI Insights)
```

### 1. Database Setup (Neon or Supabase)
1. Create a PostgreSQL database at [Neon.tech](https://neon.tech) or [Supabase.com](https://supabase.com).
2. Copy the connection string (format: `postgres://user:password@host/dbname?sslmode=require`).
3. Note: The backend automatically converts `postgres://` or `postgresql://` to `postgresql+psycopg2://`.
4. Tables are automatically initialized on startup via SQLAlchemy (`init_db()`).
5. *(Optional)* To migrate data from your local SQLite database to PostgreSQL, run:
   ```bash
   cd backend
   python copy_sqlite_to_postgres.py --sqlite placement.db --pg "your-neon-postgres-url"
   ```

### 2. Backend Deployment on Render
1. Sign in to [Render.com](https://render.com) and click **New +** -> **Web Service**.
2. Connect your Git repository.
3. Configure the service:
   - **Name**: `skillbay-placement-backend`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/health`
4. Set Environment Variables in the Render Dashboard:
   | Variable | Value | Notes |
   | :--- | :--- | :--- |
   | `DEV_MODE` | `False` | **CRITICAL**: Enables Firebase auth verification |
   | `DATABASE_URL` | `postgresql+psycopg2://...` | Connection string from Neon/Supabase |
   | `FIREBASE_SERVICE_ACCOUNT_JSON` | `{"type":"service_account",...}` | Single-line JSON from Firebase Console |
   | `GEMINI_API_KEY` | `AIzaSy...` | API key from Google AI Studio |
   | `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model identifier |
   | `GEMINI_TIMEOUT_SECONDS` | `8.0` | Timeout before fallback to local engine |
   | `CORS_ORIGINS` | `https://your-frontend.vercel.app` | Comma-separated allowed frontend URLs |
   | `FRONTEND_ORIGIN` | `https://your-frontend.vercel.app` | Production frontend URL |
   | `PYTHON_VERSION` | `3.11.9` | Pinned Python runtime |

### 3. Frontend Deployment on Vercel
1. Sign in to [Vercel.com](https://vercel.com) and click **Add New** -> **Project**.
2. Import your Git repository.
3. In **Project Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` *(or leave root; `vercel.json` handles both)*
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Configure Environment Variables in Vercel:
   | Variable | Value | Notes |
   | :--- | :--- | :--- |
   | `VITE_API_URL` | `https://your-backend.onrender.com` | Backend URL on Render (no trailing slash) |
   | `VITE_DEV_MODE` | `false` | Must match backend `DEV_MODE=False` |
   | `VITE_FIREBASE_API_KEY` | `AIzaSy...` | Firebase web client config |
   | `VITE_FIREBASE_AUTH_DOMAIN` | `project-id.firebaseapp.com` | Firebase auth domain |
   | `VITE_FIREBASE_PROJECT_ID` | `project-id` | Firebase project ID |
   | `VITE_FIREBASE_STORAGE_BUCKET`| `project-id.firebasestorage.app` | Storage bucket |
   | `VITE_FIREBASE_MESSAGING_SENDER_ID` | `1234567890` | Messaging sender ID |
   | `VITE_FIREBASE_APP_ID` | `1:1234567890:web:...` | App ID |
5. Deploy. The `frontend/vercel.json` rewrite routes all paths to `/index.html` for client-side routing.

---

## Option B: VPS Deployment with Docker Compose & Nginx
### Ubuntu / Debian VPS (DigitalOcean, Hetzner, AWS EC2, Linode)

```
[ Internet ] ── HTTPS (443) ──► Nginx Reverse Proxy (SSL / Certbot)
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                 Frontend Container            Backend Container
                  (Nginx / Static)               (FastAPI / Uvicorn)
                                                       │
                                                       ▼
                                               PostgreSQL Container
```

### 1. Initial VPS Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Certbot for SSL
sudo apt install -y certbot
```

### 2. Clone Repository & Configure Environment
```bash
git clone https://github.com/your-org/ai-placement-dashboard.git
cd ai-placement-dashboard

# Create production environment file
cp .env.example .env
nano .env
```

Ensure `.env` contains:
```ini
POSTGRES_USER=skillbay
POSTGRES_PASSWORD=generate_a_strong_random_password_here
POSTGRES_DB=skillbay_placement

DEV_MODE=False
DATABASE_URL=postgresql+psycopg2://skillbay:generate_a_strong_random_password_here@db:5432/skillbay_placement
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=8.0
CORS_ORIGINS=https://yourdomain.com
FRONTEND_ORIGIN=https://yourdomain.com

VITE_API_URL=https://yourdomain.com
VITE_DEV_MODE=false
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
```

### 3. Update Domain in `nginx.conf`
Replace `yourdomain.com` with your real domain in [nginx.conf](file:///c:/Users/Lenovo/Downloads/ai-placement-dashboard-mvp/ai-placement-dashboard/nginx.conf).

### 4. Obtain SSL Certificate via Certbot
```bash
sudo certbot certonly --standalone -d yourdomain.com
```

### 5. Launch Services
```bash
# Build and run containers
docker compose --profile production up -d --build

# Verify all containers are running
docker compose ps
```

---

## Security Hardening Checklist

1. **Authentication**:
   - `DEV_MODE=False` must be set in production on both frontend and backend.
   - All admin endpoints (`/api/admin/*`, `/api/jobs/*`, `/api/ai/*`, `/api/reports/*`, `/api/upload/*`, `/api/students/*`) require `Authorization: Bearer <token>`.
   - `/api/health` is the only public endpoint.
2. **File Upload Limit**:
   - 25 MB hard streaming limit enforced on backend via 64 KB chunks. Returns HTTP 413 if exceeded.
   - Allowed file extensions strictly restricted to `.xlsx`, `.xls`, `.csv` (HTTP 400 otherwise).
3. **CORS**:
   - Wildcards are disabled. Origins are strictly read from `CORS_ORIGINS`.
4. **CSV Injection**:
   - All CSV export cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are prefixed with a single quote (`'`).
5. **XSS Protection**:
   - All AI markdown HTML renders are sanitized with `DOMPurify.sanitize()`.
6. **Gemini Timeout & Resiliency**:
   - Timeout configured to 8.0s. If Google Gemini API is slow or times out, the local deterministic fallback generates the report immediately.
