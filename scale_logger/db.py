
import sqlite3
from datetime import datetime

DB_PATH = "scale_logger/foodlog.db"

def connect():
    return sqlite3.connect(DB_PATH)

def initialize_db():
    conn = connect()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        sort_order INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        weight_lb REAL NOT NULL,
        source_id INTEGER NOT NULL,
        type_id INTEGER NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('record', 'delete')) DEFAULT 'record',
        FOREIGN KEY(source_id) REFERENCES sources(id),
        FOREIGN KEY(type_id) REFERENCES types(id)
    )''')

    seed_sources()
    seed_types()
    conn.commit()
    conn.close()

def seed_sources():
    default_sources = [
        "Food for Neighbors", "Trader Joe's", "Whole Foods", "Wegmans", "Safeway",
        "Good Shepherd donations", "FreshFarm St John Neumann"
    ]
    conn = connect()
    for name in default_sources:
        conn.execute("INSERT OR IGNORE INTO sources (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def seed_types():
    default_types = [
        "Produce", "Dry", "Dairy", "Meat", "Prepared", "Bread", "Non-Food"
    ]
    conn = connect()
    for i, name in enumerate(default_types):
        conn.execute("INSERT OR IGNORE INTO types (name, sort_order) VALUES (?, ?)", (name, i))
    conn.commit()
    conn.close()

def get_sources():
    conn = connect()
    rows = conn.execute("SELECT name FROM sources ORDER BY name").fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_types():
    conn = connect()
    rows = conn.execute("SELECT name FROM types ORDER BY sort_order").fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_id_by_name(table, name):
    conn = connect()
    row = conn.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row[0] if row else None

def log_entry(weight, dtype, source):
    source_id = get_id_by_name("sources", source)
    type_id = get_id_by_name("types", dtype)
    conn = connect()
    conn.execute(
        "INSERT INTO logs (timestamp, weight_lb, source_id, type_id, action) VALUES (?, ?, ?, ?, 'record')",
        (datetime.now().isoformat(), weight, source_id, type_id)
    )
    conn.commit()
    conn.close()

def delete_last_entry():
    conn = connect()
    row = conn.execute(
        "SELECT id FROM logs WHERE action = 'record' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if row:
        conn.execute(
            "INSERT INTO logs (timestamp, weight_lb, source_id, type_id, action) "
            "SELECT ?, weight_lb, source_id, type_id, 'delete' FROM logs WHERE id = ?",
            (datetime.now().isoformat(), row[0])
        )
        conn.commit()
    conn.close()

def undelete_last_entry():
    conn = connect()
    row = conn.execute(
        "SELECT id FROM logs WHERE action = 'delete' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if row:
        conn.execute(
            "DELETE FROM logs WHERE id = ?", (row[0],)
        )
        conn.commit()
    conn.close()

def get_all_logs(include_deleted=False):
    query = """
    SELECT logs.timestamp, logs.weight_lb, s.name, t.name, logs.action
    FROM logs
    JOIN sources s ON s.id = logs.source_id
    JOIN types t ON t.id = logs.type_id
    """
    if not include_deleted:
        query += " WHERE logs.action = 'record'"
    query += " ORDER BY logs.timestamp DESC"

    conn = connect()
    return conn.execute(query).fetchall()

def create_report(source, start_date=None, end_date=None):
    source_id = get_id_by_name("sources", source)
    if not source_id:
        return {}, 0.0, []

    if start_date is None:
        start_date = datetime.now().date().isoformat()
    if end_date is None:
        end_date = start_date

    query = """
    SELECT t.name, logs.weight_lb
    FROM logs
    JOIN types t ON t.id = logs.type_id
    WHERE logs.source_id = ? AND logs.timestamp BETWEEN ? AND ? AND logs.action = 'record'
    """
    conn = connect()
    rows = conn.execute(query, (source_id, start_date + "T00:00", end_date + "T23:59")).fetchall()

    cat_totals = {}
    total_weight = 0.0
    for cat, wt in rows:
        cat_totals[cat] = cat_totals.get(cat, 0.0) + wt
        total_weight += wt

    return cat_totals, total_weight, rows
