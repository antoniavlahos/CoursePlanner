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
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, List, Dict

try:
    from flask import Flask, request, jsonify, g
    from flask_cors import CORS
    from werkzeug.security import generate_password_hash, check_password_hash
    import jwt
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install flask flask-cors PyJWT")
    sys.exit(1)

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-change-in-production')
JWT_EXP_DAYS = 30

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
        self._migrate()

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

    def create_plan(self, name: str, duration_years: int, start_year: int,
                    department: str, user_id: Optional[int] = None) -> int:
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO plans (name, duration_years, start_year, department, created_at, updated_at, user_id) VALUES (?,?,?,?,?,?,?)",
            (name, duration_years, start_year, department, now, now, user_id),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_plan(self, plan_id: int) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_plans(self, user_id: Optional[int] = None) -> List[dict]:
        cursor = self.conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT * FROM plans WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        else:
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

    def update_plan_course_slot(self, plan_course_id: int,
                                year: Optional[int] = None,
                                semester: Optional[int] = None):
        """Move a plan course to a different year / semester."""
        fields, vals = [], []
        if year is not None:
            fields.append('year = ?'); vals.append(year)
        if semester is not None:
            fields.append('semester = ?'); vals.append(semester)
        if fields:
            vals.append(plan_course_id)
            self.conn.execute(
                f"UPDATE plan_courses SET {', '.join(fields)} WHERE id = ?", vals
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

    def _migrate(self):
        """Run lightweight schema migrations (idempotent)."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                email        TEXT    UNIQUE NOT NULL,
                password_hash TEXT   NOT NULL,
                created_at   TEXT    NOT NULL
            )
        """)
        # Add user_id column to plans if it doesn't exist yet
        cols = {row[1] for row in self.conn.execute("PRAGMA table_info(plans)")}
        if 'user_id' not in cols:
            self.conn.execute("ALTER TABLE plans ADD COLUMN user_id INTEGER REFERENCES users(id)")
        self.conn.commit()

    def create_user(self, email: str, password_hash: str) -> int:
        now = datetime.now().isoformat()
        cursor = self.conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?,?,?)",
            (email.lower().strip(), password_hash, now),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_user_by_email(self, email: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT id, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()


# ── Keyword search helper ──────────────────────────────────────────────────────

_STOP_WORDS = {
    'i', 'a', 'an', 'the', 'and', 'or', 'in', 'of', 'is', 'are', 'for', 'with',
    'my', 'am', 'be', 'would', 'like', 'want', 'to', 'learn', 'study', 'take',
    'course', 'class', 'courses', 'classes', 'purdue', 'looking', 'interested',
    'interest', 'get', 'have', 'has', 'was', 'were', 'will', 'can', 'how', 'what',
    'which', 'that', 'this', 'it', 'at', 'as', 'by', 'on', 'up', 'do', 'did',
    'not', 'but', 'so', 'if', 'more', 'some', 'me', 'us', 'we', 'they', 'their',
    'about', 'into', 'from', 'also', 'just', 'any', 'all', 'one', 'two', 'three',
    'good', 'great', 'really', 'very', 'too', 'much', 'many', 'most', 'other',
    'new', 'use', 'used', 'using', 'need', 'needed', 'able', 'help', 'make',
}


def _keyword_search(query: str, courses: List[Course], top_n: int = 40) -> List[tuple]:
    """Score courses against a free-text query using title (3×) and description (1×) hits.

    Returns a list of (score, Course) tuples sorted by descending score, capped at top_n.
    """
    tokens = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
    keywords = [t for t in tokens if t not in _STOP_WORDS]
    if not keywords:
        return []

    scored = []
    for course in courses:
        title_lower = (course.title or '').lower()
        desc_lower  = (course.description or '').lower()
        score = sum(
            (3 if kw in title_lower else 0) + (1 if kw in desc_lower else 0)
            for kw in keywords
        )
        if score > 0:
            scored.append((score, course))

    scored.sort(key=lambda x: -x[0])
    return scored[:top_n]


# ── LLM planner ───────────────────────────────────────────────────────────────

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
                            department: str, candidate_courses: List[Course] = None) -> List[dict]:
        """Two-phase recommendation: caller pre-filters candidates via keyword search,
        then this method asks the LLM to pick the 5-8 most relevant, given each
        course's actual title and description so it can reason accurately."""
        if not self.is_available() or not candidate_courses:
            return []

        # Build a compact catalogue block: course_number: title — description_preview
        course_lines = []
        for c in candidate_courses:
            desc = (c.description or '').replace('\n', ' ')[:120].strip()
            if desc:
                course_lines.append(f"{c.course_number}: {c.title} — {desc}")
            else:
                course_lines.append(f"{c.course_number}: {c.title}")

        course_block  = '\n'.join(course_lines)
        completed_str = ', '.join(completed) if completed else 'none'

        prompt = (
            f"You are a Purdue University academic advisor.\n"
            f"A student in the {department} program says: \"{interests}\"\n"
            f"Courses already completed: {completed_str}\n\n"
            f"From the list below, select the 5-8 courses MOST relevant to the student's goals. "
            f"Use ONLY course numbers from this exact list. "
            f"Do not invent or modify any course number.\n\n"
            f"{course_block}\n\n"
            "Respond ONLY with a valid JSON array, no explanation, no code fences:\n"
            '[{"course_number": "DEPT 00000", "reason": "one sentence explaining relevance"}, ...]'
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

                # Ollama ≥0.17 surfaces reasoning in a separate 'thinking' field;
                # strip legacy <think>…</think> tags just in case.
                text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
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
                        out.append({
                            'course': c.to_dict(),
                            'reason': r.get('reason', ''),
                            'ai_ranked': True,
                        })
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


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _make_token(user_id: int, email: str) -> str:
    payload = {
        'sub': user_id,
        'email': email,
        'exp': datetime.now(tz=timezone.utc) + timedelta(days=JWT_EXP_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        token = auth[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            g.user_id = payload['sub']
            g.user_email = payload['email']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    body = request.get_json(force=True)
    email = (body.get('email') or '').strip().lower()
    password = body.get('password') or ''
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if _db.get_user_by_email(email):
        return jsonify({'error': 'Email already registered'}), 409
    password_hash = generate_password_hash(password)
    user_id = _db.create_user(email, password_hash)
    token = _make_token(user_id, email)
    return jsonify({'token': token, 'user': {'id': user_id, 'email': email}}), 201


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    body = request.get_json(force=True)
    email = (body.get('email') or '').strip().lower()
    password = body.get('password') or ''
    user = _db.get_user_by_email(email)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid email or password'}), 401
    token = _make_token(user['id'], user['email'])
    return jsonify({'token': token, 'user': {'id': user['id'], 'email': user['email']}})


@app.route('/api/auth/me')
@require_auth
def auth_me():
    user = _db.get_user_by_id(g.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user)


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
@require_auth
def list_plans():
    return jsonify(_db.get_all_plans(user_id=g.user_id))


@app.route('/api/plans', methods=['POST'])
@require_auth
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
        user_id=g.user_id,
    )
    return jsonify(_db.get_plan(plan_id)), 201


@app.route('/api/plans/<int:plan_id>', methods=['GET'])
@require_auth
def get_plan(plan_id):
    plan = _db.get_plan(plan_id)
    if not plan:
        return jsonify({'error': 'Not found'}), 404
    if plan.get('user_id') != g.user_id:
        return jsonify({'error': 'Forbidden'}), 403
    return jsonify(plan)


@app.route('/api/plans/<int:plan_id>', methods=['DELETE'])
@require_auth
def delete_plan(plan_id):
    plan = _db.get_plan(plan_id)
    if plan and plan.get('user_id') != g.user_id:
        return jsonify({'error': 'Forbidden'}), 403
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
    body     = request.get_json(force=True)
    status   = body.get('status')
    grade    = body.get('grade')
    year     = body.get('year')
    semester = body.get('semester')
    if status:
        _db.update_course_status(pc_id, status, grade)
    if year is not None or semester is not None:
        _db.update_plan_course_slot(pc_id, year, semester)
    return jsonify({'ok': True})


# ── AI Recommendations ────────────────────────────────────────────────────────

@app.route('/api/ai/status')
def ai_status():
    return jsonify({'available': _llm.is_available(), 'model': _llm.model})


@app.route('/api/ai/recommend', methods=['POST'])
def ai_recommend():
    body       = request.get_json(force=True)
    interests  = (body.get('interests') or '').strip()
    completed  = body.get('completed_courses', [])
    department = body.get('department', 'CS')

    if not interests:
        return jsonify([])

    all_courses = _db.get_all_courses()

    # ── Phase 1: keyword search across ALL 6 000+ courses ─────────────────────
    # Score every course by how many query keywords appear in its title (3×)
    # and description (1×).  Returns the top-40 most relevant candidates.
    keyword_hits = _keyword_search(interests, all_courses, top_n=40)

    # Also pull in courses from the student's own department so they always
    # appear as candidates even when the query is very broad.
    dept_courses = [c for c in all_courses if c.department == department]
    seen         = {c.course_number for _, c in keyword_hits}
    extra_dept   = [c for c in dept_courses if c.course_number not in seen]

    candidates = [c for _, c in keyword_hits] + extra_dept[:15]

    print(f"AI recommend: dept={department}, interests='{interests[:60]}', "
          f"keyword_hits={len(keyword_hits)}, candidates={len(candidates)}")

    # ── Phase 2: LLM re-ranks candidates using titles + description previews ──
    # The LLM sees each course's actual content, not just its code, so it can
    # reason accurately and write meaningful one-sentence reasons.
    if _llm.is_available():
        recs = _llm.get_recommendations(interests, completed, department, candidates[:50])
        if recs:
            return jsonify(recs)

    # ── Fallback: return keyword-scored results when Ollama is not running ─────
    if not keyword_hits and not dept_courses:
        return jsonify([])

    fallback = keyword_hits if keyword_hits else [(0, c) for c in dept_courses[:10]]
    out = []
    for _score, course in fallback[:10]:
        desc_preview = (course.description or '').strip()[:120]
        reason = (desc_preview + '…') if desc_preview else f'A {course.department} course related to your query.'
        out.append({'course': course.to_dict(), 'reason': reason, 'ai_ranked': False})
    return jsonify(out)


# ── Program plan scheduler ────────────────────────────────────────────────────

def _collect_with_prereqs(seed_numbers: List[str], completed_set: set,
                          db: 'Database', depth_limit: int = 3) -> Dict[str, Course]:
    """Recursively expand a list of required course numbers to include their
    unmet prerequisites (up to depth_limit levels deep).

    Only adds prerequisites that exist in the DB and are not already completed.
    Returns a dict of {course_number: Course} ready for scheduling.
    """
    result: Dict[str, Course] = {}
    queue = list(seed_numbers)
    depth: Dict[str, int] = {cn: 0 for cn in seed_numbers}

    while queue:
        cn = queue.pop(0)
        if cn in result or cn in completed_set:
            continue
        course = db.get_course_by_number(cn)
        if not course:
            continue
        result[cn] = course
        if depth.get(cn, 0) < depth_limit:
            for prereq in course.prerequisites:
                if prereq not in result and prereq not in completed_set:
                    depth[prereq] = depth.get(cn, 0) + 1
                    queue.append(prereq)

    return result


def _schedule_courses(courses_dict: Dict[str, Course], completed_set: set,
                      duration_years: int, max_credits: int = 15) -> tuple:
    """Greedy semester scheduler that respects prerequisites.

    - Iterates Fall/Spring semesters across duration_years.
    - Each pass picks all "ready" courses (every prerequisite already completed
      or placed in an earlier semester) up to max_credits.
    - Returns (semesters, unscheduled_courses):
        semesters          – list of {year, semester, courses, credits}
        unscheduled_courses – list of Course objects that couldn't be placed
    """
    from collections import deque

    scheduled = set(completed_set)
    remaining = dict(courses_dict)

    # Topological sort to detect obvious ordering (breaks ties in a sensible way)
    in_degree: Dict[str, int] = {}
    adj: Dict[str, List[str]] = {cn: [] for cn in remaining}
    for cn, c in remaining.items():
        effective_prereqs = [p for p in c.prerequisites if p in remaining]
        in_degree[cn] = len(effective_prereqs)
        for p in effective_prereqs:
            adj.setdefault(p, []).append(cn)

    topo_queue: deque = deque(cn for cn, d in in_degree.items() if d == 0)
    topo_order: List[str] = []
    while topo_queue:
        cn = topo_queue.popleft()
        topo_order.append(cn)
        for dep in adj.get(cn, []):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                topo_queue.append(dep)
    # Any courses left in a cycle get appended at end
    topo_order += [cn for cn in remaining if cn not in set(topo_order)]
    priority = {cn: i for i, cn in enumerate(topo_order)}

    semesters: List[dict] = []
    total_semesters = duration_years * 2   # fall + spring only

    for sem_idx in range(total_semesters):
        year     = (sem_idx // 2) + 1
        semester = (sem_idx % 2) + 1     # 1 = Fall, 2 = Spring

        # Courses whose prerequisites are all satisfied
        ready = [
            (cn, c) for cn, c in remaining.items()
            if all(
                p in scheduled
                for p in c.prerequisites
                if p in courses_dict     # only enforce internal prereqs
            )
        ]
        # Sort: lowest topo index (earliest in dependency chain) first
        ready.sort(key=lambda x: priority.get(x[0], 9999))

        sem_courses: List[Course] = []
        sem_credits = 0

        for cn, course in ready:
            if sem_credits + course.credits <= max_credits:
                sem_courses.append(course)
                sem_credits += course.credits
                scheduled.add(cn)
                remaining.pop(cn)

        if sem_courses:
            semesters.append({
                'year':     year,
                'semester': semester,
                'courses':  sem_courses,
                'credits':  sem_credits,
            })

    return semesters, list(remaining.values())


@app.route('/api/ai/program-plan', methods=['POST'])
def ai_program_plan():
    body        = request.get_json(force=True)
    interests   = (body.get('interests') or '').strip()
    completed   = body.get('completed_courses', [])
    department  = body.get('department', 'CS')
    duration    = max(1, min(int(body.get('duration_years', 4)), 8))
    max_credits = max(9, min(int(body.get('max_credits_per_semester', 15)), 22))
    start_year  = int(body.get('start_year', 2025))

    completed_set = set(completed)

    # ── 1. Load requirements ──────────────────────────────────────────────────
    dept_req  = _db.get_department_requirements(department)
    univ_reqs = _db.get_university_requirements()

    # ── 2. Collect required courses ───────────────────────────────────────────
    dept_required_set = set(dept_req['required_courses']) if dept_req else set()
    seed_numbers: List[str] = []

    # Department required courses
    for cn in dept_required_set:
        if cn not in completed_set:
            seed_numbers.append(cn)

    # University requirements — pick one satisfying course per requirement
    univ_course_map: Dict[int, str] = {}   # req_id → chosen course_number
    for req in univ_reqs:
        if req['courses_required']:
            # Already satisfied by a completed course?
            if any(cn in completed_set for cn in req['courses_required']):
                continue
            for cn in req['courses_required']:
                c = _db.get_course_by_number(cn)
                if c and cn not in completed_set:
                    if cn not in seed_numbers:
                        seed_numbers.append(cn)
                    univ_course_map[req['id']] = cn
                    break

    univ_required_set = set(univ_course_map.values())

    # Recursively pull in unmet prerequisites
    courses_to_schedule = _collect_with_prereqs(seed_numbers, completed_set, _db)

    print(f"Program plan: dept={department}, duration={duration}yr, "
          f"required={len(seed_numbers)}, with_prereqs={len(courses_to_schedule)}, "
          f"completed={len(completed_set)}")

    # ── 3. Schedule required + prerequisite courses ───────────────────────────
    semesters, unscheduled = _schedule_courses(
        courses_to_schedule, completed_set, duration, max_credits
    )

    # ── 4. Fill remaining semester capacity with interest-based electives ─────
    ai_elective_reasons: Dict[str, str] = {}   # course_number → Ollama reason
    ai_ranked_plan = False

    if interests:
        all_courses   = _db.get_all_courses()
        excluded      = set(courses_to_schedule.keys()) | completed_set
        elective_pool = [c for c in all_courses if c.course_number not in excluded]
        elective_hits = _keyword_search(interests, elective_pool, top_n=40)

        electives: List[Course] = []

        # Phase 1: try Ollama for AI-ranked elective selection
        if _llm.is_available() and elective_hits:
            candidates = [c for _, c in elective_hits]
            ai_recs    = _llm.get_recommendations(interests, completed, department, candidates)
            if ai_recs:
                ai_ranked_plan      = True
                ai_elective_reasons = {
                    rec['course']['course_number']: rec['reason'] for rec in ai_recs
                }
                # AI-selected courses first (in Ollama rank order), then keyword remainder
                ai_cns   = {rec['course']['course_number'] for rec in ai_recs}
                ai_rank  = {rec['course']['course_number']: i for i, rec in enumerate(ai_recs)}
                ai_first = sorted(
                    [c for _, c in elective_hits if c.course_number in ai_cns],
                    key=lambda c: ai_rank.get(c.course_number, 999),
                )
                rest     = [c for _, c in elective_hits if c.course_number not in ai_cns]
                electives = ai_first + rest
                print(f"Ollama selected {len(ai_first)} electives for program plan")

        # Phase 2: fallback to keyword order when Ollama is unavailable / returned nothing
        if not electives:
            electives = [c for _, c in elective_hits]

        elective_idx = 0

        # First pass: fill existing semesters that have room
        for sem in semesters:
            while elective_idx < len(electives):
                ec = electives[elective_idx]
                if sem['credits'] + ec.credits <= max_credits:
                    sem['courses'].append(ec)
                    sem['credits'] += ec.credits
                    excluded.add(ec.course_number)
                    elective_idx += 1
                else:
                    break

        # Second pass: open new semesters for remaining electives
        total_slots = duration * 2
        while elective_idx < len(electives) and len(semesters) < total_slots:
            sem_idx     = len(semesters)
            year        = (sem_idx // 2) + 1
            semester    = (sem_idx % 2) + 1
            sem_courses = []
            sem_credits = 0
            while elective_idx < len(electives):
                ec = electives[elective_idx]
                if sem_credits + ec.credits <= max_credits:
                    sem_courses.append(ec)
                    sem_credits += ec.credits
                    elective_idx += 1
                else:
                    break
            if sem_courses:
                semesters.append({'year': year, 'semester': semester,
                                   'courses': sem_courses, 'credits': sem_credits})

    # ── 5. Build response ─────────────────────────────────────────────────────
    SEMESTER_NAMES = {1: 'Fall', 2: 'Spring'}

    result_semesters = []
    for sem in semesters:
        year     = sem['year']
        semester = sem['semester']
        cal_year = start_year + (year - 1) + (1 if semester == 2 else 0)

        courses_out = []
        for course in sem['courses']:
            if course.course_number in dept_required_set:
                ctype  = 'required'
                reason = f'Required for the {department} degree'
            elif course.course_number in univ_required_set:
                ctype  = 'university'
                reason = 'Satisfies a university graduation requirement'
            elif course.course_number in courses_to_schedule:
                ctype  = 'prereq'
                reason = 'Prerequisite for a required course'
            else:
                ctype  = 'elective'
                reason = ai_elective_reasons.get(
                    course.course_number,
                    'Suggested elective based on your stated interests',
                )
            courses_out.append({**course.to_dict(), 'type': ctype, 'reason': reason})

        result_semesters.append({
            'year':     year,
            'semester': semester,
            'label':    f"{SEMESTER_NAMES.get(semester, '')} {cal_year}",
            'courses':  courses_out,
            'credits':  sem['credits'],
        })

    completed_credits = sum(
        (c.credits if (c := _db.get_course_by_number(cn)) else 0)
        for cn in completed_set
    )

    return jsonify({
        'semesters':     result_semesters,
        'unscheduled':   [c.to_dict() for c in unscheduled],
        'total_credits': sum(s['credits'] for s in result_semesters) + completed_credits,
        'dept_required': len(dept_required_set),
        'univ_required': len(univ_required_set),
        'ai_ranked':     ai_ranked_plan,
    })


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Purdue Course Planner API running at http://127.0.0.1:5000")
    print("Start the React frontend with: cd frontend && npm run dev")
    app.run(host='127.0.0.1', port=5000, debug=True)
