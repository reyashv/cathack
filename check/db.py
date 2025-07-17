import sqlite3
import uuid
from datetime import datetime, timedelta

# Define the name of the database file
DB_NAME = "operator_assistant.db"

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("PRAGMA foreign_keys = 1")
        print(f"Successfully connected to SQLite database: {DB_NAME}")
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def create_tables(conn):
    """Create all necessary tables for the application."""
    cursor = conn.cursor()
    tables_to_drop = [
        "machine_logs", "tasks", "predefined_tasks", "machines", "users"
    ]
    for table in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table};")
    print("Dropped existing tables for a fresh setup.")

    # --- Core Tables ---
    cursor.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            operator_id_str TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE machines (
            id TEXT PRIMARY KEY,
            machine_id_str TEXT NOT NULL UNIQUE,
            model TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE predefined_tasks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL, -- e.g., Trenching, Loading, Grading
            avg_cycles_per_hour REAL NOT NULL -- Used for predictive model baseline
        );
    """)
    cursor.execute("""
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            predefined_task_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Pending', 'In Progress', 'Completed')),
            day TEXT NOT NULL, -- YYYY-MM-DD format for calendar
            assigned_to_user_id TEXT NOT NULL,
            assigned_to_machine_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (predefined_task_id) REFERENCES predefined_tasks (id),
            FOREIGN KEY (assigned_to_user_id) REFERENCES users (id),
            FOREIGN KEY (assigned_to_machine_id) REFERENCES machines (id)
        );
    """)
    cursor.execute("""
        CREATE TABLE machine_logs (
            id TEXT PRIMARY KEY,
            machine_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            seatbelt_status TEXT NOT NULL,
            tilt_angle REAL NOT NULL,
            visibility_percent INTEGER NOT NULL,
            safety_alert_type TEXT NOT NULL DEFAULT 'None',
            FOREIGN KEY (machine_id) REFERENCES machines (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)
    conn.commit()
    print("All tables created successfully.")

def seed_data(conn):
    """Seed the database with comprehensive sample data."""
    cursor = conn.cursor()
    
    # --- Seed Users and Machines ---
    user_id = str(uuid.uuid4())
    machine_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO users (id, operator_id_str, name) VALUES (?, ?, ?)",
                   (user_id, 'OP1001', 'John Doe'))
    cursor.execute("INSERT INTO machines (id, machine_id_str, model) VALUES (?, ?, ?)",
                   (machine_id, 'EXC001', 'Caterpillar 336 Excavator'))
    print("Seeded user and machine.")

    # --- Seed Predefined Tasks ---
    predefined_tasks = [
        (str(uuid.uuid4()), 'Dig foundation (Shallow)', 'Trenching', 15.0),
        (str(uuid.uuid4()), 'Dig foundation (Deep)', 'Trenching', 10.0),
        (str(uuid.uuid4()), 'Load trucks with gravel', 'Loading', 25.0),
        (str(uuid.uuid4()), 'Grade site area', 'Grading', 8.0),
        (str(uuid.uuid4()), 'Daily Pre-op Check', 'Checklist', 0)
    ]
    cursor.executemany("INSERT INTO predefined_tasks (id, name, category, avg_cycles_per_hour) VALUES (?, ?, ?, ?)", predefined_tasks)
    print(f"Seeded {len(predefined_tasks)} predefined tasks.")

    # --- Seed Scheduled Tasks for the Calendar ---
    today = datetime.today()
    deep_dig_id = cursor.execute("SELECT id FROM predefined_tasks WHERE name = 'Dig foundation (Deep)'").fetchone()[0]
    load_trucks_id = cursor.execute("SELECT id FROM predefined_tasks WHERE name = 'Load trucks with gravel'").fetchone()[0]
    
    tasks_to_add = [
        (str(uuid.uuid4()), deep_dig_id, 'In Progress', today.strftime('%Y-%m-%d'), user_id, machine_id),
        (str(uuid.uuid4()), load_trucks_id, 'Pending', (today + timedelta(days=1)).strftime('%Y-%m-%d'), user_id, machine_id)
    ]
    cursor.executemany("INSERT INTO tasks (id, predefined_task_id, status, day, assigned_to_user_id, assigned_to_machine_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       [(t[0], t[1], t[2], t[3], t[4], t[5], datetime.now().isoformat()) for t in tasks_to_add])
    print(f"Seeded {len(tasks_to_add)} scheduled tasks.")

    # --- Seed Machine Logs with New Safety Data ---
    logs_to_add = [
        # timestamp, seatbelt_status, tilt_angle, visibility_percent, alert_type
        (datetime.now() - timedelta(minutes=30), "Fastened", 2.5, 95, "None"),
        (datetime.now() - timedelta(minutes=20), "Fastened", 8.2, 90, "None"),
        (datetime.now() - timedelta(minutes=15), "Unfastened", 9.5, 88, "Seatbelt"),
        (datetime.now() - timedelta(minutes=10), "Fastened", 16.1, 85, "Tilt"), # Critical tilt angle
        (datetime.now() - timedelta(minutes=5), "Fastened", 12.0, 45, "Visibility"), # Low visibility
        (datetime.now(), "Fastened", 5.0, 90, "None"),
    ]
    for log in logs_to_add:
        cursor.execute("""
            INSERT INTO machine_logs (id, machine_id, user_id, timestamp, seatbelt_status, tilt_angle, visibility_percent, safety_alert_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), machine_id, user_id, log[0].isoformat(), log[1], log[2], log[3], log[4]))
    print(f"Seeded {len(logs_to_add)} machine logs with new safety data.")

    conn.commit()
    print("Database seeded successfully.")

if __name__ == '__main__':
    conn = create_connection()
    if conn:
        create_tables(conn)
        seed_data(conn)
        conn.close()
        print("Database setup complete and connection closed.")


# import sqlite3
# import uuid
# from datetime import datetime
# import json

# # Define the name of the database file
# DB_NAME = "operator_assistant.db"

# def create_connection():
#     """Create a database connection to the SQLite database."""
#     conn = None
#     try:
#         conn = sqlite3.connect(DB_NAME)
#         # Enforce foreign key constraints for data integrity
#         conn.execute("PRAGMA foreign_keys = 1")
#         print(f"Successfully connected to SQLite database: {DB_NAME}")
#     except sqlite3.Error as e:
#         print(f"Error connecting to database: {e}")
#     return conn

# def create_tables(conn):
#     """Create all necessary tables for the application."""
#     try:
#         cursor = conn.cursor()

#         # Drop existing tables in reverse order of dependency to ensure a clean setup
#         tables_to_drop = [
#             "issue_reports", "user_checklist_log", "checklist_items", 
#             "user_badges", "badges", "training_modules", 
#             "machine_logs", "tasks", "machines", "users"
#         ]
#         for table in tables_to_drop:
#             cursor.execute(f"DROP TABLE IF EXISTS {table};")
#         print("Dropped existing tables for a fresh setup.")

#         # --- Core Tables ---
#         cursor.execute("""
#             CREATE TABLE users (
#                 id TEXT PRIMARY KEY,
#                 operator_id_str TEXT NOT NULL UNIQUE,
#                 name TEXT NOT NULL,
#                 points INTEGER NOT NULL DEFAULT 0,
#                 created_at TEXT NOT NULL
#             );
#         """)

#         cursor.execute("""
#             CREATE TABLE machines (
#                 id TEXT PRIMARY KEY,
#                 machine_id_str TEXT NOT NULL UNIQUE,
#                 model TEXT NOT NULL,
#                 created_at TEXT NOT NULL
#             );
#         """)

#         cursor.execute("""
#             CREATE TABLE tasks (
#                 id TEXT PRIMARY KEY,
#                 title TEXT NOT NULL,
#                 status TEXT NOT NULL CHECK(status IN ('Pending', 'In Progress', 'Completed')),
#                 task_type TEXT NOT NULL DEFAULT 'Operational',
#                 instructions TEXT,
#                 safety_notes TEXT,
#                 target_cycles INTEGER DEFAULT 0,
#                 current_cycles INTEGER DEFAULT 0,
#                 assigned_to_user_id TEXT NOT NULL,
#                 assigned_to_machine_id TEXT NOT NULL,
#                 created_at TEXT NOT NULL,
#                 FOREIGN KEY (assigned_to_user_id) REFERENCES users (id),
#                 FOREIGN KEY (assigned_to_machine_id) REFERENCES machines (id)
#             );
#         """)

#         # This table is named 'machine_logs' to match the app.py code
#         cursor.execute("""
#             CREATE TABLE machine_logs (
#                 id TEXT PRIMARY KEY,
#                 machine_id TEXT NOT NULL,
#                 user_id TEXT NOT NULL,
#                 task_id TEXT, -- Can be NULL for logs not associated with a specific task
#                 timestamp TEXT NOT NULL,
#                 engine_hours REAL NOT NULL,
#                 fuel_used_l REAL NOT NULL,
#                 load_cycles INTEGER NOT NULL,
#                 idling_time_min INTEGER NOT NULL,
#                 seatbelt_status TEXT NOT NULL,
#                 safety_alert_type TEXT NOT NULL DEFAULT 'None',
#                 safety_alert_details TEXT,
#                 FOREIGN KEY (machine_id) REFERENCES machines (id),
#                 FOREIGN KEY (user_id) REFERENCES users (id),
#                 FOREIGN KEY (task_id) REFERENCES tasks (id)
#             );
#         """)

#         # --- Supporting Tables for App Features ---
#         cursor.execute("""
#             CREATE TABLE training_modules (
#                 id TEXT PRIMARY KEY,
#                 title TEXT NOT NULL,
#                 module_type TEXT NOT NULL CHECK(module_type IN ('Video', 'Quiz', 'Document')),
#                 content_url TEXT,
#                 duration_minutes INTEGER,
#                 associated_machine_model TEXT
#             );
#         """)
        
#         cursor.execute("""
#             CREATE TABLE badges (
#                 id TEXT PRIMARY KEY,
#                 name TEXT NOT NULL UNIQUE,
#                 description TEXT NOT NULL,
#                 icon_class TEXT NOT NULL
#             );
#         """)

#         cursor.execute("""
#             CREATE TABLE user_badges (
#                 user_id TEXT NOT NULL,
#                 badge_id TEXT NOT NULL,
#                 earned_at TEXT NOT NULL,
#                 PRIMARY KEY (user_id, badge_id),
#                 FOREIGN KEY (user_id) REFERENCES users (id),
#                 FOREIGN KEY (badge_id) REFERENCES badges (id)
#             );
#         """)

#         cursor.execute("""
#             CREATE TABLE checklist_items (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 item_text TEXT NOT NULL,
#                 category TEXT NOT NULL
#             );
#         """)

#         cursor.execute("""
#             CREATE TABLE user_checklist_log (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id TEXT NOT NULL,
#                 machine_id TEXT NOT NULL,
#                 completed_at TEXT NOT NULL,
#                 checked_items_json TEXT NOT NULL,
#                 FOREIGN KEY (user_id) REFERENCES users (id),
#                 FOREIGN KEY (machine_id) REFERENCES machines (id)
#             );
#         """)

#         cursor.execute("""
#             CREATE TABLE issue_reports (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id TEXT NOT NULL,
#                 machine_id TEXT NOT NULL,
#                 category TEXT NOT NULL,
#                 details TEXT,
#                 reported_at TEXT NOT NULL,
#                 FOREIGN KEY (user_id) REFERENCES users (id),
#                 FOREIGN KEY (machine_id) REFERENCES machines (id)
#             );
#         """)
        
#         conn.commit()
#         print("All tables created successfully.")

#     except sqlite3.Error as e:
#         print(f"Error creating tables: {e}")

# def seed_data(conn):
#     """Insert initial sample data into the tables so the app works on first run."""
#     try:
#         cursor = conn.cursor()
        
#         # --- Seed Users and Machines ---
#         user_id = str(uuid.uuid4())
#         machine_id = str(uuid.uuid4())
        
#         cursor.execute("INSERT INTO users (id, operator_id_str, name, points, created_at) VALUES (?, ?, ?, ?, ?)",
#                        (user_id, 'OP1001', 'John Doe', 75, datetime.now().isoformat()))
        
#         cursor.execute("INSERT INTO machines (id, machine_id_str, model, created_at) VALUES (?, ?, ?, ?)",
#                        (machine_id, 'EXC001', 'Caterpillar 336 Excavator', datetime.now().isoformat()))
        
#         print("Seeded user 'OP1001' and machine 'EXC001'.")

#         # --- Seed Tasks ---
#         task_in_progress_id = str(uuid.uuid4())
#         tasks_to_add = [
#             (str(uuid.uuid4()), 'Daily Pre-op Check', 'Pending', 'Checklist', 'Complete all items before starting operational tasks.', 'Ensure machine is on level ground and stable.', 0, 0, user_id, machine_id),
#             (task_in_progress_id, 'Dig foundation for Sector A', 'In Progress', 'Operational', 'Excavate to a depth of 2 meters as per site plan. Pile soil to the north.', 'Beware of underground utilities marked on the map. Maintain a safe distance from trench edges.', 50, 20, user_id, machine_id),
#             (str(uuid.uuid4()), 'Load 10 trucks with gravel', 'Pending', 'Operational', 'Use the front loader attachment. Each truck requires 3 full buckets.', 'Confirm each truck driver signals "all clear" before loading.', 30, 0, user_id, machine_id)
#         ]
#         cursor.executemany("INSERT INTO tasks (id, title, status, task_type, instructions, safety_notes, target_cycles, current_cycles, assigned_to_user_id, assigned_to_machine_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#                            [(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], t[9], datetime.now().isoformat()) for t in tasks_to_add])
#         print(f"Seeded {len(tasks_to_add)} tasks.")

#         # --- Seed Machine Logs (operation_logs) ---
#         logs_to_add = [
#             (task_in_progress_id, "2025-07-17 08:00:00", 1523.5, 5.2, 12, 5, "Fastened", "None", None),
#             (task_in_progress_id, "2025-07-17 10:00:00", 1524.8, 3.8, 8, 20, "Unfastened", "Seatbelt", "CRITICAL: Seatbelt is unfastened."),
#             (None, "2025-07-17 12:05:00", 1525.5, 4.1, 0, 5, "Fastened", "Operational", "WARNING: 4+ hours of continuous operation. A short break is recommended."),
#         ]
#         for log in logs_to_add:
#             cursor.execute("""
#                 INSERT INTO machine_logs (id, task_id, machine_id, user_id, timestamp, engine_hours, fuel_used_l, load_cycles, idling_time_min, seatbelt_status, safety_alert_type, safety_alert_details)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """, (str(uuid.uuid4()), log[0], machine_id, user_id, *log[1:]))
#         print(f"Seeded {len(logs_to_add)} machine logs.")

#         # --- Seed Supporting Data ---
#         cursor.execute("INSERT INTO training_modules (id, title, module_type, content_url, duration_minutes, associated_machine_model) VALUES (?, ?, ?, ?, ?, ?)",
#                    (str(uuid.uuid4()), 'Excavator Pre-op Inspection', 'Video', 's6o31g_H_KI', 3, 'Caterpillar 336 Excavator'))
        
#         badge_id = str(uuid.uuid4())
#         cursor.execute("INSERT INTO badges (id, name, description, icon_class) VALUES (?, ?, ?, ?)", 
#                    (badge_id, 'Quick Learner', 'Complete a training module.', 'fa-graduation-cap'))
#         cursor.execute("INSERT INTO user_badges (user_id, badge_id, earned_at) VALUES (?, ?, ?)", (user_id, badge_id, datetime.now().isoformat()))

#         checklist_items = [
#             ('Check for fluid leaks (oil, coolant, hydraulic)', 'Fluids'),
#             ('Inspect tracks/tires for wear and damage', 'Mechanical'),
#             ('Verify all lights and alarms are functional', 'Safety'),
#         ]
#         cursor.executemany("INSERT INTO checklist_items (item_text, category) VALUES (?, ?)", checklist_items)
#         print("Seeded training, badges, and checklist items.")

#         conn.commit()
#         print("Database seeded successfully.")

#     except sqlite3.Error as e:
#         print(f"Error seeding data: {e}")
#         conn.rollback()

# if __name__ == '__main__':
#     """Main function to set up and seed the database."""
#     connection = create_connection()
#     if connection:
#         create_tables(connection)
#         seed_data(connection)
#         connection.close()
#         print("Database setup complete and connection closed.")
