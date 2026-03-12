"""
Purdue Course Planner – Flask REST API Backend
Run: python app.py
API:  http://127.0.0.1:5000/api/
"""

import re
import sys
import sqlite3
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, List, Dict

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install flask flask-cors")
    sys.exit(1)

DB_PATH = "purdue_courses.db"

# ── Data Classes ──────────────────────────────────────────────────────────────

class Course:
    def __init__(self, id: int, course_number: str, title: str, description: str,
                 credits: int, department: str, prerequisites: List[str],
                 corequisites: List[str], terms_offered: List[str], is_required: int = 0):
        self.id = id
        self.course_number = course_number
        self.title = title
        self.description = description
        self.credits = credits
        self.department = department
        self.prerequisites = prerequisites
        self.corequisites = corequisites
        self.terms_offered = terms_offered
        self.is_required = is_required

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'course_number': self.course_number,
            'title': self.title,
            'description': self.description,
            'credits': self.credits,
            'department': self.department,
            'prerequisites': self.prerequisites,
            'corequisites': self.corequisites,
            'terms_offered': self.terms_offered,
            'is_required': self.is_required,
        }


class PlanCourse:
    def __init__(self, id: int, course: Course, semester: int, year: int,
                 status: str, grade: Optional[str] = None, semester_type: str = "regular"):
        self.id = id
        self.course = course
        self.semester = semester
        self.year = year
        self.status = status
        self.grade = grade
        self.semester_type = semester_type

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'course': self.course.to_dict(),
            'semester': self.semester,
            'year': self.year,
            'status': self.status,
            'grade': self.grade,
            'semester_type': self.semester_type,
        }


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def get_all_courses(self) -> List[Course]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM courses ORDER BY course_number")
        return [self._row_to_course(r) for r in cursor.fetchall()]

    def get_courses_by_department(self, dept: str) -> List[Course]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE department = ? ORDER BY course_number", (dept,))
        return [self._row_to_course(r) for r in cursor.fetchall()]

    def search_courses(self, query: str) -> List[Course]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM courses WHERE course_number LIKE ? OR title LIKE ? ORDER BY course_number",
            (f"%{query}%", f"%{query}%"),
        )
        return [self._row_to_course(r) for r in cursor.fetchall()]

    def get_course_by_id(self, course_id: int) -> Optional[Course]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
        row = cursor.fetchone()
        return self._row_to_course(row) if row else None

    def get_course_by_number(self, course_number: str) -> Optional[Course]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE course_number = ?", (course_number,))
        row = cursor.fetchone()
        return self._row_to_course(row) if row else None

    def get_all_departments(self) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT code, name, required_credits, required_courses FROM departments ORDER BY code")
        rows = cursor.fetchall()
        return [
            {
                'code': r['code'],
                'name': r['name'],
                'required_credits': r['required_credits'],
                'required_courses': json.loads(r['required_courses']) if r['required_courses'] else [],
            }
            for r in rows
        ]

    def get_department_requirements(self, dept_code: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM departments WHERE code = ?", (dept_code,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            'code': row['code'],
            'name': row['name'],
            'required_credits': row['required_credits'],
            'required_courses': json.loads(row['required_courses']) if row['required_courses'] else [],
        }

    def get_university_requirements(self) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM university_requirements")
        return [
            {
                'id': r['id'],
                'name': r['name'],
                'description': r['description'],
                'category': r['category'],
                'credits_required': r['credits_required'],
                'courses_required': json.loads(r['courses_required']) if r['courses_required'] else [],
                'minimum_grade': r['minimum_grade'],
            }
            for r in cursor.fetchall()
        ]

    def create_plan(self, name: str, duration_years: int, start_year: int, department: str) -> int:
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO plans (name, duration_years, start_year, department, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (name, duration_years, start_year, department, now, now),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_plan(self, plan_id: int) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_plans(self) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM plans ORDER BY created_at DESC")
        return [dict(r) for r in cursor.fetchall()]

    def delete_plan(self, plan_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM plan_courses WHERE plan_id = ?", (plan_id,))
        cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        self.conn.commit()

    def add_course_to_plan(self, plan_id: int, course_id: int, semester: int,
                           year: int, semester_type: str = "regular") -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO plan_courses (plan_id, course_id, semester, year, semester_type, status) VALUES (?,?,?,?,?,'planned')",
            (plan_id, course_id, semester, year, semester_type),
        )
        self.conn.commit()
        return cursor.lastrowid

    def remove_course_from_plan(self, plan_course_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM plan_courses WHERE id = ?", (plan_course_id,))
        self.conn.commit()

    def update_course_status(self, plan_course_id: int, status: str, grade: Optional[str] = None):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE plan_courses SET status = ?, grade = ? WHERE id = ?",
            (status, grade, plan_course_id),
        )
        self.conn.commit()

    def get_plan_courses(self, plan_id: int) -> List[PlanCourse]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT pc.id, pc.semester, pc.year, pc.status, pc.grade, pc.semester_type,
                   c.id, c.course_number, c.title, c.description, c.credits,
                   c.department, c.prerequisites, c.corequisites, c.terms_offered
            FROM plan_courses pc
            JOIN courses c ON pc.course_id = c.id
            WHERE pc.plan_id = ?
            ORDER BY pc.year, pc.semester
            """,
            (plan_id,),
        )
        results = []
        for row in cursor.fetchall():
            course = Course(
                id=row[6], course_number=row[7], title=row[8],
                description=row[9], credits=row[10], department=row[11],
                prerequisites=json.loads(row[12]) if row[12] else [],
                corequisites=json.loads(row[13]) if row[13] else [],
                terms_offered=json.loads(row[14]) if row[14] else [],
            )
            results.append(PlanCourse(row[0], course, row[1], row[2], row[3], row[4], row[5]))
        return results

    def _row_to_course(self, row) -> Course:
        try:
            is_req = row['is_required']
        except (KeyError, IndexError):
            is_req = 0
        return Course(
            id=row['id'], course_number=row['course_number'], title=row['title'],
            description=row['description'], credits=row['credits'], department=row['department'],
            prerequisites=json.loads(row['prerequisites']) if row['prerequisites'] else [],
            corequisites=json.loads(row['corequisites']) if row['corequisites'] else [],
            terms_offered=json.loads(row['terms_offered']) if row['terms_offered'] else [],
            is_required=is_req,
        )

    def close(self):
        self.conn.close()


class LLMCoursePlanner:
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.model = "llama3.2"
        self._check_model()

    def _check_model(self):
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get('models', [])
                if models:
                    self.model = models[0]['name']
        except Exception:
            pass

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception:
            return False

    def get_recommendations(self, interests: str, completed: List[str],
                            department: str, available_courses: List[str] = None) -> List[dict]:
        if not self.is_available():
            return []

        course_list = ', '.join(available_courses) if available_courses else (
            'CS 18000, CS 18200, CS 24000, CS 25000, CS 25100, CS 30700, CS 35400, '
            'CS 37300, CS 40800, CS 42600, CS 43000, CS 45600, CS 47800, '
            'MA 16100, MA 16200, MA 26100, MA 35100, MA 36600, '
            'STAT 35000, PHYS 17200, PHYS 27200, ECON 11000, PSY 10000'
        )

        prompt = (
            f"You are a Purdue University academic advisor. "
            f"A student in the {department} major has these interests: {interests}\n"
            f"Completed courses: {', '.join(completed) if completed else 'none'}\n\n"
            f"Choose 5-8 courses to recommend from ONLY this list (do not invent course numbers):\n"
            f"{course_list}\n\n"
            "Consider prerequisites and the student's stated interests.\n"
            "Respond ONLY with a valid JSON array – no explanation, no markdown fences:\n"
            '[{"course_number": "DEPT 00000", "reason": "one sentence reason"}, ...]'
        )

        try:
            payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode()
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=180) as response:
                result = json.loads(response.read().decode())
                text = result.get('response', '')

                # Ollama ≥0.17 surfaces reasoning separately in a 'thinking' field;
                # older builds embedded it as <think>…</think> inside 'response'.
                # Strip legacy tags in case the response field still contains them.
                text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
                # Strip markdown code fences if present
                text = re.sub(r'```[a-z]*\n?', '', text)

                start = text.find('[')
                end   = text.rfind(']') + 1
                if start == -1 or end <= start:
                    print(f"LLM: no JSON array found in response: {text[:300]}")
                    return []

                recs = json.loads(text[start:end])
                db = Database()
                out = []
                for r in recs:
                    c = db.get_course_by_number(r.get('course_number', '').strip())
                    if c:
                        out.append({'course': c.to_dict(), 'reason': r.get('reason', '')})
                    else:
                        print(f"LLM recommended unknown course: {r.get('course_number')}")
                db.close()
                return out

        except Exception as e:
            print(f"LLM error: {e}")
        return []


# ── Flask App ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)
_db = Database()
_llm = LLMCoursePlanner()


# ── Courses ───────────────────────────────────────────────────────────────────

@app.route('/api/courses')
def list_courses():
    q = request.args.get('q', '').strip()
    dept = request.args.get('dept', '').strip()
    if q:
        courses = _db.search_courses(q)
    elif dept:
        courses = _db.get_courses_by_department(dept)
    else:
        courses = _db.get_all_courses()
    return jsonify([c.to_dict() for c in courses])


@app.route('/api/courses/<int:course_id>')
def get_course(course_id):
    course = _db.get_course_by_id(course_id)
    if not course:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(course.to_dict())


# ── Departments ───────────────────────────────────────────────────────────────

@app.route('/api/departments')
def list_departments():
    return jsonify(_db.get_all_departments())


@app.route('/api/departments/<code>/requirements')
def dept_requirements(code):
    reqs = _db.get_department_requirements(code)
    if not reqs:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(reqs)


@app.route('/api/requirements')
def university_requirements():
    return jsonify(_db.get_university_requirements())


# ── Plans ─────────────────────────────────────────────────────────────────────

@app.route('/api/plans', methods=['GET'])
def list_plans():
    return jsonify(_db.get_all_plans())


@app.route('/api/plans', methods=['POST'])
def create_plan():
    body = request.get_json(force=True)
    name = body.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    plan_id = _db.create_plan(
        name=name,
        duration_years=int(body.get('duration_years', 4)),
        start_year=int(body.get('start_year', datetime.now().year)),
        department=body.get('department', 'CS'),
    )
    return jsonify(_db.get_plan(plan_id)), 201


@app.route('/api/plans/<int:plan_id>', methods=['GET'])
def get_plan(plan_id):
    plan = _db.get_plan(plan_id)
    if not plan:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(plan)


@app.route('/api/plans/<int:plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    _db.delete_plan(plan_id)
    return jsonify({'ok': True})


# ── Plan Courses ──────────────────────────────────────────────────────────────

@app.route('/api/plans/<int:plan_id>/courses', methods=['GET'])
def list_plan_courses(plan_id):
    pcs = _db.get_plan_courses(plan_id)
    return jsonify([pc.to_dict() for pc in pcs])


@app.route('/api/plans/<int:plan_id>/courses', methods=['POST'])
def add_plan_course(plan_id):
    body = request.get_json(force=True)
    course_id = body.get('course_id')
    semester = int(body.get('semester', 1))
    year = int(body.get('year', 1))
    if not course_id:
        return jsonify({'error': 'course_id is required'}), 400
    pc_id = _db.add_course_to_plan(plan_id, int(course_id), semester, year)
    # Return the newly created plan course
    pcs = _db.get_plan_courses(plan_id)
    new_pc = next((pc for pc in pcs if pc.id == pc_id), None)
    return jsonify(new_pc.to_dict() if new_pc else {'id': pc_id}), 201


@app.route('/api/plan-courses/<int:pc_id>', methods=['DELETE'])
def remove_plan_course(pc_id):
    _db.remove_course_from_plan(pc_id)
    return jsonify({'ok': True})


@app.route('/api/plan-courses/<int:pc_id>', methods=['PATCH'])
def update_plan_course(pc_id):
    body = request.get_json(force=True)
    status = body.get('status')
    grade = body.get('grade')
    if status:
        _db.update_course_status(pc_id, status, grade)
    return jsonify({'ok': True})


# ── AI Recommendations ────────────────────────────────────────────────────────

@app.route('/api/ai/status')
def ai_status():
    return jsonify({'available': _llm.is_available(), 'model': _llm.model})


@app.route('/api/ai/recommend', methods=['POST'])
def ai_recommend():
    body = request.get_json(force=True)
    interests = body.get('interests', '')
    completed = body.get('completed_courses', [])
    department = body.get('department', 'CS')

    # Build a *focused* course list so we don't overflow the model's context window.
    # The full DB has 6,000+ courses across 150+ departments; passing them all (~20K tokens)
    # breaks local LLMs.  Instead include:
    #   1. Every course in the student's primary department
    #   2. Common core / service departments taken by most majors
    #   3. Any department already represented in the student's completed courses
    CORE_DEPTS = {'MA', 'STAT', 'PHYS', 'ENGL', 'COM', 'ECON', 'PSY'}
    completed_depts = {cn.split()[0] for cn in completed if cn.strip()}
    focus_depts = {department} | CORE_DEPTS | completed_depts

    all_courses = _db.get_all_courses()
    available = [c.course_number for c in all_courses if c.department in focus_depts]

    print(f"AI recommend: dept={department}, focus_depts={focus_depts}, "
          f"available courses={len(available)} (of {len(all_courses)} total)")

    recs = _llm.get_recommendations(interests, completed, department, available_courses=available)
    return jsonify(recs)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Purdue Course Planner API running at http://127.0.0.1:5000")
    print("Start the React frontend with: cd frontend && npm run dev")
    app.run(host='127.0.0.1', port=5000, debug=True)
