import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.db_file = "chat_group.db"
        self.spam_threshold = 5
        self.time_window = 30 * 60  # 30 minutes

    async def init(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                messages INTEGER DEFAULT 0,
                balance REAL DEFAULT 0.0
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                user_id TEXT,
                text TEXT,
                timestamp TEXT
            )"""
        )
        conn.commit()
        conn.close()

    async def get_user(self, user_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        if user:
            return {"user_id": user[0], "name": user[1], "messages": user[2], "balance": user[3]}
        return None

    async def create_user(self, user_id, name):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO users (user_id, name, messages, balance) VALUES (?, ?, 0, 0.0)",
            (user_id, name)
        )
        conn.commit()
        conn.close()

    async def increment_message(self, user_id, name, text):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute(
            "UPDATE users SET messages = messages + 1, balance = balance + 1.0, name = ? WHERE user_id = ?",
            (name, user_id)
        )
        c.execute(
            "INSERT INTO messages (user_id, text, timestamp) VALUES (?, ?, ?)",
            (user_id, text, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    async def get_top_users(self, limit=10):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT * FROM users ORDER BY messages DESC LIMIT ?", (limit,))
        users = c.fetchall()
        conn.close()
        return [{"user_id": u[0], "name": u[1], "messages": u[2], "balance": u[3]} for u in users]

    async def reset_stats(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("DELETE FROM users")
        c.execute("DELETE FROM messages")
        conn.commit()
        conn.close()

    async def reset_balance(self, user_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = 0.0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    async def is_spam(self, user_id, text):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(seconds=self.time_window)).isoformat()
        c.execute(
            "SELECT text, timestamp FROM messages WHERE user_id = ? AND timestamp > ?",
            (user_id, cutoff)
        )
        messages = c.fetchall()
        conn.close()

        if len(text.strip()) < 5:
            return True

        from difflib import SequenceMatcher
        message_counts = {}
        for msg, ts in messages:
            similarity = SequenceMatcher(None, text.lower(), msg.lower()).ratio()
            if similarity > 0.9:
                return True
            message_counts[msg] = message_counts.get(msg, 0) + 1
            if message_counts[msg] >= self.spam_threshold:
                return True
        
        if messages:
            last_ts = datetime.fromisoformat(messages[-1][1])
            if (datetime.now() - last_ts) < timedelta(seconds=5):
                return True
        
        return False

# Create global db instance
db = Database()