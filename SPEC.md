# College Plan of Study Planner - Specification

## 1. Project Overview

**Project Name:** College Plan of Study Planner  
**Type:** Desktop Application  
**Core Functionality:** A 4 or 5 year college course planning application that allows students to plan their courses, track progress to completion, manage degree requirements, and get AI-assisted course recommendations based on their interests.  
**Target Users:** College students at Purdue University planning their academic trajectory.

---

## 2. UI/UX Specification

### Layout Structure

**Main Window (1400x900 minimum)**
- **Header:** Application title, student info summary
- **Left Sidebar (280px):** Navigation menu, plan summary, department selector
- **Main Content Area:** Dynamic content based on selected view
- **Footer:** Status bar with current plan progress

### Visual Design

**Color Palette:**
- Primary: `#0A2463` (Purdue Navy)
- Secondary: `#C8102E` (Purdue Gold/Maroon)
- Accent: `#FFDD00` (Bright Gold)
- Background: `#F8F9FA` (Light Gray)
- Surface: `#FFFFFF` (White)
- Text Primary: `#1A1A1A`
- Text Secondary: `#6C757D`
- Success: `#28A745`
- Warning: `#FFC107`
- Error: `#DC3545`
- Info: `#17A2B8`

**Typography:**
- Headings: "Roboto Slab", serif (H1: 28px, H2: 24px, H3: 20px)
- Body: "Roboto", sans-serif (16px)
- Monospace (course codes): "Fira Code", monospace (14px)

**Spacing System:**
- Base unit: 8px
- Margins: 16px, 24px, 32px
- Padding: 8px, 12px, 16px, 24px
- Border radius: 4px (buttons), 8px (cards)

**Visual Effects:**
- Card shadows: `0 2px 8px rgba(0,0,0,0.1)`
- Hover transitions: 200ms ease
- Focus rings: 2px solid `#0A2463`

### Components

**Navigation Sidebar:**
- Course Catalog link
- My Plan link
- Requirements link
- AI Planner link
- Plan Settings (4/5 year toggle)
- Department Selector

**Course Card:**
- Course number (bold)
- Course title
- Credits badge
- Department tag
- Terms offered indicators (Fall/Spring/Summer)
- Prerequisites/Corequisites section
- Status indicator (planned/in-progress/completed)
- Add to Plan button
- Prerequisite warning icon if not satisfied

**Year/Semester Planner:**
- 8-10 semester blocks (depending on 4/5 year plan)
- Each semester shows:
  - Term name (e.g., "Fall 2024")
  - Semester type (Regular/Study Abroad/Co-op/Off)
  - Course slots with course cards
  - Total credits counter
  - Prerequisite status indicator
  - Add course button
  - Mark as off-semester option

**Progress Tracker:**
- Overall completion percentage
- Credits completed vs required by department
- Courses completed vs required
- Prerequisites satisfied indicator
- Graduation requirements checklist

**AI Course Planner:**
- Natural language input field
- Student interests text area
- Loading indicator during LLM query
- Course recommendations list with:
  - Course suggestions
  - Reasoning for recommendation
  - Add to plan button

---

## 3. Database Schema

### Tables

**courses**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| course_number | TEXT | e.g., "CS 18000" |
| title | TEXT | Course title |
| description | TEXT | Course description |
| credits | INTEGER | Number of credit hours |
| department | TEXT | Department code (e.g., "CS") |
| prerequisites | TEXT | JSON array of prereq course numbers |
| corequisites | TEXT | JSON array of coreq course numbers |
| terms_offered | TEXT | JSON array ["Fall", "Spring", "Summer"] |
| is_required | INTEGER | 1 if required for some majors, 0 otherwise |

**plans**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| name | TEXT | Plan name |
| duration_years | INTEGER | 4 or 5 |
| start_year | INTEGER | Starting year for the plan |
| department | TEXT | Major department |
| created_at | TEXT | ISO timestamp |
| updated_at | TEXT | ISO timestamp |

**plan_courses**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| plan_id | INTEGER | Foreign key to plans |
| course_id | INTEGER | Foreign key to courses |
| semester | INTEGER | 1-8 or 1-10 |
| year | INTEGER | Year number in plan |
| semester_type | TEXT | "regular", "study_abroad", "coop" |
| status | TEXT | "planned", "completed", "in_progress" |
| grade | TEXT | Grade received (if completed) |

**departments**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| code | TEXT | Department code (e.g., "CS") |
| name | TEXT | Department full name |
| required_credits | INTEGER | Credits required for graduation |
| required_courses | TEXT | JSON array of required course numbers |

**university_requirements**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| name | TEXT | Requirement name |
| description | TEXT | Requirement description |
| category | TEXT | Category (e.g., "Core", "Electives") |
| credits_required | INTEGER | Credits required |
| courses_required | TEXT | JSON array of acceptable course numbers |
| minimum_grade | TEXT | Minimum grade required |

---

## 4. Functionality Specification

### Core Features

1. **Course Catalog Browser**
   - View all Purdue courses
   - Filter by department, credits, terms offered
   - Search by course number or title
   - View course details (description, prereqs, coreqs)
   - View which courses are required for specific majors

2. **Plan Management**
   - Create new plan (4 or 5 year)
   - Select major/department
   - View plan by semester/year (8-10 semesters)
   - Move courses between semesters via drag-drop or cut/paste
   - Set plan duration
   - Mark semesters as Study Abroad, Co-op, or Off

3. **Semester Off Functionality**
   - Mark any semester as: Regular, Study Abroad, Co-op, or Off
   - semesters count toward total duration but don't require courses
   - Visual indicator showing semester type
   - Can add limited courses during off-semesters

4. **Course Selection**
   - Add courses to specific semesters
   - Remove courses from plan
   - Mark courses as completed/in-progress
   - Record grades for completed courses

5. **Prerequisites Validation**
   - Real-time prerequisite checking
   - Visual warning if prerequisites not met
   - Show which prerequisites are missing
   - Block adding course if prerequisites not satisfied (with override option)
   - Track completed prerequisites across all semesters

6. **Department Graduation Requirements**
   - Select major/department when creating plan
   - View required courses for selected major
   - Track completion of major-specific requirements
   - Show remaining required courses

7. **University-Wide Graduation Requirements**
   - Core curriculum requirements
   - Credit hour minimums
   - Elective requirements
   - Minimum GPA requirements
   - Track completion of all university requirements

8. **Progress Tracking**
   - View overall completion percentage
   - Track credits completed vs required
   - See prerequisites satisfied
   - Identify missing prerequisites
   - View graduation requirements checklist
   - Department-specific progress

9. **AI Course Planner (LLM Integration)**
   - Natural language input for student interests
   - Parse student goals and interests
   - Recommend courses based on:
     - Student interests
     - Major requirements
     - Prerequisites already satisfied
     - Career goals
   - Provide multiple course options with reasoning
   - Allow selection and automatic addition to plan
   - Use local LLM (Ollama) for privacy and offline capability

### User Interactions

- Click course card → View details modal with full description
- Click semester → View semester details and add courses
- Right-click course → Copy/cut/paste to different semester
- Click "Mark Complete" → Toggle course status with grade input
- Click AI Planner → Open AI assistant panel
- Enter interests → Get course recommendations
- Click recommended course → View details and add to plan

### Edge Cases

- Courses with no prerequisites
- Courses offered only in specific terms
- Multiple sections of same course
- Plan with more than 18 credits in a semester
- Semester off with no courses
- Changing major mid-plan
- LLM unavailable or fails
- Invalid natural language input

---

## 5. Technical Implementation

**Backend:** Python with Tkinter  
**Database:** SQLite  
**LLM:** Ollama API (local) with llama3.2 or similar model  
**Frontend:** Tkinter with custom styling  

### LLM Integration

- Connect to local Ollama server (http://localhost:11434)
- Use /api/generate endpoint
- Prompt engineering for course recommendations
- Parse JSON responses for structured course data
- Fallback to manual planning if LLM unavailable

---

## 6. Acceptance Criteria

1. ✅ SQLite database created with Purdue course catalog
2. ✅ Each course contains: title, description, course_number, credits, department, prerequisites, corequisites, terms_offered
3. ✅ User can create a 4 or 5 year plan
4. ✅ User can add courses to specific semesters
5. ✅ User can mark courses as completed
6. ✅ Progress tracking shows completion percentage
7. ✅ Prerequisites are tracked and validated
8. ✅ UI displays course information clearly
9. ✅ Application runs without errors
10. ✅ User can mark semesters as Study Abroad/Co-op/Off
11. ✅ Department graduation requirements are defined and tracked
12. ✅ University-wide graduation requirements are tracked
13. ✅ Prerequisites validation warns before adding courses
14. ✅ AI Planner accepts natural language input
15. ✅ AI Planner provides course recommendations based on interests
16. ✅ User can select from AI recommendations and add to plan
