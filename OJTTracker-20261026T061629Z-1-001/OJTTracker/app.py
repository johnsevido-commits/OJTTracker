
from flask import Flask, render_template, session, redirect, url_for, request
from config import Config
from database import close_db, init_database


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    from pathlib import Path
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)

    from routes.auth import bp as auth_bp
    from routes.student import bp as student_bp
    from routes.admin import bp as admin_bp
    from routes.attendance import bp as attendance_bp, action as attendance_action
    from routes.activities import bp as activities_bp
    from routes.reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(reports_bp)

    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)
    csrf.exempt(attendance_action)

    @app.before_request
    def security_and_access():
        endpoint = request.endpoint or ""

        public = {
            "auth.login",
            "auth.register",
            "auth.index",
            "static",
        }

        if not endpoint or endpoint == "None":
            return None

        if endpoint in public:
            return None

        if not session.get("user_id"):
            return redirect(url_for("auth.login"))

        role = session.get("role")

        # Admin-only pages
        if endpoint.startswith(("admin.", "reports.")):
            if role != "admin":
                return render_template("unauthorized.html"), 403

        # Student pages: students and coordinators may access
        # these pages. Admin access remains unchanged.
        if endpoint.startswith(("student.", "attendance.", "activities.")):
            if role not in ("student", "coordinator"):
                return render_template("unauthorized.html"), 403

        return None

    @app.context_processor
    def inject_globals():
        return {
            "current_user_name": session.get("full_name"),
            "current_role": session.get("role"),
        }

    @app.template_filter("ph_time")
    def format_ph_time(value):
        if not value:
            return "—"

        from datetime import datetime
        from zoneinfo import ZoneInfo

        try:
            parsed = datetime.fromisoformat(value)

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=ZoneInfo("Asia/Manila")
                )

            return parsed.astimezone(
                ZoneInfo("Asia/Manila")
            ).strftime("%b %d, %Y · %I:%M %p")

        except (TypeError, ValueError):
            return str(value)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500

    with app.app_context():
        init_database()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))

