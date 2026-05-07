import os
import sqlite3

# --- File System Configuration ---
# This ensures the database 'kitchen.db' is always created in the same folder as this script
basedir = os.path.abspath(os.path.dirname(__file__))

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    db_path = os.path.join(basedir, 'kitchen.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Creates the database schema and populates it with initial starting data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. INGREDIENT LIST: Tracks current stock levels and 'critical' warning points.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredient_list (
            item TEXT PRIMARY KEY,
            stock_count INTEGER,
            critical_count INTEGER,
            units TEXT
        )
    ''')

    # 2. RECIPE AMOUNTS: A reference table to know exactly how much of each item makes one Menemen.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipe_amounts (
            item TEXT PRIMARY KEY,
            required_amount INTEGER,
            units TEXT
        )
    ''')

    # 3. KITCHEN TOOLS: Tracks the availability of physical hardware (pans, spoons).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mutfak_araclari (
            urun TEXT PRIMARY KEY,
            ekstrasi TEXT,
            durum_ana TEXT,
            durum_ekst TEXT
        )
    ''')

    # 4. SIDES: Tracks inventory for non-core items like tea or bread.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sides (
            urun TEXT PRIMARY KEY,
            eldeki_sayi INTEGER,
            birimler TEXT
        )
    ''')

    # 5. FEEDBACK: Stores user-submitted data for quality control.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            q_id TEXT,
            ans TEXT
        )
    ''')

    # 6. FINANCES: A single-row table to store the running balance of the business.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_revenue REAL DEFAULT 0.0,
            total_costs REAL DEFAULT 0.0,
            profit REAL DEFAULT 0.0
        )
    ''')

    # Initialize the first row of finances if it doesn't exist
    cursor.execute("INSERT OR IGNORE INTO finances (id, total_revenue, total_costs, profit) VALUES (1, 0, 0, 0)")

    # 7. ACTIVITY LOGS: An audit trail for every sale and expense.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            activity_text TEXT,
            amount REAL,
            type TEXT -- 'sale' or 'expense'
        )
    ''')    
    
    # Add 'Bread' to the primary ingredient list for stock management
    cursor.execute("INSERT OR IGNORE INTO ingredient_list (item, stock_count, units) VALUES ('Bread', 20, 'Loaf')")
    


    # --- DATA SEEDING ---
    # Initial Stock
    ingredients = [
        ('Tomato', 10, 2, 'piece'),
        ('Pepper', 10, 2, 'piece'),
        ('Egg', 12, 3, 'piece'),
        ('Onion', 10, 1, 'piece'),
        ('Oil', 20, 5, 'spoon')
    ]
    cursor.executemany('INSERT OR IGNORE INTO ingredient_list VALUES (?,?,?,?)', ingredients)

    # Standard Recipe Logic
    recipe = [
        ('Tomato', 3, 'piece'),
        ('Pepper', 2, 'piece'),
        ('Egg', 2, 'piece'),
        ('Onion', 1, 'piece')
    ]
    cursor.executemany('INSERT OR IGNORE INTO recipe_amounts VALUES (?,?,?)', recipe)

    # Tools Seeding
    tools = [
        ('tava', 'sahan', 'mevcut', 'mevcut'),
        ('spatula', 'kasik', 'mevcut', 'mevcut')
    ]
    cursor.executemany('INSERT OR IGNORE INTO mutfak_araclari VALUES (?,?,?,?)', tools)

    # Sides Seeding
    sides_data = [
        ('Bread', 5, 'slices'),
        ('Tea', 10, 'cups')
    ]
    cursor.executemany('INSERT OR IGNORE INTO sides VALUES (?,?,?)', sides_data)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")
