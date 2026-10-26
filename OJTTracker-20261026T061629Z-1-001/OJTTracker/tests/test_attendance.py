import tempfile, os, unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from app import create_app
from database import get_db, init_database
from services.attendance_service import classify_time_in

class AttendanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False); self.tmp.close()
        self.app = create_app({"TESTING":True,"WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","DATABASE":self.tmp.name})
        with self.app.app_context():
            init_database()
    def tearDown(self):
        os.unlink(self.tmp.name)
    def test_late_at_one_hour_is_absent(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE settings SET value='08:00' WHERE key='official_start_time'")
            db.execute("UPDATE settings SET value='60' WHERE key='late_after_minutes'")
            db.commit()
            status, reason = classify_time_in(datetime(2026,1,1,9,0,tzinfo=ZoneInfo("Asia/Manila")))
            self.assertEqual(status,"absent")
            self.assertIn("marked absent",reason)
    def test_before_start_present(self):
        with self.app.app_context():
            status, _ = classify_time_in(datetime(2026,1,1,7,55,tzinfo=ZoneInfo("Asia/Manila")))
            self.assertEqual(status,"present")
