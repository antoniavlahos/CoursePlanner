"""
Purdue Course Planner – Flask REST API Backend
Run: python app.py
API:  http://127.0.0.1:5050/api/
"""

import re
import sys
import sqlite3
import json
import urllib.request
import urllib.error
import os
import concurrent.futures
import requests
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

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-change-in-production!')
JWT_EXP_DAYS = 30

DB_PATH = os.environ.get('DB_PATH', 'purdue_courses.db')

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
        import threading
        self._lock = threading.Lock()
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
                    department: str, user_id: Optional[int] = None,
                    plan_type: str = 'single', secondary_department: str = '') -> int:
        with self._lock:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO plans (name, duration_years, start_year, department, created_at, updated_at, user_id, plan_type, secondary_department) VALUES (?,?,?,?,?,?,?,?,?)",
                (name, duration_years, start_year, department, now, now, user_id, plan_type, secondary_department),
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
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM plan_courses WHERE plan_id = ?", (plan_id,))
            cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
            self.conn.commit()

    def add_course_to_plan(self, plan_id: int, course_id: int, semester: int,
                           year: int, semester_type: str = "regular") -> int:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO plan_courses (plan_id, course_id, semester, year, semester_type, status) VALUES (?,?,?,?,?,'planned')",
                (plan_id, course_id, semester, year, semester_type),
            )
            self.conn.commit()
            return cursor.lastrowid

    def remove_course_from_plan(self, plan_course_id: int):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM plan_courses WHERE id = ?", (plan_course_id,))
            self.conn.commit()

    def update_course_status(self, plan_course_id: int, status: str, grade: Optional[str] = None):
        with self._lock:
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
            with self._lock:
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
        # Add first_name / last_name to users if not present
        user_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(users)")}
        if 'first_name' not in user_cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT NOT NULL DEFAULT ''")
        if 'last_name' not in user_cols:
            self.conn.execute("ALTER TABLE users ADD COLUMN last_name TEXT NOT NULL DEFAULT ''")
        # Add share_token / plan_type / secondary_department to plans if not present
        plan_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(plans)")}
        if 'share_token' not in plan_cols:
            self.conn.execute("ALTER TABLE plans ADD COLUMN share_token TEXT")
            self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_plans_share_token ON plans (share_token)")
        if 'plan_type' not in plan_cols:
            self.conn.execute("ALTER TABLE plans ADD COLUMN plan_type TEXT NOT NULL DEFAULT 'single'")
        if 'secondary_department' not in plan_cols:
            self.conn.execute("ALTER TABLE plans ADD COLUMN secondary_department TEXT NOT NULL DEFAULT ''")
        self.conn.commit()

    def create_user(self, email: str, password_hash: str,
                    first_name: str = '', last_name: str = '') -> int:
        with self._lock:
            now = datetime.now().isoformat()
            cursor = self.conn.execute(
                "INSERT INTO users (email, password_hash, created_at, first_name, last_name) VALUES (?,?,?,?,?)",
                (email.lower().strip(), password_hash, now, first_name.strip(), last_name.strip()),
            )
            self.conn.commit()
            return cursor.lastrowid

    def get_user_by_email(self, email: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT id, email, password_hash, first_name, last_name FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT id, email, first_name, last_name FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_plan(self, plan_id: int, name: str, duration_years: int, start_year: int,
                    department: str, plan_type: str = 'single', secondary_department: str = ''):
        with self._lock:
            now = datetime.now().isoformat()
            self.conn.execute(
                """UPDATE plans
                   SET name=?, duration_years=?, start_year=?, department=?,
                       plan_type=?, secondary_department=?, updated_at=?
                   WHERE id=?""",
                (name, duration_years, start_year, department, plan_type, secondary_department, now, plan_id),
            )
            self.conn.commit()

    def generate_share_token(self, plan_id: int) -> str:
        import secrets
        token = secrets.token_urlsafe(32)
        with self._lock:
            self.conn.execute("UPDATE plans SET share_token = ? WHERE id = ?", (token, plan_id))
            self.conn.commit()
        return token

    def revoke_share_token(self, plan_id: int):
        with self._lock:
            self.conn.execute("UPDATE plans SET share_token = NULL WHERE id = ?", (plan_id,))
            self.conn.commit()

    def get_plan_by_share_token(self, token: str) -> Optional[dict]:
        row = self.conn.execute(
            """
            SELECT p.id, p.name, p.duration_years, p.start_year, p.department, p.share_token,
                   u.first_name, u.last_name, u.email
            FROM plans p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.share_token = ?
            """,
            (token,)
        ).fetchone()
        return dict(row) if row else None

    def update_user(self, user_id: int, first_name: str, last_name: str):
        with self._lock:
            self.conn.execute(
                "UPDATE users SET first_name = ?, last_name = ? WHERE id = ?",
                (first_name.strip(), last_name.strip(), user_id),
            )
            self.conn.commit()

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

# ── Semantic search (sentence embeddings) ────────────────────────────────────
# Loaded lazily on first use so the app starts fast even without embeddings.

_embed_model  = None   # SentenceTransformer instance
_embed_matrix = None   # np.ndarray  shape (N, 384), float32, unit-normalised
_embed_ids    = None   # list[int]   course DB ids in the same row order

def _load_embeddings():
    """Load the sentence-transformer model and all stored course embeddings.

    Called once on the first semantic-search request.  Safe to call multiple
    times — subsequent calls are no-ops.
    """
    global _embed_model, _embed_matrix, _embed_ids
    if _embed_model is not None:
        return  # already loaded

    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return  # library not installed — fall back to keyword search silently

    model_name = 'all-MiniLM-L6-v2'
    print(f'Semantic search: loading model {model_name!r} …', flush=True)
    _embed_model = SentenceTransformer(model_name)

    # Pull every row that has a stored embedding
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        rows = conn.execute(
            'SELECT id, embedding FROM courses WHERE embedding IS NOT NULL'
        ).fetchall()
        conn.close()
    except sqlite3.OperationalError as e:
        print(f'Semantic search: DB error ({e}) — run generate_embeddings.py first.')
        _embed_model = None
        return

    if not rows:
        print('Semantic search: no embeddings found in DB — run generate_embeddings.py first.')
        _embed_model = None
        return

    _embed_ids    = [r[0] for r in rows]
    _embed_matrix = np.stack([
        np.frombuffer(r[1], dtype=np.float32) for r in rows
    ])  # shape (N, 384)
    print(f'Semantic search: loaded {len(_embed_ids)} embeddings ({_embed_matrix.nbytes // 1024} KB).')


def _semantic_search(query: str, courses: List[Course], top_n: int = 40) -> List[tuple]:
    """Rank courses by cosine similarity to the query embedding.

    Falls back to keyword search if embeddings are unavailable.
    Returns a list of (score, Course) tuples sorted by descending similarity.
    """
    _load_embeddings()

    if _embed_model is None or _embed_matrix is None:
        # Embeddings not available — fall back gracefully
        return _keyword_search(query, courses, top_n)

    import numpy as np

    # Embed the query (unit-normalised → dot product == cosine similarity)
    q_vec = _embed_model.encode(
        query, convert_to_numpy=True, normalize_embeddings=True
    ).astype(np.float32)

    # Build a fast id→Course lookup restricted to the supplied course list
    course_map = {c.id: c for c in courses}

    # Score only the rows whose course_id is in the supplied list
    # (avoids ranking courses the caller has already excluded)
    valid_mask = [i for i, cid in enumerate(_embed_ids) if cid in course_map]
    if not valid_mask:
        return _keyword_search(query, courses, top_n)

    sub_matrix = _embed_matrix[valid_mask]          # (M, 384)
    sub_ids    = [_embed_ids[i] for i in valid_mask]

    scores = sub_matrix @ q_vec                     # cosine similarity, shape (M,)
    top_indices = scores.argsort()[::-1][:top_n]

    return [(float(scores[i]), course_map[sub_ids[i]]) for i in top_indices]


# ── Year-level appropriateness ────────────────────────────────────────────────
# Maps academic year → (min_course_level, max_course_level)
# e.g. year 1 → only 100-299 level courses; year 4 → 300-599
_YEAR_LEVEL_RANGE: Dict[int, tuple] = {
    1: (100, 299),
    2: (100, 399),
    3: (200, 499),
    4: (300, 599),
    5: (400, 599),
}

def _course_level(course_number: str) -> int:
    """Extract the numeric level from a course number (e.g. 'CS 301' → 301).

    Purdue uses 5-digit course numbers (e.g. 'CS 18000').  Normalize those to
    the equivalent 3-digit level so they compare correctly against
    _YEAR_LEVEL_RANGE (18000 → 180, 25100 → 251, 30700 → 307, etc.).
    """
    m = re.search(r'\d+', course_number)
    if not m:
        return 0
    level = int(m.group())
    if level >= 10000:
        level //= 100
    elif level >= 1000:
        level //= 10
    return level

def _level_ok(course_number: str, year: int) -> bool:
    """Return True if the course's numeric level is appropriate for the given year."""
    lo, hi = _YEAR_LEVEL_RANGE.get(year, _YEAR_LEVEL_RANGE[5])
    return lo <= _course_level(course_number) <= hi


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


# ── LLM planner (Ollama) ─────────────────────────────────────────────────────
#
# Requires Ollama running locally: https://ollama.com
#
# Set the host via environment variable (default: http://localhost:11434):
#   export OLLAMA_HOST="http://localhost:11434"
#
# Falls back to semantic/keyword search automatically when Ollama is not running.

_DEFAULT_OLLAMA_HOST  = 'http://localhost:11434'
_DEFAULT_OLLAMA_MODEL = 'llama3'

class LLMCoursePlanner:
    def __init__(self):
        self.host  = os.environ.get('OLLAMA_HOST', _DEFAULT_OLLAMA_HOST).rstrip('/')
        self.model = None
        self._detect_model()

    def _detect_model(self):
        preferred = os.environ.get('OLLAMA_MODEL', '').strip()
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                if preferred and any(preferred in m for m in models):
                    self.model = preferred
                elif models:
                    # prefer llama3 variants, else first available
                    llama = [m for m in models if 'llama3' in m.lower()]
                    self.model = llama[0] if llama else models[0]
                    print(f"LLM: Ollama detected, using model '{self.model}'")
        except Exception as e:
            print(f"LLM: Ollama not available at {self.host} — {e}")
            self.model = None

    def is_available(self) -> bool:
        if self.model is None:
            self._detect_model()
        return self.model is not None

    def get_recommendations(self, interests: str, completed: List[str],
                            department: str, candidate_courses: List[Course] = None) -> List[dict]:
        """Ask Ollama to pick the 5-8 most relevant courses from the pre-filtered candidate list."""
        if not self.is_available() or not candidate_courses:
            return []

        # Build a compact catalogue block
        course_lines = []
        for c in candidate_courses:
            desc = (c.description or '').replace('\n', ' ')[:80].strip()
            course_lines.append(
                f"{c.course_number}: {c.title}" + (f" — {desc}" if desc else "")
            )

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

        LLM_TIMEOUT = 60

        def _do_ollama_call():
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=LLM_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()['message']['content']

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_do_ollama_call)
                try:
                    text = future.result(timeout=LLM_TIMEOUT + 5)
                except concurrent.futures.TimeoutError:
                    future.cancel()
                    print(f"LLM timed out after {LLM_TIMEOUT}s — using semantic fallback")
                    return []

            # Strip any accidental code fences or think tags
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
            text = re.sub(r'```[a-z]*\n?', '', text)

            start = text.find('[')
            end   = text.rfind(']') + 1
            if start == -1 or end <= start:
                print(f"LLM: no JSON array in response: {text[:300]}")
                return []

            recs = json.loads(text[start:end])
            db   = Database()
            out  = []
            for r in recs:
                c = db.get_course_by_number(r.get('course_number', '').strip())
                if c:
                    out.append({'course': c.to_dict(), 'reason': r.get('reason', ''), 'ai_ranked': True})
                else:
                    print(f"LLM recommended unknown course: {r.get('course_number')}")
            db.close()
            return out

        except Exception as e:
            print(f"LLM error: {e}")
        return []


# ── Flask App ─────────────────────────────────────────────────────────────────

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(__file__), 'frontend', 'dist'),
            static_url_path='')
CORS(app)
_db = Database()
_llm = LLMCoursePlanner()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _make_token(user_id: int, email: str) -> str:
    import time
    payload = {
        'sub': str(user_id),
        'email': email,
        'exp': int(time.time()) + JWT_EXP_DAYS * 24 * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        token = auth[7:].strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            g.user_id = int(payload['sub'])
            g.user_email = payload['email']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError as e:
            print(f"[AUTH] Invalid token ({type(e).__name__}): {e}")
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    body = request.get_json(force=True)
    email      = (body.get('email')      or '').strip().lower()
    password   = (body.get('password')   or '')
    first_name = (body.get('first_name') or '').strip()
    last_name  = (body.get('last_name')  or '').strip()
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    if not first_name or not last_name:
        return jsonify({'error': 'First name and last name are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if _db.get_user_by_email(email):
        return jsonify({'error': 'Email already registered'}), 409
    password_hash = generate_password_hash(password)
    user_id = _db.create_user(email, password_hash, first_name, last_name)
    token = _make_token(user_id, email)
    return jsonify({'token': token, 'user': {
        'id': user_id, 'email': email,
        'first_name': first_name, 'last_name': last_name,
    }}), 201


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    body = request.get_json(force=True)
    email = (body.get('email') or '').strip().lower()
    password = body.get('password') or ''
    user = _db.get_user_by_email(email)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid email or password'}), 401
    token = _make_token(user['id'], user['email'])
    return jsonify({'token': token, 'user': {
        'id': user['id'], 'email': user['email'],
        'first_name': user.get('first_name', ''), 'last_name': user.get('last_name', ''),
    }})


@app.route('/api/auth/me')
@require_auth
def auth_me():
    user = _db.get_user_by_id(g.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user)


@app.route('/api/auth/me', methods=['PATCH'])
@require_auth
def update_me():
    body       = request.get_json(force=True)
    first_name = (body.get('first_name') or '').strip()
    last_name  = (body.get('last_name')  or '').strip()
    if not first_name or not last_name:
        return jsonify({'error': 'First name and last name are required'}), 400
    _db.update_user(g.user_id, first_name, last_name)
    user = _db.get_user_by_id(g.user_id)
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
        plan_type=body.get('plan_type', 'single'),
        secondary_department=body.get('secondary_department', ''),
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


@app.route('/api/plans/<int:plan_id>', methods=['PATCH'])
@require_auth
def update_plan(plan_id):
    plan = _db.get_plan(plan_id)
    if not plan:
        return jsonify({'error': 'Not found'}), 404
    if plan.get('user_id') != g.user_id:
        return jsonify({'error': 'Forbidden'}), 403
    body = request.get_json(force=True)
    name = (body.get('name') or plan['name']).strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    _db.update_plan(
        plan_id,
        name=name,
        duration_years=int(body.get('duration_years', plan['duration_years'])),
        start_year=int(body.get('start_year', plan['start_year'])),
        department=body.get('department', plan['department']),
        plan_type=body.get('plan_type', plan.get('plan_type', 'single')),
        secondary_department=body.get('secondary_department', plan.get('secondary_department', '')),
    )
    return jsonify(_db.get_plan(plan_id))


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
    return jsonify({
        'available':         _llm.is_available(),
        'model':             _llm.model if _llm.is_available() else None,
        'provider':          'ollama',
        'semantic_search':   _embed_matrix is not None,
        'embeddings_count':  len(_embed_ids) if _embed_ids else 0,
    })


@app.route('/api/ai/recommend', methods=['POST'])
def ai_recommend():
    body       = request.get_json(force=True)
    interests  = (body.get('interests') or '').strip()
    completed  = body.get('completed_courses', [])
    department = body.get('department', 'CS')

    if not interests:
        return jsonify([])

    all_courses = _db.get_all_courses()

    # ── Phase 1: semantic search across ALL 6 000+ courses ───────────────────
    # Uses sentence embeddings when available, falls back to keyword matching.
    keyword_hits = _semantic_search(interests, all_courses, top_n=40)

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
        recs = _llm.get_recommendations(interests, completed, department, candidates[:25])
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

        # Split into level-appropriate vs overdue (below this year's min level,
        # meaning they should have been placed earlier — still schedule them so
        # required courses are never silently dropped).  Skip courses that are
        # too advanced for this year; they will be picked up in a later semester.
        lo, hi = _YEAR_LEVEL_RANGE.get(year, _YEAR_LEVEL_RANGE[5])
        preferred  = [(cn, c) for cn, c in ready if lo <= _course_level(cn) <= hi]
        overdue    = [(cn, c) for cn, c in ready if _course_level(cn) < lo]
        # courses whose level exceeds hi are intentionally deferred

        sem_courses: List[Course] = []
        sem_credits = 0

        for cn, course in preferred + overdue:
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
    body             = request.get_json(force=True)
    interests        = (body.get('interests') or '').strip()
    completed        = body.get('completed_courses', [])
    transfer_credits = body.get('transfer_credits', [])   # course numbers already earned via transfer
    department       = body.get('department', 'CS')
    duration         = max(1, min(int(body.get('duration_years', 4)), 8))
    max_credits      = max(9, min(int(body.get('max_credits_per_semester', 15)), 22))
    start_year       = int(body.get('start_year', 2025))

    # Transfer credits are treated exactly like completed courses — exclude from plan
    completed_set = set(completed) | set(transfer_credits)

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
    # Program plan uses fast keyword ranking only — LLM re-ranking is skipped
    # here to keep generation instant. LLM is used in the "Find Courses" tab.
    ai_elective_reasons: Dict[str, str] = {}
    ai_ranked_plan = False

    if interests:
        all_courses   = _db.get_all_courses()
        excluded      = set(courses_to_schedule.keys()) | completed_set
        elective_pool = [c for c in all_courses if c.course_number not in excluded]
        elective_hits = _semantic_search(interests, elective_pool, top_n=40)
        electives: List[Course] = [c for _, c in elective_hits]

        # Build a per-semester elective pool sorted by level appropriateness,
        # so we never place a 400-level elective in year 1, etc.
        remaining_electives = list(electives)

        # First pass: fill existing semesters that have room
        for sem in semesters:
            sem_year = sem['year']
            # Pick only electives whose level fits this year
            fitting     = [e for e in remaining_electives if _level_ok(e.course_number, sem_year)]
            non_fitting = [e for e in remaining_electives if not _level_ok(e.course_number, sem_year)]
            added_this_sem: List[Course] = []
            for ec in fitting:
                if sem['credits'] + ec.credits <= max_credits:
                    sem['courses'].append(ec)
                    sem['credits'] += ec.credits
                    excluded.add(ec.course_number)
                    added_this_sem.append(ec)
            added_set = {e.course_number for e in added_this_sem}
            remaining_electives = [e for e in remaining_electives if e.course_number not in added_set]

        # Second pass: open new semesters for remaining electives
        total_slots = duration * 2
        while remaining_electives and len(semesters) < total_slots:
            sem_idx     = len(semesters)
            year        = (sem_idx // 2) + 1
            semester    = (sem_idx % 2) + 1
            fitting     = [e for e in remaining_electives if _level_ok(e.course_number, year)]
            sem_courses: List[Course] = []
            sem_credits = 0
            added_this_sem = []
            for ec in fitting:
                if sem_credits + ec.credits <= max_credits:
                    sem_courses.append(ec)
                    sem_credits += ec.credits
                    added_this_sem.append(ec)
            added_set = {e.course_number for e in added_this_sem}
            remaining_electives = [e for e in remaining_electives if e.course_number not in added_set]
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


# ── Plan Sharing ──────────────────────────────────────────────────────────────

@app.route('/api/plans/<int:plan_id>/share', methods=['POST'])
@require_auth
def create_share_link(plan_id):
    plan = _db.get_plan(plan_id)
    if not plan:
        return jsonify({'error': 'Not found'}), 404
    if plan.get('user_id') != g.user_id:
        return jsonify({'error': 'Forbidden'}), 403
    # Return existing token if already shared, otherwise generate a new one
    token = plan.get('share_token') or _db.generate_share_token(plan_id)
    return jsonify({'share_token': token})


@app.route('/api/plans/<int:plan_id>/share', methods=['DELETE'])
@require_auth
def revoke_share_link(plan_id):
    plan = _db.get_plan(plan_id)
    if not plan:
        return jsonify({'error': 'Not found'}), 404
    if plan.get('user_id') != g.user_id:
        return jsonify({'error': 'Forbidden'}), 403
    _db.revoke_share_token(plan_id)
    return jsonify({'ok': True})


@app.route('/api/shared/<token>', methods=['GET'])
def get_shared_plan(token):
    plan = _db.get_plan_by_share_token(token)
    if not plan:
        return jsonify({'error': 'Shared plan not found or link has been revoked'}), 404
    # Exclude internal fields
    return jsonify({k: v for k, v in plan.items() if k != 'user_id'})


@app.route('/api/shared/<token>/courses', methods=['GET'])
def get_shared_plan_courses(token):
    plan = _db.get_plan_by_share_token(token)
    if not plan:
        return jsonify({'error': 'Shared plan not found or link has been revoked'}), 404
    pcs = _db.get_plan_courses(plan['id'])
    return jsonify([pc.to_dict() for pc in pcs])


# ── PDF Export ────────────────────────────────────────────────────────────────

GRADE_POINTS = {
    'A+': 4.0, 'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'D-': 0.7,
    'F':  0.0,
}


def _calc_gpa(items):  # items: list of (credits, grade)
    total_pts, total_cr = 0.0, 0
    for credits, grade in items:
        pts = GRADE_POINTS.get((grade or '').strip().upper())
        if pts is not None:
            total_pts += pts * credits
            total_cr  += credits
    return round(total_pts / total_cr, 2) if total_cr else None


def _to_rel_year(year_val, plan):
    duration   = plan.get('duration_years', 4)
    start_year = plan.get('start_year', 2024)
    if year_val > duration:
        rel = year_val - start_year + 1
        return max(1, min(duration, rel))
    return year_val


def _generate_plan_pdf(plan: dict, plan_courses: List[PlanCourse], user_email: str = '') -> bytes:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from io import BytesIO
    except ImportError:
        raise RuntimeError('reportlab is not installed. Run: pip install reportlab')

    # ── Colours ────────────────────────────────────────────────────────────────
    GOLD      = HexColor('#CFB991')
    DARK      = HexColor('#1a1a2e')
    MUTED     = HexColor('#6b7280')
    PLANNED   = HexColor('#9ca3af')
    IN_PROG   = HexColor('#f59e0b')
    COMPLETED = HexColor('#22c55e')
    ROW_ALT   = HexColor('#f9fafb')
    BORDER    = HexColor('#e5e7eb')

    STATUS_LABEL = {'planned': 'Planned', 'in_progress': 'In Progress', 'completed': 'Completed'}
    STATUS_COLOR = {'planned': PLANNED, 'in_progress': IN_PROG, 'completed': COMPLETED}
    TERM         = {1: 'Fall', 2: 'Spring', 3: 'Summer'}

    buf  = BytesIO()
    doc  = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.65 * inch, rightMargin=0.65 * inch,
        topMargin=0.75 * inch, bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'PlanTitle', parent=styles['Title'],
        fontSize=20, textColor=DARK, spaceAfter=4, leading=24,
        alignment=0,  # left-align
    )
    sub_style = ParagraphStyle(
        'PlanSub', parent=styles['Normal'],
        fontSize=9, textColor=MUTED, spaceAfter=2,
    )
    name_style = ParagraphStyle(
        'PlanName', parent=title_style,
        alignment=2,  # right-align; everything else inherited from title_style
    )
    sub_style_right = ParagraphStyle(
        'PlanSubRight', parent=styles['Normal'],
        fontSize=9, textColor=MUTED, spaceAfter=2,
        alignment=2,  # right-align
    )
    year_style = ParagraphStyle(
        'YearHeader', parent=styles['Normal'],
        fontSize=8, textColor=MUTED, fontName='Helvetica-Bold',
        spaceBefore=14, spaceAfter=4, textTransform='uppercase',
    )
    sem_style = ParagraphStyle(
        'SemHeader', parent=styles['Normal'],
        fontSize=10, textColor=white, fontName='Helvetica-Bold',
        spaceAfter=0,
    )
    stat_style = ParagraphStyle(
        'Stat', parent=styles['Normal'],
        fontSize=8, textColor=MUTED, spaceAfter=2,
    )

    # ── Derived plan data ──────────────────────────────────────────────────────
    duration   = plan.get('duration_years', 4)
    start_year = plan.get('start_year', 2024)

    # Normalise year values and build slot map
    slot_map: dict = {}
    for pc in plan_courses:
        yr  = _to_rel_year(pc.year, plan)
        key = (yr, pc.semester)
        slot_map.setdefault(key, []).append(pc)

    total_credits     = sum(pc.course.credits for pc in plan_courses)
    completed_credits = sum(
        pc.course.credits for pc in plan_courses if pc.status == 'completed'
    )
    overall_gpa = _calc_gpa([
        (pc.course.credits, pc.grade)
        for pc in plan_courses if pc.status == 'completed'
    ])

    has_summer    = any(pc.semester == 3 for pc in plan_courses)
    sem_types     = [1, 2, 3] if has_summer else [1, 2]

    def sem_label(year, semester):
        cal = start_year + (year - 1) + (1 if semester == 2 else 0)
        return f"{TERM[semester]} {cal}"

    # ── Build cumulative GPA map ───────────────────────────────────────────────
    cum_accum: list = []
    cum_gpa_map: dict = {}
    sem_gpa_map: dict = {}
    for yr in range(1, duration + 1):
        for sem in sem_types:
            courses = slot_map.get((yr, sem), [])
            sem_items = [
                (pc.course.credits, pc.grade)
                for pc in courses if pc.status == 'completed'
            ]
            sem_gpa_map[(yr, sem)] = _calc_gpa(sem_items)
            cum_accum.extend(sem_items)
            cum_gpa_map[(yr, sem)] = _calc_gpa(cum_accum)

    # ── Build story ────────────────────────────────────────────────────────────
    story = []

    # Header block
    full_name = ''
    if user_email:
        user_rec = _db.get_user_by_email(user_email)
        if user_rec:
            full_name = f"{user_rec.get('first_name', '')} {user_rec.get('last_name', '')}".strip()

    plan_type   = plan.get('plan_type', 'single')
    secondary   = (plan.get('secondary_department') or '').strip()
    primary_dept = plan.get('department', '')
    if plan_type == 'double_major' and secondary:
        dept_label = f"{primary_dept} & {secondary} (Double Major)"
    elif plan_type == 'major_minor' and secondary:
        dept_label = f"{primary_dept} + {secondary} (Minor)"
    else:
        dept_label = primary_dept
    sub_line = f"{dept_label} · {duration}-Year Plan · {start_year}–{start_year + duration - 1}"

    # Two-column header: plan info left, owner info right
    left_cell  = [Paragraph(plan.get('name', 'Course Plan'), title_style),
                  Paragraph(sub_line, sub_style)]
    right_cell = []
    if full_name:
        right_cell.append(Paragraph(full_name, name_style))
    if user_email:
        right_cell.append(Paragraph(user_email, sub_style_right))

    if right_cell:
        header_tbl = Table([[left_cell, right_cell]], colWidths=['55%', '45%'])
        header_tbl.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(header_tbl)
    else:
        story.append(Paragraph(plan.get('name', 'Course Plan'), title_style))
        story.append(Paragraph(sub_line, sub_style))

    story.append(HRFlowable(width='100%', thickness=2, color=GOLD, spaceAfter=8))

    # Summary row
    transfer_cr_total = sum(
        pc.course.credits for pc in plan_courses if pc.year == 0 and pc.semester == 0
    )
    gpa_str = f"{overall_gpa:.2f}" if overall_gpa is not None else '—'
    if transfer_cr_total:
        summary_data = [['Transfer Credits', 'Credits Planned', 'Credits Completed', 'Cumulative GPA', 'Generated']]
        summary_data.append([
            str(transfer_cr_total),
            str(total_credits),
            str(completed_credits),
            gpa_str,
            datetime.now().strftime('%B %d, %Y'),
        ])
    else:
        summary_data = [['Credits Planned', 'Credits Completed', 'Cumulative GPA', 'Generated']]
        summary_data.append([
            str(total_credits),
            str(completed_credits),
            gpa_str,
            datetime.now().strftime('%B %d, %Y'),
        ])
    summary_table = Table(summary_data, colWidths=['*'] * len(summary_data[0]))
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR',   (0, 0), (-1, 0), GOLD),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, 0), 8),
        ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME',    (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 1), (-1, 1), 12),
        ('TEXTCOLOR',   (0, 1), (-1, 1), DARK),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f3f4f6')]),
        ('TOPPADDING',  (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID',        (0, 0), (-1, -1), 0.5, BORDER),
        ('ROUNDEDCORNERS', [4]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # Transfer credits section
    transfer_courses = [pc for pc in plan_courses if pc.year == 0 and pc.semester == 0]
    if transfer_courses:
        transfer_credits = sum(pc.course.credits for pc in transfer_courses)
        story.append(Paragraph('TRANSFER CREDITS', year_style))

        xfer_hdr_data = [[
            Paragraph(f"Transfer Credits  —  {transfer_credits} cr", sem_style)
        ]]
        xfer_hdr_tbl = Table(xfer_hdr_data, colWidths=[page_w if 'page_w' in dir() else (letter[0] - 1.30 * inch)])
        # page_w not defined yet — compute inline
        _pw = letter[0] - 1.30 * inch
        xfer_hdr_tbl = Table(xfer_hdr_data, colWidths=[_pw])
        xfer_hdr_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), HexColor('#92400e')),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ]))
        story.append(xfer_hdr_tbl)

        _col_w = [1.1 * inch, _pw - 1.1 * inch - 0.48 * inch - 0.85 * inch - 0.48 * inch,
                  0.48 * inch, 0.85 * inch, 0.48 * inch]
        xfer_data = [['Course', 'Title', 'Cr', 'Status', 'Grade']]
        for pc in sorted(transfer_courses, key=lambda x: x.course.course_number):
            xfer_data.append([
                pc.course.course_number,
                pc.course.title,
                str(pc.course.credits),
                'Transfer',
                pc.grade or '—',
            ])
        xfer_tbl = Table(xfer_data, colWidths=_col_w)
        xfer_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), HexColor('#374151')),
            ('TEXTCOLOR',     (0, 0), (-1, 0), GOLD),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, 0), 7.5),
            ('ALIGN',         (2, 0), (4, -1), 'CENTER'),
            ('FONTSIZE',      (0, 1), (-1, -1), 8),
            ('FONTNAME',      (0, 1), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR',     (3, 1), (3, -1), HexColor('#16a34a')),
            ('FONTNAME',      (3, 1), (3, -1), 'Helvetica-Bold'),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
            ('GRID',          (0, 0), (-1, -1), 0.4, BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, ROW_ALT]),
        ]))
        story.append(xfer_tbl)
        story.append(Spacer(1, 16))

    # Semester grids
    page_w = letter[0] - 1.30 * inch  # usable width
    col_widths = [1.1 * inch, None, 0.48 * inch, 0.85 * inch, 0.48 * inch]
    # title column takes remaining space
    col_widths[1] = page_w - sum(w for w in col_widths if w is not None)

    for yr in range(1, duration + 1):
        story.append(Paragraph(
            f"YEAR {yr}  ·  {start_year + yr - 1}–{start_year + yr}",
            year_style,
        ))

        for sem in sem_types:
            courses = sorted(
                slot_map.get((yr, sem), []),
                key=lambda pc: pc.course.course_number,
            )
            total_cr  = sum(pc.course.credits for pc in courses)
            sem_gpa   = sem_gpa_map.get((yr, sem))
            cum_gpa   = cum_gpa_map.get((yr, sem))

            # Semester header
            gpa_parts = []
            if sem_gpa is not None:
                gpa_parts.append(f"Sem GPA {sem_gpa:.2f}")
            if cum_gpa is not None:
                gpa_parts.append(f"Cum GPA {cum_gpa:.2f}")
            gpa_suffix = f"  |  {' · '.join(gpa_parts)}" if gpa_parts else ''

            sem_hdr_data = [[
                Paragraph(
                    f"{sem_label(yr, sem)}  —  {total_cr} cr{gpa_suffix}",
                    sem_style,
                )
            ]]
            sem_hdr_tbl = Table(sem_hdr_data, colWidths=[page_w])
            sem_hdr_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), DARK),
                ('TOPPADDING',    (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING',   (0, 0), (-1, -1), 10),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
            ]))
            story.append(sem_hdr_tbl)

            if not courses:
                no_courses_data = [['No courses planned for this semester.']]
                no_courses_tbl = Table(no_courses_data, colWidths=[page_w])
                no_courses_tbl.setStyle(TableStyle([
                    ('TEXTCOLOR',     (0, 0), (-1, -1), MUTED),
                    ('FONTSIZE',      (0, 0), (-1, -1), 8),
                    ('FONTNAME',      (0, 0), (-1, -1), 'Helvetica-Oblique'),
                    ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
                    ('TOPPADDING',    (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID',          (0, 0), (-1, -1), 0.5, BORDER),
                ]))
                story.append(no_courses_tbl)
            else:
                # Column headers
                tbl_data = [['Course', 'Title', 'Cr', 'Status', 'Grade']]
                for i, pc in enumerate(courses):
                    status_col = STATUS_LABEL.get(pc.status, pc.status)
                    tbl_data.append([
                        pc.course.course_number,
                        pc.course.title,
                        str(pc.course.credits),
                        status_col,
                        pc.grade or '—',
                    ])

                course_tbl = Table(tbl_data, colWidths=col_widths)

                # Build per-row status colour stripes
                row_styles = [
                    ('BACKGROUND',    (0, 0), (-1, 0), HexColor('#374151')),
                    ('TEXTCOLOR',     (0, 0), (-1, 0), GOLD),
                    ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE',      (0, 0), (-1, 0), 7.5),
                    ('ALIGN',         (2, 0), (4, -1), 'CENTER'),
                    ('FONTSIZE',      (0, 1), (-1, -1), 8),
                    ('FONTNAME',      (0, 1), (0, -1), 'Helvetica-Bold'),
                    ('TOPPADDING',    (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
                    ('GRID',          (0, 0), (-1, -1), 0.4, BORDER),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, ROW_ALT]),
                ]
                for row_idx, pc in enumerate(courses, start=1):
                    status_c = STATUS_COLOR.get(pc.status, MUTED)
                    # coloured left border via a thin left-column background isn't
                    # directly supported, so tint the status cell instead
                    row_styles.append(('TEXTCOLOR', (3, row_idx), (3, row_idx), status_c))
                    row_styles.append(('FONTNAME',  (3, row_idx), (3, row_idx), 'Helvetica-Bold'))

                course_tbl.setStyle(TableStyle(row_styles))
                story.append(course_tbl)

            story.append(Spacer(1, 8))

    doc.build(story)
    return buf.getvalue()


@app.route('/api/plans/<int:plan_id>/pdf', methods=['GET'])
@require_auth
def download_plan_pdf(plan_id):
    from flask import send_file
    from io import BytesIO

    plan = _db.get_plan(plan_id)
    if not plan:
        return jsonify({'error': 'Not found'}), 404
    if plan.get('user_id') != g.user_id:
        return jsonify({'error': 'Forbidden'}), 403

    plan_courses = _db.get_plan_courses(plan_id)

    try:
        pdf_bytes = _generate_plan_pdf(plan, plan_courses, user_email=g.user_email)
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500

    safe_name = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_'
                        for c in plan.get('name', 'plan')).strip().replace(' ', '_')
    filename  = f"{safe_name}_course_plan.pdf"

    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


# ── Frontend catch-all (serves React for any non-API route) ──────────────────

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the React SPA for all non-API routes."""
    dist = app.static_folder
    # Serve the file directly if it exists (JS, CSS, assets, etc.)
    full = os.path.join(dist, path)
    if path and os.path.exists(full):
        return app.send_static_file(path)
    # Fall back to index.html so React Router handles the route
    return app.send_static_file('index.html')


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    print(f"Purdue Course Planner running at http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
