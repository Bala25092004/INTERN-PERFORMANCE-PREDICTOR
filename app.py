from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import numpy as np

from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import qrcode

import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_super_secret_key' # IMPORTANT: Replace with a strong, random key in production!

DATABASE = 'database.db'

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if database file exists
    if not os.path.exists(DATABASE):
        print("Creating new database...")
    else:
        print("Database already exists, checking schema...")


    # --- IMPORTANT DEVELOPMENT TIP: To reset your database schema during development ---
    # If you add new columns or change table structures, your existing database.db
    # might not update automatically due to 'CREATE TABLE IF NOT EXISTS'.
    # To force a schema update and resolve "no such column" errors:
    # 1. STOP your Flask application (if running).
    # 2. MANUALLY DELETE the 'database.db' file from your 'backend' directory.
    #    (e.g., in your file explorer, navigate to C:\Users\ADMIN\Documents\isp\backend\ and delete database.db)
    # 3. RESTART your Flask application. The init_db() function will then create a fresh database.
    #    You should see "Creating new database..." in your console.
    # Alternatively, for quick resets (use with caution as it deletes all data):
    # cursor.execute("DROP TABLE IF EXISTS feedback")
    # cursor.execute("DROP TABLE IF EXISTS tasks")
    # cursor.execute("DROP TABLE IF EXISTS attendance")
    # cursor.execute("DROP TABLE IF EXISTS students")
    # cursor.execute("DROP TABLE IF EXISTS courses")
    # cursor.execute("DROP TABLE IF EXISTS users")
    # cursor.execute("DROP TABLE IF EXISTS behaviour_ratings")
    # cursor.execute("DROP TABLE IF EXISTS student_feedback_to_admin") # New table to drop


    # Check if database file exists to print appropriate message
    if not os.path.exists(DATABASE):
        print("Creating new database...")
    else:
        print("Database already exists, checking schema...")


    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            total_expected_tasks INTEGER DEFAULT 10 -- New: For course completion calculation
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        course_id INTEGER,
        user_id INTEGER UNIQUE,

        -- NEW FIELDS
        internship_type TEXT,
        joining_date TEXT,
        ending_date TEXT,
        college_name TEXT,
        department TEXT,

        FOREIGN KEY (course_id) REFERENCES courses(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL, -- FK to students.id
            course_id INTEGER, -- New: Link task to a course
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'overdue'
            mark REAL DEFAULT 0, -- Task mark (0-100)
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL, -- FK to students.id
            date TEXT NOT NULL, -- YYYY-MM-DD
            status TEXT NOT NULL, -- 'present', 'absent'
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE(student_id, date) -- Ensure only one attendance record per student per day
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER, -- Can be NULL if general feedback
            student_id INTEGER NOT NULL, -- Link to student
            admin_id INTEGER NOT NULL, -- FK to users.id (admin)
            score REAL, -- e.g., 1-10 (general feedback score) - this might be redundant with category now
            comments TEXT,
            feedback_date TEXT NOT NULL, -- YYYY-MM-DD
            feedback_category TEXT, -- Re-added: 'Excellent', 'Good', 'Average', 'Poor'
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (admin_id) REFERENCES users(id)
        )
    ''')
    cursor.execute("""
CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    from_date TEXT,
    to_date TEXT,
    leave_type TEXT,
    reason TEXT,
    status TEXT DEFAULT 'Pending',
    FOREIGN KEY(student_id) REFERENCES students(id)
)
""")




    cursor.execute('''
CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    reason TEXT,
    from_date TEXT,
    to_date TEXT,
    status TEXT DEFAULT 'Pending',
    FOREIGN KEY(student_id) REFERENCES students(id)
)
''')

    # NEW TABLE: For student feedback to admin
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_feedback_to_admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL, -- FK to students.id
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL, -- YYYY-MM-DD HH:MM:SS
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS behaviour_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            rating INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            UNIQUE(student_id, date)
        )
    ''')
    # Add some initial data (for testing)
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'adminpass', 'admin'))
    
    # If 'intern1' user doesn't exist, create it and a corresponding student entry
    cursor.execute("SELECT id FROM users WHERE username = 'intern1'")
    intern1_user_id = cursor.fetchone()
    if not intern1_user_id:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('intern1', 'internpass', 'intern'))
        intern1_user_id = cursor.lastrowid
        cursor.execute("INSERT INTO students (unique_student_id, name, email, user_id) VALUES (?, ?, ?, ?)",
                       ('INT001', 'Intern One', 'intern1@example.com', intern1_user_id))
    
    # Add sample courses if they don't exist, with total_expected_tasks
    cursor.execute("INSERT OR IGNORE INTO courses (name, total_expected_tasks) VALUES (?, ?)", ('Web Development Basics', 10))
    cursor.execute("INSERT OR IGNORE INTO courses (name, total_expected_tasks) VALUES (?, ?)", ('Data Science Fundamentals', 8))
    cursor.execute("INSERT OR IGNORE INTO courses (name, total_expected_tasks) VALUES (?, ?)", ('Mobile App Development', 12))
    cursor.execute("INSERT OR IGNORE INTO courses (name, total_expected_tasks) VALUES (?, ?)", ('Cloud Computing Essentials', 7))
    cursor.execute("INSERT OR IGNORE INTO courses (name, total_expected_tasks) VALUES (?, ?)", ('Cybersecurity Basics', 9))
    
    # Get course IDs for sample tasks
    cursor.execute("SELECT id FROM courses WHERE name = 'Web Development Basics'")
    web_dev_course_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM courses WHERE name = 'Data Science Fundamentals'")
    data_science_course_id = cursor.fetchone()[0]

    # Update Intern One to be assigned to 'Web Development Basics'
    cursor.execute("SELECT id FROM students WHERE unique_student_id = 'INT001'")
    int001_student_id = cursor.fetchone()
    if int001_student_id:
        int001_student_id = int001_student_id[0]
        cursor.execute("UPDATE students SET course_id = ? WHERE id = ?", (web_dev_course_id, int001_student_id))
        
        # Add sample tasks for Intern One if they don't exist, linked to course
        cursor.execute("SELECT id FROM tasks WHERE student_id = ? AND title = ?", (int001_student_id, 'Complete Flask Tutorial'))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO tasks (student_id, course_id, title, description, due_date, status, mark) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (int001_student_id, web_dev_course_id, 'Complete Flask Tutorial', 'completed', '2025-08-10', 'completed', 90)) # Marked completed with a mark
        
        cursor.execute("SELECT id FROM tasks WHERE student_id = ? AND title = ?", (int001_student_id, 'Research ML Models'))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO tasks (student_id, course_id, title, description, due_date, status, mark) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (int001_student_id, web_dev_course_id, 'Research ML Models', 'Research different ML models for performance prediction.', '2025-08-05', 'completed', 85)) # Marked completed with a mark

        cursor.execute("SELECT id FROM tasks WHERE student_id = ? AND title = ?", (int001_student_id, 'Build Simple API'))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO tasks (student_id, course_id, title, description, due_date, status, mark) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (int001_student_id, web_dev_course_id, 'Build Simple API', 'Develop a basic REST API using Flask.', '2025-08-15', 'pending', 0))
        
        # Add sample attendance for Intern One
        cursor.execute("SELECT id FROM attendance WHERE student_id = ? AND date = '2025-07-20'", (int001_student_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", (int001_student_id, '2025-07-20', 'present'))
        cursor.execute("SELECT id FROM attendance WHERE student_id = ? AND date = '2025-07-21'", (int001_student_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", (int001_student_id, '2025-07-21', 'present'))
        cursor.execute("SELECT id FROM attendance WHERE student_id = ? AND date = '2025-07-22'", (int001_student_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", (int001_student_id, '2025-07-22', 'absent'))

        # Add sample feedback for Intern One (admin-to-student)
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_user_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM feedback WHERE student_id = ? AND comments LIKE '%Good work on Flask%'", (int001_student_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO feedback (student_id, admin_id, score, comments, feedback_date, feedback_category) VALUES (?, ?, ?, ?, ?, ?)",
                           (int001_student_id, admin_user_id, 8.5, 'Good work on Flask tutorial, keep it up!', '2025-07-20', 'Good'))
        cursor.execute("SELECT id FROM feedback WHERE student_id = ? AND comments LIKE '%Excellent research skills%'", (int001_student_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO feedback (student_id, admin_id, score, comments, feedback_date, feedback_category) VALUES (?, ?, ?, ?, ?, ?)",
                           (int001_student_id, admin_user_id, 9.0, 'Excellent research skills demonstrated.', '2025-07-25', 'Excellent'))

        # Add sample behaviour ratings for Intern One
        cursor.execute("SELECT id FROM behaviour_ratings WHERE student_id = ? AND date = '2025-07-20'", (int001_student_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO behaviour_ratings (student_id, date, rating, admin_id) VALUES (?, ?, ?, ?)",
                           (int001_student_id, '2025-07-20', 4, admin_user_id))
        cursor.execute("SELECT id FROM behaviour_ratings WHERE student_id = ? AND date = '2025-07-21'", (int001_student_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO behaviour_ratings (student_id, date, rating, admin_id) VALUES (?, ?, ?, ?)",
                           (int001_student_id, '2025-07-21', 5, admin_user_id))

        # Add sample student-to-admin feedback
        cursor.execute("SELECT id FROM student_feedback_to_admin WHERE student_id = ? AND subject = 'Website UI Suggestion'", (int001_student_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO student_feedback_to_admin (student_id, subject, message, timestamp) VALUES (?, ?, ?, ?)",
                           (int001_student_id, 'Website UI Suggestion', 'Consider making the navigation menu more prominent.', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        cursor.execute("SELECT id FROM student_feedback_to_admin WHERE student_id = ? AND subject = 'Query about Task 3'", (int001_student_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO student_feedback_to_admin (student_id, subject, message, timestamp) VALUES (?, ?, ?, ?)",
                           (int001_student_id, 'Query about Task 3', 'Could you provide more examples for Task 3 requirements?', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))


    conn.commit()
    conn.close()

# --- Initialize database immediately when the script runs ---
init_db()

# --- Helper function to check admin login ---
def is_admin_logged_in():
    return 'role' in session and session['role'] == 'admin'

# --- Helper function to check intern login ---
def is_intern_logged_in():
    return 'role' in session and session['role'] == 'intern'

# --- Feature Calculation Functions ---
def calculate_attendance_rate(student_db_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ?", (student_db_id,))
    total_days = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'present'", (student_db_id,))
    present_days = cursor.fetchone()[0]
    conn.close()
    return present_days / total_days if total_days > 0 else 0.0

def calculate_average_task_mark(student_db_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Only consider marks for completed tasks
    cursor.execute("SELECT AVG(mark) FROM tasks WHERE student_id = ? AND status = 'completed'", (student_db_id,))
    avg_mark = cursor.fetchone()[0]
    conn.close()
    return avg_mark if avg_mark is not None else 0.0
def mark_online_attendance(student_db_id):
    today = date.today().strftime('%Y-%m-%d')

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("""
        INSERT INTO attendance (student_id, date, status)
        VALUES (?, ?, 'present')
        ON CONFLICT(student_id, date) DO NOTHING
    """, (student_db_id, today))

    con.commit()
    con.close()

def calculate_average_feedback_score_numeric(student_db_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Map qualitative feedback to numerical values for averaging
    # Using a 0-3 scale for Poor-Excellent, then normalizing to 0-100 later if needed
    feedback_category_map = {'Poor': 0, 'Average': 1, 'Good': 2, 'Excellent': 3}
    
    cursor.execute("SELECT feedback_category FROM feedback WHERE student_id = ?", (student_db_id,))
    feedback_categories = cursor.fetchall()
    
    numeric_values = []
    for category_tuple in feedback_categories:
        category = category_tuple[0]
        if category in feedback_category_map:
            numeric_values.append(feedback_category_map[category])
            
    conn.close()
    # Convert average numeric category back to a 0-100 scale for consistency with other metrics
    # Max category value is 3 (Excellent). So (avg / 3) * 100
    avg_numeric = np.mean(numeric_values) if numeric_values else 0.0
    return (avg_numeric / 3.0) * 100.0 # Scale to 0-100

def calculate_average_behaviour_rating(student_db_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(rating) FROM behaviour_ratings WHERE student_id = ?", (student_db_id,))
    avg_rating = cursor.fetchone()[0]
    conn.close()
    # Behaviour rating is 1-5. Scale to 0-100. (avg - 1) / 4 * 100
    return ((avg_rating - 1) / 4.0) * 100.0 if avg_rating is not None else 0.0

def calculate_course_completion_percentage(student_db_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get the course_id for the student
    cursor.execute("SELECT course_id FROM students WHERE id = ?", (student_db_id,))
    student_course_id = cursor.fetchone()
    
    if not student_course_id or student_course_id[0] is None:
        conn.close()
        return 0.0 # Student not assigned to a course

    student_course_id = student_course_id[0]

    # Get total expected tasks for that course
    cursor.execute("SELECT total_expected_tasks FROM courses WHERE id = ?", (student_course_id,))
    total_expected_tasks = cursor.fetchone()[0]

    if total_expected_tasks == 0:
        conn.close()
        return 0.0 # Avoid division by zero

    # Get completed tasks for this student for this course
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE student_id = ? AND course_id = ? AND status = 'completed'", 
                   (student_db_id, student_course_id))
    completed_tasks = cursor.fetchone()[0]
    
    conn.close()
    return (completed_tasks / total_expected_tasks) * 100.0

# --- Overall Performance Calculation ---
def calculate_overall_performance_score(student_db_id):
    # Weights for each metric (adjust as needed)
    weights = {
        'attendance': 0.20, # 20%
        'task_mark': 0.30,  # 30%
        'behaviour': 0.15,  # 15%
        'feedback': 0.20,   # 20%
        'course_completion': 0.15 # 15%
    }

    # Calculate individual scaled scores (all are already 0-100)
    attendance_score = calculate_attendance_rate(student_db_id) * 100
    task_mark_score = calculate_average_task_mark(student_db_id)
    behaviour_score = calculate_average_behaviour_rating(student_db_id)
    feedback_score = calculate_average_feedback_score_numeric(student_db_id)
    course_completion_score = calculate_course_completion_percentage(student_db_id)

    # Handle cases where a metric might be N/A (e.g., no tasks, no feedback)
    # If a metric is N/A, we can treat it as 0 for score calculation, but report it as N/A in breakdown
    
    # Sum weighted scores
    overall_score = (
        attendance_score * weights['attendance'] +
        task_mark_score * weights['task_mark'] +
        behaviour_score * weights['behaviour'] +
        feedback_score * weights['feedback'] +
        course_completion_score * weights['course_completion']
    )
    
    # Ensure score is within 0-100 range
    overall_score = max(0, min(100, overall_score))

    # Determine performance category
    if overall_score >= 90:
        category = "Excellent"
    elif overall_score >= 75:
        category = "Good"
    elif overall_score >= 50:
        category = "Average"
    else:
        category = "Poor"
        
    return {
        'overall_score': round(overall_score, 2),
        'category': category,
        'breakdown': {
            'attendance': {'value': round(attendance_score, 2), 'weight': weights['attendance']},
            'task_mark': {'value': round(task_mark_score, 2), 'weight': weights['task_mark']},
            'behaviour': {'value': round(behaviour_score, 2), 'weight': weights['behaviour']},
            'feedback': {'value': round(feedback_score, 2), 'weight': weights['feedback']},
            'course_completion': {'value': round(course_completion_score, 2), 'weight': weights['course_completion']}
        }
    }


# --- Routes ---

@app.route('/')
def index():
    # Clear session on root access to ensure a fresh start for login
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # Clear session on GET request to login page to prevent automatic redirection
        session.clear()
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        selected_role = request.form['role'] # Get the selected role from the form

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        # Check credentials and selected role
        cursor.execute("SELECT id, username, role FROM users WHERE username = ? AND password = ? AND role = ?", (username, password, selected_role))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[2] # This will be the role from the DB, matching selected_role
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif session['role'] == 'intern': # Using 'intern' as the role in DB for students
                return redirect(url_for('intern_dashboard'))
        else:
            flash('Invalid credentials or role mismatch', 'error') # More specific error message
            return render_template('login.html')
    return render_template('login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Total Students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    # Pending Tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    pending_tasks_count = cursor.fetchone()[0]

    # Total Courses
    cursor.execute("SELECT COUNT(*) FROM courses")
    total_courses = cursor.fetchone()[0]

    # Attendance Summary for Today
    today_date = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'present'", (today_date,))
    today_present_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'absent'", (today_date,))
    today_absent_count = cursor.fetchone()[0]
    
    conn.close()
    return render_template('admin_dashboard.html', 
                           username=session['username'], 
                           total_students=total_students, 
                           pending_tasks=pending_tasks_count,
                           total_courses=total_courses, # Pass total courses
                           today_present_count=today_present_count, # Pass present count
                           today_absent_count=today_absent_count) # Pass absent count

@app.route('/admin/profile')
def admin_profile():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    return render_template('admin_profile.html', username=session['username'])

@app.route('/admin/add-course', methods=['GET', 'POST'])
def add_courses():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == 'POST':
        course_name = request.form['course_name']
        total_expected_tasks = request.form.get('total_expected_tasks', 10) # New: Get expected tasks
        try:
            cursor.execute("INSERT INTO courses (name, total_expected_tasks) VALUES (?, ?)", (course_name, total_expected_tasks))
            conn.commit()
            flash(f'Course "{course_name}" added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash(f'Error: Course "{course_name}" already exists.', 'error')
        except Exception as e:
            flash(f'An unexpected error occurred: {e}', 'error')
        finally:
            conn.close()
            return redirect(url_for('add_courses')) # Redirect to clear form and show message
    
    # For GET request, fetch existing courses to display
    cursor.execute("SELECT name, total_expected_tasks FROM courses ORDER BY name")
    existing_courses = cursor.fetchall()
    conn.close()

    return render_template('add_courses.html', username=session['username'], existing_courses=existing_courses)

@app.route('/admin/get_course_suggestions')
def get_course_suggestions():
    if not is_admin_logged_in():
        return jsonify([]) # Return empty list if not logged in

    query = request.args.get('q', '').lower()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM courses WHERE LOWER(name) LIKE ? ORDER BY name LIMIT 10", (f'%{query}%',))
    suggestions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(suggestions)


@app.route('/admin/course-validity')
def course_validity():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    return render_template('course_validity.html', username=session['username'])

@app.route('/admin/assignment')
def assignment():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    return render_template('assignment.html', username=session['username'])

@app.route('/admin/add-task', methods=['GET', 'POST'])
def add_task():
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == 'POST':
        assign_type = request.form['assign_type']   # single / all
        task_title = request.form['task_title']
        task_description = request.form['task_description']
        due_date = request.form['due_date']

        try:
            # 🔹 SINGLE INTERN TASK
            if assign_type == "single":
                assigned_student_id = request.form['assigned_to']

                cursor.execute(
                    "SELECT id FROM students WHERE unique_student_id=?",
                    (assigned_student_id,)
                )
                student = cursor.fetchone()

                if not student:
                    flash("Student not found", "error")
                    return redirect(url_for('add_task'))

                cursor.execute("""
                    INSERT INTO tasks (student_id, title, description, due_date, status)
                    VALUES (?, ?, ?, ?, 'pending')
                """, (student[0], task_title, task_description, due_date))

            # 🔹 ALL INTERNS TASK (🔥 BULK)
            elif assign_type == "all":
                cursor.execute("SELECT id FROM students")
                students = cursor.fetchall()

                for student in students:
                    cursor.execute("""
                        INSERT INTO tasks (student_id, title, description, due_date, status)
                        VALUES (?, ?, ?, ?, 'pending')
                    """, (student[0], task_title, task_description, due_date))

            conn.commit()
            flash("Task assigned successfully!", "success")

        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")

        finally:
            conn.close()

        return redirect(url_for('add_task'))

    # 🔹 GET DATA FOR FORM
    cursor.execute("SELECT unique_student_id, name FROM students ORDER BY name")
    students = cursor.fetchall()
    conn.close()

    return render_template(
        'add_task.html',
        username=session['username'],
        students=students
    )

@app.route('/admin/announcement')
def announcement():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    return render_template('announcement.html', username=session['username'])

@app.route('/admin/add-student', methods=['GET', 'POST'])
def add_student():
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        unique_student_id = request.form['unique_student_id']
        name = request.form['student_name']
        email = request.form['student_email']
        temp_password = request.form['temp_password']
        assigned_course_name = request.form.get('assigned_course')

        # ✅ NEW FIELDS
        internship_type = request.form['internship_type']
        joining_date = request.form['joining_date']
        ending_date = request.form['ending_date']
        college_name = request.form['college_name']
        department = request.form['department']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            # Check duplicate user
            cursor.execute("SELECT id FROM users WHERE username = ?", (unique_student_id,))
            if cursor.fetchone():
                flash('Error: Student ID already exists.', 'error')
                conn.close()
                return redirect(url_for('add_student'))

            cursor.execute("SELECT id FROM students WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Error: Email already exists.', 'error')
                conn.close()
                return redirect(url_for('add_student'))

            # Create login user
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (unique_student_id, temp_password, 'intern')
            )
            user_id = cursor.lastrowid

            # Course ID
            course_id = None
            if assigned_course_name:
                cursor.execute("SELECT id FROM courses WHERE name = ?", (assigned_course_name,))
                course = cursor.fetchone()
                if course:
                    course_id = course[0]

            # Insert student
            cursor.execute("""
                INSERT INTO students (
                    unique_student_id, name, email, course_id, user_id,
                    internship_type, joining_date, ending_date,
                    college_name, department
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                unique_student_id, name, email, course_id, user_id,
                internship_type, joining_date, ending_date,
                college_name, department
            ))

            conn.commit()
            flash("Student added successfully", "success")
            return redirect(url_for('student_list'))

        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
        finally:
            conn.close()

    # GET
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM courses")
    courses = [row[0] for row in cursor.fetchall()]
    conn.close()

    return render_template('add_student.html', courses=courses)
@app.route("/intern_download_certificate")
def intern_download_certificate():

    if session.get("role") != "intern":
        return redirect("/")

    username = session["username"]

    file_name = f"{username}_Certificate.pdf"
    return redirect(f"/static/{file_name}")

@app.route("/download_certificate")
def download_certificate():
    if session.get("role") != "intern":
        return redirect(url_for("login"))

    username = session["username"]

    # ✅ FIX: Direct DB connection
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    # Get student unique id
    cur.execute("""
        SELECT s.unique_student_id
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE u.username = ?
    """, (username,))
    
    row = cur.fetchone()
    con.close()

    if not row:
        return "❌ Student not found"

    student_unique_id = row[0]

    file_name = f"{student_unique_id}_Certificate.pdf"
    file_path = f"static/{file_name}"

    # ✅ Check if file exists
    if not os.path.exists(file_path):
        return "❌ Certificate not generated by admin yet"

    # ✅ Send file for download
    return send_file(file_path, as_attachment=True)



@app.route('/admin/student-list')
def student_list():
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Join students with courses to display course name
    cursor.execute('''
        SELECT s.unique_student_id, s.name, s.email, c.name AS course_name, s.id as student_db_id
        FROM students s
        LEFT JOIN courses c ON s.course_id = c.id
        ORDER BY s.name
    ''')
    students_data = cursor.fetchall()
    conn.close()
    return render_template('student_list.html', username=session['username'], students=students_data)

# New route for Pending Tasks
@app.route('/admin/pending-tasks')
def pending_tasks():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Fetch pending tasks, joining with students to get student name
    cursor.execute("SELECT t.title, s.name, t.due_date, t.status FROM tasks t JOIN students s ON t.student_id = s.id WHERE t.status = 'pending' ORDER BY t.due_date")
    pending_tasks_data = cursor.fetchall()
    conn.close()
    return render_template('pending_tasks.html', username=session['username'], pending_tasks=pending_tasks_data)

# Removed predict_performance as it was for ML model.
# The overall performance calculation is now done in calculate_overall_performance_score.

@app.route('/admin/attendance', methods=['GET', 'POST'])
def attendance():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    # Determine the date for which to display attendance
    selected_date = request.args.get('selected_date', datetime.now().strftime('%Y-%m-%d'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Fetch all students and their attendance status for the selected date (if recorded)
    # Note: s.id is included as record[0] for use in forms
    cursor.execute(f'''
        SELECT s.id, s.unique_student_id, s.name, a.status
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
        ORDER BY s.name
    ''', (selected_date,))
    attendance_records = cursor.fetchall()
    conn.close()

    return render_template('attendance.html', username=session['username'], current_date=selected_date, attendance_records=attendance_records)

@app.route('/admin/mark-attendance', methods=['POST'])
def mark_attendance():
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    student_db_id = request.form['student_id'] # This is the internal DB ID
    # Use .get() to avoid KeyError if 'attendance_date' is somehow missing
    date = request.form.get('attendance_date', datetime.now().strftime('%Y-%m-%d')) 
    status = request.form['status'] # 'present', 'absent', or 'not_recorded'

    if not date: # If date is still None or empty after .get()
        flash('Error: Attendance date was not provided.', 'error')
        return redirect(url_for('attendance'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        if status == 'not_recorded':
            # Delete the attendance record if 'Clear Status' is clicked
            cursor.execute("DELETE FROM attendance WHERE student_id = ? AND date = ?", (student_db_id, date))
            flash(f'Attendance for student ID {student_db_id} on {date} cleared.', 'info')
        else:
            # Check if an attendance record for this student and date already exists
            cursor.execute("SELECT id FROM attendance WHERE student_id = ? AND date = ?", (student_db_id, date))
            existing_record = cursor.fetchone()

            if existing_record:
                # Update existing record
                cursor.execute("UPDATE attendance SET status = ? WHERE id = ?", (status, existing_record[0]))
                flash(f'Attendance for student ID {student_db_id} on {date} updated to {status}.', 'success')
            else:
                # Insert new record
                cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", (student_db_id, date, status))
                flash(f'Attendance for student ID {student_db_id} on {date} marked as {status}.', 'success')
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f'Error marking attendance: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('attendance', selected_date=date)) # Redirect back to the attendance page, preserving date


@app.route('/admin/add-feedback', methods=['GET', 'POST'])
def add_feedback():
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # get interns list
    cur.execute("SELECT id, name, unique_student_id FROM students")
    students = cur.fetchall()

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        feedback_comments = request.form.get('feedback')  # ✅ FIXED

        cur.execute("""
    INSERT INTO feedback (student_id, admin_id, comments, feedback_date, feedback_category)
    VALUES (?, ?, ?, ?, ?)
""", (
    student_id,
    session['user_id'],
    feedback_comments,
    datetime.now().strftime('%Y-%m-%d'),
    "Good"
))


        conn.commit()
        flash("Feedback submitted successfully ✅", "success")
        return redirect(url_for('add_feedback'))

    conn.close()
    return render_template(
        'add_feedback.html',
        students=students,
        username=session.get('username')
    )

    
    cursor.execute("SELECT unique_student_id, name FROM students ORDER BY name")
    students = cursor.fetchall()
    conn.close()
    return render_template('add_feedback.html', username=session['username'], students=students)

@app.route('/admin/behaviour-rating', methods=['GET', 'POST'])
def add_behaviour_rating():
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get interns list
    cur.execute("SELECT id, name FROM students")
    students = cur.fetchall()

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        rating = request.form.get('rating')
        comments = request.form.get('comments')  # ✅ matches HTML
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Validation
        if not student_id or not rating:
            flash("Please select intern and rating", "error")
            return redirect(url_for('add_behaviour_rating'))

        # Insert behaviour rating
        cur.execute("""
    INSERT INTO behaviour_ratings (student_id, date, rating, admin_id)
    VALUES (?, ?, ?, ?)
""", (
    student_id,
    datetime.now().strftime('%Y-%m-%d'),
    rating,
    session['user_id']
))


        conn.commit()
        conn.close()

        flash("Behaviour rating saved successfully ✅", "success")
        return redirect(url_for('add_behaviour_rating'))

    conn.close()
    return render_template(
        'add_behaviour_rating.html',
        students=students,
        username=session.get('username')
    )


@app.route('/admin/performance')
def admin_performance_overview():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT id, unique_student_id, name FROM students")
    rows = cur.fetchall()
    conn.close()

    performance_summaries = []
    for r in rows:
        score = calculate_overall_performance_score(r[0])
        performance_summaries.append({
            "unique_student_id": r[1],
            "name": r[2],
            "overall_score": score["overall_score"],
            "category": score["category"]
        })

    return render_template(
        "admin_performance_overview.html",
        performance_summaries=performance_summaries
    )


@app.route('/admin/view-student-feedback')
def admin_view_student_feedback():
    if not is_admin_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sf.subject, sf.message, sf.timestamp, s.name AS student_name, s.unique_student_id
        FROM student_feedback_to_admin sf
        JOIN students s ON sf.student_id = s.id
        ORDER BY sf.timestamp DESC
    ''')
    student_feedback_records = cursor.fetchall()
    conn.close()
    return render_template('admin_view_student_feedback.html', 
                           username=session['username'], 
                           student_feedback_records=student_feedback_records)

# --- NEW ROUTE: Admin Task Completion ---
@app.route('/admin/complete-tasks', methods=['GET', 'POST'])
def admin_complete_tasks():
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == 'POST':
        tasks_to_update = 0
        for key, value in request.form.items():
            if key.startswith('completed_task_') and value == 'on':
                task_id = key.replace('completed_task_', '')
                mark_key = f'mark_{task_id}'
                mark = request.form.get(mark_key, 0) # Get mark, default to 0 if not provided
                
                try:
                    mark = float(mark)
                    if not (0 <= mark <= 100):
                        flash(f'Warning: Mark for task {task_id} must be between 0 and 100. Not updated.', 'warning')
                        continue # Skip this task if mark is invalid
                except ValueError:
                    flash(f'Warning: Invalid mark for task {task_id}. Not updated.', 'warning')
                    continue # Skip if mark is not a valid number

                try:
                    cursor.execute("UPDATE tasks SET status = 'completed', mark = ? WHERE id = ? AND status = 'pending'", (mark, task_id))
                    if cursor.rowcount > 0:
                        tasks_to_update += 1
                except Exception as e:
                    flash(f'Error updating task {task_id}: {e}', 'error')
        
        conn.commit()
        if tasks_to_update > 0:
            flash(f'{tasks_to_update} task(s) marked as completed and marks assigned!', 'success')
        else:
            flash('No tasks were updated.', 'info')
        
        conn.close()
        return redirect(url_for('admin_complete_tasks'))

    # GET request: Display all pending tasks
    cursor.execute('''
        SELECT t.id, t.title, t.description, t.due_date, s.name AS student_name, s.unique_student_id
        FROM tasks t
        JOIN students s ON t.student_id = s.id
        WHERE t.status = 'pending'
        ORDER BY t.due_date, s.name
    ''')
    pending_tasks = cursor.fetchall()
    conn.close()
    return render_template('complete_tasks.html', username=session['username'], pending_tasks=pending_tasks)


@app.route('/student/dashboard')
def intern_dashboard():

    # 🔐 Intern login check
    if not is_intern_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # -------------------------
    # BASIC DEFAULT VALUES
    # -------------------------
    assigned_tasks = []
    suggested_courses = []
    today_attendance_status = "Not Recorded"
    overall_performance_data = {'overall_score': 0, 'category': 'N/A'}
    student_profile_data = {}
    certificate_eligible = False
    attendance_percentage = 0

    # -------------------------
    # GET STUDENT DATA
    # -------------------------
    cursor.execute(
        "SELECT id, name, email FROM students WHERE user_id = ?",
        (session['user_id'],)
    )
    student_data_row = cursor.fetchone()

    if student_data_row:
        current_student_db_id = student_data_row[0]

        student_profile_data = {
            'id': current_student_db_id,
            'name': student_data_row[1],
            'email': student_data_row[2]
        }

        # -------------------------
        # TASKS
        # -------------------------
        cursor.execute("""
            SELECT title, description, due_date, status, mark
            FROM tasks
            WHERE student_id = ?
            ORDER BY due_date
        """, (current_student_db_id,))
        assigned_tasks = cursor.fetchall()

        # -------------------------
        # COURSES
        # -------------------------
        cursor.execute("SELECT name FROM courses ORDER BY name")
        suggested_courses = [row[0] for row in cursor.fetchall()]

        # -------------------------
        # TODAY ATTENDANCE
        # -------------------------
        today_date = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT status
            FROM attendance
            WHERE student_id = ? AND date = ?
        """, (current_student_db_id, today_date))
        attendance_result = cursor.fetchone()
        if attendance_result:
            today_attendance_status = attendance_result[0]

        # -------------------------
        # ATTENDANCE %
        # -------------------------
        cursor.execute("""
            SELECT COUNT(*) FROM attendance WHERE student_id = ?
        """, (current_student_db_id,))
        total_days = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE student_id = ? AND status = 'present'
        """, (current_student_db_id,))
        present_days = cursor.fetchone()[0]

        if total_days > 0:
            attendance_percentage = round((present_days / total_days) * 100, 2)

        # -------------------------
        # PERFORMANCE SCORE
        # -------------------------
        overall_performance_data = calculate_overall_performance_score(
            current_student_db_id
        )

        # -------------------------
        # 🎓 CERTIFICATE ELIGIBILITY
        # -------------------------
        if attendance_percentage >= 75 and overall_performance_data['overall_score'] >= 60:
            certificate_eligible = True

    conn.close()

    # -------------------------
    # RENDER DASHBOARD
    # -------------------------
    return render_template(
        'intern_dashboard.html',
        username=session['username'],
        tasks=assigned_tasks,
        suggested_courses=suggested_courses,
        today_attendance_status=today_attendance_status,
        predicted_performance=overall_performance_data['category'],
        overall_score=overall_performance_data['overall_score'],
        attendance_percentage=attendance_percentage,
        student_profile_data=student_profile_data,
        certificate_eligible=certificate_eligible
    )

# --- Student-specific Routes for Navigation ---

@app.route('/student/tasks')
def intern_tasks():
    if not is_intern_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
    student_id_row = cursor.fetchone()
    tasks = []
    if student_id_row:
        current_student_db_id = student_id_row[0]
        cursor.execute("SELECT title, description, due_date, status, mark FROM tasks WHERE student_id = ? ORDER BY due_date", (current_student_db_id,))
        tasks = cursor.fetchall()
    conn.close()
    return render_template('intern_tasks.html', username=session['username'], tasks=tasks)

@app.route('/student/attendance')
def intern_attendance():
    if not is_intern_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
    student_id_row = cursor.fetchone()
    attendance_records = []
    if student_id_row:
        current_student_db_id = student_id_row[0]
        # Fetch all attendance records for the student
        cursor.execute("SELECT date, status FROM attendance WHERE student_id = ? ORDER BY date DESC", (current_student_db_id,))
        attendance_records = cursor.fetchall()
    conn.close()
    return render_template('intern_attendance.html', username=session['username'], attendance_records=attendance_records)


@app.route('/student/courses')
def intern_courses():
    if not is_intern_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM courses ORDER BY name")
    suggested_courses = [row[0] for row in cursor.fetchall()]
    conn.close()
    return render_template('intern_courses.html', username=session['username'], suggested_courses=suggested_courses)

@app.route('/student/performance') # This is now the factor-wise analysis page for the intern
def intern_performance():
    if not is_intern_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
    student_id_row = cursor.fetchone()
    
    performance_data = None
    average_task_mark = 0.0 # Initialize
    if student_id_row:
        current_student_db_id = student_id_row[0]
        performance_data = calculate_overall_performance_score(current_student_db_id)
        average_task_mark = calculate_average_task_mark(current_student_db_id)
        
    conn.close()
    return render_template('intern_performance.html', 
                           username=session['username'], 
                           performance_data=performance_data,
                           average_task_mark=round(average_task_mark, 2)) # Pass average task mark

@app.route('/student/profile')
def intern_profile():
    if not is_intern_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Fetch student's profile details
    cursor.execute("SELECT s.unique_student_id, s.name, s.email, c.name FROM students s LEFT JOIN courses c ON s.course_id = c.id WHERE s.user_id = ?", (session['user_id'],))
    profile_data = cursor.fetchone()
    conn.close()

    student_profile = {}
    if profile_data:
        student_profile = {
            'unique_student_id': profile_data[0],
            'name': profile_data[1],
            'email': profile_data[2],
            'course': profile_data[3] if profile_data[3] else 'Not Assigned'
        }
    return render_template('intern_profile.html', username=session['username'], student_profile=student_profile)

@app.route('/student/feedback') # This is for admin-to-student feedback
def intern_feedback():
    if not is_intern_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
    student_id_row = cursor.fetchone()
    feedback_records = []
    if student_id_row:
        current_student_db_id = student_id_row[0]
        cursor.execute('''
            SELECT f.comments, f.score, f.feedback_date, t.title AS task_title, u.username AS admin_username, f.id AS feedback_id, f.feedback_category
            FROM feedback f
            LEFT JOIN tasks t ON f.task_id = t.id
            JOIN users u ON f.admin_id = u.id
            WHERE f.student_id = ? ORDER BY f.feedback_date DESC
        ''', (current_student_db_id,))
        feedback_records = cursor.fetchall()
    conn.close()
    return render_template('intern_feedback.html', username=session['username'], feedback_records=feedback_records)

@app.route('/student/send-feedback', methods=['GET', 'POST'])
def intern_send_feedback():
    if not is_intern_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == 'POST':
        subject = request.form['subject']
        message = request.form['message']
        student_id = None
        
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        student_id_row = cursor.fetchone()
        if student_id_row:
            student_id = student_id_row[0]
        
        if student_id:
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT INTO student_feedback_to_admin (student_id, subject, message, timestamp) VALUES (?, ?, ?, ?)",
                               (student_id, subject, message, timestamp))
                conn.commit()
                flash('Your feedback has been sent to the admin successfully!', 'success')
                return redirect(url_for('intern_send_feedback'))
            except Exception as e:
                conn.rollback()
                flash(f'An error occurred while sending feedback: {e}', 'error')
        else:
            flash('Could not find your student profile. Please contact support.', 'error')
        conn.close()
        return redirect(url_for('intern_send_feedback'))



    conn.close()
    return render_template('intern_send_feedback.html', username=session['username'])



@app.route('/student/leave-permission', methods=['GET','POST'])
def intern_leave_permission():
    if not is_intern_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Get student id
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
    student_row = cursor.fetchone()
    student_id = student_row[0]

    # ---------- POST : Submit Leave ----------
    if request.method == 'POST':
        from_date = request.form.get('from_date')
        to_date   = request.form.get('to_date')
        leave_type = request.form.get('leave_type')
        reason    = request.form.get('reason')

        # ✅ Validation
        if not from_date or not to_date or not leave_type or not reason:
            flash("All fields required!", "error")
            return redirect(url_for('intern_leave_permission'))

        # ✅ Insert into DB
        cursor.execute("""
            INSERT INTO leave_requests
            (student_id, from_date, to_date, leave_type, reason, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        """, (student_id, from_date, to_date, leave_type, reason))

        conn.commit()
        flash("Leave request submitted successfully ✅", "success")
        return redirect(url_for('intern_leave_permission'))

    # ---------- GET : Show My Leave Requests ----------
    cursor.execute("""
        SELECT from_date, to_date, leave_type, reason, status
        FROM leave_requests
        WHERE student_id = ?
        ORDER BY id DESC
    """, (student_id,))
    leave_requests = cursor.fetchall()

    conn.close()

    return render_template(
        'intern_leave_permission.html',
        username=session['username'],
        leave_requests=leave_requests
    )



@app.route('/admin/leave-requests')
def admin_leave_requests():
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lr.id, s.name, s.unique_student_id,
               lr.reason, lr.from_date, lr.to_date, lr.status
        FROM leave_requests lr
        JOIN students s ON lr.student_id = s.id
        ORDER BY lr.id DESC
    """)
    leave_requests = cursor.fetchall()
    conn.close()

    return render_template('admin_leave_requests.html',
                           leave_requests=leave_requests)



@app.route('/admin/update-leave/<int:leave_id>/<string:action>')
def update_leave_status(leave_id, action):
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    if action not in ['Approved','Rejected']:
        return "Invalid Action"

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE leave_requests
        SET status = ?
        WHERE id = ?
    """, (action, leave_id))
    conn.commit()
    conn.close()

    flash(f"Leave request {action} successfully ✅", "success")
    return redirect(url_for('admin_leave_requests'))



@app.route('/intern/course/<course_name>')
def intern_course_details(course_name):

    # 🔐 Check login using role (NOT logged_in)
    if 'role' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'intern':
        return redirect(url_for('login'))

    return render_template(
        'course_details.html',
        course_name=course_name
    )
@app.route("/admin_generate_certificate/<string:student_unique_id>")
def admin_generate_certificate(student_unique_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id, s.name, s.unique_student_id, c.name
        FROM students s
        LEFT JOIN courses c ON s.course_id = c.id
        WHERE s.unique_student_id = ?
    """, (student_unique_id,))
    
    student = cursor.fetchone()
    conn.close()

    if not student:
        return "❌ Student not found"

    student_db_id = student[0]
    student_name = student[1]
    student_unique_id = student[2]
    course_name = student[3] if student[3] else "Internship Program"

    performance = calculate_overall_performance_score(student_db_id)

    if performance['category'] not in ("Excellent", "Good"):
        return "❌ Intern not eligible for certificate"

    today = datetime.now().strftime("%d %B %Y")

    file_name = f"{student_unique_id}_Certificate.pdf"
    file_path = f"static/{file_name}"

    c = canvas.Canvas(file_path, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(w/2, h-120, "INTERNSHIP CERTIFICATE")
    c.setFont("Helvetica", 14)
    c.drawCentredString(w/2, h-200, "This is to certify that")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w/2, h-240, student_name)
    c.setFont("Helvetica", 14)
    c.drawCentredString(w/2, h-280, f"has successfully completed the {course_name}")
    c.drawCentredString(w/2, h-320, f"Performance: {performance['category']}")
    c.drawCentredString(w/2, h-360, f"Date: {today}")
    c.drawString(70, 120, "Authorized Signatory")
    c.drawString(w-180, 120, "Company Seal")
    c.save()

    flash("Certificate Generated Successfully ✅", "success")
    return redirect(url_for("student_list"))



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
@app.route('/admin/edit-student/<string:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        college = request.form['college_name']
        department = request.form['department']

        cur.execute("""
            UPDATE students
            SET name = ?, email = ?, college_name = ?, department = ?
            WHERE unique_student_id = ?
        """, (name, email, college, department, student_id))

        con.commit()
        con.close()

        flash("Student updated successfully", "success")
        return redirect(url_for('student_list'))

    student = cur.execute("""
        SELECT unique_student_id, name, email, college_name, department
        FROM students
        WHERE unique_student_id = ?
    """, (student_id,)).fetchone()

    con.close()
    return render_template('edit_student.html', student=student)
@app.route('/admin/delete-student/<string:student_id>', methods=['POST'])
def delete_student(student_id):
    if not is_admin_logged_in():
        return redirect(url_for('login'))

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute(
        "DELETE FROM students WHERE unique_student_id = ?",
        (student_id,)
    )

    con.commit()
    con.close()

    flash("Student deleted successfully", "success")
    return redirect(url_for('student_list'))

if __name__ == '__main__':
    app.run(debug=True)

