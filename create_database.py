import sqlite3
import json
from datetime import datetime

DB_PATH = "purdue_courses.db"

def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS plan_courses")
    cursor.execute("DROP TABLE IF EXISTS plans")
    cursor.execute("DROP TABLE IF EXISTS courses")
    cursor.execute("DROP TABLE IF EXISTS departments")
    cursor.execute("DROP TABLE IF EXISTS university_requirements")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            required_credits INTEGER DEFAULT 120,
            required_courses TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_number TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            credits INTEGER NOT NULL,
            department TEXT NOT NULL,
            prerequisites TEXT,
            corequisites TEXT,
            terms_offered TEXT,
            is_required INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration_years INTEGER NOT NULL DEFAULT 4,
            start_year INTEGER DEFAULT 2024,
            department TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plan_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            semester INTEGER NOT NULL,
            year INTEGER NOT NULL,
            semester_type TEXT DEFAULT 'regular',
            status TEXT DEFAULT 'planned',
            grade TEXT,
            FOREIGN KEY (plan_id) REFERENCES plans(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS university_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            credits_required INTEGER DEFAULT 0,
            courses_required TEXT,
            minimum_grade TEXT DEFAULT 'D'
        )
    """)

    conn.commit()
    return conn

def populate_departments(cursor):
    departments = [
        ("CS", "Computer Science", 120, '["CS 18000", "CS 18200", "CS 24000", "CS 25000", "CS 25100", "CS 30700", "CS 35400", "CS 38000"]'),
        ("MA", "Mathematics", 120, '["MA 16100", "MA 16200", "MA 26100", "MA 26200", "MA 35100", "MA 36600"]'),
        ("PH", "Physics", 120, '["PHYS 17200", "PHYS 27200", "PHYS 31000", "PHYS 33000", "PHYS 36000"]'),
        ("CH", "Chemistry", 120, '["CHM 11500", "CHM 11600", "CHM 26505", "CHM 26605"]'),
        ("BI", "Biology", 120, '["BIOL 11000", "BIOL 12100", "BIOL 12200", "BIOL 23100"]'),
        ("ECE", "Electrical & Computer Engineering", 126, '["ECE 20000", "ECE 20100", "ECE 20200", "ECE 20800", "ECE 25500", "ECE 27000", "ECE 30100", "ECE 30200"]'),
        ("ME", "Mechanical Engineering", 126, '["ME 20000", "ME 27000", "ME 30900", "ME 31500", "ME 35200"]'),
        ("AE", "Aerospace Engineering", 126, '["AE 20000", "AE 21000", "AE 22000"]'),
        ("CE", "Civil Engineering", 126, '["CE 20300", "CE 29700", "CE 29800", "CE 31100", "CE 34000"]'),
        ("IE", "Industrial Engineering", 126, '["IE 33000", "IE 37000", "IE 47400"]'),
        ("BME", "Biomedical Engineering", 128, '["BME 20000", "BME 30000", "BME 38000"]'),
        ("CHE", "Chemical Engineering", 128, '["CHE 20000", "CHE 21100", "CHE 30000", "CHE 30600"]'),
        ("CSEC", "Cybersecurity", 120, '["CSEC 27000", "CSEC 37000", "CSEC 47300", "CNIT 18000", "CNIT 34000"]'),
        ("STAT", "Statistics", 120, '["STAT 35000", "STAT 41700", "STAT 42000"]'),
        ("ECON", "Economics", 120, '["ECON 11000", "ECON 21000", "ECON 36000"]'),
        ("PSY", "Psychology", 120, '["PSY 10000", "PSY 12000", "PSY 20000", "PSY 35000"]'),
        ("SOC", "Sociology", 120, '["SOC 10000", "SOC 22000"]'),
        ("ENGL", "English", 120, '["ENGL 10600", "ENGL 10800", "ENGL 30400"]'),
        ("COM", "Communication", 120, '["COM 11400", "COM 21200", "COM 32000"]'),
        ("HIST", "History", 120, '["HIST 15100", "HIST 15200"]'),
        ("PHIL", "Philosophy", 120, '["PHIL 11000", "PHIL 12000", "PHIL 26000"]'),
        ("POL", "Political Science", 120, '["POL 13000", "POL 14100"]'),
        ("NUR", "Nursing", 120, '["NUR 10000", "NUR 20000", "NUR 30000", "NUR 40000"]'),
        ("CNIT", "Computer & Information Technology", 120, '["CNIT 18000", "CNIT 24200", "CNIT 32000", "CNIT 34000"]'),
        ("ENGR", "Engineering", 120, '["ENGR 10000", "ENGR 13000", "ENGR 14100"]'),
    ]
    cursor.executemany("INSERT INTO departments (code, name, required_credits, required_courses) VALUES (?, ?, ?, ?)", departments)

def populate_university_requirements(cursor):
    requirements = [
        ("English Composition", "First-year writing requirement", "Core", 4, '["ENGL 10600", "ENGL 10800"]', "C"),
        ("Speech Communication", "Oral communication requirement", "Core", 3, '["COM 11400"]', "D"),
        ("Mathematics", "College-level mathematics", "Core", 3, '["MA 16100", "MA 16200", "MA 16500"]', "D"),
        ("Science", "Laboratory science requirement", "Core", 6, '["PHYS 17200", "CHM 11500", "BIOL 11000"]', "D"),
        ("Humanities", "Humanities distribution", "Distribution", 9, '["HIST 15100", "HIST 15200", "PHIL 11000", "PHIL 12000"]', "D"),
        ("Social Sciences", "Social science distribution", "Distribution", 9, '["ECON 11000", "PSY 10000", "SOC 10000", "POL 13000"]', "D"),
        ("Total Credits", "Minimum total credits for graduation", "Graduation", 120, "[]", "D"),
        ("Residency", "Minimum credits at Purdue", "Graduation", 30, "[]", "D"),
    ]
    cursor.executemany("""
        INSERT INTO university_requirements 
        (name, description, category, credits_required, courses_required, minimum_grade) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, requirements)

def populate_courses(cursor):
    courses = [
        ("CS 18000", "Problem Solving and Object-Oriented Programming", "Introduction to computer science and programming using object-oriented paradigm. Topics include classes, objects, inheritance, polymorphism, arrays, files, and basic data structures.", 4, "CS", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("CS 18200", "Foundations of Computer Science", "Theoretical foundations of computer science including automata, formal languages, computability, and complexity.", 3, "CS", "[]", "[]", '["Fall", "Spring"]', 1),
        ("CS 24000", "Programming in C", "Programming in C with emphasis on pointers, memory management, and system programming.", 3, "CS", "[\"CS 18000\"]", "[]", '["Fall", "Spring"]', 1),
        ("CS 25000", "Computer Architecture", "Introduction to computer organization and architecture. Topics include digital logic, data representation, assembly language, memory hierarchies, and performance.", 4, "CS", "[\"CS 18000\"]", "[]", '["Fall", "Spring"]', 1),
        ("CS 25100", "Data Structures and Algorithms", "Fundamental data structures and algorithms. Topics include arrays, linked lists, trees, graphs, sorting, searching, and algorithm analysis.", 3, "CS", "[\"CS 18000\", \"CS 25000\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("CS 30700", "Software Engineering I", "Introduction to software engineering. Topics include requirements, design, implementation, testing, and project management.", 3, "CS", "[\"CS 18200\", \"CS 25100\"]", "[]", '["Fall", "Spring"]', 1),
        ("CS 35400", "Operating Systems", "Introduction to operating system design and implementation. Topics include processes, threads, scheduling, synchronization, memory management, and file systems.", 3, "CS", "[\"CS 25000\", \"CS 24000\"]", "[]", '["Fall", "Spring"]', 1),
        ("CS 35500", "Introduction to Cryptography", "Fundamentals of cryptography including symmetric and asymmetric cryptography, hash functions, digital signatures, and cryptographic protocols.", 3, "CS", "[\"CS 25100\", \"MA 35100\"]", "[]", '["Fall"]', 0),
        ("CS 37300", "Data Mining and Machine Learning", "Introduction to data mining and machine learning algorithms. Topics include classification, regression, clustering, and dimensionality reduction.", 3, "CS", "[\"CS 25100\", \"STAT 35000\"]", "[]", '["Spring"]', 0),
        ("CS 40800", "Software Engineering II", "Advanced software engineering including design patterns, software architecture, and large-scale software development.", 3, "CS", "[\"CS 30700\"]", "[]", '["Fall", "Spring"]', 1),
        ("CS 42600", "Introduction to Computer Security", "Introduction to computer security principles. Topics include threats, vulnerabilities, access control, cryptography, and secure software development.", 3, "CS", "[\"CS 35400\"]", "[]", '["Fall", "Spring"]', 0),
        ("CS 45600", "Programming Languages", "Study of programming language concepts and paradigms. Topics include syntax, semantics, type systems, and implementation.", 3, "CS", "[\"CS 25100\"]", "[]", '["Spring"]', 0),
        ("CS 48300", "Introduction to Parallel Computing", "Introduction to parallel programming and high-performance computing. Topics include parallel algorithms, distributed memory, and shared memory programming.", 3, "CS", "[\"CS 35400\"]", "[]", '["Fall"]', 0),
        ("CS 48900", "Embedded Systems", "Introduction to embedded system design. Topics include microcontrollers, real-time operating systems, and hardware-software co-design.", 4, "CS", "[\"CS 25000\", \"CS 24000\"]", "[]", '["Spring"]', 0),
        ("CS 38000", "Professional Practice and Ethics in Computer Science", "Professional ethics and practice in computing.", 3, "CS", "[\"CS 30700\"]", "[]", '["Fall", "Spring"]', 1),
        ("CS 43000", "Introduction to Artificial Intelligence", "Introduction to AI including search, planning, and machine learning.", 3, "CS", "[\"CS 25100\"]", "[]", '["Fall", "Spring"]', 0),
        ("CS 42200", "Computer Networks", "Computer networking concepts including protocols and network programming.", 3, "CS", "[\"CS 35400\", \"CS 25100\"]", "[]", '["Fall", "Spring"]', 0),
        ("CS 47800", "Introduction to Cloud Computing", "Cloud computing principles and technologies.", 3, "CS", "[\"CS 35400\"]", "[]", '["Fall", "Spring"]', 0),
        ("CS 23500", "Introduction to Computer Game Development", "Introduction to game design and development.", 3, "CS", "[\"CS 18000\"]", "[]", '["Fall"]', 0),
        ("CS 33400", "Foundations of Game Development", "Advanced game development including physics engines and AI.", 3, "CS", "[\"CS 23500\", \"CS 25100\"]", "[]", '["Spring"]', 0),

        ("MA 16100", "Plane Analytic Geometry and Calculus I", "Differential calculus including limits, continuity, derivatives, and applications.", 5, "MA", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("MA 16200", "Plane Analytic Geometry and Calculus II", "Integral calculus including definite integrals, techniques of integration, and series.", 5, "MA", "[\"MA 16100\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("MA 26100", "Multivariate Calculus", "Three-dimensional calculus including partial derivatives, multiple integrals, and vector calculus.", 5, "MA", "[\"MA 16200\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("MA 26200", "Linear Algebra and Differential Equations", "Introduction to linear algebra and ordinary differential equations.", 4, "MA", "[\"MA 26100\"]", "[]", '["Fall", "Spring"]', 1),
        ("MA 35100", "Elementary Linear Algebra", "Linear algebra including matrices, vector spaces, linear transformations, and eigenvalues.", 3, "MA", "[\"MA 26100\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("MA 36600", "Ordinary Differential Equations", "Theory and solutions of ordinary differential equations.", 3, "MA", "[\"MA 26200\"]", "[]", '["Fall", "Spring"]', 1),
        ("MA 41600", "Probability", "Introduction to probability theory including random variables, distributions, and limit theorems.", 3, "MA", "[\"MA 26100\"]", "[]", '["Fall", "Spring"]', 0),

        ("STAT 35000", "Introduction to Statistics", "Introduction to statistical methods including descriptive statistics, probability, hypothesis testing, and regression.", 3, "STAT", "[\"MA 16100\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("STAT 41700", "Statistical Theory", "Theory of point estimation, hypothesis testing, and confidence intervals.", 3, "STAT", "[\"STAT 35000\", \"MA 26100\"]", "[]", '["Fall", "Spring"]', 0),
        ("STAT 42000", "Introduction to Time Series", "Time series analysis including ARIMA models, forecasting, and spectral analysis.", 3, "STAT", "[\"STAT 41700\"]", "[]", '["Spring"]', 0),

        ("PHYS 17200", "Modern Mechanics", "Introduction to classical mechanics with a focus on motion, energy, and momentum.", 4, "PH", "[\"MA 16100\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("PHYS 27200", "Electricity and Optics", "Electric fields, magnetic fields, electromagnetic waves, and optics.", 4, "PH", "[\"PHYS 17200\", \"MA 16200\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("PHYS 31000", "Intermediate Mechanics", "Advanced classical mechanics including Lagrangian and Hamiltonian mechanics.", 4, "PH", "[\"PHYS 27200\", \"MA 36600\"]", "[]", '["Fall"]', 1),
        ("PHYS 33000", "Intermediate Electricity and Magnetism", "Advanced electromagnetism including Maxwell's equations.", 3, "PH", "[\"PHYS 27200\", \"MA 26100\"]", "[]", '["Spring"]', 1),
        ("PHYS 36000", "Quantum Mechanics", "Introduction to quantum mechanics including the Schrödinger equation and applications.", 3, "PH", "[\"PHYS 31000\"]", "[]", '["Fall"]', 1),

        ("CHM 11500", "General Chemistry I", "Fundamental concepts of chemistry including atomic structure, bonding, and reactions.", 4, "CH", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("CHM 11600", "General Chemistry II", "Continuation of general chemistry including kinetics, equilibrium, and thermodynamics.", 4, "CH", "[\"CHM 11500\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("CHM 26505", "Organic Chemistry I", "Organic chemistry including structure, reactivity, and synthesis.", 3, "CH", "[\"CHM 11600\"]", "[]", '["Fall", "Spring", "Summer"]', 0),
        ("CHM 26605", "Organic Chemistry II", "Continuation of organic chemistry with emphasis on synthesis.", 3, "CH", "[\"CHM 26505\"]", "[]", '["Fall", "Spring", "Summer"]', 0),

        ("BIOL 11000", "Fundamentals of Biology", "Introduction to biological principles including cell structure, genetics, and evolution.", 4, "BI", "[]", "[]", '["Fall", "Spring"]', 1),
        ("BIOL 12100", "Biology I: Diversity, Ecology, and Behavior", "Survey of organismal diversity, ecology, and behavior.", 2, "BI", "[]", "[]", '["Fall", "Spring"]', 1),
        ("BIOL 12200", "Biology II: Development, Structure, and Function", "Development, structure, and function of plants and animals.", 2, "BI", "[\"BIOL 12100\"]", "[]", '["Fall", "Spring"]', 1),
        ("BIOL 23100", "Cell Biology", "Cell structure and function including metabolism, genetics, and signaling.", 3, "BI", "[\"BIOL 12100\", \"CHM 11500\"]", "[]", '["Fall", "Spring"]', 0),

        ("ECE 20000", "Electrical and Computer Engineering Fundamentals", "Introduction to circuit analysis, signals, and systems.", 3, "ECE", "[\"PHYS 27200\", \"MA 26200\"]", "[]", '["Fall", "Spring"]', 1),
        ("ECE 20100", "Linear Circuit Analysis I", "DC and AC circuit analysis, network theorems, and introduction to transient analysis.", 3, "ECE", "[\"ECE 20000\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("ECE 20200", "Linear Circuit Analysis II", "Transient analysis, Laplace transforms, and frequency response.", 3, "ECE", "[\"ECE 20100\"]", "[]", '["Fall", "Spring"]', 1),
        ("ECE 20800", "Electronic Devices and Design Laboratory", "Design and testing of electronic circuits with semiconductor devices.", 1, "ECE", "[]", "[\"ECE 20100\"]", '["Fall", "Spring"]', 1),
        ("ECE 25500", "Introduction to Electronic Analysis and Design", "Analysis and design of electronic circuits including amplifiers.", 3, "ECE", "[\"ECE 20200\", \"ECE 20800\"]", "[]", '["Fall", "Spring"]', 1),
        ("ECE 27000", "Introduction to Digital System Design", "Digital logic design including combinational and sequential circuits.", 3, "ECE", "[\"CS 18000\"]", "[]", '["Fall", "Spring"]', 1),
        ("ECE 30100", "Signals and Systems", "Continuous and discrete-time signals and systems, Fourier analysis, and Laplace transforms.", 3, "ECE", "[\"ECE 20200\", \"MA 36600\"]", "[]", '["Fall", "Spring"]', 1),
        ("ECE 30200", "Probabilistic Methods in Electrical Engineering", "Probability theory and its applications in electrical engineering.", 3, "ECE", "[\"ECE 30100\", \"STAT 35000\"]", "[]", '["Fall", "Spring"]', 1),
        ("ECE 30500", "Semiconductor Devices", "Physics and operation of semiconductor devices including diodes, transistors, and MOSFETs.", 3, "ECE", "[\"ECE 25500\", \"PHYS 27200\"]", "[]", '["Fall"]', 0),
        ("ECE 43700", "Computer and Digital Systems Architecture", "Advanced computer architecture including pipelines, memory hierarchy, and parallelism.", 3, "ECE", "[\"ECE 27000\", \"CS 25000\"]", "[]", '["Fall", "Spring"]', 0),

        ("ME 20000", "Therodynamics I", "Fundamental principles of thermodynamics including energy, entropy, and properties of pure substances.", 3, "ME", "[\"PHYS 17200\", \"MA 26100\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("ME 27000", "Statics and Dynamics", "Statics of rigid bodies, kinematics and kinetics of particles and rigid bodies.", 4, "ME", "[\"PHYS 17200\", \"MA 26100\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("ME 30900", "Fluid Mechanics", "Fluid properties, statics, kinematics, and dynamics of fluid flow.", 3, "ME", "[\"ME 27000\", \"ME 20000\"]", "[]", '["Fall", "Spring"]', 1),
        ("ME 31500", "Heat and Mass Transfer", "Conduction, convection, radiation, and mass transfer.", 3, "ME", "[\"ME 30900\", \"MA 36600\"]", "[]", '["Fall", "Spring"]', 1),
        ("ME 35200", "Machine Design I", "Fundamentals of mechanical design including stress analysis, deflection, and failure theory.", 3, "ME", "[\"ME 27000\"]", "[]", '["Fall", "Spring"]', 1),

        ("AE 20000", "Aerospace Engineering Analysis", "Mathematical methods for aerospace engineering including vectors, matrices, and differential equations.", 3, "AE", "[\"MA 26200\", \"PHYS 17200\"]", "[]", '["Fall", "Spring"]', 1),
        ("AE 21000", "Aerodynamics I", "Fundamentals of aerodynamics including fluid mechanics and lift generation.", 3, "AE", "[\"AE 20000\", \"ME 30900\"]", "[]", '["Fall", "Spring"]', 1),
        ("AE 22000", "Aircraft Performance", "Aircraft performance analysis including drag, thrust, and climb performance.", 3, "AE", "[\"AE 21000\"]", "[]", '["Fall", "Spring"]', 1),

        ("CE 20300", "Principles and Practice of Civil Engineering", "Introduction to civil engineering disciplines, design, and professional practice.", 3, "CE", "[\"ME 27000\", \"CHM 11600\"]", "[]", '["Fall", "Spring"]', 1),
        ("CE 29700", "Basic Mechanics I (Statics)", "Force systems, equilibrium, and structural analysis.", 3, "CE", "[\"PHYS 17200\", \"MA 26100\"]", "[]", '["Fall", "Spring"]', 1),
        ("CE 29800", "Basic Mechanics II (Dynamics)", "Kinematics and kinetics of particles and rigid bodies.", 3, "CE", "[\"CE 29700\"]", "[]", '["Fall", "Spring"]', 1),
        ("CE 31100", "Structural Analysis", "Analysis of statically determinate and indeterminate structures.", 3, "CE", "[\"CE 29700\"]", "[]", '["Fall", "Spring"]', 1),
        ("CE 34000", "Hydraulics", "Fluid mechanics and hydraulic engineering including pipe flow and open channel flow.", 3, "CE", "[\"CE 29800\", \"ME 30900\"]", "[]", '["Fall", "Spring"]', 1),

        ("IE 33000", "Engineering Economics", "Economic analysis of engineering projects including cost estimation and decision making.", 3, "IE", "[\"MA 16200\"]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("IE 37000", "Operations Research I", "Linear programming, network models, and optimization techniques.", 3, "IE", "[\"MA 35100\", \"STAT 35000\"]", "[]", '["Fall", "Spring"]', 1),
        ("IE 47400", "Industrial Control Systems", "Design and analysis of industrial control systems and automation.", 3, "IE", "[\"ECE 30100\", \"IE 37000\"]", "[]", '["Fall"]', 0),

        ("BME 20000", "Biomedical Engineering Fundamentals", "Introduction to biomedical engineering including biomechanics, bioinstrumentation, and biomaterials.", 3, "BME", "[\"PHYS 17200\", \"CHM 11500\", \"BIOL 11000\"]", "[]", '["Fall", "Spring"]', 1),
        ("BME 30000", "Biomechanics", "Mechanical behavior of biological tissues and systems.", 3, "BME", "[\"BME 20000\", \"ME 27000\"]", "[]", '["Fall", "Spring"]', 1),
        ("BME 38000", "Bioinstrumentation", "Principles of biomedical instrumentation and signal processing.", 3, "BME", "[\"BME 20000\", \"ECE 20100\"]", "[]", '["Fall", "Spring"]', 1),

        ("CHE 20000", "Chemical Engineering Fundamentals", "Introduction to chemical engineering principles including material and energy balances.", 3, "CHE", "[\"CHM 11600\", \"PHYS 17200\", \"MA 26100\"]", "[]", '["Fall", "Spring"]', 1),
        ("CHE 21100", "Introductory Chemical Reactor Analysis", "Analysis of chemical reactors including ideal reactor models.", 3, "CHE", "[\"CHE 20000\", \"MA 36600\"]", "[]", '["Fall", "Spring"]', 1),
        ("CHE 30000", "Chemical Engineering Thermodynamics", "Application of thermodynamics to chemical engineering processes.", 3, "CHE", "[\"CHE 20000\", \"ME 20000\"]", "[]", '["Fall", "Spring"]', 1),
        ("CHE 30600", "Transport Phenomena", "Momentum, heat, and mass transfer fundamentals.", 3, "CHE", "[\"CHE 30000\", \"ME 30900\"]", "[]", '["Fall", "Spring"]', 1),

        ("CSEC 27000", "Data and Application Security", "Fundamentals of data security and secure application development.", 3, "CSEC", "[\"CS 18000\"]", "[]", '["Fall", "Spring"]', 1),
        ("CSEC 37000", "Network Security", "Network security principles and practices including firewalls and intrusion detection.", 3, "CSEC", "[\"CSEC 27000\", \"ECE 30100\"]", "[]", '["Spring"]', 1),
        ("CSEC 47300", "Software Security", "Secure software development practices and vulnerability analysis.", 3, "CSEC", "[\"CSEC 27000\", \"CS 30700\"]", "[]", '["Fall"]', 1),

        ("CNIT 18000", "Introduction to Cybersecurity", "Introduction to cybersecurity principles, threats, and defenses.", 3, "CNIT", "[]", "[]", '["Fall", "Spring"]', 1),
        ("CNIT 24200", "System Vulnerability and Penetration Testing", "Penetration testing methodologies and tools.", 3, "CNIT", "[\"CNIT 18000\", \"CS 24000\"]", "[]", '["Fall"]', 1),
        ("CNIT 32000", "Policy and Law in Cybersecurity", "Cybersecurity policy, law, and ethics.", 3, "CNIT", "[\"CNIT 18000\"]", "[]", '["Spring"]', 1),
        ("CNIT 34000", "Cryptography and Network Security", "Cryptographic algorithms and network security protocols.", 3, "CNIT", "[\"CNIT 18000\", \"MA 35100\"]", "[]", '["Fall", "Spring"]', 1),

        ("ECON 11000", "Principles of Economics", "Introduction to microeconomics and macroeconomics.", 3, "ECON", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("ECON 21000", "Economic Principles and Problems", "Intermediate microeconomic and macroeconomic theory.", 3, "ECON", "[\"ECON 11000\"]", "[]", '["Fall", "Spring"]', 0),
        ("ECON 36000", "International Economics", "Theory and practice of international trade and finance.", 3, "ECON", "[\"ECON 21000\"]", "[]", '["Spring"]', 0),

        ("PSY 10000", "Introduction to Psychology", "Survey of psychology including learning, cognition, development, and social psychology.", 3, "PSY", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("PSY 12000", "Elementary Psychology", "Introduction to psychology with emphasis on experimental methods.", 3, "PSY", "[]", "[]", '["Fall", "Spring"]', 1),
        ("PSY 20000", "Introduction to Applied Psychology", "Application of psychological principles to real-world problems.", 3, "PSY", "[\"PSY 12000\"]", "[]", '["Fall", "Spring"]', 1),
        ("PSY 35000", "Abnormal Psychology", "Study of psychological disorders including etiology and treatment.", 3, "PSY", "[\"PSY 20000\"]", "[]", '["Fall", "Spring"]', 0),

        ("SOC 10000", "Introductory Sociology", "Introduction to sociological concepts and methods.", 3, "SOC", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("SOC 22000", "Social Problems", "Analysis of contemporary social problems.", 3, "SOC", "[\"SOC 10000\"]", "[]", '["Fall", "Spring"]', 1),

        ("ENGL 10600", "First-Year Composition", "College-level writing with emphasis on argumentation and critical analysis.", 4, "ENGL", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("ENGL 10800", "Accelerated First-Year Composition", "Intensive first-year composition for advanced writers.", 3, "ENGL", "[]", "[]", '["Fall", "Spring"]', 1),
        ("ENGL 30400", "Advanced Composition", "Advanced writing with emphasis on scholarly writing.", 3, "ENGL", "[\"ENGL 10600\"]", "[]", '["Fall", "Spring"]', 0),

        ("COM 11400", "Fundamentals of Speech Communication", "Principles of public speaking and oral communication.", 3, "COM", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("COM 21200", "Approaches to Cultural Studies", "Analysis of culture through communication perspectives.", 3, "COM", "[]", "[]", '["Fall", "Spring"]', 0),
        ("COM 32000", "Small Group Communication", "Theory and practice of small group communication.", 3, "COM", "[\"COM 11400\"]", "[]", '["Fall", "Spring"]', 0),

        ("HIST 15100", "American History to 1877", "Survey of American history from colonization to Reconstruction.", 3, "HIST", "[]", "[]", '["Fall", "Spring"]', 1),
        ("HIST 15200", "United States since 1877", "Survey of American history from Reconstruction to the present.", 3, "HIST", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),

        ("PHIL 11000", "Introduction to Philosophy", "Introduction to major philosophical problems and methods.", 3, "PHIL", "[]", "[]", '["Fall", "Spring"]', 1),
        ("PHIL 12000", "Ethics", "Introduction to moral philosophy and ethical theory.", 3, "PHIL", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("PHIL 26000", "Philosophy of Religion", "Philosophical issues concerning religion.", 3, "PHIL", "[\"PHIL 11000\"]", "[]", '["Fall", "Spring"]', 0),

        ("POL 13000", "Introduction to United States Politics", "Introduction to American political institutions and processes.", 3, "POL", "[]", "[]", '["Fall", "Spring", "Summer"]', 1),
        ("POL 14100", "Governments of the World", "Comparative analysis of political systems.", 3, "POL", "[]", "[]", '["Fall", "Spring"]', 1),

        ("NUR 10000", "Introduction to Nursing", "Introduction to nursing profession and healthcare.", 2, "NUR", "[]", "[]", '["Fall"]', 1),
        ("NUR 20000", "Fundamentals of Nursing", "Fundamental nursing skills and concepts.", 4, "NUR", "[\"NUR 10000\", \"BIOL 11000\", \"CHM 11500\"]", "[]", '["Spring"]', 1),
        ("NUR 30000", "Medical-Surgical Nursing I", "Nursing care of adult patients with medical-surgical conditions.", 4, "NUR", "[\"NUR 20000\"]", "[]", '["Fall"]', 1),
        ("NUR 40000", "Leadership in Nursing", "Leadership and management principles for nursing practice.", 3, "NUR", "[\"NUR 30000\"]", "[]", '["Fall"]', 1),

        ("ENGR 10000", "Engineering Seminars", "Introduction to engineering disciplines and professional development.", 1, "ENGR", "[]", "[]", '["Fall", "Spring"]', 1),
        ("ENGR 13000", "Engineering Computing", "Introduction to computing for engineers including MATLAB and Excel.", 3, "ENGR", "[\"MA 16100\"]", "[]", '["Fall", "Spring"]', 1),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO courses 
        (course_number, title, description, credits, department, prerequisites, corequisites, terms_offered, is_required)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, courses)

def main():
    conn = create_database()
    cursor = conn.cursor()
    
    populate_departments(cursor)
    populate_courses(cursor)
    populate_university_requirements(cursor)
    
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM courses")
    count = cursor.fetchone()[0]
    print(f"Database created successfully with {count} courses!")
    
    cursor.execute("SELECT COUNT(*) FROM departments")
    dept_count = cursor.fetchone()[0]
    print(f"Added {dept_count} departments!")
    
    cursor.execute("SELECT COUNT(*) FROM university_requirements")
    req_count = cursor.fetchone()[0]
    print(f"Added {req_count} university requirements!")
    
    conn.close()

if __name__ == "__main__":
    main()
