import sqlite3
import uuid
from datetime import datetime, timedelta
import random
import numpy as np

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
        "issue_reports", "training_modules", "machine_logs",
        "tasks", "predefined_tasks", "machines", "users"
    ]
    for table in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table};")
    print("Dropped existing tables for a fresh setup.")

    # --- Table schemas are unchanged ---
    cursor.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            operator_id_str TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            experience_level TEXT NOT NULL,
            password TEXT NOT NULL
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
            category TEXT NOT NULL,
            task_unit TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            predefined_task_id TEXT NOT NULL,
            status TEXT NOT NULL,
            day TEXT NOT NULL,
            task_volume REAL NOT NULL,
            current_cycles REAL NOT NULL DEFAULT 0,
            assigned_to_user_id TEXT NOT NULL,
            assigned_to_machine_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            actual_duration_minutes REAL,
            weather_factor REAL NOT NULL DEFAULT 1.0,
            material_density_factor REAL NOT NULL DEFAULT 1.0,
            safety_alerts_triggered INTEGER DEFAULT 0,
            idling_time_min REAL DEFAULT 0,
            FOREIGN KEY (predefined_task_id) REFERENCES predefined_tasks (id),
            FOREIGN KEY (assigned_to_user_id) REFERENCES users (id),
            FOREIGN KEY (assigned_to_machine_id) REFERENCES machines (id)
        );
    """)
    cursor.execute("""
        CREATE TABLE machine_logs (
            id TEXT PRIMARY KEY,
            machine_id_str TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            seatbelt_status TEXT NOT NULL,
            tilt_angle REAL NOT NULL,
            visibility_percent INTEGER NOT NULL,
            hydraulic_pressure REAL NOT NULL,
            engine_temp REAL NOT NULL,
            FOREIGN KEY (machine_id_str) REFERENCES machines (machine_id_str)
        );
    """)
    cursor.execute("""
        CREATE TABLE training_modules (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            module_type TEXT NOT NULL,
            url TEXT NOT NULL,
            associated_machine_model TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE issue_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT,
            user_id TEXT NOT NULL,
            category TEXT NOT NULL,
            details TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (machine_id) REFERENCES machines (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)

    conn.commit()
    print("All new tables created successfully.")

def seed_data(conn):
    """Seed the database with comprehensive sample data in the correct order."""
    cursor = conn.cursor()

    # 1. Seed Users
    users_data = [
        (str(uuid.uuid4()), 'OP1001', 'John Doe', 'Senior', 'pass'),
        (str(uuid.uuid4()), 'OP1002', 'Jane Smith', 'Mid', 'pass'),
        (str(uuid.uuid4()), 'OP1003', 'Peter Jones', 'Junior', 'pass'),
    ]
    cursor.executemany("INSERT INTO users (id, operator_id_str, name, experience_level, password) VALUES (?, ?, ?, ?, ?)", users_data)
    print(f"Seeded {len(users_data)} users.")

    # 2. Seed Machines
    machines_data = [
        (str(uuid.uuid4()), 'EXC001', 'Caterpillar 336 Excavator'),
        (str(uuid.uuid4()), 'EXC002', 'Komatsu PC210 LC'),
        (str(uuid.uuid4()), 'DOZ001', 'Caterpillar D6R Dozer'),
    ]
    cursor.executemany("INSERT INTO machines (id, machine_id_str, model) VALUES (?, ?, ?)", machines_data)
    print(f"Seeded {len(machines_data)} machines.")
    
    # 3. Seed Machine Logs
    machine_logs = [
        (str(uuid.uuid4()), 'EXC001', datetime.now().isoformat(), 'Unfastened', 16.5, 45, 2850, 110),
        (str(uuid.uuid4()), 'EXC002', datetime.now().isoformat(), 'Fastened', 2.1, 95, 3100, 95),
        (str(uuid.uuid4()), 'DOZ001', datetime.now().isoformat(), 'Unfastened', 3.5, 98, 2500, 98),
    ]
    cursor.executemany("INSERT INTO machine_logs (id, machine_id_str, timestamp, seatbelt_status, tilt_angle, visibility_percent, hydraulic_pressure, engine_temp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", machine_logs)
    print(f"Seeded {len(machine_logs)} machine logs.")
    
    # 4. Seed Training and Predefined Tasks
    training_materials = [
        (str(uuid.uuid4()), 'Excavator Walkaround Inspection', 'Video', 'uaRFepWny-g', 'Caterpillar 336 Excavator'),
        (str(uuid.uuid4()), 'Working Safely Around Heavy Equipment', 'Video', '7tdfizoornI', 'All'),
        (str(uuid.uuid4()), 'Komatsu Excavator Operation', 'PDF', 'https://example.com/komatsu.pdf', 'Komatsu PC210 LC'),
    ]
    cursor.executemany("INSERT INTO training_modules (id, title, module_type, url, associated_machine_model) VALUES (?, ?, ?, ?, ?)", training_materials)
    print(f"Seeded {len(training_materials)} training modules.")
    
    predefined_tasks_data = [
        (str(uuid.uuid4()), 'Trenching for Utilities', 'Trenching', 'cubic_meters'),
        (str(uuid.uuid4()), 'Loading Haul Trucks', 'Loading', 'cubic_meters'),
        (str(uuid.uuid4()), 'Site Grading', 'Grading', 'square_meters'),
    ]
    cursor.executemany("INSERT INTO predefined_tasks (id, name, category, task_unit) VALUES (?, ?, ?, ?)", predefined_tasks_data)
    print(f"Seeded {len(predefined_tasks_data)} predefined tasks.")

    # 5. Seed historical data for ML training
    print("Seeding historical data for ML training...")
    historical_records = []
    num_records = 500
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now() - timedelta(days=1)
    
    all_users = cursor.execute("SELECT id, experience_level FROM users").fetchall()
    all_machines = cursor.execute("SELECT id FROM machines").fetchall()
    all_predefined_tasks = cursor.execute("SELECT id, name FROM predefined_tasks").fetchall()

    for _ in range(num_records):
        task_info = random.choice(all_predefined_tasks)
        predefined_task_id, task_name = task_info[0], task_info[1]
        
        user_id, op_exp_level = random.choice(all_users)
        machine_id = random.choice(all_machines)[0]

        task_volume = np.random.uniform(50, 200) if 'Loading' in task_name else np.random.uniform(1000, 5000)

        material_density_factor = np.random.uniform(0.8, 1.5)
        weather_factor = random.choice([1.0, 1.0, 1.0, 1.1, 1.1, 1.2, 1.3])
        
        op_exp_multiplier = {'Junior': 1.2, 'Mid': 1.0, 'Senior': 0.85}[op_exp_level] * np.random.uniform(0.95, 1.05)

        idling_time_min = np.random.uniform(0, 5)
        safety_alerts = random.randint(0, 2) if random.random() < 0.1 else 0
        if safety_alerts > 0: idling_time_min += np.random.uniform(5, 15)

        base_duration = (task_volume * 0.1) * op_exp_multiplier * material_density_factor * weather_factor
        actual_duration = base_duration + idling_time_min + (safety_alerts * 10)
        actual_duration = round(max(15, actual_duration + np.random.normal(0, 5)))

        task_start_time = start_date + timedelta(seconds=random.randint(0, int((end_date - start_date).total_seconds())))
        task_end_time = task_start_time + timedelta(minutes=actual_duration)
        
        historical_records.append((
            str(uuid.uuid4()), predefined_task_id, 'Completed', task_start_time.strftime('%Y-%m-%d'),
            round(task_volume, 1), round(task_volume, 1), user_id, machine_id, task_start_time.isoformat(),
            task_start_time.isoformat(), task_end_time.isoformat(), actual_duration,
            weather_factor, material_density_factor, safety_alerts, round(idling_time_min,1)
        ))

    cursor.executemany("""
        INSERT INTO tasks (
            id, predefined_task_id, status, day, task_volume, current_cycles, 
            assigned_to_user_id, assigned_to_machine_id, created_at, started_at, completed_at, 
            actual_duration_minutes, weather_factor, material_density_factor, 
            safety_alerts_triggered, idling_time_min
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, historical_records)
    print(f"Seeded {len(historical_records)} historical task records for ML training.")
    
    # 6. Seed today's tasks for dashboard demo for multiple users
    today_str = datetime.today().strftime('%Y-%m-%d')
    # Tasks for John Doe (OP1001)
    user_id_john = users_data[0][0]
    machine_id_cat = machines_data[0][0]
    tasks_today_john = [
        (str(uuid.uuid4()), predefined_tasks_data[0][0], 'In Progress', today_str, 150, 60, user_id_john, machine_id_cat, datetime.now().isoformat(), datetime.now().isoformat()),
        (str(uuid.uuid4()), predefined_tasks_data[1][0], 'Pending', today_str, 200, 0, user_id_john, machine_id_cat, datetime.now().isoformat(), None),
    ]
    # Task for Jane Smith (OP1002)
    user_id_jane = users_data[1][0]
    machine_id_komatsu = machines_data[1][0]
    tasks_today_jane = [
        (str(uuid.uuid4()), predefined_tasks_data[2][0], 'Pending', today_str, 2500, 0, user_id_jane, machine_id_komatsu, datetime.now().isoformat(), None),
    ]
    
    tasks_today = tasks_today_john + tasks_today_jane
    cursor.executemany("""
        INSERT INTO tasks (id, predefined_task_id, status, day, task_volume, current_cycles, assigned_to_user_id, assigned_to_machine_id, created_at, started_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tasks_today)
    print(f"Seeded {len(tasks_today)} tasks for today's dashboard across multiple users.")

    conn.commit()
    print("Database seeded successfully.")

if __name__ == '__main__':
    conn = create_connection()
    if conn:
        create_tables(conn)
        seed_data(conn)
        conn.close()
        print("Database setup complete.")
