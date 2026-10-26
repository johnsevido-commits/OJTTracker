from database import get_db

def notify(user_id, title, message):
    db = get_db()
    db.execute("INSERT INTO notifications(user_id,title,message) VALUES(?,?,?)",
               (user_id, title, message))
    db.commit()

def audit(actor_id, action, target_type="", target_id=None, details=""):
    db = get_db()
    db.execute("""INSERT INTO audit_logs(actor_user_id,action,target_type,target_id,details)
                  VALUES(?,?,?,?,?)""", (actor_id, action, target_type, target_id, details))
    db.commit()
