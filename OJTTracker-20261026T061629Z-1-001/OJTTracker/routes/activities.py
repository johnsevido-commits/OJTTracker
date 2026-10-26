from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db
from services.notification_service import notify, audit

bp = Blueprint("activities", __name__, url_prefix="/activities")

def current_student():
    return get_db().execute("SELECT * FROM students WHERE user_id=?", (session["user_id"],)).fetchone()

@bp.route("/")
def list_activities():
    student = current_student()
    rows = get_db().execute("SELECT * FROM activity_reports WHERE student_id=? ORDER BY activity_date DESC",
                            (student["id"],)).fetchall() if student else []
    return render_template("student/activities.html", rows=rows)

@bp.route("/new", methods=["GET", "POST"])
def new():
    student = current_student()
    if not student:
        flash("Student profile not found.", "error")
        return redirect(url_for("student.dashboard"))
    if request.method == "POST":
        form = request.form
        try:
            hours = float(form.get("hours_spent", "0"))
            if not 0 <= hours <= 24:
                raise ValueError
        except ValueError:
            flash("Hours must be between 0 and 24.", "error")
            return render_template("student/activity_form.html")
        if not form.get("activity_date") or not form.get("title","").strip() or not form.get("description","").strip():
            flash("Date, title, and description are required.", "error")
            return render_template("student/activity_form.html")
        cur = get_db().execute("""INSERT INTO activity_reports(student_id,activity_date,title,description,skills_learned,challenges,hours_spent)
          VALUES(?,?,?,?,?,?,?)""", (student["id"], form["activity_date"], form["title"].strip(),
          form["description"].strip(), form.get("skills_learned","").strip(), form.get("challenges","").strip(), hours))
        get_db().commit()
        admins = get_db().execute("SELECT id FROM users WHERE role='admin' AND account_status='active'").fetchall()
        for admin in admins:
            notify(admin["id"], "New OJT activity report", f"{session.get('full_name')} submitted an activity report.")
        audit(session["user_id"], "activity_submit", "activity_report", cur.lastrowid, form["title"].strip())
        flash("Activity report submitted.", "success")
        return redirect(url_for("activities.list_activities"))
    return render_template("student/activity_form.html")

@bp.route("/<int:report_id>/edit", methods=["GET", "POST"])
def edit(report_id):
    student = current_student()
    report = get_db().execute("SELECT * FROM activity_reports WHERE id=? AND student_id=?", (report_id, student["id"])).fetchone() if student else None
    if not report:
        flash("Activity report not found.", "error")
        return redirect(url_for("activities.list_activities"))
    if report["status"] != "submitted":
        flash("Only reports awaiting review can be edited.", "error")
        return redirect(url_for("activities.list_activities"))
    if request.method == "POST":
        f = request.form
        get_db().execute("""UPDATE activity_reports SET activity_date=?,title=?,description=?,skills_learned=?,challenges=?,hours_spent=?,updated_at=CURRENT_TIMESTAMP
          WHERE id=? AND student_id=?""", (f["activity_date"], f["title"].strip(), f["description"].strip(),
          f.get("skills_learned","").strip(), f.get("challenges","").strip(), float(f.get("hours_spent",0)), report_id, student["id"]))
        get_db().commit()
        flash("Activity report updated.", "success")
        return redirect(url_for("activities.list_activities"))
    return render_template("student/activity_form.html", report=report)
