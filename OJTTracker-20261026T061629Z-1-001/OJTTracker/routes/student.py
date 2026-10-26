from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from database import get_db

bp = Blueprint("student", __name__, url_prefix="/student")

def student_row():
    return get_db().execute("SELECT * FROM students WHERE user_id=?", (session["user_id"],)).fetchone()

@bp.route("/dashboard")
def dashboard():
    student = student_row()
    if not student:
        flash("Student profile was not found. Contact the administrator.", "error")
        return render_template("student/dashboard.html", student=None, stats={})
    db = get_db()
    stats = db.execute("""SELECT COALESCE(SUM(rendered_hours),0) hours,
      SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) present,
      SUM(CASE WHEN status='late' THEN 1 ELSE 0 END) late,
      SUM(CASE WHEN status='absent' THEN 1 ELSE 0 END) absent
      FROM attendance WHERE student_id=?""", (student["id"],)).fetchone()
    required = float(student["required_ojt_hours"])
    rendered = float(stats["hours"] or 0)
    recent = db.execute("SELECT * FROM attendance WHERE student_id=? ORDER BY attendance_date DESC LIMIT 5", (student["id"],)).fetchall()
    activities = db.execute("SELECT * FROM activity_reports WHERE student_id=? ORDER BY activity_date DESC LIMIT 5", (student["id"],)).fetchall()
    return render_template("student/dashboard.html", student=student, stats=stats, rendered=rendered,
                           required=required, remaining=max(0, required-rendered),
                           progress=min(100, round(rendered/required*100, 1)) if required else 0,
                           recent=recent, activities=activities)

@bp.route("/profile", methods=["GET", "POST"])
def profile():
    student = student_row()
    if request.method == "POST" and student:
        db = get_db()
        db.execute("UPDATE students SET course=?,section=?,company_name=? WHERE id=?",
                   (request.form.get("course","").strip(), request.form.get("section","").strip(),
                    request.form.get("company_name","").strip(), student["id"]))
        db.commit()
        flash("Profile details updated.", "success")
        return redirect(url_for("student.profile"))
    user = get_db().execute("SELECT full_name,email,username FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return render_template("student/profile.html", student=student, user=user)

@bp.route("/history")
def history():
    student = student_row()
    rows = get_db().execute("SELECT * FROM attendance WHERE student_id=? ORDER BY attendance_date DESC", (student["id"],)).fetchall() if student else []
    return render_template("student/attendance_history.html", rows=rows)

@bp.route("/notifications")
def notifications():
    rows = get_db().execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC", (session["user_id"],)).fetchall()
    get_db().execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],))
    get_db().commit()
    return render_template("student/notifications.html", rows=rows)
