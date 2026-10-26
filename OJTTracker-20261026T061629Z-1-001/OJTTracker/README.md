# OJTTrack — OJT Hours and Activity Monitoring System

A beginner-friendly Flask + SQLite mini-capstone starter for Bago City College. It implements student accounts, attendance history, daily activity reports, coordinator review, GPS location capture, configurable workplace geofencing, CSV reporting, notifications, and audit events.

## Technology
- Python / Flask
- SQLite
- HTML5, CSS3, vanilla JavaScript
- HTML5 Geolocation API
- Leaflet.js and OpenStreetMap for maps

## Windows PowerShell setup

1. Install Python 3.11 or newer from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Open this `OJTTrack` folder in VS Code.
3. Open a terminal in the project folder and create a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

4. Copy `.env.example` to `.env` and replace `SECRET_KEY` with a long random value. Keep `.env` private.
5. Initialize the database:

```powershell
python init_db.py
```

6. Optional: create development sample accounts (this does not reset existing data):

```powershell
python seed_db.py
```

7. Start the app:

```powershell
python app.py
```

8. Open http://127.0.0.1:5000 in your browser.

## Development seed credentials

- Admin: `admin` / `Admin123!`
- Student: `student` / `Student123!`

These credentials are for local development only. Change or remove them before deploying the app.

## GPS setup

1. Sign in as the administrator.
2. Open **Workplace & GPS**.
3. Enter the real workplace name, address, latitude, and longitude.
4. Configure the allowed radius and maximum accepted GPS accuracy.
5. Enable geofencing only after confirming the coordinates and radius.
6. On a student account, open **GPS Attendance**, allow browser location access, and click **Get my current location** before time-in/time-out.

Browser geolocation generally requires HTTPS on deployed sites. `localhost` is generally treated as a secure context for local development. GPS accuracy depends on the device, permissions, signal, browser, and environment. A browser coordinate does not prove a person's identity. Use the coordinator's approved alternative verification process when location is unavailable.

## Attendance rules

The default official start time is 08:00, and a time-in at or after 09:00 is marked absent. Administrators can configure the official start time and threshold. The original time-in is preserved and an explanation is recorded. Rendered hours are calculated from time-in/time-out; credited hours may still require coordinator review.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## Database location

An initialized SQLite database is included at `instance/ojttrack.sqlite3`; the app also safely creates missing tables/settings on startup. Do not delete this file to reset the system unless you intentionally want to remove local data. The schema initialization uses `CREATE TABLE IF NOT EXISTS`; it does not reset existing records.

## Project structure

- `routes/`: Flask route blueprints
- `services/`: GPS and attendance business rules, notifications/audit helpers
- `templates/`: Jinja HTML pages
- `static/css/`: styling
- `static/js/`: GPS, map, and UI interactions
- `tests/`: automated unit tests

## Notes / limitations

- This is a local mini-capstone implementation, not a production-hosted service.
- Browser GPS is not tamper-proof and cannot guarantee identity or physical presence.
- Map tiles require an internet connection.
- CSV reports are supported; PDF export is not included.
- CSRF protection is enabled for HTML forms through Flask-WTF. JSON attendance requests are same-origin and session-protected; deploy behind HTTPS and consider adding a dedicated CSRF token to JSON actions before public production deployment.
- Review the school's official attendance policy before using this for real OJT credit.
