import os
import sqlite3
import json
from datetime import datetime

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DB_PATH = os.path.join(DATA_DIR, "bot_data.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Table for user preferences/profile
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT, 
                  goals TEXT, 
                  joined_at TEXT)''')

    # Table for study plans or general tasks
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  description TEXT,
                  schedule_time TEXT,
                  status TEXT,
                  created_at TEXT)''')

    # Table for recurring schedules (long-term memory)
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_schedules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  description TEXT,
                  frequency TEXT,
                  time TEXT,
                  end_date TEXT,
                  created_at TEXT)''')
                  
    conn.commit()
    conn.close()

# ... (existing functions) ...

def add_recurring_schedule(user_id, description, frequency, time, end_date=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO recurring_schedules (user_id, description, frequency, time, end_date, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, description, frequency, time, end_date, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_schedules(user_id):
    """
    Returns a list of recurring schedules as dictionaries.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT description, frequency, time, end_date FROM recurring_schedules WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    
    schedules = []
    for row in rows:
        schedules.append({
            "description": row[0],
            "days_of_week": row[1] if row[1] else "", # frequency column stores days (e.g., "mon,wed")
            "time": row[2],
            "end_date": row[3]
        })
    return schedules

def add_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, joined_at) VALUES (?, ?, ?)",
              (user_id, username, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def add_task(user_id, description, schedule_time):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (user_id, description, schedule_time, status, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, description, schedule_time, 'pending', datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_tasks_for_date(user_id, target_date_str):
    """
    target_date_str: YYYY-MM-DD
    Returns list of dictionaries: {'description': ..., 'schedule_time': ...}
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Simple string matching for date part of ISO string
    c.execute("SELECT description, schedule_time FROM tasks WHERE user_id = ? AND schedule_time LIKE ?", 
              (user_id, f"{target_date_str}%"))
    rows = c.fetchall()
    conn.close()
    
    tasks = []
    for row in rows:
        tasks.append({
            "description": row[0],
            "schedule_time": row[1]
        })
    return tasks

def delete_task(user_id, description_keyword):
    """Deletes a one-off task matching the keyword."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE user_id = ? AND description LIKE ?", (user_id, f"%{description_keyword}%"))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0

def delete_recurring_schedule(user_id, description_keyword):
    """Deletes a recurring schedule matching the keyword."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM recurring_schedules WHERE user_id = ? AND description LIKE ?", (user_id, f"%{description_keyword}%"))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0

def update_user_goal(user_id, goal_text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET goals = ? WHERE user_id = ?", (goal_text, user_id))
    conn.commit()
    conn.close()

def get_user_goals(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT goals FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def delete_all_tasks(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows

def delete_all_recurring_schedules(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM recurring_schedules WHERE user_id = ?", (user_id,))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows

def delete_tasks_by_date(user_id, date_str):
    """Deletes tasks for a specific date (YYYY-MM-DD)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE user_id = ? AND schedule_time LIKE ?", (user_id, f"{date_str}%"))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, NULL as first_name FROM users") # Schema doesn't have first_name, using NULL or just username
    users = c.fetchall()
    conn.close()
    return users
    conn.commit()
    conn.close()
    return rows
def check_duplicate_recurring(user_id, description, frequency, time):
    """Checks if a recurring schedule already exists."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Check for exact match on time and frequency, and fuzzy match on description
    c.execute("SELECT id FROM recurring_schedules WHERE user_id = ? AND frequency = ? AND time = ? AND description LIKE ?", 
              (user_id, frequency, time, f"%{description}%"))
    result = c.fetchone()
    conn.close()
    return result is not None

def check_duplicate_task(user_id, description, schedule_time):
    """Checks if a one-off task already exists."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM tasks WHERE user_id = ? AND schedule_time = ? AND description LIKE ?", 
              (user_id, schedule_time, f"%{description}%"))
    result = c.fetchone()
    conn.close()
    return result is not None
