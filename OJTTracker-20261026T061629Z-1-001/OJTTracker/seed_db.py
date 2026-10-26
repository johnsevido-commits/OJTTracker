
"""Create development-only sample accounts without resetting existing data."""

from werkzeug.security import generate_password_hash
from app import create_app
from database import get_db, init_database

app = create_app()

with app.app_context():
    init_database()
    db = get_db()

    users = [
        (
            "OJTTrack Administrator",
            "admin",
            "admin@example.local",
            "Admin123!",
            "admin",
        ),
        (
            "Sample Student",
            "student",
            "student@example.local",
            "Student123!",
            "student",
        ),
        (
            "OJT Coordinator",
            "coordinator",
            "coordinator@example.local",
            "Coord123!",
            "coordinator",
        ),
    ]

    for full_name, username, email, password, role in users:
        existing = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not existing:
            db.execute(
                """
                INSERT INTO users
                (full_name, username, email, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    full_name,
                    username,
                    email,
                    generate_password_hash(password),
                    role,
                ),
            )

            print(f"Created account: {username}")

        else:
            print(f"Account already exists: {username}")

    student = db.execute(
        "SELECT id FROM users WHERE username = 'student'"
    ).fetchone()

    if student:
        student_profile = db.execute(
            "SELECT user_id FROM students WHERE user_id = ?",
            (student["id"],),
        ).fetchone()

        if not student_profile:
            db.execute(
                """
                INSERT INTO students
                (
                    user_id,
                    student_number,
                    course,
                    section,
                    company_name,
                    required_ojt_hours
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    student["id"],
                    "DEMO-001",
                    "BSIS",
                    "1A",
                    "Sample Partner Company",
                    486,
                ),
            )

    workplace = db.execute(
        "SELECT id FROM workplaces LIMIT 1"
    ).fetchone()

    if not workplace:
        db.execute(
            """
            INSERT INTO workplaces
            (
                workplace_name,
                address,
                latitude,
                longitude,
                allowed_radius_meters,
                geofencing_enabled
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Sample OJT Workplace",
                "Set the real address in workplace settings",
                None,
                None,
                150,
                0,
            ),
        )

    db.commit()

    print("\nDevelopment seed complete.")
    print("Admin:       admin / Admin123!")
    print("Student:     student / Student123!")
    print("Coordinator: coordinator / Coord123!")
    print("\nChange these credentials before real deployment.")
