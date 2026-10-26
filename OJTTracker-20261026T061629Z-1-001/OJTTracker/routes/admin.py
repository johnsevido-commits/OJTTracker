from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from database import get_db
from services.notification_service import notify, audit

bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.route("/")
def dashboard():
    db = get_db()
    stats = {
      "students": db.execute("SELECT COUNT(*) n FROM students s JOIN users u ON s.user_id=u.id WHERE u.account_status='active'").fetchone()["n"],
      "attendance": db.execute("SELECT COUNT(*) n FROM attendance").fetchone()["n"],
      "absent": db.execute("SELECT COUNT(*) n FROM attendance WHERE status='absent'").fetchone()["n"],
      "pending": db.execute("SELECT COUNT(*) n FROM activity_reports WHERE status='submitted'").fetchone()["n"],
    }
    latest = db.execute("""SELECT a.*,u.full_name,s.student_number FROM attendance a
       JOIN students s ON a.student_id=s.id JOIN users u ON s.user_id=u.id
       ORDER BY a.attendance_date DESC,a.id DESC LIMIT 8""").fetchall()
    return render_template("admin/dashboard.html", stats=stats, latest=latest)

@bp.route("/students")
def students():
    rows = get_db().execute("""SELECT u.id user_id,u.full_name,u.username,u.email,u.account_status,
      s.id student_id,s.student_number,s.course,s.section,s.company_name,s.required_ojt_hours
      FROM users u JOIN students s ON u.id=s.user_id ORDER BY u.full_name""").fetchall()
    return render_template("admin/students.html", rows=rows)

@bp.route("/students/new", methods=["GET", "POST"])
@bp.route("/students/<int:user_id>/edit", methods=["GET", "POST"])
def student_form(user_id=None):
    db = get_db()
    user = db.execute("SELECT u.*,s.id student_id,s.student_number,s.course,s.section,s.company_name,s.required_ojt_hours FROM users u LEFT JOIN students s ON s.user_id=u.id WHERE u.id=? AND u.role='student'", (user_id,)).fetchone() if user_id else None
    if request.method == "POST":
        f = request.form
        full_name, username, email = f.get("full_name","").strip(), f.get("username","").strip(), f.get("email","").strip().lower()
        try:
            required = max(0, float(f.get("required_ojt_hours",486)))
        except ValueError:
            required = 486
        if not all([full_name, username, email]):
            flash("Name, username, and email are required.", "error")
        elif user_id:
            try:
                db.execute("UPDATE users SET full_name=?,username=?,email=?,account_status=? WHERE id=?",
                           (full_name, username, email, f.get("account_status","active"), user_id))
                db.execute("UPDATE students SET student_number=?,course=?,section=?,company_name=?,required_ojt_hours=? WHERE user_id=?",
                           (f.get("student_number","").strip(),f.get("course","BSIS"),f.get("section",""),f.get("company_name",""),required,user_id))
                db.commit()
                audit(session["user_id"], "student_update", "user", user_id, "Updated student profile")
                flash("Student updated.", "success")
                return redirect(url_for("admin.students"))
            except Exception:
                db.rollback()
                flash("Could not update student. Check for duplicate username, email, or student number.", "error")
        else:
            password = f.get("password","")
            if len(password) < 8:
                flash("New student password must be at least 8 characters.", "error")
            else:
                try:
                    cur = db.execute("INSERT INTO users(full_name,username,email,password_hash,role) VALUES(?,?,?,?, 'student')",
                                     (full_name,username,email,generate_password_hash(password)))
                    db.execute("INSERT INTO students(user_id,student_number,course,section,company_name,required_ojt_hours) VALUES(?,?,?,?,?,?)",
                               (cur.lastrowid,f.get("student_number","").strip(),f.get("course","BSIS"),f.get("section",""),f.get("company_name",""),required))
                    db.commit()
                    audit(session["user_id"], "student_create", "user", cur.lastrowid, "Created student account")
                    flash("Student account created.", "success")
                    return redirect(url_for("admin.students"))
                except Exception:
                    db.rollback()
                    flash("Could not create student. Check for duplicate username, email, or student number.", "error")
    return render_template("admin/student_form.html", student=user)

@bp.route("/activities")
def activities():
    rows = get_db().execute("""SELECT ar.*,u.full_name,s.student_number FROM activity_reports ar
       JOIN students s ON ar.student_id=s.id JOIN users u ON s.user_id=u.id ORDER BY ar.submitted_at DESC""").fetchall()
    return render_template("admin/activities.html", rows=rows)

@bp.route("/activities/<int:report_id>/review", methods=["POST"])
def review_activity(report_id):
    status = request.form.get("status")
    feedback = request.form.get("feedback","").strip()
    if status not in ("approved","rejected") or (status == "rejected" and not feedback):
        flash("Choose a valid status and provide a reason when rejecting.", "error")
        return redirect(url_for("admin.activities"))
    db = get_db()
    row = db.execute("SELECT ar.*,s.user_id FROM activity_reports ar JOIN students s ON ar.student_id=s.id WHERE ar.id=?", (report_id,)).fetchone()
    if not row:
        flash("Report not found.", "error")
    else:
        db.execute("UPDATE activity_reports SET status=?,coordinator_feedback=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (status,feedback,report_id))
        db.commit()
        notify(row["user_id"], f"Activity report {status}", feedback or "Your activity report was approved.")
        audit(session["user_id"], "activity_review", "activity_report", report_id, status)
        flash("Activity report reviewed.", "success")
    return redirect(url_for("admin.activities"))

@bp.route("/workplaces", methods=["GET","POST"])
def workplaces():
    db = get_db()
    workplace = db.execute("SELECT * FROM workplaces ORDER BY id LIMIT 1").fetchone()
    if request.method == "POST":
        f = request.form
        try:
            lat = float(f["latitude"]) if f.get("latitude","").strip() else None
            lon = float(f["longitude"]) if f.get("longitude","").strip() else None
            radius = float(f.get("allowed_radius_meters",150))
            accuracy = float(f.get("minimum_gps_accuracy_meters",100))
            if (lat is None) != (lon is None) or (lat is not None and not (-90<=lat<=90 and -180<=lon<=180)) or radius <= 0 or accuracy <= 0:
                raise ValueError
        except ValueError:
            flash("Check coordinates, radius, and accuracy values.", "error")
            return render_template("admin/workplaces.html", workplace=workplace)
        enabled = 1 if f.get("geofencing_enabled") == "on" else 0
        if workplace:
            db.execute("""UPDATE workplaces SET workplace_name=?,address=?,latitude=?,longitude=?,allowed_radius_meters=?,
              geofencing_enabled=?,minimum_gps_accuracy_meters=? WHERE id=?""",
              (f.get("workplace_name","").strip(),f.get("address","").strip(),lat,lon,radius,enabled,accuracy,workplace["id"]))
        else:
            db.execute("""INSERT INTO workplaces(workplace_name,address,latitude,longitude,allowed_radius_meters,geofencing_enabled,minimum_gps_accuracy_meters)
              VALUES(?,?,?,?,?,?,?)""", (f.get("workplace_name","").strip(),f.get("address","").strip(),lat,lon,radius,enabled,accuracy))
        db.commit()
        audit(session["user_id"], "workplace_update", "workplace", workplace["id"] if workplace else None, "Updated workplace/GPS settings")
        flash("Workplace settings saved.", "success")
        return redirect(url_for("admin.workplaces"))
    return render_template("admin/workplaces.html", workplace=workplace)

@bp.route("/attendance-settings", methods=["GET","POST"])
def attendance_settings():
    db = get_db()
    settings = {r["key"]:r["value"] for r in db.execute("SELECT key,value FROM settings")}
    if request.method == "POST":
        start = request.form.get("official_start_time","08:00")
        try:
            from datetime import time
            time.fromisoformat(start)
            late = int(request.form.get("late_after_minutes","60"))
            daily = float(request.form.get("daily_required_hours","8"))
            if late < 0 or daily < 0 or daily > 24: raise ValueError
        except ValueError:
            flash("Enter valid work start time and non-negative hour/minute values.", "error")
            return render_template("admin/attendance_settings.html", settings=settings)
        for key,value in [("official_start_time",start),("late_after_minutes",str(late)),("daily_required_hours",str(daily))]:
            db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key,value))
        db.commit()
        audit(session["user_id"], "attendance_settings_update", "settings", None, f"start={start}; late={late}")
        flash("Attendance rules updated.", "success")
        return redirect(url_for("admin.attendance_settings"))
    return render_template("admin/attendance_settings.html", settings=settings)

@bp.route("/gps-map")
def gps_map():
    rows = get_db().execute("""SELECT a.*,u.full_name,s.student_number FROM attendance a
      JOIN students s ON a.student_id=s.id JOIN users u ON s.user_id=u.id
      WHERE a.time_in_latitude IS NOT NULL OR a.time_out_latitude IS NOT NULL
      ORDER BY a.attendance_date DESC LIMIT 300""").fetchall()
    return render_template("admin/gps_map.html", rows=rows)

@bp.route("/audit-logs")
def audit_logs():
    rows = get_db().execute("""SELECT al.*,u.full_name FROM audit_logs al LEFT JOIN users u ON al.actor_user_id=u.id
      ORDER BY al.created_at DESC LIMIT 300""").fetchall()
    return render_template("admin/audit_logs.html", rows=rows)

@bp.route("/attendance")
def attendance():
    rows = get_db().execute("""SELECT a.*,u.full_name,s.student_number FROM attendance a
      JOIN students s ON a.student_id=s.id JOIN users u ON s.user_id=u.id
      ORDER BY a.attendance_date DESC LIMIT 500""").fetchall()
    return render_template("admin/attendance.html", rows=rows)
