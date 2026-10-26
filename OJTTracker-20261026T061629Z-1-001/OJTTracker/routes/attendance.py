from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from database import get_db
from services.gps_service import validate_coordinates
from services.attendance_service import time_in, time_out

bp = Blueprint("attendance", __name__, url_prefix="/attendance")

def current_student():
    return get_db().execute("SELECT * FROM students WHERE user_id=?", (session["user_id"],)).fetchone()

@bp.route("/", methods=["GET"])
def page():
    student = current_student()
    today = None
    if student:
        from services.attendance_service import now_ph
        today = get_db().execute("SELECT * FROM attendance WHERE student_id=? AND attendance_date=?",
                                 (student["id"], now_ph().date().isoformat())).fetchone()
    return render_template("student/attendance.html", today=today)

@bp.route("/action", methods=["POST"])
def action():
    if session.get("role") != "student":
        return jsonify(ok=False, message="Student access required."), 403
    student = current_student()
    if not student:
        return jsonify(ok=False, message="Student profile not found."), 400
    payload = request.get_json(silent=True) or {}
    workplace = get_db().execute("SELECT minimum_gps_accuracy_meters FROM workplaces WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()
    max_accuracy = workplace["minimum_gps_accuracy_meters"] if workplace else 100
    location, error = validate_coordinates(payload, max_accuracy)
    if error:
        return jsonify(ok=False, message=error), 400
    try:
        if payload.get("action") == "time_in":
            status, message = time_in(student["id"], session["user_id"], location)
            return jsonify(ok=True, message=message, status=status)
        if payload.get("action") == "time_out":
            hours, message = time_out(student["id"], session["user_id"], location)
            return jsonify(ok=True, message=message, hours=hours)
        return jsonify(ok=False, message="Unknown attendance action."), 400
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400

@bp.route("/history")
def history_alias():
    return redirect(url_for("student.history"))
