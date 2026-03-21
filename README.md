# Purdue Course Planner

A full-stack web application for planning a Purdue University degree program. Browse the course catalog, build a multi-year semester schedule, track requirements, and use AI-powered course recommendations.

---

## Features

### User Accounts
- Register and sign in with email and password
- JWT-based authentication (30-day sessions)
- Each user's plans are private and scoped to their account

### Course Catalog
- Browse and search all Purdue courses by keyword or department
- View full course details: description, credits, prerequisites, terms offered
- Add courses to your plan via a semester picker modal
- Warning shown if a course is not typically offered in the selected semester

### My Plan
- Semester-by-semester view of your degree plan (Year 1–4+)
- Drag and drop courses between semesters
- Mark courses as Planned, In Progress, or Completed
- Enter letter grades; GPA is calculated automatically
- Remove courses from any semester

### Requirements Checker
- View major (department) requirements and university graduation requirements
- See which requirements are satisfied by your current plan

### AI Planner
- **Find Courses**: Describe your interests in plain text; the planner searches the full catalog and ranks the best matches using Ollama (AI) or keyword matching as a fallback
- **Full Program Plan**: Automatically generate a complete semester-by-semester schedule that satisfies all major and university requirements, respects prerequisites, and fills elective slots based on your interests
  - Drag and drop to rearrange courses before applying
  - Apply the generated plan to your My Plan in one click
- Semester picker modal when adding individual courses, with availability warning

### Settings
- Create, load, and delete degree plans
- Configure plan name, department/major, duration (3–5 years), and start year

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Ollama | latest | Optional — enables AI-ranked results |

---

## Setup

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

### 3. Frontend

```bash
cd frontend
npm install
cd ..
```

---

## Running the App

Open **two terminals** — one for the backend, one for the frontend.

### Terminal 1 — Backend (Flask API)

```bash
# From the project root (with venv activated)
python app.py
```

The API will be available at `http://127.0.0.1:5000`.

### Terminal 2 — Frontend (Vite dev server)

```bash
cd frontend
npm run dev
```

Open your browser at **http://localhost:3000**.

> The frontend proxies all `/api` requests to the Flask backend automatically, so no CORS configuration is needed during development.

---

## Ollama (AI Features) — Optional

Ollama enables AI-ranked course recommendations and intelligent program plan generation. Without it, the app falls back to keyword matching automatically.

### Install Ollama

**macOS:**
```bash
brew install ollama
```

**Windows / Linux:**
Download from [ollama.com](https://ollama.com/download)

### Start Ollama and pull the model

```bash
# Start the Ollama server
ollama serve

# In a separate terminal, pull the model
ollama pull llama3.2
```

The app will detect Ollama automatically at `http://localhost:11434`. A banner in the AI Planner will indicate whether AI ranking is active.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `dev-secret-change-in-production!` | Secret key for signing JWT tokens. **Change this in production.** |

Set it before starting the backend:

```bash
# macOS / Linux
export JWT_SECRET="your-long-random-secret"

# Windows (PowerShell)
$env:JWT_SECRET = "your-long-random-secret"
```

---

## Project Structure

```
CoursePlanner/
├── app.py                  # Flask REST API (auth, courses, plans, AI endpoints)
├── requirements.txt        # Python dependencies
├── purdue_courses.db       # SQLite database
├── create_database.py      # Script to initialise / seed the database
├── scrape_purdue_catalog.py# Catalog scraper
├── course_planner.py       # Legacy Tkinter desktop app
└── frontend/
    ├── src/
    │   ├── App.jsx         # Root component, routing, auth context
    │   ├── api.js          # API client (fetch wrapper + all endpoints)
    │   ├── pages/
    │   │   ├── Catalog.jsx
    │   │   ├── MyPlan.jsx
    │   │   ├── Requirements.jsx
    │   │   ├── AiPlanner.jsx
    │   │   ├── Settings.jsx
    │   │   ├── Login.jsx
    │   │   └── Register.jsx
    │   └── components/
    │       └── CourseDetailDrawer.jsx
    ├── package.json
    └── vite.config.js      # Dev server on :3000, proxies /api → :5000
```
