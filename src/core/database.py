import sqlite3
import datetime
import os

class Database:
    def __init__(self, username):
        self.username = username
        self.db_file = f"{self.username}_data.db"
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        """Initializes SQLite database and creates tables."""
        try:
            self.conn = sqlite3.connect(self.db_file)
            self.cursor = self.conn.cursor()
            self.create_tables()
            print("Database connection successful.")
        except Exception as e:
            print(f"Database error: {e}")

    def create_tables(self):
        # History Table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                target TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Indexes (For performance)
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_target ON history(target)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_action ON history(action)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)")
        
        # Stats Table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                date DATE PRIMARY KEY,
                likes INTEGER DEFAULT 0,
                follows INTEGER DEFAULT 0,
                unfollows INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def log_action(self, action, target):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        try:
            self.cursor.execute("INSERT INTO history (action, target, timestamp) VALUES (?, ?, ?)", (action, target, timestamp))
            
            # Update stats
            col_map = {"LIKE": "likes", "FOLLOW": "follows", "UNFOLLOW": "unfollows", "COMMENT": "comments"}
            if action in col_map:
                col = col_map[action]
                self.cursor.execute(f"""
                    INSERT INTO stats (date, {col}) VALUES (?, 1)
                    ON CONFLICT(date) DO UPDATE SET {col} = {col} + 1
                """, (today,))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Log Error: {e}")
            return False

    def check_history(self, target):
        try:
            self.cursor.execute("SELECT 1 FROM history WHERE target = ?", (target,))
            if self.cursor.fetchone():
                return True
        except:
            pass
        return False
    
    def get_stats(self, date=None):
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            self.cursor.execute("SELECT * FROM stats WHERE date = ?", (date,))
            return self.cursor.fetchone()
        except:
            return None

    def get_follow_timestamp(self, username):
        """Returns when the user was followed (datetime object or None)."""
        try:
            self.cursor.execute("SELECT timestamp FROM history WHERE target = ? AND action LIKE 'FOLLOW%' ORDER BY timestamp DESC LIMIT 1", (username,))
            row = self.cursor.fetchone()
            if row:
                return datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"DB Timestamp Error: {e}")
        return None

    def close(self):
        if self.conn:
            self.conn.close()
