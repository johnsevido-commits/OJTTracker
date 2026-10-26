from app import create_app
from database import init_database

app = create_app()
with app.app_context():
    init_database()
    print(f"Database initialized at: {app.config['DATABASE']}")
