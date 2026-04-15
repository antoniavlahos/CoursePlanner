# Purdue Course Planner

A full-stack web application for planning a Purdue University degree program. Browse the course catalog, build a multi-year semester schedule, track requirements, and use AI-powered course recommendations.

---

## Features

### User Accounts
- Register and sign in with email, password, first name, and last name
- JWT-based authentication (30-day sessions)
- Edit account information (name) from Account Settings
- Each user's plans are private and scoped to their account

### Course Catalog
- Browse and search all Purdue courses by keyword or department
- Department dropdown shows full department names
- View full course details: description, credits, prerequisites, terms offered
- Add courses to your plan via a semester picker modal, or directly to Transfer Credits
- Warning shown if a course is not typically offered in the selected semester

### My Plan
- Semester-by-semester view of your degree plan (Year 1 through duration)
- **Transfer Credits card**: add courses you brought in as transfer credit; drag courses in/out
- Drag and drop courses between semesters (transfer ↔ regular semesters supported)
- Mark courses as Planned, In Progress, or Completed
- Enter letter grades; GPA is calculated automatically per semester and cumulatively
- Summary strip: transfer credits, credits planned, credits completed, overall GPA
- Download plan as a formatted PDF
- Copy a read-only shareable link directly from the page header

### Requirements
- Graduation progress bar (credits completed vs. required)
- Cumulative and per-semester GPA tracking
- Department required courses checklist with **Add to Plan** button for each unscheduled course
- University graduation requirements checklist
- Courses already in plan show "In plan" label; completed courses show ✅

### Plans (New / Load Plan)
- Create, load, edit, and delete degree plans
- Plan types: **Single Major**, **Double Major**, or **Major + Minor**
- Configure plan name, primary department, optional secondary department, duration (2–6 years), and start year
- **Share Plan**: generate a public read-only link — no login required for viewers
- Generate, copy, preview, and revoke share links

### AI Planner
- **Find Courses**: Describe your interests in plain text; the planner searches the full catalog and ranks the best matches using Ollama (AI) or keyword matching as a fallback
- **Full Program Plan**: Automatically generate a complete semester-by-semester schedule that:
  - Satisfies all major and university requirements
  - Respects prerequisite chains (up to 3 levels deep)
  - Excludes transfer credits and already-completed courses
  - Places courses at the appropriate year level (100-level in Year 1, 400-level in Year 4, etc.)
  - Fills elective slots based on your stated interests
  - Drag and drop to rearrange before applying
  - Apply the generated plan to My Plan in one click

### Account Settings
- Edit first and last name
- Email is read-only (used for login)

### Shared (Read-Only) View
- Public URL — no login required
- Shows plan name, owner name, department, duration, year range
- Displays transfer credits, all semesters, course status
- Grades and GPA are hidden from the shared view

---

## Prerequisites

### Docker (recommended)

| Tool | Version |
|------|---------|
| Docker | 24+ |
| Docker Compose | v2+ |

### Local development

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Ollama | latest | Optional — enables AI-ranked results |

---

## Docker (Recommended)

The simplest way to run the app. A single container serves both the React frontend and the Flask API; the SQLite database is persisted in a named Docker volume.

### 1. Clone the repository

```bash
git clone https://github.com/antoniavlahos/CoursePlanner.git
cd CoursePlanner
```

### 2. Build and start

```bash
docker compose up --build
```

Open your browser at **http://localhost:8000**.

That's it. On first start the database is automatically seeded with the full Purdue course catalog.

### Common commands

```bash
# Run in the background
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down

# Stop and wipe the database volume (full reset)
docker compose down -v
```

### Environment variables

Set these in `docker-compose.yml` or pass them with `-e`:

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `change-me-in-production` | Secret key for signing JWT tokens. **Change this before deploying.** |
| `PORT` | `8000` | Port the server listens on inside the container |
| `GUNICORN_WORKERS` | `4` | Number of gunicorn worker processes |

---

## Local Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/antoniavlahos/CoursePlanner.git
cd CoursePlanner
```

### 2. Backend

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Seed the database

```bash
python create_database.py
```

### 4. Frontend

```bash
cd frontend
npm install
cd ..
```

---

## Running Locally

Open **two terminals** — one for the backend, one for the frontend.

### Terminal 1 — Backend (Flask API)

```bash
# From the project root (with venv activated)
python app.py
```

The API will be available at `http://127.0.0.1:8000`.

### Terminal 2 — Frontend (Vite dev server)

```bash
cd frontend
npm run dev
```

Open your browser at **http://localhost:3000**.

> The frontend proxies all `/api` requests to the Flask backend automatically, so no CORS configuration is needed during development.

---

## Ollama (AI Features) — Optional

Ollama enables AI-ranked course recommendations in the "Find Courses" tab. Without it, the app falls back to keyword matching automatically. Program plan generation always uses fast keyword ranking.

### Install Ollama

**macOS:**
```bash
brew install ollama
```

**Windows / Linux:**
Download from [ollama.com](https://ollama.com/download)

### Start Ollama and pull a model

```bash
# Start the Ollama server
ollama serve

# In a separate terminal, pull the recommended model
ollama pull qwen:8b
```

The app auto-detects all available Ollama models at startup and prefers any `qwen` variant. The active model is shown in the AI Planner banner and at `/api/ai/status`.

---

## Environment Variables

For local development, export before starting the backend:

```bash
# macOS / Linux
export JWT_SECRET="your-long-random-secret"

# Windows (PowerShell)
$env:JWT_SECRET = "your-long-random-secret"
```

For Docker, set them in `docker-compose.yml` (see the Docker section above).

---

## Project Structure

```
CoursePlanner/
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Single-service compose with persistent DB volume
├── entrypoint.sh             # Seeds DB on first run, then launches gunicorn
├── app.py                    # Flask REST API (auth, courses, plans, AI, PDF, sharing)
├── requirements.txt          # Python dependencies (includes gunicorn)
├── create_database.py        # Script to initialise / seed the database
├── scrape_purdue_catalog.py  # Catalog scraper
└── frontend/
    ├── src/
    │   ├── App.jsx           # Root component, routing, auth/plan context, sidebar
    │   ├── api.js            # API client (fetch wrapper + all endpoints)
    │   ├── pages/
    │   │   ├── Catalog.jsx          # Course catalog: search, filter, add-to-plan
    │   │   ├── MyPlan.jsx           # Semester grid, transfer credits, drag-drop, PDF, share
    │   │   ├── Requirements.jsx     # Progress bar, GPA, dept/univ checklists, add-to-plan
    │   │   ├── AiPlanner.jsx        # Find Courses + Full Program Plan tabs
    │   │   ├── Plans.jsx            # Create/load/edit/delete plans, share link
    │   │   ├── AccountSettings.jsx  # Name/email editing
    │   │   ├── SharedPlan.jsx       # Public read-only plan view
    │   │   ├── Login.jsx
    │   │   └── Register.jsx
    │   └── components/
    │       └── CourseDetailDrawer.jsx
    ├── package.json
    └── vite.config.js        # Dev server on :3000, proxies /api → :8000
```
