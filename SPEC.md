# Purdue Course Planner — Specification

## 1. Project Overview

**Project Name:** Purdue Course Planner
**Type:** Web Application (Flask REST API + React SPA)
**Core Functionality:** A 2–6 year college course planning tool that lets students browse the Purdue course catalog, build a semester-by-semester plan, track progress toward graduation, check department and university requirements, manage transfer credits, share read-only plan links, export PDFs, and get AI-assisted course recommendations.
**Target Users:** Purdue University students planning their academic trajectory.

---

## 2. Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask, Flask-CORS, ReportLab |
| Database | SQLite (`purdue_courses.db`) |
| Frontend | React 18 (Vite), React Router v6 |
| AI | Ollama local LLM (auto-detected; prefers `qwen` variants) |

### Key Files

```
app.py                    Flask REST API — single entry point for the backend
create_database.py        Seeds the SQLite database with Purdue course data
purdue_courses.db         SQLite database
requirements.txt          pip deps: flask, flask-cors, reportlab, etc.

frontend/
  vite.config.js          Proxy: /api → http://127.0.0.1:5050
  src/
    main.jsx              React entry point
    App.jsx               BrowserRouter, AuthContext, PlanContext, Sidebar, route table
    App.css               Global styles — Purdue blue/gold theme + component classes
    api.js                fetch() wrappers for every REST endpoint
    components/
      CourseDetailDrawer.jsx  Slide-in drawer showing full course detail
    pages/
      Catalog.jsx             Course catalog: search, filter, add-to-plan / transfer modal
      MyPlan.jsx              Semester grid, transfer credits card, drag-drop, PDF export, share
      Requirements.jsx        Progress bar, GPA, dept/univ requirement checklists, add-to-plan
      AiPlanner.jsx           "Find Courses" tab + "Full Program Plan" tab
      Plans.jsx               Create / load / edit / delete plans; share link management
      AccountSettings.jsx     First/last name editing, email display
      SharedPlan.jsx          Public read-only plan view (no login required)
      Login.jsx
      Register.jsx
```

### Running the App

```bash
# Terminal 1 – backend (from project root, venv activated)
python app.py
# API available at http://127.0.0.1:5050

# Terminal 2 – frontend
cd frontend
npm install
npm run dev
# UI available at http://localhost:3000
```

#### Ollama (Optional — AI Features)

The AI Planner "Find Courses" tab uses Ollama for re-ranking. The app falls back to keyword matching when Ollama is unavailable. Program plan generation always uses fast keyword ranking only.

```bash
ollama serve
ollama pull qwen:8b   # recommended model
```

The app auto-detects the best available model on startup (prefers any `qwen` variant).

---

## 3. Database Schema

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| email | TEXT UNIQUE | Login identifier |
| password_hash | TEXT | bcrypt hash |
| first_name | TEXT | |
| last_name | TEXT | |
| created_at | TEXT | ISO timestamp |

### `courses`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| course_number | TEXT | e.g. "CS 18000" |
| title | TEXT | |
| description | TEXT | |
| credits | INTEGER | |
| department | TEXT | Dept code, e.g. "CS" |
| prerequisites | TEXT | JSON array of course numbers |
| corequisites | TEXT | JSON array of course numbers |
| terms_offered | TEXT | JSON array: ["Fall","Spring","Summer"] |
| is_required | INTEGER | 1 = required for some major |

### `plans`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | INTEGER | FK → users |
| name | TEXT | User-chosen plan name |
| duration_years | INTEGER | 2–6 |
| start_year | INTEGER | Calendar year of first Fall semester |
| department | TEXT | Primary major dept code |
| plan_type | TEXT | `single`, `double_major`, or `major_minor` |
| secondary_department | TEXT | Second major / minor dept code (when applicable) |
| share_token | TEXT UNIQUE | Random token for public read-only link (null = not shared) |
| created_at | TEXT | ISO timestamp |
| updated_at | TEXT | ISO timestamp |

### `plan_courses`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| plan_id | INTEGER | FK → plans |
| course_id | INTEGER | FK → courses |
| year | INTEGER | Relative year within plan (1…duration_years); 0 = transfer credit |
| semester | INTEGER | 1=Fall, 2=Spring, 3=Summer; 0 = transfer credit |
| semester_type | TEXT | "regular", "study_abroad", "coop" |
| status | TEXT | "planned", "in_progress", "completed" |
| grade | TEXT | Letter grade if completed (e.g. "A", "B+") |

### `departments`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| code | TEXT | e.g. "CS" |
| name | TEXT | Full department name |
| required_credits | INTEGER | Credits required for graduation |
| required_courses | TEXT | JSON array of required course numbers |

### `university_requirements`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT | Requirement name |
| description | TEXT | |
| category | TEXT | e.g. "Core", "Electives" |
| credits_required | INTEGER | |
| courses_required | TEXT | JSON array of acceptable course numbers |
| minimum_grade | TEXT | e.g. "C" |

---

## 4. REST API

All endpoints are prefixed `/api/` and served from `http://127.0.0.1:5050`.
Protected endpoints require `Authorization: Bearer <jwt>` header.
Responses are JSON. The Vite dev server proxies `/api` → backend.

### Auth

| Method | Path | Auth | Body | Description |
|--------|------|------|------|-------------|
| POST | `/api/auth/register` | No | `{email, password, first_name, last_name}` | Create account. Returns `{token, user}`. |
| POST | `/api/auth/login` | No | `{email, password}` | Returns `{token, user}`. |
| GET | `/api/auth/me` | Yes | — | Returns current user object. |
| PATCH | `/api/auth/me` | Yes | `{first_name, last_name}` | Update name. Returns updated user. |

### Courses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/courses` | No | Search courses. Query: `q` (text), `dept` (code). |
| GET | `/api/courses/:id` | No | Single course by ID. |

### Departments

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/departments` | No | All departments (code, name, required_credits, required_courses). |
| GET | `/api/departments/:code/requirements` | No | Single dept's requirements. |
| GET | `/api/requirements` | No | All university-wide requirements. |

### Plans

| Method | Path | Auth | Body | Description |
|--------|------|------|------|-------------|
| GET | `/api/plans` | Yes | — | All plans for current user. |
| POST | `/api/plans` | Yes | `{name, duration_years, start_year, department, plan_type, secondary_department}` | Create plan. |
| GET | `/api/plans/:id` | Yes | — | Single plan. |
| PATCH | `/api/plans/:id` | Yes | `{name?, duration_years?, start_year?, department?, plan_type?, secondary_department?}` | Update plan parameters. |
| DELETE | `/api/plans/:id` | Yes | — | Delete plan + all plan_courses. |

### Plan Sharing

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/plans/:id/share` | Yes | Generate (or return existing) share token. Returns `{share_token}`. |
| DELETE | `/api/plans/:id/share` | Yes | Revoke share token. |
| GET | `/api/shared/:token` | No | Public plan metadata (name, dept, owner name/email). |
| GET | `/api/shared/:token/courses` | No | Public plan courses (read-only). |

### Plan Courses

| Method | Path | Auth | Body | Description |
|--------|------|------|------|-------------|
| GET | `/api/plans/:id/courses` | Yes | — | All courses in plan, ordered by year+semester. |
| POST | `/api/plans/:id/courses` | Yes | `{course_id, semester, year}` | Add course. Transfer credit: `year=0, semester=0`. |
| DELETE | `/api/plan-courses/:id` | Yes | — | Remove single plan_course. |
| PATCH | `/api/plan-courses/:id` | Yes | `{status?, grade?, year?, semester?}` | Update status/grade/slot. |

### PDF Export

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/plans/:id/pdf` | Yes | Returns a PDF binary of the plan. Two-column header: plan name + details (left), owner name + email (right). Includes transfer credits section. |

### AI

| Method | Path | Auth | Body | Description |
|--------|------|------|------|-------------|
| GET | `/api/ai/status` | No | — | `{available: bool, model: string}`. |
| POST | `/api/ai/recommend` | No | `{interests, completed_courses?, department?}` | Up to 10 AI-ranked or keyword-matched course recommendations. Each: `{course, reason, ai_ranked}`. |
| POST | `/api/ai/program-plan` | No | `{interests?, completed_courses?, transfer_credits?, department?, duration_years?, start_year?, max_credits_per_semester?}` | Full semester schedule satisfying dept + university requirements. Returns `{semesters, unscheduled, total_credits, dept_required, univ_required, ai_ranked}`. |

---

## 5. Frontend Pages

### Global State

**`AuthContext`** (`App.jsx`): `{auth, setAuth, logout}` — holds `{user, token}` after login.
**`PlanContext`** (`App.jsx`): `{currentPlanId, currentPlan, setCurrentPlanId}` — persisted in `localStorage`.

### Sidebar

Persistent left navigation. Links: Course Catalog, My Plan, Requirements, AI Planner, Plans, Account Settings. Displays current plan name, department (with plan type formatting), duration, start year. "+ New / Load Plan" button navigates to Plans. User name + email + Sign out at the bottom.

### Course Catalog (`/catalog`)

- Search bar: text input + department dropdown (shows `CODE – Full Name`) + Search button.
- Course cards: course number, title, truncated description, credits/dept/terms/prereqs badges.
- Clicking course number or title opens `CourseDetailDrawer`.
- "Add to Plan" opens `AddModal`: year pill selector, semester pill selector (Fall/Spring/Summer), Transfer Credit radio option. Availability warning shown if course not typically offered that term.

### My Plan (`/plan`)

- Summary strip: Transfer Credits (amber), Credits Planned, Credits Completed, GPA.
- **Transfer Credits card**: search box for courses, results dropdown, add courses; draggable rows; dropping a course into Transfer sets status=completed; dropping out sets status=planned.
- Semester grid: Fall + Spring columns per year (Summer shown only if used).
- Each semester card header: term label, total credits, semester GPA, cumulative GPA.
- Course rows: drag handle, course number (clickable), status badge, title (clickable), credits/dept, grade.
- Status cycle (↻): planned → in_progress → completed (opens GradeModal).
- Remove (✕): confirm dialog.
- Drag-and-drop: optimistic UI update, persists via PATCH.
- Page header actions: **Download PDF** button, **Copy Share Link** button (three-tier clipboard fallback).

### Requirements (`/requirements`)

- Graduation Progress card: credits completed, credits required, %, cumulative GPA, animated progress bar.
- Semester Overview grid: GPA per semester card.
- Department Requirements card: each required course with ✅/⭕, **+ Add to Plan** button (opens AddModal) when not yet in plan, "In plan" label when scheduled but not completed.
- University Requirements card: ✅/⭕, category badge, description + credits.

### AI Planner (`/ai`)

**Find Courses tab:**
- Natural language textarea + Cmd/Ctrl+Enter shortcut.
- AI/keyword badge in results header. Ollama warning banner when unavailable.
- Results: course number, title (clickable), italicized reason, description preview, badges, "+ Plan" button (adds to Year 1 / Fall).

**Full Program Plan tab:**
- Shared interests textarea.
- Max credits per semester radio: 12, 15, 17, 19.
- "Generate" sends completed courses + transfer credits (excluded from plan), department, duration, start year.
- Summary bar: semesters, courses, total credits, major required, univ required counts. Color legend.
- "Apply All" button: batches of 5, shows progress, applied courses dim.
- Semester grid: drag-and-drop to rearrange before applying; delete (✕) removes from generated plan.
- Unscheduled panel: courses that couldn't fit.

### Plans (`/plans`)

- Current Plan card: name, dept (with plan type), duration, year range, Delete button.
- Share Plan card: generate link, copy, preview ↗, revoke. Auto-syncs with active plan.
- "+ Create New Plan" → `CreatePlanModal`: name, plan type (Single/Double/Major+Minor), primary dept, optional secondary dept, duration (2–6 years), start year.
- All Plans table: Name (active badge), Dept, Duration, Start Year, Actions (Load / Edit / Delete).
- Edit → `EditPlanModal`: same form pre-populated; calls PATCH on save.

### Account Settings (`/account-settings`)

- First name + last name inputs (editable), email (read-only).
- Save button updates name via PATCH and refreshes AuthContext.
- Success confirmation message auto-dismisses after 3 seconds.

### Shared Plan (`/shared/:token`)

- Public — no authentication required.
- Read-only banner + Purdue logo.
- Two-column header: plan name + dept/duration/year range (left), owner full name + email (right).
- Summary strip: Transfer Credits, Credits Planned, Credits Completed. No GPA shown.
- Transfer Credits card (if any).
- Year × Semester grid with course status (color-coded left border). No grades shown.
- Status legend.

---

## 6. AI Implementation

### Two-Phase Course Search (`/api/ai/recommend`)

1. **Keyword scoring** — tokenizes interests (strips stop words), scores every course by hits in title (3×) + description (1×). Top 40 matches + up to 15 from student's own department.
2. **LLM re-ranking** — if Ollama available, sends up to 25 candidates (course_number: title — 80-char description) to the model with a structured JSON prompt. 30-second hard wall-clock timeout via `concurrent.futures`.
3. **Fallback** — keyword-scored results with description preview as the reason.

### Greedy Program Plan Scheduler (`/api/ai/program-plan`)

1. Accepts `transfer_credits` (always excluded) and `completed_courses`.
2. Loads department required courses + university requirements; skips already-completed/transferred.
3. Recursively expands prerequisites up to 3 levels deep.
4. Topological sort to determine dependency order.
5. For each Fall/Spring semester slot (year 1 → duration):
   - Filters "ready" courses (all prerequisites satisfied) by **year-level appropriateness**:
     - Year 1: 100–299 level · Year 2: 100–399 · Year 3: 200–499 · Year 4: 300–599 · Year 5+: 400–599
   - Schedules preferred (level-appropriate) courses first, then overdue (below minimum level).
   - Courses above the year's maximum level are deferred to a later semester.
6. Fills remaining capacity with keyword-matched electives, also filtered by year-level range. LLM is **not** called here — results are immediate.
7. Labels each course: `required`, `university`, `prereq`, or `elective`.

---

## 7. PDF Export

Generated by ReportLab (Platypus). Two-column header table:
- Left (55%): plan name (large, left-aligned) + subtitle (dept/plan-type, duration, year range)
- Right (45%): owner full name (large, right-aligned) + email (small, right-aligned)

Transfer Credits section appears before the year grid. Each year/semester block lists courses with credits and status. Footer shows generation timestamp.

---

## 8. Visual Design

**Color Palette:**
- Primary blue: `#0A2463` / `#1a1a2e` (Purdue Navy) — sidebar, card headers
- Gold: `#CFB991` (Purdue Gold) — accents, badges
- Background: `#F0F2F5`
- Surface/cards: `#FFFFFF`
- Status: Planned `#9ca3af` · In Progress `#f59e0b` · Completed `#22c55e`
- Transfer credit accent: `#92400e`
- Error: `#DC3545`

**Key CSS classes (`App.css`):**
`.layout`, `.sidebar`, `.main-content`, `.card`, `.course-card`, `.search-bar`, `.summary-strip`, `.pill-group`, `.modal-overlay`, `.modal-box`, `.req-item`, `.data-table`, `.btn` variants, `.meta-tag` variants, `.mono`, `.course-link`, `.empty-state`, `.loading`, `.error-msg`, `.page-title`, `.sidebar-user-name`, `.sidebar-divider`

---

## 9. Acceptance Criteria

1. ✅ SQLite database with full Purdue course catalog (title, description, course_number, credits, dept, prerequisites, corequisites, terms_offered)
2. ✅ User registration with first name, last name, email, password
3. ✅ JWT authentication with 30-day sessions
4. ✅ Edit account name from Account Settings
5. ✅ Create plans with type (Single / Double Major / Major+Minor), primary dept, optional secondary dept, duration 2–6 years, start year
6. ✅ Edit plan parameters after creation
7. ✅ Browse/search/filter course catalog with full department names
8. ✅ Add courses to specific year + semester slots
9. ✅ Add courses as Transfer Credits (year=0, semester=0 sentinel)
10. ✅ Drag-and-drop courses between semesters and to/from Transfer Credits card
11. ✅ Cycle course status: planned → in_progress → completed
12. ✅ Record letter grades; per-semester and cumulative GPA calculated automatically
13. ✅ Requirements page with progress bar, GPA overview, dept + university checklists
14. ✅ Add-to-Plan button on each unscheduled required course in Requirements
15. ✅ AI course search with natural language, LLM re-ranking or keyword fallback
16. ✅ LLM call has 30-second hard wall-clock timeout; always falls back gracefully
17. ✅ AI Full Program Plan respects prerequisites, year-level appropriateness, transfer credits, and completed courses
18. ✅ Generated plan can be applied in one click (batches of 5)
19. ✅ Generated plan courses rearrangeable via drag-drop before applying
20. ✅ PDF export with two-column header (plan details left, owner right), transfer credits section
21. ✅ Shareable read-only link (no login required); grades and GPA hidden from shared view
22. ✅ Share link can be generated, copied, previewed, and revoked
23. ✅ Multiple plans: create, load, edit, delete; active plan persists in localStorage
24. ✅ Course detail drawer: full description, prereqs, coreqs, terms offered
