# ResumeAI — AI Resume Analyzer & ATS Intelligence

A real, working full-stack app: upload a resume (PDF/DOCX), paste a job description,
and get an AI-generated ATS score, skills-gap analysis, and improvement suggestions —
powered by Claude via the Anthropic API.

```
resumeai-app/
├── backend/          FastAPI + SQLAlchemy + JWT auth + Claude-powered analysis
│   ├── app/
│   │   ├── main.py           FastAPI entrypoint
│   │   ├── config.py         Environment settings
│   │   ├── database.py       SQLAlchemy engine/session
│   │   ├── models.py         User / Resume / Analysis tables
│   │   ├── schemas.py        Pydantic request/response models
│   │   ├── security.py       Password hashing + JWT
│   │   ├── routers/          auth.py, resumes.py, analyze.py
│   │   └── services/
│   │       ├── parser.py     PDF/DOCX text extraction
│   │       └── ai_engine.py  Calls Claude, returns structured JSON verdict
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── index.html    Single-file frontend (Dark Burgundy / Champagne Gold / Soft White)
```

## What's real here

- **Auth**: real registration/login pages with bcrypt-hashed passwords and JWT bearer tokens (no more browser prompts).
- **Resume parsing**: actual text extraction from uploaded PDF (pdfplumber) and DOCX
  (python-docx) files — not mocked.
- **Structured field extraction**: on upload, Claude also extracts name, contact info,
  education, skills, experience, and projects into structured fields, shown on an
  editable review panel so you can correct anything it got wrong.
- **AI analysis**: the extracted resume text and your pasted job description are sent
  to Claude, which returns a structured JSON verdict (ATS score, sub-scores, matched/
  missing skills and keywords, and specific suggestions).
- **Bullet Point Optimizer**: paste one resume bullet, get an AI-rewritten, stronger
  version with an explanation of why it's better.
- **Analytics**: score-over-time chart and your most frequently recurring missing
  skills, computed from your real analysis history.
- **Resume History**: search, sort, view, re-run, or delete past analyses.
- **Resume Comparison**: pick any two past analyses and see them side by side.
- **Theme**: Dark / Light / System, saved per device.
- **404 page** and basic hash-based routing (refreshing on `#analytics` etc. reopens that page if you're logged in).
- **Database**: SQLite by default (zero setup), swappable to PostgreSQL by changing
  one environment variable.

## What's intentionally simplified

- Structured field editing covers the scalar fields (name, contact info, skills) with
  a text input; education/experience/projects are shown read-only for now — the data
  and endpoint (`PUT /api/resumes/:id/parsed`) already support full editing if you want
  to build that UI out further.
- "Forgot password" is a UI stub (no email-sending backend yet).
- No profile-photo/avatar upload.


## Local setup

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY (get one at https://console.anthropic.com/)
# and a random SECRET_KEY (python -c "import secrets; print(secrets.token_hex(32))")

uvicorn app.main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`.

### 2. Frontend

The frontend is a single static HTML file — no build step.

Open `frontend/index.html` in a browser, or serve it:

```bash
cd frontend
python -m http.server 5500
```

Then visit `http://localhost:5500`.

If your backend isn't running on `http://localhost:8000`, update the API base in
`frontend/index.html`:

```html
<meta name="api-base" content="http://localhost:8000">
```

## Deploying

- **Backend**: any platform that runs a Python web service (Render, Railway, Fly.io,
  a VPS with Docker, etc.). Set `DATABASE_URL`, `SECRET_KEY`, and `ANTHROPIC_API_KEY`
  as environment variables there — never commit `.env` to GitHub (it's already in
  place to be gitignored).
- **Database**: swap SQLite for Postgres in production by setting:
  `DATABASE_URL=postgresql://user:password@host:5432/dbname`
- **Frontend**: any static host (GitHub Pages, Netlify, Vercel). Update the
  `api-base` meta tag to your deployed backend's public URL, and set that same URL
  in the backend's `CORS_ORIGINS` environment variable so the browser is allowed to
  call it.

## Suggested `.gitignore`

```
backend/venv/
backend/.env
backend/resumeai.db
__pycache__/
*.pyc
```

## Extending it

- Add the remaining pages (History, Comparison, Profile, Auth screens) as new
  sections in `frontend/index.html` following the existing pattern — the API
  (`/api/history`, `/api/analysis/:id`) already supports them.
- Swap the AI provider by editing only `backend/app/services/ai_engine.py` —
  every route consumes `analyze_resume()`, so nothing else needs to change.
- Move file storage to S3/Cloud Storage if you want to keep the original uploaded
  files, not just their extracted text (currently only extracted text is stored).
