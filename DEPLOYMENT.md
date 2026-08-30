# PostPulse — Production Deployment (Render + Vercel + PostgreSQL)

This guide walks you through deploying PostPulse to production:

- **Backend (FastAPI API)** → [Render](https://render.com) web service
- **Database** → [Render](https://render.com) managed **PostgreSQL** (free tier)
- **Frontend (React)** → [Vercel](https://vercel.com) static hosting

Everything is pre-configured for you. You just connect your GitHub repo and
fill in a few secrets.

---

## 0. Prerequisites

1. A **GitHub account** (free).
2. A **Render account** (free tier is fine).
3. A **Vercel account** (connected to GitHub).
4. (Optional, for real verification emails) a Gmail address with **2-Step
   Verification** enabled and a generated **App Password** —
   see [Email Verification](#5-email-verification-optional-but-recommended).

---

## 1. Push the code to GitHub

The repo is already initialized with git (no remote). From the project root:

```bash
git add -A
git commit -m "Prepare PostPulse for deployment (Render + Vercel + Postgres)"
git remote add origin git@github.com:<your-username>/postpulse.git
git branch -M main
git push -u origin main
```

> Push the **entire** repo. The backend (`backend/`) is self-contained (it
> carries its own model bundle and inference code), so Render can build it
> in isolation, and Vercel can build the frontend from `frontend/`.

---

## 2. Create the database + backend on Render (via Blueprint)

Render's **Blueprint** feature provisions the PostgreSQL database **and** the
backend web service together from the included `render.yaml`.

1. In Render's dashboard, click **New → Blueprint**.
2. Connect your GitHub repo (the one you just pushed).
3. Render reads `render.yaml` and shows:
   - `postpulse-db` — managed PostgreSQL (free)
   - `postpulse-api` — the FastAPI web service (free)
4. Render will prompt you for the env vars marked `sync: false`. Fill them in:
   - **`SECRET_KEY`** (REQUIRED) — generate one:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - **`ALLOWED_ORIGINS`** (REQUIRED) — your deployed frontend URL, e.g.
     `https://postpulse.vercel.app`. (You can set this after the frontend is
     live — see step 4 — then the backend will auto-redeploy.)
   - **`ADMIN_BOOTSTRAP_EMAIL`** — an email address that becomes the admin
     account on first registration. Set it **before** you register that address.
   - **`FRONTEND_URL`** — your Vercel URL, e.g. `https://postpulse.vercel.app`
     (used to build email verification links).
   - **`EMAIL_USER`** / **`EMAIL_APP_PASSWORD`** — optional, for real emails.
   - `DATABASE_URL` is wired automatically from the provisioned database — do
     not override it.
5. Click **Apply**. Render builds and deploys the backend, and creates the
   database and its tables on first startup.

Your backend URL will look like: `https://postpulse-api.onrender.com`
(confirm it in the Render dashboard's service details).

> **Note:** Render free-tier web services **spin down** after ~15 min of
> inactivity and take a few seconds to wake on the next request. This is fine
> for a portfolio/demo. The database persists.
>
> **Heads-up on free PostgreSQL:** as of 2025 Render no longer provisions *new*
> free-tier PostgreSQL databases on all accounts — you may be asked to choose a
> paid Postgres tier (the smallest is cheap). If free isn't offered, pick the
> lowest paid instance, or substitute any other hosted Postgres (Neon, Supabase)
> by pasting its connection string into the backend's `DATABASE_URL` instead.

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

Without SMTP configured, verification links are **printed to the Render log**
instead of emailed — the app still works, but real users won't get emails.

To enable real emails:

1. Enable 2-Step Verification on your Google account.
2. Generate an **App Password**:
   [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. In Render, set the backend env vars:
   - `EMAIL_HOST=smtp.gmail.com`
   - `EMAIL_PORT=587`
   - `EMAIL_USER=<youraddress@gmail.com>`
   - `EMAIL_APP_PASSWORD=<16-char app password>`
   - `FRONTEND_URL=https://postpulse.vercel.app`
4. Save — Render redeploys.

Never use your real Google password; always an App Password.

---

## 6. Create your admin account

1. If you set `ADMIN_BOOTSTRAP_EMAIL` in Render **before** deploying, then
   register an account with that exact email → it is auto-promoted to admin.
2. Log in and visit `/admin` to see the admin module (user list, plan control,
   usage stats).

---

## 7. Verify it works

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
| `DATABASE_URL` | auto | Injected from the provisioned `postpulse-db`. |
| `SECRET_KEY` | Yes | Random 64-char hex. Never reuse the dev default. |
| `ALLOWED_ORIGINS` | Yes | Comma-separated frontend origin(s). |
| `ADMIN_BOOTSTRAP_EMAIL` | Optional | Email promoted to admin on first registration. |
| `FRONTEND_URL` | Yes (if emailing) | Base URL for verification links. |
| `EMAIL_HOST` / `EMAIL_PORT` | Optional | SMTP server (default smtp.gmail.com:587). |
| `EMAIL_USER` / `EMAIL_APP_PASSWORD` | Optional | Gmail App Password. |
| `MODEL_BUNDLE_PATH` | Optional | Override for the joblib bundle path. |

### Frontend (Vercel)

| Variable | Required | Notes |
|---|---|---|
| `VITE_API_URL` | Yes | Backend URL + `/api`. Build-time only. |
