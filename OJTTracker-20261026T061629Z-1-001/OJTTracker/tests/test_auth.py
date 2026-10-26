import tempfile, os, unittest
from app import create_app
from database import get_db, init_database
from werkzeug.security import generate_password_hash

class AuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.app = create_app({"TESTING":True,"WTF_CSRF_ENABLED":False,"SECRET_KEY":"test","DATABASE":self.tmp.name})
        self.client = self.app.test_client()
        with self.app.app_context():
            init_database()
            db = get_db()
            db.execute("INSERT INTO users(full_name,username,email,password_hash,role) VALUES(?,?,?,?,?)",
                       ("Test Student","teststudent","test@example.test",generate_password_hash("Password123!"),"student"))
            uid = db.execute("SELECT id FROM users WHERE username='teststudent'").fetchone()["id"]
            db.execute("INSERT INTO students(user_id,student_number) VALUES(?,?)",(uid,"TEST-1"))
            db.commit()
    def tearDown(self):
        os.unlink(self.tmp.name)
    def test_login_success(self):
        response = self.client.post("/login", data={"username":"teststudent","password":"Password123!"}, follow_redirects=True)
        self.assertEqual(response.status_code,200)
        self.assertIn(b"STUDENT WORKSPACE", response.data)
    def test_bad_login(self):
        response = self.client.post("/login", data={"username":"teststudent","password":"wrong"}, follow_redirects=True)
        self.assertIn(b"Invalid username or password", response.data)
