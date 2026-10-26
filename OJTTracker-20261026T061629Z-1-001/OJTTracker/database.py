
import sqlite3
from flask import current_app, g
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 full_name TEXT NOT NULL,
 username TEXT NOT NULL UNIQUE,
 email TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('student','admin','coordinator')),
 account_status TEXT NOT NULL DEFAULT 'active'
 CHECK(account_status IN ('active','inactive')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
 student_number TEXT UNIQUE,
 course TEXT DEFAULT 'BSIS',
 section TEXT DEFAULT '',
 company_name TEXT DEFAULT '',
 required_ojt_hours REAL NOT NULL DEFAULT 486
 CHECK(required_ojt_hours >= 0),
 assigned_start_date TEXT,
 assigned_end_date TEXT
);

CREATE TABLE IF NOT EXISTS workplaces (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workplace_name TEXT NOT NULL,
 address TEXT NOT NULL DEFAULT '',
 latitude REAL,
 longitude REAL,
 allowed_radius_meters REAL NOT NULL DEFAULT 150,
 geofencing_enabled INTEGER NOT NULL DEFAULT 0,
 minimum_gps_accuracy_meters REAL NOT NULL DEFAULT 100,
 is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS attendance (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
 attendance_date TEXT NOT NULL,
 time_in TEXT,
 time_out TEXT,
 rendered_hours REAL NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'incomplete',
 time_in_latitude REAL,
 time_in_longitude REAL,
 time_in_accuracy REAL,
 time_out_latitude REAL,
 time_out_longitude REAL,
 time_out_accuracy REAL,
 location_verification_status TEXT DEFAULT 'not_checked',
 absence_reason TEXT DEFAULT '',
 remarks TEXT DEFAULT '',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(student_id, attendance_date)
);

CREATE TABLE IF NOT EXISTS activity_reports (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
 activity_date TEXT NOT NULL,
 title TEXT NOT NULL,
 description TEXT NOT NULL,
 skills_learned TEXT DEFAULT '',
 challenges TEXT DEFAULT '',
 hours_spent REAL NOT NULL DEFAULT 0
 CHECK(hours_spent >= 0 AND hours_spent <= 24),
 status TEXT NOT NULL DEFAULT 'submitted'
 CHECK(status IN ('submitted','approved','rejected')),
 coordinator_feedback TEXT DEFAULT '',
 submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title TEXT NOT NULL,
 message TEXT NOT NULL,
 is_read INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
 action TEXT NOT NULL,
 target_type TEXT NOT NULL DEFAULT '',
 target_id INTEGER,
 details TEXT DEFAULT '',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
 key TEXT PRIMARY KEY,
 value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attendance_date
 ON attendance(attendance_date);
CREATE INDEX IF NOT EXISTS idx_attendance_student
 ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_activities_student
 ON activity_reports(student_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user
 ON notifications(user_id, is_read);
"""


def get_db():
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_database():
    db = get_db()

    # Check whether an existing users table needs migration.
    table = db.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type='table' AND name='users'"
    ).fetchone()

    if table and "'coordinator'" not in (table["sql"] or ""):
        db.execute("PRAGMA foreign_keys = OFF")

        db.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK(role IN ('student','admin','coordinator')),
                account_status TEXT NOT NULL DEFAULT 'active'
                    CHECK(account_status IN ('active','inactive')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            INSERT INTO users_new
                (id, full_name, username, email, password_hash,
                 role, account_status, created_at)
            SELECT id, full_name, username, email, password_hash,
                   role, account_status, created_at
            FROM users
        """)

        db.execute("DROP TABLE users")
        db.execute("ALTER TABLE users_new RENAME TO users")

        db.execute("PRAGMA foreign_keys = ON")

    db.executescript(SCHEMA)

    defaults = {
        "official_start_time": "08:00",
        "late_after_minutes": "60",
        "daily_required_hours": "8",
    }

    for key, value in defaults.items():
        db.execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)",
            (key, value),
        )

    db.commit()
