
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db
from services.notification_service import audit

bp = Blueprint("auth", __name__)


def dashboard_for_role(role):
    if role == "student":
        return url_for("student.dashboard")

    if role == "coordinator":
        # Use the student dashboard temporarily until a
        # dedicated coordinator dashboard is created.
        return url_for("student.dashboard")

    if role == "admin":
        return url_for("admin.dashboard")

    return url_for("auth.login")


@bp.route("/", methods=["GET"])
def index():
    if session.get("user_id"):
        return redirect(dashboard_for_role(session.get("role")))

    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            """
            SELECT * FROM users
            WHERE username = ? AND account_status = 'active'
            """,
            (username,),
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]

            audit(
                user["id"],
                "login",
                "user",
                user["id"],
                "Successful login",
            )

            return redirect(dashboard_for_role(user["role"]))

        flash(
            "Invalid username or password, or the account is inactive.",
            "error",
        )

    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        student_number = request.form.get("student_number", "").strip()
        password = request.form.get("password", "")

        if not all([full_name, username, email, student_number, password]):
            flash("Please complete all fields.", "error")

        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")

        else:
            db = get_db()

            try:
                cur = db.execute(
                    """
                    INSERT INTO users
                    (full_name, username, email, password_hash, role)
                    VALUES (?, ?, ?, ?, 'student')
                    """,
                    (
                        full_name,
                        username,
                        email,
                        generate_password_hash(password),
                    ),
                )

                db.execute(
                    """
                    INSERT INTO students (user_id, student_number)
                    VALUES (?, ?)
                    """,
                    (cur.lastrowid, student_number),
                )

                db.commit()

                flash("Registration successful. You can now log in.", "success")
                return redirect(url_for("auth.login"))

            except Exception:
                db.rollback()
                flash(
                    "Username, email, or student number may already be registered.",
                    "error",
                )

    return render_template("login.html", register_mode=True)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))

