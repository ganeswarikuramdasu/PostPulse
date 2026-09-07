# PostPulse — Production Deployment (Render + Vercel + Supabase)

This guide walks you through deploying PostPulse to production:

- **Backend (FastAPI API)** → [Render](https://render.com) web service
- **Database** → [Supabase](https://supabase.com) managed **PostgreSQL**
- **Frontend (React)** → [Vercel](https://vercel.com) static hosting

Everything is pre-configured for you. You just connect your GitHub repo and
fill in a few secrets.

---

## 0. Prerequisites

1. A **GitHub account** (free).
2. A **Supabase account** (free tier PostgreSQL).
3. A **Render account** (free tier is fine).
4. A **Vercel account** (connected to GitHub).
5. (Optional, for real verification emails) a **Brevo account** with a free
   API key — see [Email verification](#5-email-verification-optional-but-recommended).

---

## 1. Push the code to GitHub

The repo is already initialized with git. From the project root:

```bash
git add -A
git commit -m "Configure Supabase database and update deployment"
git push
```

> Push the **entire** repo. The backend (`backend/`) is self-contained (it
> carries its own model bundle and inference code), so Render can build it
> in isolation, and Vercel can build the frontend from `frontend/`.

---

## 2. Configure Backend on Render (via Blueprint or Manual Service)

Render provisions the backend web service from the included `render.yaml`.

1. In Render's dashboard, click **New → Blueprint** (or go to your existing `postpulse-api` web service).
2. Connect your GitHub repo (the one you pushed).
3. Render reads `render.yaml` and shows:
   - `postpulse-api` — the FastAPI web service (free)
4. Render will prompt you for the env vars marked `sync: false`. Fill them in:
   - **`DATABASE_URL`** (REQUIRED) — your Supabase connection string:
     ```
     postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
     ```
     *(If your password has special characters like `?` or `/`, ensure they are URL-encoded, e.g. `%3F` for `?` and `%2F` for `/`).*
   - **`SECRET_KEY`** (REQUIRED) — generate one:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - **`ALLOWED_ORIGINS`** (REQUIRED) — your deployed frontend URL, e.g.
     `https://postpulse.vercel.app`. (You can set this after the frontend is
     live — see step 4 — then the backend will auto-redeploy.)
   - **`FRONTEND_URL`** — your Vercel URL, e.g. `https://postpulse.vercel.app`
     (used to build email verification links).
   - **`BREVO_API_KEY`** — optional, but recommended for real emails (free
     300/day over HTTPS). Registering without it still works — verification
     links print to the Render logs instead.
5. Click **Apply** (or **Save Changes** in Environment if updating an already-deployed service).
   Render builds and deploys the backend, and automatically creates all required tables
   (`users`, `email_verification_tokens`, `prediction_history`) on first startup.

Your backend URL will look like: `https://postpulse-api.onrender.com`
(confirm it in the Render dashboard's service details).

> **Note:** Render free-tier web services **spin down** after ~15 min of
> inactivity and take a few seconds to wake on the next request. The Supabase
> database persists continuously.

---

## 3. Deploy the frontend on Vercel

1. Go to [vercel.com/new](https://vercel.com/new) and import your GitHub repo.
2. Vercel auto-detects the Vite framework. Configure:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add the build-time environment variable:
   - **`VITE_API_URL`** = your Render backend URL + `/api`, e.g.
     `https://postpulse-api.onrender.com/api`
   - Must be a **Production** env var (and Preview if you want previews to work).
4. Click **Deploy**.

Your frontend URL will look like: `https://postpulse.vercel.app`

The included `frontend/vercel.json` handles client-side routing, so direct
visits/refreshes to `/predict`, `/history`, `/verify-email`, etc. work.

---

## 4. Link CORS (after both are live)

Once both are deployed, update the backend's **`ALLOWED_ORIGINS`** env var in
Render to your exact frontend URL, e.g.:

```
ALLOWED_ORIGINS=https://postpulse.vercel.app
```

(And `FRONTEND_URL` to the same URL, no trailing slash.) Render re-deploys the
backend automatically when you save. From then on the browser can talk to the
API.

---

## 5. Email verification (optional but recommended)

Without an email service configured, verification links are **printed to the
Render log** instead of emailed — the app still works, but real users won't
get emails.

To enable real emails with **Brevo** (free — 300 emails/day over HTTPS, no
SMTP ports needed, works on Render's free tier):

1. Create a free account at [brevo.com](https://brevo.com).
2. Go to **Settings → SMTP & API → API Keys** and generate an API key.
3. In Render, set the backend env vars:
   - `BREVO_API_KEY=<your_brevo_api_key>`
   - `EMAIL_USER=<your_sender_address>` (a sender verified in Brevo)
   - `EMAIL_FROM_NAME=PostPulse`
   - `FRONTEND_URL=https://postpulse.vercel.app`
4. Save — Render redeploys.

Fallbacks (optional): a **Resend** API key (`RESEND_API_KEY`), or classic
**SMTP** (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_APP_PASSWORD` — for
Gmail, always an App Password, never your real Google password).

---

## 6. Verify it works

1. Open your Vercel URL.
2. Register an account, click the verification link from your email (or the
   Render log if email isn't configured).
3. Log in and run a prediction on `/predict`.
4. Visit `/history` to see saved predictions.

---

## Troubleshooting

| Symptom | Likely fix |
|---|---|
| Frontend can't reach API (CORS error in browser console) | Check backend `ALLOWED_ORIGINS` matches your exact Vercel URL (no trailing slash). |
| Frontend calls the wrong API | Rebuild frontend after changing `VITE_API_URL` (it's baked in at build time). |
| API responds but predictions fail / 503 on model-info | Model bundle missing. Confirm `backend/models/content_performance_bundle.joblib` is committed (not gitignored). |
| 500 on first request / tables missing | The Render DB needs a moment to provision; re-deploy the backend once the DB shows "Available". |

---

## Environment variable reference

### Backend (Render)

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Supabase PostgreSQL connection string (with ?sslmode=require). |
| `SECRET_KEY` | Yes | Random 64-char hex. Never reuse the dev default. |
| `ALLOWED_ORIGINS` | Yes | Comma-separated frontend origin(s). |
| `FRONTEND_URL` | Yes (if emailing) | Base URL for verification links. |
| `BREVO_API_KEY` | Recommended | Brevo API key (free 300 emails/day over HTTPS). Preferred on Render. |
| `EMAIL_USER` / `EMAIL_FROM_NAME` | With Brevo | Sender address/name verified in Brevo. |
| `RESEND_API_KEY` | Optional | Alternative API-based sender (resend.com). |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USER` / `EMAIL_APP_PASSWORD` | Optional | Legacy SMTP fallback (e.g. Gmail App Password). |
| `MODEL_BUNDLE_PATH` | Optional | Override for the joblib bundle path. |

### Frontend (Vercel)

| Variable | Required | Notes |
|---|---|---|
| `VITE_API_URL` | Yes | Backend URL + `/api`. Build-time only. |
