from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from database import get_db
from services.gps_service import haversine_meters
from services.notification_service import notify, audit

PH_TZ = ZoneInfo("Asia/Manila")

def now_ph():
    return datetime.now(PH_TZ)

def current_settings():
    db = get_db()
    return {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM settings")}

def get_active_workplace():
    return get_db().execute("SELECT * FROM workplaces WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()

def verify_workplace(lat, lon, accuracy):
    workplace = get_active_workplace()
    if not workplace:
        return "no_workplace", "No active workplace has been configured."
    if accuracy > float(workplace["minimum_gps_accuracy_meters"]):
        return "poor_accuracy", f"GPS accuracy must be {workplace['minimum_gps_accuracy_meters']:.0f} m or better."
    if workplace["geofencing_enabled"]:
        if workplace["latitude"] is None or workplace["longitude"] is None:
            return "configuration_error", "The workplace GPS coordinates are not configured."
        distance = haversine_meters(lat, lon, workplace["latitude"], workplace["longitude"])
        if distance > float(workplace["allowed_radius_meters"]):
            return "outside_radius", f"You are about {distance:.0f} m from the workplace, outside the permitted radius."
    return "verified", "Location accepted."

def classify_time_in(now):
    settings = current_settings()
    start_str = settings.get("official_start_time", "08:00")
    late_after = int(settings.get("late_after_minutes", "60"))
    start = datetime.combine(now.date(), time.fromisoformat(start_str), tzinfo=PH_TZ)
    minutes_late = (now - start).total_seconds() / 60
    if minutes_late >= late_after:
        return "absent", f"You were marked absent because your time-in was at least {late_after} minutes after the official start time ({start_str}). Please contact your OJT coordinator if this needs correction."
    if minutes_late > 0:
        return "late", f"Your time-in was {int(minutes_late)} minute(s) after the official start time."
    return "present", "Attendance recorded successfully."

def time_in(student_id, user_id, location):
    db = get_db()
    now = now_ph()
    day = now.date().isoformat()
    existing = db.execute("SELECT * FROM attendance WHERE student_id=? AND attendance_date=?", (student_id, day)).fetchone()
    if existing:
        raise ValueError("An attendance record already exists for today. Contact your coordinator if it needs correction.")
    loc_status, loc_message = verify_workplace(location["latitude"], location["longitude"], location["accuracy"])
    if loc_status != "verified":
        raise ValueError(loc_message)
    status, reason = classify_time_in(now)
    stamp = now.isoformat(timespec="seconds")
    cur = db.execute("""INSERT INTO attendance
      (student_id,attendance_date,time_in,status,time_in_latitude,time_in_longitude,time_in_accuracy,
       location_verification_status,absence_reason,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (student_id, day, stamp, status, location["latitude"], location["longitude"], location["accuracy"],
       loc_status, reason if status == "absent" else "", stamp, stamp))
    db.commit()
    notify(user_id, "Time-in recorded", reason)
    audit(user_id, "time_in", "attendance", cur.lastrowid, f"status={status}; location={loc_status}")
    return status, reason

def time_out(student_id, user_id, location):
    db = get_db()
    now = now_ph()
    day = now.date().isoformat()
    record = db.execute("SELECT * FROM attendance WHERE student_id=? AND attendance_date=?", (student_id, day)).fetchone()
    if not record or not record["time_in"]:
        raise ValueError("You must have a valid time-in before timing out.")
    if record["time_out"]:
        raise ValueError("You have already timed out for today.")
    loc_status, loc_message = verify_workplace(location["latitude"], location["longitude"], location["accuracy"])
    if loc_status != "verified":
        raise ValueError(loc_message)
    start = datetime.fromisoformat(record["time_in"])
    seconds = max(0, (now - start).total_seconds())
    hours = round(seconds / 3600, 2)
    stamp = now.isoformat(timespec="seconds")
    db.execute("""UPDATE attendance SET time_out=?,rendered_hours=?,time_out_latitude=?,time_out_longitude=?,
      time_out_accuracy=?,updated_at=? WHERE id=?""",
      (stamp, hours, location["latitude"], location["longitude"], location["accuracy"], stamp, record["id"]))
    db.commit()
    notify(user_id, "Time-out recorded", f"Your recorded duration is {hours:.2f} hours. Final credited hours are subject to coordinator review.")
    audit(user_id, "time_out", "attendance", record["id"], f"rendered_hours={hours}")
    return hours, "Time-out recorded successfully."
