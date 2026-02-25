from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_NAME = "database.db"


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_no TEXT NOT NULL UNIQUE,
        department TEXT NOT NULL,
        semester TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS subject_marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject_code TEXT NOT NULL,
        subject_name TEXT NOT NULL,
        attendance REAL NOT NULL,
        internal_marks REAL NOT NULL,
        external_marks REAL NOT NULL,
        total REAL NOT NULL,
        grade TEXT NOT NULL,
        grade_point REAL NOT NULL,
        result TEXT NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )
    """)

    conn.commit()
    conn.close()


def grade_from_total(total: float):
    # Simple common mapping (you can change later)
    if total >= 90:
        return "O", 10, "PASS"
    elif total >= 80:
        return "A+", 9, "PASS"
    elif total >= 70:
        return "A", 8, "PASS"
    elif total >= 60:
        return "B+", 7, "PASS"
    elif total >= 50:
        return "B", 6, "PASS"
    elif total >= 45:
        return "C", 5, "PASS"
    elif total >= 40:
        return "P", 4, "PASS"
    else:
        return "F", 0, "FAIL"


def calc_cgpa(grade_points):
    if not grade_points:
        return 0.0
    return round(sum(grade_points) / len(grade_points), 2)


@app.route("/")
def home():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM students")
    total_students = cur.fetchone()["c"]
    conn.close()
    return render_template("home.html", total_students=total_students)

@app.route("/add-student", methods=["GET", "POST"])
def add_student():
    if request.method == "GET":
        return render_template("add_student.html")

    name = request.form.get("name", "").strip()
    roll_no = request.form.get("roll_no", "").strip()
    department = request.form.get("department", "").strip()
    semester = request.form.get("semester", "").strip()

    subject_code_list = request.form.getlist("subject_code[]")
    subject_name_list = request.form.getlist("subject_name[]")
    attendance_list   = request.form.getlist("attendance[]")
    internal_list     = request.form.getlist("internal_marks[]")
    external_list     = request.form.getlist("external_marks[]")

    valid_subjects = []
    for i in range(len(subject_code_list)):
        code = (subject_code_list[i] or "").strip()
        sname = (subject_name_list[i] or "").strip()

        if not code and not sname:
            continue

        try:
            att = float(attendance_list[i])
            internal = float(internal_list[i])
            external = float(external_list[i])
        except:
            return "Please enter valid numbers for attendance/internal/external."

        total = internal + external
        grade, gp, result = grade_from_total(total)
        valid_subjects.append((code, sname, att, internal, external, total, grade, gp, result))

    if len(valid_subjects) == 0:
        return "Add at least 1 subject."

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO students (name, roll_no, department, semester) VALUES (?, ?, ?, ?)",
            (name, roll_no, department, semester),
        )
        student_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return render_template("add_student.html", error="Roll number already exists! Use a unique roll number.")
    for code, sname, att, internal, external, total, grade, gp, result in valid_subjects:
        cur.execute(
            """
            INSERT INTO subject_marks
            (student_id, subject_code, subject_name, attendance, internal_marks, external_marks,
             total, grade, grade_point, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, code, sname, att, internal, external, total, grade, gp, result),
        )

    conn.commit()
    conn.close()
    return redirect(url_for("students_list"))

@app.route("/students")
def students_list():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students ORDER BY id DESC")
    students = cur.fetchall()
    conn.close()
    return render_template("students.html", students=students)


@app.route("/view-marks/<int:student_id>")
def view_marks(student_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM students WHERE id=?", (student_id,))
    student = cur.fetchone()

    cur.execute("""
        SELECT subject_code, subject_name, attendance, internal_marks, external_marks,
               total, grade, grade_point, result
        FROM subject_marks
        WHERE student_id=?
        ORDER BY id ASC
    """, (student_id,))
    marks = cur.fetchall()

    gps = [row["grade_point"] for row in marks]
    cgpa = calc_cgpa(gps)

    conn.close()
    return render_template("view_marks.html", student=student, marks=marks, cgpa=cgpa)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5001)