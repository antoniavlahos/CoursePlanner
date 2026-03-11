import sqlite3
import json
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, List, Dict
import urllib.request
import urllib.error
# database path
DB_PATH = "purdue_courses.db"

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

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def get_all_courses(self) -> List[Course]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM courses ORDER BY course_number")
        rows = cursor.fetchall()
        return [self._row_to_course(row) for row in rows]
    
    def get_courses_by_department(self, dept: str) -> List[Course]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE department = ? ORDER BY course_number", (dept,))
        rows = cursor.fetchall()
        return [self._row_to_course(row) for row in rows]
    
    def search_courses(self, query: str) -> List[Course]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM courses 
            WHERE course_number LIKE ? OR title LIKE ?
            ORDER BY course_number
        """, (f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        return [self._row_to_course(row) for row in rows]
    
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
    
    def get_all_departments(self) -> List[tuple]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT code, name, required_credits, required_courses FROM departments ORDER BY code")
        return cursor.fetchall()
    
    def get_department_requirements(self, dept_code: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM departments WHERE code = ?", (dept_code,))
        row = cursor.fetchone()
        if row:
            return {
                'code': row['code'],
                'name': row['name'],
                'required_credits': row['required_credits'],
                'required_courses': json.loads(row['required_courses']) if row['required_courses'] else []
            }
        return None
    
    def get_university_requirements(self) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM university_requirements")
        rows = cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'category': row['category'],
                'credits_required': row['credits_required'],
                'courses_required': json.loads(row['courses_required']) if row['courses_required'] else [],
                'minimum_grade': row['minimum_grade']
            })
        return results
    
    def create_plan(self, name: str, duration_years: int, start_year: int, department: str) -> int:
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO plans (name, duration_years, start_year, department, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, duration_years, start_year, department, now, now))
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
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_plan(self, plan_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM plan_courses WHERE plan_id = ?", (plan_id,))
        cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        self.conn.commit()
    
    def add_course_to_plan(self, plan_id: int, course_id: int, semester: int, 
                           year: int, semester_type: str = "regular") -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO plan_courses (plan_id, course_id, semester, year, semester_type, status)
            VALUES (?, ?, ?, ?, ?, 'planned')
        """, (plan_id, course_id, semester, year, semester_type))
        self.conn.commit()
        return cursor.lastrowid
    
    def remove_course_from_plan(self, plan_course_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM plan_courses WHERE id = ?", (plan_course_id,))
        self.conn.commit()
    
    def update_course_status(self, plan_course_id: int, status: str, grade: str = None):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE plan_courses 
            SET status = ?, grade = ?
            WHERE id = ?
        """, (status, grade, plan_course_id))
        self.conn.commit()
    
    def update_semester_type(self, plan_id: int, year: int, semester: int, semester_type: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE plan_courses 
            SET semester_type = ?
            WHERE plan_id = ? AND year = ? AND semester = ?
        """, (semester_type, plan_id, year, semester))
        self.conn.commit()
    
    def get_plan_courses(self, plan_id: int) -> List[PlanCourse]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pc.id, pc.semester, pc.year, pc.status, pc.grade, pc.semester_type,
                   c.id, c.course_number, c.title, c.description, c.credits,
                   c.department, c.prerequisites, c.corequisites, c.terms_offered
            FROM plan_courses pc
            JOIN courses c ON pc.course_id = c.id
            WHERE pc.plan_id = ?
            ORDER BY pc.year, pc.semester
        """, (plan_id,))
        
        results = []
        for row in cursor.fetchall():
            course = Course(
                id=row[6], course_number=row[7], title=row[8], 
                description=row[9], credits=row[10], department=row[11],
                prerequisites=json.loads(row[12]), corequisites=json.loads(row[13]),
                terms_offered=json.loads(row[14])
            )
            results.append(PlanCourse(row[0], course, row[1], row[2], row[3], row[4], row[5]))
        return results
    
    def get_plan_courses_by_semester(self, plan_id: int) -> Dict[int, List[PlanCourse]]:
        courses = self.get_plan_courses(plan_id)
        result = {}
        for pc in courses:
            key = pc.year * 10 + pc.semester
            if key not in result:
                result[key] = []
            result[key].append(pc)
        return result
    
    def _row_to_course(self, row) -> Course:
        try:
            is_req = row['is_required']
        except (KeyError, IndexError):
            is_req = 0
        return Course(
            id=row['id'], course_number=row['course_number'], title=row['title'],
            description=row['description'], credits=row['credits'],
            department=row['department'],
            prerequisites=json.loads(row['prerequisites']) if row['prerequisites'] else [],
            corequisites=json.loads(row['corequisites']) if row['corequisites'] else [],
            terms_offered=json.loads(row['terms_offered']) if row['terms_offered'] else [],
            is_required=is_req
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
            import urllib.request
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get('models', [])
                if models:
                    self.model = models[0]['name']
                    print(f"Using model: {self.model}")
        except Exception as e:
            print(f"Could not get model list: {e}")
    
    def is_available(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception as e:
            print(f"Ollama not available: {e}")
            return False
    
    def get_course_recommendations(self, interests: str, completed_courses: List[str], 
                                   department: str) -> List[dict]:
        if not self.is_available():
            return []
        
        courses_db = Database()
        all_courses = courses_db.get_all_courses()
        
        course_list = []
        for c in all_courses:
            course_list.append({
                'number': c.course_number,
                'title': c.title,
                'credits': c.credits,
                'department': c.department,
                'prerequisites': c.prerequisites,
                'description': c.description[:100]
            })
        
        prompt = f"""You are a Purdue University academic advisor. A student in {department} major has these interests: {interests}

Completed courses: {', '.join(completed_courses) if completed_courses else 'none'}

Recommend 5-8 courses from this list that match their interests:
CS 18000, CS 18200, CS 24000, CS 25000, CS 25100, CS 30700, CS 35400, CS 35500, CS 37300, CS 40800, CS 42600, CS 43000, CS 45600, CS 47800, MA 16100, MA 16200, MA 26100, MA 35100, MA 36600, STAT 35000, PHYS 17200, PHYS 27200, ECON 11000, PSY 10000

Consider prerequisites and their career goals.

Respond ONLY with JSON array: [{{"course_number": "XX 00000", "reason": "brief reason"}}, ...]"""

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                response_text = result.get('response', '')
                
                start = response_text.find('[')
                end = response_text.rfind(']') + 1
                
                if start != -1 and end > start:
                    recommendations = json.loads(response_text[start:end])
                    
                    valid_recommendations = []
                    for rec in recommendations:
                        course = courses_db.get_course_by_number(rec.get('course_number', ''))
                        if course:
                            valid_recommendations.append({
                                'course': course,
                                'reason': rec.get('reason', '')
                            })
                    return valid_recommendations
                    
        except Exception as e:
            print(f"LLM Error: {e}")
        
        courses_db.close()
        return []


class CoursePlannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Purdue Course Planner")
        self.root.geometry("1400x900")
        self.root.configure(bg="#F8F9FA")
        
        self.db = Database()
        self.current_plan_id = None
        self.current_plan_duration = 4
        self.current_plan_department = "CS"
        self.current_plan_start_year = 2024
        
        self.llm_planner = LLMCoursePlanner()
        
        self._setup_styles()
        self._create_layout()
        self._load_initial_data()
        
        plans = self.db.get_all_plans()
        if plans:
            for plan in plans:
                courses = self.db.get_plan_courses(plan['id'])
                if courses:
                    self.current_plan_id = plan['id']
                    self.current_plan_duration = plan['duration_years']
                    self.current_plan_department = plan['department']
                    self.current_plan_start_year = plan['start_year']
                    self.plan_label.config(text=f"Plan: {plan['name']} ({plan['duration_years']}yr, {plan['department']})")
                    break
            if not self.current_plan_id and plans:
                self.current_plan_id = plans[0]['id']
                self.current_plan_duration = plans[0]['duration_years']
                self.current_plan_department = plans[0]['department']
                self.current_plan_start_year = plans[0]['start_year']
                self.plan_label.config(text=f"Plan: {plans[0]['name']} ({plans[0]['duration_years']}yr, {plans[0]['department']})")
    
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Title.TLabel', font=('Roboto Slab', 24, 'bold'), 
                       background='#F8F9FA', foreground='#0A2463')
        style.configure('Heading.TLabel', font=('Roboto Slab', 16, 'bold'),
                       background='#F8F9FA', foreground='#0A2463')
        style.configure('Subheading.TLabel', font=('Roboto', 14, 'bold'),
                       background='#F8F9FA', foreground='#1A1A1A')
        style.configure('Body.TLabel', font=('Roboto', 12),
                       background='#F8F9FA', foreground='#1A1A1A')
        style.configure('CourseNumber.TLabel', font=('Fira Code', 11, 'bold'),
                       background='#FFFFFF', foreground='#0A2463')
    
    def _create_layout(self):
        self.main_container = ttk.Frame(self.root, style='Card.TFrame')
        self.main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        self._create_sidebar()
        self._create_content_area()
        
        self.sidebar_frame.pack(side='left', fill='y', padx=(0, 10))
        self.content_frame.pack(side='left', fill='both', expand=True)
        
        self._show_catalog_view()
    
    def _create_sidebar(self):
        self.sidebar_frame = tk.Frame(self.main_container, bg='#0A2463', width=280)
        self.sidebar_frame.pack_propagate(False)
        
        title_label = tk.Label(self.sidebar_frame, text="Purdue\nCourse Planner",
                              font=('Roboto Slab', 20, 'bold'), bg='#0A2463', 
                              fg='#FFDD00', justify='center')
        title_label.pack(pady=(20, 10))
        
        self.nav_buttons = {}
        
        nav_items = [
            ("Course Catalog", self._show_catalog_view),
            ("My Plan", self._show_plan_view),
            ("Requirements", self._show_requirements_view),
            ("AI Planner", self._show_ai_planner_view),
            ("Settings", self._show_settings_view)
        ]
        
        for text, cmd in nav_items:
            btn = tk.Button(self.sidebar_frame, text=text, font=('Roboto', 13),
                           bg='#1A3A7A', fg='white', relief='flat', bd=0,
                           pady=12, padx=20, cursor='hand2', anchor='w',
                           command=cmd)
            btn.pack(fill='x', padx=10, pady=2)
            self.nav_buttons[text] = btn
        
        separator = tk.Frame(self.sidebar_frame, bg='#FFDD00', height=2)
        separator.pack(fill='x', padx=20, pady=20)
        
        self.plan_info_frame = tk.Frame(self.sidebar_frame, bg='#0A2463')
        self.plan_info_frame.pack(fill='x', padx=20, pady=10)
        
        self.plan_label = tk.Label(self.plan_info_frame, text="No Plan Selected",
                                  font=('Roboto', 11), bg='#0A2463', fg='white')
        self.plan_label.pack()
        
        tk.Button(self.sidebar_frame, text="+ Create New Plan", 
                 font=('Roboto', 12, 'bold'), bg='#FFDD00', fg='#0A2463',
                 relief='flat', pady=8, cursor='hand2',
                 command=self._create_new_plan).pack(fill='x', padx=20, pady=10)
        
        tk.Button(self.sidebar_frame, text="Load Existing Plan", 
                 font=('Roboto', 11), bg='#C8102E', fg='white',
                 relief='flat', pady=8, cursor='hand2',
                 command=self._load_existing_plan).pack(fill='x', padx=20, pady=5)
    
    def _create_content_area(self):
        self.content_frame = tk.Frame(self.main_container, bg='#F8F9FA')
        
        self.header_frame = tk.Frame(self.content_frame, bg='#F8F9FA')
        self.header_frame.pack(fill='x', pady=(0, 15))
        
        self.view_title = tk.Label(self.header_frame, text="Course Catalog",
                                  font=('Roboto Slab', 24, 'bold'), bg='#F8F9FA',
                                  fg='#0A2463')
        self.view_title.pack(side='left')
        
        self.search_frame = tk.Frame(self.content_frame, bg='#F8F9FA')
        self.search_frame.pack(fill='x', pady=(0, 15))
        
        self.search_entry = tk.Entry(self.search_frame, font=('Roboto', 12),
                                     fg='#1A1A1A', bg='white', relief='flat',
                                     insertbackground='#0A2463')
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.search_entry.insert(0, "Search courses...")
        self.search_entry.bind('<FocusIn>', lambda e: self._on_search_focus(e, True))
        self.search_entry.bind('<FocusOut>', lambda e: self._on_search_focus(e, False))
        self.search_entry.bind('<KeyRelease>', lambda e: self._on_search())
        
        self.dept_filter = ttk.Combobox(self.search_frame, font=('Roboto', 11),
                                         state='readonly', width=15)
        self.dept_filter.pack(side='left', padx=5)
        
        tk.Button(self.search_frame, text="Search", font=('Roboto', 11),
                 bg='#0A2463', fg='white', relief='flat', padx=15, pady=5,
                 cursor='hand2', command=self._on_search).pack(side='left')
        
        self.content_container = tk.Frame(self.content_frame, bg='#F8F9FA')
        self.content_container.pack(fill='both', expand=True)
    
    def _load_initial_data(self):
        self.courses = self.db.get_all_courses()
        self.departments = self.db.get_all_departments()
        
        dept_codes = ["All Departments"] + [d[0] for d in self.departments]
        self.dept_filter['values'] = dept_codes
        self.dept_filter.current(0)
        self.dept_filter.bind('<<ComboboxSelected>>', lambda e: self._on_search())
    
    def _on_search_focus(self, event, focused):
        if focused and self.search_entry.get() == "Search courses...":
            self.search_entry.delete(0, 'end')
        elif not focused and self.search_entry.get() == "":
            self.search_entry.insert(0, "Search courses...")
    
    def _on_search(self):
        query = self.search_entry.get()
        if query == "Search courses...":
            query = ""
        
        dept = self.dept_filter.get()
        
        if query:
            results = self.db.search_courses(query)
        elif dept and dept != "All Departments":
            results = self.db.get_courses_by_department(dept)
        else:
            results = self.db.get_all_courses()
        
        self._display_courses(results)
    
    def _display_courses(self, courses):
        for widget in self.content_container.winfo_children():
            widget.destroy()
        
        canvas_frame = tk.Frame(self.content_container, bg='#F8F9FA')
        canvas_frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg='#F8F9FA', highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        scrollable = tk.Frame(canvas, bg='#F8F9FA')
        
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        row = 0
        for course in courses:
            card = self._create_course_card(scrollable, course)
            card.grid(row=row, column=0, sticky='ew', padx=5, pady=5)
            row += 1
        
        scrollable.grid_columnconfigure(0, weight=1)
        
        if not courses:
            tk.Label(scrollable, text="No courses found",
                    font=('Roboto', 14), bg='#F8F9FA', fg='#6C757D').pack(pady=50)
    
    def _create_course_card(self, parent, course: Course):
        card = tk.Frame(parent, bg='white', relief='flat', borderwidth=1)
        card.configure(highlightbackground='#E0E0E0', highlightthickness=1)
        
        left_frame = tk.Frame(card, bg='white')
        left_frame.pack(side='left', fill='both', expand=True, padx=15, pady=12)
        
        course_num = tk.Label(left_frame, text=course.course_number,
                             font=('Fira Code', 12, 'bold'), bg='white',
                             fg='#0A2463')
        course_num.pack(anchor='w')
        
        title = tk.Label(left_frame, text=course.title,
                        font=('Roboto', 12, 'bold'), bg='white', fg='#1A1A1A',
                        wraplength=600, justify='left')
        title.pack(anchor='w', pady=(2, 5))
        
        desc = tk.Label(left_frame, text=course.description[:120] + "..." 
                        if len(course.description) > 120 else course.description,
                       font=('Roboto', 10), bg='white', fg='#6C757D',
                       wraplength=600, justify='left')
        desc.pack(anchor='w')
        
        info_frame = tk.Frame(left_frame, bg='white')
        info_frame.pack(anchor='w', pady=(8, 0))
        
        tk.Label(info_frame, text=f"Credits: {course.credits}",
                font=('Roboto', 10, 'bold'), bg='white', fg='#0A2463').pack(side='left', padx=(0, 15))
        
        tk.Label(info_frame, text=course.department,
                font=('Roboto', 10), bg='white', fg='#C8102E').pack(side='left', padx=(0, 15))
        
        terms = ", ".join(course.terms_offered)
        tk.Label(info_frame, text=f"Terms: {terms}",
                font=('Roboto', 10), bg='white', fg='#28A745').pack(side='left')
        
        if course.prerequisites:
            prereqs = ", ".join(course.prerequisites[:3]) + ("..." if len(course.prerequisites) > 3 else "")
            tk.Label(left_frame, text=f"Prereqs: {prereqs}",
                    font=('Roboto', 9), bg='white', fg='#FFC107').pack(anchor='w', pady=(5, 0))
        
        right_frame = tk.Frame(card, bg='white', width=150)
        right_frame.pack(side='right', fill='y', padx=15, pady=12)
        right_frame.pack_propagate(False)
        
        if self.current_plan_id:
            add_btn = tk.Button(right_frame, text="Add to Plan",
                               font=('Roboto', 10, 'bold'), bg='#28A745',
                               fg='white', relief='flat', padx=10, pady=8,
                               cursor='hand2', command=lambda: self._show_add_course_dialog(course))
            add_btn.pack(fill='x')
        
        return card
    
    def _clear_content(self):
        for widget in self.content_container.winfo_children():
            widget.destroy()
    
    def _update_nav_selection(self, selected):
        for text, btn in self.nav_buttons.items():
            if text == selected:
                btn.config(bg='#FFDD00', fg='#0A2463')
            else:
                btn.config(bg='#1A3A7A', fg='white')
    
    def _show_catalog_view(self):
        self._update_nav_selection("Course Catalog")
        self.view_title.config(text="Course Catalog")
        self.search_frame.pack(fill='x', pady=(0, 15))
        self._on_search()
    
    def _show_plan_view(self):
        self._update_nav_selection("My Plan")
        self.view_title.config(text="My Plan")
        self.search_frame.pack_forget()
        
        if not self.current_plan_id:
            self._display_no_plan_message()
            return
        
        self._display_plan_view()
    
    def _display_no_plan_message(self):
        self._clear_content()
        frame = tk.Frame(self.content_container, bg='#F8F9FA')
        frame.pack(fill='both', expand=True, pady=100)
        
        tk.Label(frame, text="No Plan Selected", 
                font=('Roboto Slab', 20, 'bold'), bg='#F8F9FA', fg='#0A2463').pack(pady=10)
        tk.Label(frame, text="Create a new plan or load an existing one from the sidebar",
                font=('Roboto', 12), bg='#F8F9FA', fg='#6C757D').pack()
    
    def _display_plan_view(self):
        self._clear_content()
        
        if not self.current_plan_id:
            self._display_no_plan_message()
            return
        
        plan_courses = self.db.get_plan_courses(self.current_plan_id)
        
        if not plan_courses:
            plan = self.db.get_plan(self.current_plan_id)
            frame = tk.Frame(self.content_container, bg='#F8F9FA')
            frame.pack(fill='both', expand=True, pady=100)
            
            tk.Label(frame, text="No Courses in Plan", 
                    font=('Roboto Slab', 20, 'bold'), bg='#F8F9FA', fg='#0A2463').pack(pady=10)
            tk.Label(frame, text=f"Plan: {plan['name']}",
                    font=('Roboto', 12), bg='#F8F9FA', fg='#6C757D').pack()
            tk.Label(frame, text="Go to Course Catalog to add courses",
                    font=('Roboto', 12), bg='#F8F9FA', fg='#6C757D').pack()
            return
        
        plan = self.db.get_plan(self.current_plan_id)
        
        semesters = {}
        semester_types = {}
        for pc in plan_courses:
            key = (pc.year, pc.semester)
            if key not in semesters:
                semesters[key] = []
                semester_types[key] = pc.semester_type
            semesters[key].append(pc)
        
        # Simple scrollable frame
        main_canvas_frame = tk.Frame(self.content_container)
        main_canvas_frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(main_canvas_frame, bg='#F8F9FA')
        scrollbar = ttk.Scrollbar(main_canvas_frame, orient='vertical', command=canvas.yview)
        scrollable = tk.Frame(canvas, bg='#F8F9FA')
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Force canvas to expand
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        # Debug: show how many courses we have
        tk.Label(scrollable, text=f"DEBUG: {len(plan_courses)} courses found",
                font=('Roboto', 14, 'bold'), bg='#FFDD00', fg='black').pack(pady=10)
        
        term_names = {1: "Fall", 2: "Spring", 3: "Summer"}
        
        for year in range(1, self.current_plan_duration + 1):
            year_label = tk.Label(scrollable, text=f"Year {year}",
                                  font=('Roboto Slab', 18, 'bold'), bg='#F8F9FA',
                                  fg='#0A2463')
            year_label.pack(anchor='w', pady=(15, 10), padx=10)
            
            semesters_frame = tk.Frame(scrollable, bg='#F8F9FA')
            semesters_frame.pack(fill='x', padx=10)
            
            for sem_num in [1, 2, 3]:
                key = (year, sem_num)
                courses = semesters.get(key, [])
                sem_type = semester_types.get(key, 'regular')
                
                sem_frame = tk.Frame(semesters_frame, bg='white', relief='flat',
                                     borderwidth=1, width=300)
                sem_frame.pack(side='left', fill='both', expand=True, padx=5)
                sem_frame.pack_propagate(False)
                
                header_colors = {
                    'regular': '#0A2463',
                    'study_abroad': '#17A2B8',
                    'coop': '#FFC107',
                    'off': '#6C757D'
                }
                
                sem_header = tk.Frame(sem_frame, bg=header_colors.get(sem_type, '#0A2463'))
                sem_header.pack(fill='x')
                
                term_name = f"{term_names.get(sem_num, '')} {self.current_plan_start_year + year - 1}"
                tk.Label(sem_header, text=term_name,
                        font=('Roboto', 11, 'bold'), bg=header_colors.get(sem_type, '#0A2463'), 
                        fg='white').pack(pady=8)
                
                type_label = tk.Label(sem_header, 
                                    text=f"({sem_type.replace('_', ' ').title()})",
                                    font=('Roboto', 9), bg=header_colors.get(sem_type, '#0A2463'),
                                    fg='white')
                type_label.pack()
                
                courses_container = tk.Frame(sem_frame, bg='white')
                courses_container.pack(fill='both', expand=True, padx=10, pady=10)
                
                total_credits = 0
                for pc in courses:
                    total_credits += pc.course.credits
                    self._create_plan_course_card(courses_container, pc)
                
                if not courses:
                    tk.Label(courses_container, text="No courses",
                            font=('Roboto', 10), bg='white', fg='#6C757D').pack()
                
                credits_label = tk.Label(sem_frame, 
                                         text=f"Total: {total_credits} credits",
                                         font=('Roboto', 10, 'bold'), bg='white',
                                         fg='#0A2463')
                credits_label.pack(pady=(0, 10))
                
                btn_frame = tk.Frame(sem_frame, bg='white')
                btn_frame.pack(pady=(0, 10))
                
                add_btn = tk.Button(btn_frame, text="+ Add",
                                   font=('Roboto', 9), bg='#28A745', fg='white',
                                   relief='flat', pady=4, padx=8,
                                   command=lambda y=year, s=sem_num: self._show_add_course_dialog_for_semester(y, s))
                add_btn.pack(side='left', padx=2)
                
                type_btn = tk.Button(btn_frame, text="Type",
                                   font=('Roboto', 9), bg='#17A2B8', fg='white',
                                   relief='flat', pady=4, padx=8,
                                   command=lambda y=year, s=sem_num: self._change_semester_type(y, s))
                type_btn.pack(side='left', padx=2)
        
        scrollable.grid_columnconfigure(0, weight=1)
    
    def _change_semester_type(self, year: int, semester: int):
        dialog = tk.Toplevel(self.root)
        dialog.title("Semester Type")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        
        tk.Label(dialog, text=f"Year {year}, Semester {semester}",
                font=('Roboto', 12, 'bold')).pack(pady=15)
        
        types = [
            ("Regular", "regular"),
            ("Study Abroad", "study_abroad"),
            ("Co-op", "coop"),
            ("Off/Semester Off", "off")
        ]
        
        for text, type_val in types:
            btn = tk.Button(dialog, text=text, font=('Roboto', 11),
                           bg='#0A2463', fg='white', relief='flat', padx=20, pady=8,
                           command=lambda t=type_val: self._set_semester_type(year, semester, t, dialog))
            btn.pack(pady=5)
    
    def _set_semester_type(self, year: int, semester: int, sem_type: str, dialog):
        self.db.update_semester_type(self.current_plan_id, year, semester, sem_type)
        dialog.destroy()
        self._display_plan_view()
    
    def _create_plan_course_card(self, parent, pc: PlanCourse):
        card = tk.Frame(parent, bg='#F8F9FA', relief='flat', borderwidth=1)
        card.pack(fill='x', pady=3)
        
        status_colors = {'planned': '#FFC107', 'in_progress': '#17A2B8', 'completed': '#28A745'}
        
        status_frame = tk.Frame(card, bg=status_colors.get(pc.status, '#6C757D'), width=4)
        status_frame.pack(side='left', fill='y', padx=(0, 8))
        
        course_info = tk.Frame(card, bg='#F8F9FA')
        course_info.pack(side='left', fill='both', expand=True)
        
        prereqs_met = self._check_prerequisites_met(pc)
        
        if not prereqs_met and pc.status != 'completed':
            warning = tk.Label(course_info, text="⚠️ Prereqs not met",
                            font=('Roboto', 9, 'bold'), bg='#F8F9FA', fg='#DC3545')
            warning.pack(anchor='w')
        
        tk.Label(course_info, text=pc.course.course_number,
                font=('Fira Code', 10, 'bold'), bg='#F8F9FA', fg='#0A2463').pack(anchor='w')
        
        tk.Label(course_info, text=f"{pc.course.credits} cr",
                font=('Roboto', 9), bg='#F8F9FA', fg='#6C757D').pack(anchor='w')
        
        if pc.status == 'completed':
            tk.Label(course_info, text=f"Grade: {pc.grade or 'N/A'}",
                    font=('Roboto', 9, 'bold'), bg='#F8F9FA', fg='#28A745').pack(anchor='w')
        
        btn_frame = tk.Frame(card, bg='#F8F9FA')
        btn_frame.pack(side='right')
        
        status_btn = tk.Button(btn_frame, text="✓", font=('Arial', 10),
                              bg=status_colors.get(pc.status, '#6C757D'), fg='white',
                              relief='flat', width=3, cursor='hand2',
                              command=lambda: self._cycle_status(pc))
        status_btn.pack(side='left', padx=2)
        
        remove_btn = tk.Button(btn_frame, text="×", font=('Arial', 10, 'bold'),
                               bg='#DC3545', fg='white', relief='flat', width=3,
                               cursor='hand2', command=lambda: self._remove_course(pc))
        remove_btn.pack(side='left')
    
    def _check_prerequisites_met(self, pc: PlanCourse) -> bool:
        if not pc.course.prerequisites:
            return True
        
        plan_courses = self.db.get_plan_courses(self.current_plan_id)
        
        completed = {c.course.course_number for c in plan_courses 
                   if c.status == 'completed' and c.year < pc.year}
        
        for prereq in pc.course.prerequisites:
            if prereq not in completed:
                return False
        return True
    
    def _cycle_status(self, pc: PlanCourse):
        statuses = ['planned', 'in_progress', 'completed']
        current_idx = statuses.index(pc.status)
        new_status = statuses[(current_idx + 1) % len(statuses)]
        
        grade = None
        if new_status == 'completed':
            grade = simpledialog.askstring("Grade", "Enter grade (A, B, C, etc.):",
                                          parent=self.root)
            if not grade:
                return
        
        self.db.update_course_status(pc.id, new_status, grade)
        self._display_plan_view()
    
    def _remove_course(self, pc: PlanCourse):
        if messagebox.askyesno("Remove Course", 
                              f"Remove {pc.course.course_number} from your plan?"):
            self.db.remove_course_from_plan(pc.id)
            self._display_plan_view()
    
    def _show_requirements_view(self):
        self._update_nav_selection("Requirements")
        self.view_title.config(text="Requirements")
        self.search_frame.pack_forget()
        
        self._clear_content()
        
        if not self.current_plan_id:
            self._display_no_plan_message()
            return
        
        self._display_requirements_view()
    
    def _display_requirements_view(self):
        self._clear_content()
        
        plan = self.db.get_plan(self.current_plan_id)
        plan_courses = self.db.get_plan_courses(self.current_plan_id)
        
        completed_courses = {pc.course.course_number: pc for pc in plan_courses if pc.status == 'completed'}
        
        dept_reqs = self.db.get_department_requirements(plan['department']) if plan else None
        univ_reqs = self.db.get_university_requirements()
        
        canvas_frame = tk.Frame(self.content_container, bg='#F8F9FA')
        canvas_frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg='#F8F9FA', highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        scrollable = tk.Frame(canvas, bg='#F8F9FA')
        
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        tk.Label(scrollable, text=f"Major: {plan['department']}",
                font=('Roboto Slab', 18, 'bold'), bg='#F8F9FA', fg='#0A2463').pack(pady=(15, 10), padx=20, anchor='w')
        
        if dept_reqs:
            dept_frame = tk.Frame(scrollable, bg='white', relief='flat', borderwidth=1)
            dept_frame.pack(fill='x', padx=20, pady=10)
            
            tk.Label(dept_frame, text=f"Department Requirements - {dept_reqs['name']}",
                    font=('Roboto', 14, 'bold'), bg='white', fg='#0A2463').pack(pady=10, padx=15, anchor='w')
            
            tk.Label(dept_frame, text=f"Required Credits: {dept_reqs['required_credits']}",
                    font=('Roboto', 11), bg='white', fg='#1A1A1A').pack(pady=(0, 10), padx=15, anchor='w')
            
            req_courses = dept_reqs['required_courses']
            completed_count = sum(1 for c in req_courses if c in completed_courses)
            
            tk.Label(dept_frame, text=f"Required Courses: {completed_count}/{len(req_courses)} completed",
                    font=('Roboto', 11), bg='white', fg='#0A2463').pack(pady=(0, 10), padx=15, anchor='w')
            
            for course_num in req_courses:
                course = self.db.get_course_by_number(course_num)
                if course:
                    status = "✓" if course_num in completed_courses else "○"
                    color = '#28A745' if course_num in completed_courses else '#6C757D'
                    tk.Label(dept_frame, text=f"  {status} {course_num}: {course.title}",
                            font=('Roboto', 10), bg='white', fg=color).pack(pady=2, padx=20, anchor='w')
        
        univ_frame = tk.Frame(scrollable, bg='white', relief='flat', borderwidth=1)
        univ_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(univ_frame, text="University Requirements",
                font=('Roboto', 14, 'bold'), bg='white', fg='#0A2463').pack(pady=10, padx=15, anchor='w')
        
        for req in univ_reqs:
            req_frame = tk.Frame(univ_frame, bg='#F8F9FA')
            req_frame.pack(fill='x', padx=15, pady=5)
            
            status = "✓" if req['name'] in completed_courses else "○"
            color = '#28A745' if req['name'] in completed_courses else '#6C757D'
            
            tk.Label(req_frame, text=f"{status} {req['name']} ({req['category']})",
                    font=('Roboto', 11, 'bold'), bg='#F8F9FA', fg=color).pack(anchor='w')
            tk.Label(req_frame, text=f"   {req['description']}",
                    font=('Roboto', 10), bg='#F8F9FA', fg='#6C757D').pack(anchor='w')
        
        total_credits = sum(pc.course.credits for pc in plan_courses if pc.status == 'completed')
        total_required = dept_reqs['required_credits'] if dept_reqs else 120
        
        summary_frame = tk.Frame(scrollable, bg='white', relief='flat', borderwidth=1)
        summary_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(summary_frame, text="Progress Summary",
                font=('Roboto', 14, 'bold'), bg='white', fg='#0A2463').pack(pady=10, padx=15, anchor='w')
        
        progress = (total_credits / total_required) * 100 if total_required > 0 else 0
        tk.Label(summary_frame, text=f"Credits: {total_credits} / {total_required} ({progress:.1f}%)",
                font=('Roboto', 12), bg='white', fg='#1A1A1A').pack(pady=5, padx=15, anchor='w')
        
        scrollable.grid_columnconfigure(0, weight=1)
    
    def _show_ai_planner_view(self):
        self._update_nav_selection("AI Planner")
        self.view_title.config(text="AI Course Planner")
        self.search_frame.pack_forget()
        
        self._clear_content()
        
        if not self.current_plan_id:
            self._display_no_plan_message()
            return
        
        self._display_ai_planner_view()
    
    def _display_ai_planner_view(self):
        self._clear_content()
        
        main_frame = tk.Frame(self.content_container, bg='#F8F9FA')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="AI Course Recommendation",
                font=('Roboto Slab', 18, 'bold'), bg='#F8F9FA', fg='#0A2463').pack(pady=(0, 15), anchor='w')
        
        if not self.llm_planner.is_available():
            tk.Label(main_frame, text="⚠️ Ollama is not running. Please start Ollama to use AI features.",
                    font=('Roboto', 12), bg='#F8F9FA', fg='#DC3545').pack(pady=20)
            tk.Label(main_frame, text="To use Ollama: Download from ollama.ai and run 'ollama serve'",
                    font=('Roboto', 11), bg='#F8F9FA', fg='#6C757D').pack(pady=5)
            return
        
        tk.Label(main_frame, text="Describe your interests and career goals:",
                font=('Roboto', 12), bg='#F8F9FA', fg='#1A1A1A').pack(anchor='w', pady=(0, 10))
        
        interests_text = tk.Text(main_frame, font=('Roboto', 11), height=6, width=60,
                                bg='white', relief='flat')
        interests_text.pack(fill='x', pady=(0, 10))
        interests_text.insert('1.0', "e.g., I'm interested in machine learning and data science, want to work on AI applications...")
        
        plan = self.db.get_plan(self.current_plan_id)
        plan_courses = self.db.get_plan_courses(self.current_plan_id)
        completed = [pc.course.course_number for pc in plan_courses if pc.status == 'completed']
        
        tk.Label(main_frame, text=f"Department: {plan['department']} | Completed courses: {', '.join(completed) if completed else 'None'}",
                font=('Roboto', 10), bg='#F8F9FA', fg='#6C757D').pack(anchor='w', pady=(0, 10))
        
        get_recommendations_btn = tk.Button(main_frame, text="Get Course Recommendations",
                                           font=('Roboto', 12, 'bold'), bg='#0A2463', fg='white',
                                           relief='flat', padx=20, pady=10, cursor='hand2',
                                           command=lambda: self._get_ai_recommendations(
                                               interests_text.get('1.0', 'end').strip(), completed, plan['department']))
        get_recommendations_btn.pack(pady=(0, 20))
        
        self.recommendations_canvas_frame = tk.Frame(main_frame, bg='#F8F9FA')
        self.recommendations_canvas_frame.pack(fill='both', expand=True)
        
        self.recommendations_canvas = tk.Canvas(self.recommendations_canvas_frame, bg='#F8F9FA', highlightthickness=0)
        self.recommendations_scrollbar = ttk.Scrollbar(self.recommendations_canvas_frame, orient='vertical', command=self.recommendations_canvas.yview)
        self.recommendations_scrollable = tk.Frame(self.recommendations_canvas, bg='#F8F9FA')
        
        self.recommendations_scrollable.bind(
            "<Configure>",
            lambda e: self.recommendations_canvas.configure(scrollregion=self.recommendations_canvas.bbox("all"))
        )
        
        self.recommendations_canvas.create_window((0, 0), window=self.recommendations_scrollable, anchor='nw')
        self.recommendations_canvas.configure(yscrollcommand=self.recommendations_scrollbar.set)
        
        self.recommendations_canvas.pack(side='left', fill='both', expand=True)
        self.recommendations_scrollbar.pack(side='right', fill='y')
        
        self.recommendations_frame = self.recommendations_scrollable
    
    def _get_ai_recommendations(self, interests: str, completed: List[str], department: str):
        for widget in self.recommendations_frame.winfo_children():
            widget.destroy()
        
        loading = tk.Label(self.recommendations_frame, text="Getting recommendations...",
                         font=('Roboto', 12), bg='#F8F9FA', fg='#6C757D')
        loading.pack(pady=20)
        
        self.recommendations_frame.update()
        
        recommendations = self.llm_planner.get_course_recommendations(interests, completed, department)
        
        loading.destroy()
        
        if not recommendations:
            tk.Label(self.recommendations_frame, text="Could not get recommendations. Please try again.",
                    font=('Roboto', 12), bg='#F8F9FA', fg='#DC3545').pack(pady=20)
            return
        
        tk.Label(self.recommendations_frame, text="Recommended Courses:",
                font=('Roboto', 14, 'bold'), bg='#F8F9FA', fg='#0A2463').pack(pady=(0, 10), anchor='w')
        
        for rec in recommendations:
            course = rec['course']
            reason = rec['reason']
            
            rec_card = tk.Frame(self.recommendations_frame, bg='white', relief='flat', borderwidth=1)
            rec_card.pack(fill='x', pady=5)
            
            tk.Label(rec_card, text=course.course_number,
                    font=('Fira Code', 12, 'bold'), bg='white', fg='#0A2463').pack(pady=(10, 5), padx=15, anchor='w')
            
            tk.Label(rec_card, text=course.title,
                    font=('Roboto', 11), bg='white', fg='#1A1A1A').pack(pady=0, padx=15, anchor='w')
            
            tk.Label(rec_card, text=f"Reason: {reason}",
                    font=('Roboto', 10), bg='white', fg='#6C757D').pack(pady=(0, 10), padx=15, anchor='w')
            
            add_btn = tk.Button(rec_card, text="Add to Plan",
                               font=('Roboto', 10, 'bold'), bg='#28A745',
                               fg='white', relief='flat', padx=15, pady=5,
                               command=lambda c=course: self._add_recommended_course(c))
            add_btn.pack(pady=(0, 10), padx=15, anchor='e')
    
    def _add_recommended_course(self, course: Course):
        plan_courses = self.db.get_plan_courses(self.current_plan_id)
        
        next_sem = 1
        next_year = 1
        max_key = 0
        
        for pc in plan_courses:
            key = pc.year * 10 + pc.semester
            if key > max_key:
                max_key = key
        
        if max_key > 0:
            next_year = (max_key // 10) + (1 if max_key % 10 == 3 else 0)
            next_sem = (max_key % 10) + 1
            if next_sem > 3:
                next_sem = 1
                next_year += 1
        
        if next_year > self.current_plan_duration:
            next_year = self.current_plan_duration
            next_sem = 1
        
        self.db.add_course_to_plan(self.current_plan_id, course.id, next_sem, next_year)
        messagebox.showinfo("Added", f"Added {course.course_number} to your plan!")
        self._display_plan_view()
    
    def _show_settings_view(self):
        self._update_nav_selection("Settings")
        self.view_title.config(text="Settings")
        self.search_frame.pack_forget()
        
        self._clear_content()
        
        settings_frame = tk.Frame(self.content_container, bg='white', relief='flat', borderwidth=1)
        settings_frame.pack(fill='x', padx=20, pady=20)
        
        tk.Label(settings_frame, text="Plan Settings",
               font=('Roboto Slab', 18, 'bold'), bg='white', fg='#0A2463').pack(pady=15)
        
        plan_frame = tk.Frame(settings_frame, bg='white')
        plan_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(plan_frame, text="Current Plan:",
                font=('Roboto', 12, 'bold'), bg='white', fg='#1A1A1A').pack(anchor='w')
        
        if self.current_plan_id:
            plan = self.db.get_plan(self.current_plan_id)
            tk.Label(plan_frame, text=f"{plan['name']} - {plan['duration_years']} Year - Dept: {plan['department']}",
                    font=('Roboto', 11), bg='white', fg='#0A2463').pack(anchor='w', pady=(5, 15))
            
            tk.Button(plan_frame, text="Delete Plan", font=('Roboto', 11),
                     bg='#DC3545', fg='white', relief='flat', padx=15, pady=5,
                     command=self._delete_current_plan).pack(anchor='w')
        else:
            tk.Label(plan_frame, text="No plan selected",
                    font=('Roboto', 11), bg='white', fg='#6C757D').pack(anchor='w', pady=5)
    
    def _create_new_plan(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Plan")
        dialog.geometry("400x420")
        dialog.transient(self.root)
        
        tk.Label(dialog, text="Create New Plan",
                font=('Roboto Slab', 16, 'bold')).pack(pady=15)
        
        tk.Label(dialog, text="Plan Name:", font=('Roboto', 11)).pack(pady=(10, 5))
        name_entry = tk.Entry(dialog, font=('Roboto', 11))
        name_entry.pack(pady=5)
        
        tk.Label(dialog, text="Duration (years):", font=('Roboto', 11)).pack(pady=(10, 5))
        duration_var = tk.StringVar(value="4")
        duration_frame = tk.Frame(dialog)
        duration_frame.pack()
        for val in ["4", "5"]:
            tk.Radiobutton(duration_frame, text=val, variable=duration_var, value=val,
                          font=('Roboto', 11)).pack(side='left', padx=10)
        
        tk.Label(dialog, text="Start Year:", font=('Roboto', 11)).pack(pady=(10, 5))
        year_var = tk.StringVar(value="2024")
        tk.Entry(dialog, textvariable=year_var, font=('Roboto', 11)).pack(pady=5)
        
        tk.Label(dialog, text="Department/Major:", font=('Roboto', 11)).pack(pady=(10, 5))
        dept_var = tk.StringVar(value="CS")
        dept_codes = [d[0] for d in self.departments]
        dept_combo = ttk.Combobox(dialog, textvariable=dept_var, values=dept_codes, state='readonly')
        dept_combo.pack(pady=5)
        dept_combo.current(0)
        
        def create():
            name = name_entry.get()
            if not name:
                messagebox.showerror("Error", "Please enter a plan name")
                return
            
            plan_id = self.db.create_plan(name, int(duration_var.get()), 
                                          int(year_var.get()), dept_var.get())
            
            self.current_plan_id = plan_id
            self.current_plan_duration = int(duration_var.get())
            self.current_plan_department = dept_var.get()
            self.current_plan_start_year = int(year_var.get())
            
            self.plan_label.config(text=f"Plan: {name} ({duration_var.get()}yr, {dept_var.get()})")
            
            dialog.destroy()
            self._show_plan_view()
            messagebox.showinfo("Success", f"Created plan: {name}")
        
        tk.Button(dialog, text="Create Plan", font=('Roboto', 12, 'bold'),
                 bg='#28A745', fg='white', relief='flat', padx=20, pady=8,
                 command=create).pack(pady=20)
    
    def _load_existing_plan(self):
        plans = self.db.get_all_plans()
        
        if not plans:
            messagebox.showinfo("No Plans", "No existing plans found.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Plan")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        
        tk.Label(dialog, text="Select a Plan:",
                font=('Roboto Slab', 14, 'bold')).pack(pady=15)
        
        listbox = tk.Listbox(dialog, font=('Roboto', 11), height=8)
        listbox.pack(fill='both', expand=True, padx=20, pady=10)
        
        for plan in plans:
            listbox.insert('end', f"{plan['name']} ({plan['duration_years']}yr, {plan['department']})")
        
        def load_selected():
            if not listbox.curselection():
                return
            
            idx = listbox.curselection()[0]
            self.current_plan_id = plans[idx]['id']
            self.current_plan_duration = plans[idx]['duration_years']
            self.current_plan_department = plans[idx]['department']
            self.current_plan_start_year = plans[idx]['start_year']
            
            self.plan_label.config(text=f"Plan: {plans[idx]['name']} ({plans[idx]['duration_years']}yr, {plans[idx]['department']})")
            
            dialog.destroy()
            self._show_plan_view()
        
        tk.Button(dialog, text="Load", font=('Roboto', 11, 'bold'),
                 bg='#28A745', fg='white', relief='flat', padx=20, pady=5,
                 command=load_selected).pack(pady=10)
    
    def _delete_current_plan(self):
        if messagebox.askyesno("Delete Plan", "Are you sure you want to delete this plan?"):
            self.db.delete_plan(self.current_plan_id)
            self.current_plan_id = None
            self.plan_label.config(text="No Plan Selected")
            self._show_settings_view()
            messagebox.showinfo("Deleted", "Plan deleted successfully.")
    
    def _show_add_course_dialog(self, course: Course):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Add {course.course_number}")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        
        tk.Label(dialog, text=course.course_number,
                font=('Fira Code', 16, 'bold')).pack(pady=(20, 5))
        tk.Label(dialog, text=course.title,
                font=('Roboto', 12)).pack()
        
        tk.Label(dialog, text=f"Credits: {course.credits} | Dept: {course.department}",
                font=('Roboto', 10), fg='#6C757D').pack()
        
        prereqs_met = self._check_prerequisites_for_dialog(course)
        
        if course.prerequisites:
            prereqs = ", ".join(course.prerequisites)
            color = '#28A745' if prereqs_met else '#DC3545'
            status = "Satisfied" if prereqs_met else "NOT MET"
            tk.Label(dialog, text=f"Prerequisites: {prereqs} - {status}",
                    font=('Roboto', 10), fg=color, wraplength=350).pack(pady=5)
        
        if course.corequisites:
            coreqs = ", ".join(course.corequisites)
            tk.Label(dialog, text=f"Corequisites: {coreqs}",
                    font=('Roboto', 10), fg='#FFC107', wraplength=350).pack(pady=5)
        
        tk.Label(dialog, text="Select Semester:",
                font=('Roboto', 12, 'bold')).pack(pady=(20, 10))
        
        year_var = tk.IntVar(value=1)
        sem_var = tk.IntVar(value=1)
        
        year_frame = tk.Frame(dialog)
        year_frame.pack()
        
        tk.Label(year_frame, text="Year:", font=('Roboto', 11)).pack(side='left')
        
        for i in range(1, self.current_plan_duration + 1):
            rb = tk.Radiobutton(year_frame, text=str(i), variable=year_var, value=i,
                              font=('Roboto', 10))
            rb.pack(side='left', padx=5)
        
        sem_frame = tk.Frame(dialog)
        sem_frame.pack(pady=10)
        
        terms = {1: "Fall", 2: "Spring", 3: "Summer"}
        
        tk.Label(sem_frame, text="Semester:", font=('Roboto', 11)).pack()
        
        for i in range(1, 4):
            rb = tk.Radiobutton(sem_frame, text=terms[i], variable=sem_var, value=i,
                              font=('Roboto', 10))
            rb.pack(side='left', padx=10)
        
        def add_to_plan():
            if not prereqs_met:
                if not messagebox.askyesno("Warning", 
                    "Prerequisites are not met. Add course anyway?"):
                    return
            
            self.db.add_course_to_plan(self.current_plan_id, course.id, 
                                      sem_var.get(), year_var.get())
            dialog.destroy()
            self._display_plan_view()
        
        tk.Button(dialog, text="Add to Plan", font=('Roboto', 12, 'bold'),
                 bg='#28A745', fg='white', relief='flat', padx=20, pady=8,
                 command=add_to_plan).pack(pady=20)
    
    def _check_prerequisites_for_dialog(self, course: Course) -> bool:
        if not course.prerequisites:
            return True
        
        plan_courses = self.db.get_plan_courses(self.current_plan_id)
        completed = {c.course.course_number for c in plan_courses if c.status == 'completed'}
        
        for prereq in course.prerequisites:
            if prereq not in completed:
                return False
        return True
    
    def _show_add_course_dialog_for_semester(self, year: int, semester: int):
        self._show_catalog_view()
        messagebox.showinfo("Add Course", 
                          f"Use the catalog to find and add courses.\nThey will be added to Year {year}, Semester {semester}.")
    
    def run(self):
        self.root.mainloop()


def main():
    root = tk.Tk()
    app = CoursePlannerApp(root)
    app.run()


if __name__ == "__main__":
    main()
