import csv, io
from flask import Blueprint, Response, render_template, request
from database import get_db

bp = Blueprint("reports", __name__, url_prefix="/reports")

@bp.route("/")
def page():
    rows = get_db().execute("""SELECT a.*,u.full_name,s.student_number FROM attendance a
      JOIN students s ON a.student_id=s.id JOIN users u ON s.user_id=u.id
      ORDER BY a.attendance_date DESC LIMIT 500""").fetchall()
    return render_template("admin/reports.html", rows=rows)

@bp.route("/export.csv")
def export_csv():
    start = request.args.get("start","")
    end = request.args.get("end","")
    sql = """SELECT a.attendance_date,u.full_name,s.student_number,a.time_in,a.time_out,a.rendered_hours,a.status,
      a.location_verification_status,a.absence_reason FROM attendance a
      JOIN students s ON a.student_id=s.id JOIN users u ON s.user_id=u.id WHERE 1=1"""
    params = []
    if start:
        sql += " AND a.attendance_date>=?"
        params.append(start)
    if end:
        sql += " AND a.attendance_date<=?"
        params.append(end)
    sql += " ORDER BY a.attendance_date DESC"
    rows = get_db().execute(sql, params).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date","Student","Student Number","Time In","Time Out","Rendered Hours","Status","Location Verification","Absence Reason"])
    for row in rows:
        writer.writerow(list(row))
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=ojttrack-attendance-report.csv"})
