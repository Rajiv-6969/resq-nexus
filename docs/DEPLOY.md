# ResQ Nexus — Production Deployment Guide

This guide details the step-by-step procedure for deploying **ResQ Nexus** across production infrastructure:
- **Frontend:** [Vercel](https://vercel.com) (React 19 + Vite SPA with global CDN caching)
- **Backend:** [Render](https://render.com) (Docker Web Service, CPU Free Tier with 512 MB RAM ceiling)
- **Database:** [Supabase](https://supabase.com) (Managed PostgreSQL + PostGIS)
- **Cron Feeds:** [GitHub Actions](https://github.com) (Automated 15-minute GDACS/USGS alert poller)

---

## 1. System Architecture Overview

```
                      +-----------------------------+
                      |   Citizen & Emergency Team  |
                      |   Web Clients (Desktop/Tab) |
                      +--------------+--------------+
                                     | HTTPS
                                     v
                      +-----------------------------+
                      |      Vercel Edge CDN        |
                      |   Frontend (React 19/Vite)  |
                      +--------------+--------------+
                                     | API Calls (HTTPS / Bearer JWT)
                                     v
                      +-----------------------------+
                      |       Render Web Service    |
                      |     FastAPI Backend (Docker)|
                      |    512 MB RAM Ceiling Tier  |
                      +-------+--------------+------+
                              |              |
           PostGIS (psycopg3) |              | Ingestion Cron
                              v              v
            +--------------------+    +-----------------------------+
            |  Supabase PostGIS  |    |     GitHub Actions Cron     |
            | PostgreSQL 15 + GIS|    |  POST /jobs/poll (15m tick) |
            +--------------------+    +-----------------------------+
```

---

## 2. Step-by-Step Deployment Instructions

### Step 1: Managed Database Setup (Supabase)
1. Sign in to [Supabase](https://app.supabase.com/) and create a new project (e.g. `resq-nexus-db`).
2. Select your closest AWS region (e.g., `ap-south-1` Mumbai or `eu-central-1` Frankfurt).
3. In the Supabase **SQL Editor**, verify that the PostGIS extension is active:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```
4. Navigate to **Project Settings -> Database**:
   - Locate the **Connection String** section and select **URI**.
   - Copy the URI (format: `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`).
   - Format it with the `postgresql+psycopg://` driver prefix:
     ```
     postgresql+psycopg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
     ```

---

### Step 2: Backend Deployment (Render)
1. Sign in to [Render](https://dashboard.render.com/) and click **New + -> Web Service**.
2. Connect your GitHub repository (`Rajiv-6969/resq-nexus`) and select branch `final` (or `main`).
3. Configure service specifications:
   - **Name:** `resq-nexus-api`
   - **Environment:** `Docker`
   - **Region:** `Oregon (US West)` or closest to your database.
   - **Branch:** `final`
   - **Docker Command / Context:**
     - Docker Context Directory: `.` (repository root)
     - Dockerfile Path: `backend/Dockerfile`
   - **Instance Type:** `Free` (0.1 CPU, 512 MB RAM)
4. Configure **Environment Variables** in Render dashboard:
   | Variable | Value | Notes |
   |---|---|---|
   | `DATABASE_URL` | `postgresql+psycopg://...` | Supabase PostGIS connection string |
   | `JWT_SECRET` | *(Click "Generate")* | 32+ character random secret for signing tokens |
   | `CRON_SECRET` | *(Generate a 32-char hex string)* | Key protecting `POST /jobs/poll` |
   | `GEMINI_API_KEY` | `AIzaSy...` | Google AI Studio API Key (optional) |
   | `FRONTEND_ORIGIN` | `https://resq-nexus.vercel.app` | Vercel production frontend URL |
   | `SEED_DEMO_DATA` | `1` | Seeds accounts and facilities into empty DB |
   | `OMP_NUM_THREADS` | `1` | Enforces single-thread execution for memory safety |
5. Set **Health Check Path** to:
   ```
   /health
   ```
6. Click **Create Web Service**. The initial deployment will run `alembic upgrade head`, seed demo accounts, and bind uvicorn to `$PORT`.

---

### Step 3: Frontend Deployment (Vercel)
1. Sign in to [Vercel](https://vercel.com/) and click **Add New... -> Project**.
2. Import the `Rajiv-6969/resq-nexus` repository.
3. Configure project settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click "Edit" and choose `frontend`.
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Set Environment Variables in Vercel:
   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://resq-nexus-api.onrender.com` (Your Render backend URL) |
5. Click **Deploy**. Vercel will install dependencies, build the production bundle, and deploy to a global edge CDN.
6. Once deployed, copy your production domain (e.g. `https://resq-nexus.vercel.app`) and ensure it is listed in the Render backend's `FRONTEND_ORIGIN`.

---

### Step 4: Scheduled Background Cron (GitHub Actions)
To ensure GDACS, USGS alerts, and weather warnings stay updated even when the Render free-tier container spins down after inactivity:
1. In your GitHub repository, navigate to **Settings -> Secrets and variables -> Actions**.
2. Add the following repository secrets:
   - `BACKEND_URL`: `https://resq-nexus-api.onrender.com`
   - `CRON_SECRET`: *(The exact same token configured in Render)*
3. The workflow `.github/workflows/poll-feeds.yml` will automatically execute every 15 minutes, sending a signed `POST /jobs/poll` request with the `X-Cron-Key` header.

---

## 3. Environment Variables Reference

| Variable | Target | Required | Description & Example |
|---|---|---|---|
| `DATABASE_URL` | Backend | Yes (prod) | SQLAlchemy connection URI (`postgresql+psycopg://user:pass@host:5432/db`). SQLite used locally if unset. |
| `JWT_SECRET` | Backend | Yes | Secret key for HS256 JWT signing (`python -c "import secrets; print(secrets.token_urlsafe(48))"`). |
| `JWT_EXPIRE_MINUTES` | Backend | No | Session lifetime in minutes (default: `720` = 12 hours). |
| `CRON_SECRET` | Backend, GitHub | Yes | Shared token guarding `POST /jobs/poll`. Transmitted via `X-Cron-Key` header. |
| `GEMINI_API_KEY` | Backend | Optional | Google Gemini API key. If omitted, deterministic templates are used for explanations and reports. |
| `GEMINI_MODEL` | Backend | No | Gemini model identifier (default: `gemini-flash-latest`). |
| `FRONTEND_ORIGIN` | Backend | Yes (prod) | Strict CORS allowed origins (`https://your-app.vercel.app,http://localhost:5173`). |
| `SEED_DEMO_DATA` | Backend | No | When `1`, seeds demo accounts, OSM facilities, and alerts if database is empty. |
| `OMP_NUM_THREADS` | Backend | No | Thread cap for OpenMP/BLAS (must be `1` on Render free tier to prevent memory spikes). |
| `OFFLINE_MODE` | Backend | No | When `1`, external network requests (STAC, GDACS, USGS) are bypassed using test fixtures. |
| `VITE_API_BASE_URL` | Frontend | Yes | Base URL where the backend is reachable (`https://resq-nexus-api.onrender.com`). |

---

## 4. Render 512 MB RAM Optimization & Verification

Render's free tier imposes a hard **512 MB container RSS memory ceiling**. Container breach results in immediate SIGKILL (OOM error 137).

### Key Memory Hardening Measures:
1. **Low-Arena ONNX Allocation:**
   In `backend/services/damage/inference.py`, ONNX Runtime's greedy memory arena allocator is disabled:
   ```python
   opts.enable_cpu_mem_arena = False
   opts.intra_op_num_threads = 1
   opts.inter_op_num_threads = 1
   opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
   ```
2. **Single-Thread Matrix Math:**
   Enforced via Dockerfile environment variables:
   `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
3. **Tiled Inference:**
   Satellite images are processed in strict $512 \times 512$ pixel sliding windows (64 px overlap) instead of whole-scene tensors.

### Empirical Memory Footprint Benchmark:
| Configuration | Peak Process RSS | RAM Ceiling Headroom (512 MB) |
|---|---|---|
| **Default Arena Allocator (2 threads)** | **346.8 MB** | 165.2 MB (32.2%) |
| **Optimized Low-Arena (1 thread, sequential)** | **181.1 MB** | **330.9 MB (64.6%)** |
| **Total Memory Savings** | **-165.7 MB (-47.7%)** | **Safe Operating Margin** |

---

## 5. Pre-Demo Checklist (5 Minutes Before Presentation)

Execute this brief verification sequence before demonstrating ResQ Nexus:

- [ ] **1. Wake Backend from Cold Sleep:**
  Render free tier spins down containers after 15 minutes of inactivity. Send a wake-up GET request:
  ```bash
  curl -I https://resq-nexus-api.onrender.com/health
  ```
  *Verify that the response returns HTTP 200 with `database: "connected"` and `damage_model: "loaded"`.*

- [ ] **2. Verify Ingestion Feeds:**
  Trigger a manual feed refresh or check that alerts are populated:
  ```bash
  curl -X POST "https://resq-nexus-api.onrender.com/jobs/poll?india_only=true" \
    -H "X-Cron-Key: YOUR_CRON_SECRET"
  ```

- [ ] **3. Verify Event Replays:**
  Open the frontend and verify that the scenario picker displays both replay badges:
  - `Periyar floods – Aluva, Ernakulam` -> `"Replay of real event (15–17 August 2018)"`
  - `Budameru breach – Vijayawada, NTR` -> `"Replay of real event (1–3 September 2024)"`

- [ ] **4. Test Demo Account Logins:**
  Verify quick one-click demo login buttons on `/login`:
  - `admin@resq.example` (`Admin#2026`) -> Opens Command Centre & Situation Reports.
  - `provider@resq.example` (`Provider#2026`) -> Opens Provider Dispatch & Stock Dashboard.
  - `citizen@resq.example` (`Citizen#2026`) -> Opens Citizen SOS & First-Aid Guide.

- [ ] **5. Situation Report Verification:**
  In Command Centre or Live Mode, click **"SITUATION REPORT &rarr;"** and confirm:
  - Executive summary and silent areas render with structured facts.
  - Green monospace badge displays **100% FAITHFULNESS VERIFIED**.
  - Toggle between English (`EN`) and Hindi (`HI`) works seamlessly.
