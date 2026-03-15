# College Plan of Study Planner — Specification

## 1. Project Overview

**Project Name:** College Plan of Study Planner
**Type:** Web Application (Flask REST API + React SPA)
**Core Functionality:** A 3–5 year college course planning tool that lets students browse the Purdue course catalog, build a semester-by-semester plan, track progress toward graduation, check department and university requirements, and get AI-assisted course recommendations.
**Target Users:** Purdue University students planning their academic trajectory.

---

## 2. Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask, Flask-CORS |
| Database | SQLite (`purdue_courses.db`) |
| Frontend | React 18 (Vite), React Router v6 |
| AI | Ollama local LLM (llama3.2 or first available model) |

### Key Files

```
app.py                    Flask REST API — single entry point for the backend
create_database.py        Seeds the SQLite database with Purdue course data
purdue_courses.db         SQLite database (auto-created by create_database.py)
course_planner.py         Legacy Tkinter prototype (kept for reference, not used)
requirements.txt          pip deps: flask, flask-cors

frontend/
  vite.config.js          Proxy: /api → http://127.0.0.1:5000
  src/
    main.jsx              React entry point
    App.jsx               BrowserRouter, PlanContext, Sidebar, route table
    App.css               Global styles — Purdue blue/gold theme + component classes
    api.js                fetch() wrappers for every REST endpoint
    components/
      CourseDetailDrawer.jsx  Slide-in drawer showing full course detail
    pages/
      Catalog.jsx         Course catalog: search, filter, add-to-plan modal
      MyPlan.jsx          Semester grid, drag-drop, status cycle, grade entry
      Requirements.jsx    Progress bar + dept/university requirement checklists
      AiPlanner.jsx       "Find Courses" tab + "Full Program Plan" tab
      Settings.jsx        Create / load / delete plans
```

### Running the App

#### Prerequisites — Ollama + DeepSeek

The AI Planner features require [Ollama](https://ollama.com) running locally with the DeepSeek model.

1. **Install Ollama**
   - macOS / Linux: `curl -fsSL https://ollama.com/install.sh | sh`
   - Windows: download the installer from https://ollama.com/download

2. **Pull the DeepSeek model**
   ```bash
   ollama pull deepseek-r1:7b
   ```
   A smaller variant (`1.5b`) is available if GPU/RAM is limited:
   ```bash
   ollama pull deepseek-r1:1.5b
   ```

3. **Start the Ollama server** (runs on `http://localhost:11434` by default)
   ```bash
   ollama serve
   ```
   On macOS the Ollama app starts the server automatically when launched.

4. **Verify it is running**
   ```bash
   curl http://localhost:11434/api/tags
   # Should list the pulled model(s)
   ```

> **Note:** The app falls back to keyword-based matching when Ollama is unavailable, so the rest of the app works without it.

#### Starting the App

```bash
# Terminal 1 – backend
pip install flask flask-cors
python app.py
# API available at http://127.0.0.1:5000

# Terminal 2 – frontend
cd frontend
sudo npm install
sudo npm run dev
# UI available at http://localhost:3000
```

---

## 3. Database Schema

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
| name | TEXT | User-chosen plan name |
| duration_years | INTEGER | 3, 4, or 5 |
| start_year | INTEGER | Calendar year of first Fall semester |
| department | TEXT | Major dept code |
| created_at | TEXT | ISO timestamp |
| updated_at | TEXT | ISO timestamp |

### `plan_courses`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| plan_id | INTEGER | FK → plans |
| course_id | INTEGER | FK → courses |
| year | INTEGER | Relative year within plan (1…duration_years) |
| semester | INTEGER | 1=Fall, 2=Spring, 3=Summer |
| semester_type | TEXT | "regular", "study_abroad", "coop" |
| status | TEXT | "planned", "in_progress", "completed" |
| grade | TEXT | Grade string if completed (e.g. "A", "B+") |

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

All endpoints are prefixed `/api/` and served from `http://127.0.0.1:5000`.
Responses are JSON. The Vite dev server proxies `/api` → backend so the frontend uses relative URLs.

### Courses

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/courses` | List/search courses. Query params: `q` (text search on course_number + title), `dept` (filter by dept code). Returns all courses if no params. |
| GET | `/api/courses/:id` | Single course by ID. 404 if not found. |

### Departments

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/departments` | All departments (code, name, required_credits, required_courses). |
| GET | `/api/departments/:code/requirements` | Single dept's graduation requirements. 404 if not found. |
| GET | `/api/requirements` | All university-wide requirements. |

### Plans

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/api/plans` | — | All plans ordered by created_at DESC. |
| POST | `/api/plans` | `{name, duration_years?, start_year?, department?}` | Create plan. Returns 201 + plan object. |
| GET | `/api/plans/:id` | — | Single plan. 404 if not found. |
| DELETE | `/api/plans/:id` | — | Delete plan + all its plan_courses. |

### Plan Courses

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/api/plans/:id/courses` | — | All courses in plan, ordered by year+semester. Each includes full course object. |
| POST | `/api/plans/:id/courses` | `{course_id, semester?, year?}` | Add course to plan (status defaults to "planned"). Returns 201 + new plan_course. |
| DELETE | `/api/plan-courses/:id` | — | Remove single plan_course. |
| PATCH | `/api/plan-courses/:id` | `{status?, grade?, year?, semester?}` | Update status/grade and/or move to different semester slot. |

### AI

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/api/ai/status` | — | `{available: bool, model: string}` — whether Ollama is reachable. |
| POST | `/api/ai/recommend` | `{interests, completed_courses?, department?}` | Returns up to 10 course recommendations. Uses two-phase approach: keyword scoring → LLM re-ranking (falls back to keyword results if Ollama unavailable). Each item: `{course, reason, ai_ranked}`. |
| POST | `/api/ai/program-plan` | `{interests?, completed_courses?, department?, duration_years?, start_year?, max_credits_per_semester?}` | Generates a full semester schedule satisfying dept + university requirements with prerequisite ordering, filling remaining slots with interest-matched electives. Returns `{semesters, unscheduled, total_credits, dept_required, univ_required}`. |

---

## 5. Frontend Pages

### Global State — PlanContext

`PlanContext` (in `App.jsx`) provides `{currentPlanId, currentPlan, setCurrentPlanId}` to all pages.
`currentPlanId` is persisted in `localStorage` so it survives page reload.

### Sidebar

Persistent left navigation with links to all five pages. Displays current plan name, department, duration, and start year. "New / Load Plan" button navigates to Settings.

### Course Catalog (`/catalog`)

- Search bar: text input (searches course_number + title) + department dropdown filter + Search button. Enter key also triggers search.
- Results count and hint to click course name for full details.
- Course card shows: course number (monospace), title, truncated description (130 chars), credits badge, department badge, terms offered badge, prerequisites badge.
- Clicking course number or title opens a `CourseDetailDrawer` (slide-in panel) with full description, prerequisites, corequisites, terms, and an "Add to Plan" button.
- "Add to Plan" button on card (only shown when a plan is loaded) opens `AddModal`.
- `AddModal`: pill selector for Year (1…duration_years with calendar year shown), pill selector for semester (Fall/Spring/Summer with emoji), error display, Cancel / Add buttons.
- Banner warning shown if no plan is selected.

### My Plan (`/plan`)

- Summary strip: plan name, department, duration, credits planned, credits completed.
- Status legend: colored dots for Planned (gray), In Progress (amber), Completed (green) + drag hint.
- Semester grid: one row per year; columns are Fall + Spring (Summer column shown only if summer courses exist in the plan).
- Each semester card has a Purdue-blue header showing the term label (e.g. "Fall 2025") and total credits.
- Each course row shows: drag handle (⠿), course number (monospace, clickable), status badge, course title (clickable), credits + department, grade (if completed).
- Status cycle button (↻): cycles planned → in_progress → completed. When cycling to "completed", opens `GradeModal` to capture a grade (letter or S/U).
- Remove button (✕): shows confirm dialog before deleting.
- Drag-and-drop: courses can be dragged between semester cards. Optimistic UI update; persists via PATCH on drop. Drop zones highlight with gold dashed border.
- Clicking course number or title opens `CourseDetailDrawer`.

### Requirements (`/requirements`)

- Graduation Progress card: credits completed, credits required, percentage, animated progress bar (turns green at 100%).
- Department Requirements card: lists each required course number with ✅/⭕ icon. Shows X/N completed count.
- University Requirements card: lists each university requirement with ✅/⭕ icon. Requirements are considered met if any satisfying course is completed (or if completed credits ≥ required credits for non-course-based requirements). Shows category badge (e.g. "Core").

### AI Planner (`/ai`)

Two tabs: **Find Courses** and **Full Program Plan**.

**Find Courses tab:**
- Textarea for natural language interest description.
- Keyboard shortcut: Cmd/Ctrl+Enter to search.
- Warning banner if Ollama is not detected (falls back to keyword matching).
- On search: fetches completed course numbers from current plan, posts to `/api/ai/recommend`.
- Results list: course number + title (clickable for details drawer), italicized AI reason, truncated description, credits/dept/terms badges, Details button, "+ Plan" button (adds to Year 1 / Fall, disables after add, shows "✓ Added").
- "AI Ranked" vs "Keyword Match" badge in results header.

**Full Program Plan tab:**
- Optional interests textarea (shared with Find Courses tab).
- Max credits per semester: radio pills — 12, 15, 17, 19.
- "Generate Full Program Plan" button: calls `/api/ai/program-plan` with plan's department, duration, start year, and max credits.
- Summary bar: semesters count, courses count, total planned credits, major required count, university required count. Color legend for Major Req / Univ Req / Prerequisite / Elective badges.
- "Apply All N Courses to My Plan" button: adds all generated courses to the actual plan in batches of 5. Shows progress count. Applied courses dim to 45% opacity.
- Semester grid: 2 columns (Fall | Spring) per year row. Each semester card is a drag-and-drop zone — courses can be rearranged within the generated plan before applying.
- Delete button (✕) on each course row removes it from the generated plan (does not affect actual plan).
- Unscheduled courses panel (amber left border): lists courses that couldn't fit due to prerequisites or credit limits.
- Clicking any course number or title opens `CourseDetailDrawer`.

### Settings (`/settings`)

- Current Plan card: shows active plan name/details + Delete button (with confirmation).
- "+ Create New Plan" button opens `CreatePlanModal`.
- `CreatePlanModal` fields: plan name (required), department dropdown, duration (3/4/5 years), start year (number input). On success, new plan is auto-loaded.
- All Plans table: columns Name, Dept, Duration, Start Year, Actions (Load + Delete buttons). Active plan row is highlighted blue. Confirming Load sets it as the current plan (persisted to localStorage).

---

## 6. AI Implementation

### Two-Phase Course Search (`/api/ai/recommend`)

1. **Keyword scoring** — tokenizes the interests string (strips stop words), scores every course by keyword hits in title (3×) + description (1×). Returns top 40 matches.
2. **Department supplement** — adds up to 15 courses from the student's own department not already in the keyword results.
3. **LLM re-ranking** — if Ollama is available, sends the candidate list (course_number: title — description_preview) to the LLM with a structured prompt. The LLM returns a JSON array of `{course_number, reason}` for the 5–8 most relevant courses.
4. **Fallback** — if Ollama is unavailable or returns no results, returns the top keyword-scored results with the description preview as the reason.

### Greedy Program Plan Scheduler (`/api/ai/program-plan`)

1. Loads department required courses + university requirements.
2. Recursively expands prerequisites up to 3 levels deep using `_collect_with_prereqs`.
3. Performs topological sort to determine dependency order.
4. Greedily fills Fall/Spring semesters across the plan duration, placing "ready" courses (all prerequisites already placed in earlier semesters) up to `max_credits` per semester.
5. Fills remaining semester capacity with interest-matched electives (keyword search on remaining courses).
6. Labels each course with a type: `required`, `university`, `prereq`, or `elective`.

---

## 7. Visual Design

**Color Palette:**
- Primary blue: `#0A2463` (Purdue Navy) — used for sidebar, semester card headers, primary text/links
- Gold: `#CFB991` (Purdue Gold) — used for accents, sidebar brand, credit badges
- Background: `#F8F9FA`
- Surface/cards: `#FFFFFF`
- Status colors: Planned `#9ca3af`, In Progress `#f59e0b`, Completed `#22c55e`
- Error: `#DC3545`, Success: `#22c55e`

**Component classes (defined in App.css):**
- `.layout` — flex container, sidebar + main-content
- `.sidebar` — fixed left nav, 240px, navy background
- `.main-content` — scrollable right panel with padding
- `.card` — white surface with shadow and border-radius
- `.course-card` — horizontal card for catalog results
- `.search-bar` — flex row: input + select + button
- `.summary-strip` — horizontal stats row on My Plan
- `.pill-group` — radio button group styled as pills
- `.modal-overlay` / `.modal-box` — centered modal dialog
- `.req-item` — row in requirements checklist
- `.data-table` — striped/hoverable HTML table
- `.btn`, `.btn-primary`, `.btn-success`, `.btn-danger`, `.btn-secondary`, `.btn-sm` — button variants
- `.meta-tag`, `.meta-credits`, `.meta-dept`, `.meta-terms`, `.meta-prereq` — info badges on course cards
- `.mono` — monospace font for course numbers
- `.course-link` — underline on hover cursor pointer
- `.empty-state` — centered placeholder when no data
- `.loading` — centered loading text
- `.error-msg` — red error box
- `.page-title` — H1 with bottom border

---

## 8. Acceptance Criteria

1. ✅ SQLite database created with Purdue course catalog
2. ✅ Each course contains: title, description, course_number, credits, department, prerequisites, corequisites, terms_offered
3. ✅ User can create a 3, 4, or 5 year plan with department and start year
4. ✅ User can browse/search/filter the full course catalog
5. ✅ User can add courses to specific year + semester slots
6. ✅ User can remove courses from their plan
7. ✅ User can drag-and-drop courses between semester slots (My Plan + AI Planner)
8. ✅ User can cycle course status: planned → in_progress → completed
9. ✅ User can record a letter grade when marking a course completed
10. ✅ Progress tracking shows credits completed vs required with animated progress bar
11. ✅ Department graduation requirements checklist (required courses with completion status)
12. ✅ University-wide graduation requirements checklist
13. ✅ AI course search accepts natural language, returns keyword-matched or LLM-ranked results
14. ✅ AI planner gracefully falls back to keyword matching when Ollama is unavailable
15. ✅ AI Full Program Plan generates a complete prerequisite-respecting schedule
16. ✅ Generated program plan can be applied to the actual plan in one click
17. ✅ Generated program plan courses can be rearranged via drag-drop before applying
18. ✅ Multiple plans can be created, switched between, and deleted
19. ✅ Active plan persists across page reloads (localStorage)
20. ✅ Course detail drawer shows full description, prereqs, coreqs, and terms offered
