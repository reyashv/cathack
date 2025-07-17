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

    # --- Table creation is unchanged ---
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
            machine_id TEXT NOT NULL,
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
        (str(uuid.uuid4()), 'OP1001', 'John Doe', 'Senior', 'password123'),
        (str(uuid.uuid4()), 'OP1002', 'Jane Smith', 'Mid', 'password123'),
        (str(uuid.uuid4()), 'OP1003', 'Peter Jones', 'Mid', 'password123'),
    ]
    cursor.executemany("INSERT INTO users (id, operator_id_str, name, experience_level, password) VALUES (?, ?, ?, ?, ?)", users_data)
    print(f"Seeded {len(users_data)} users.")

    # 2. Seed Machines
    machines_data = [
        (str(uuid.uuid4()), 'EXC001', 'Caterpillar 336 Excavator'),
        (str(uuid.uuid4()), 'EXC002', 'Komatsu PC210 LC'),
        (str(uuid.uuid4()), 'EXC004', 'Volvo ECR235EL'),
    ]
    cursor.executemany("INSERT INTO machines (id, machine_id_str, model) VALUES (?, ?, ?)", machines_data)
    print(f"Seeded {len(machines_data)} machines.")
    
    # 3. Seed Machine Logs
    machine_logs = [
        (str(uuid.uuid4()), 'EXC001', datetime.now().isoformat(), 'Unfastened', 16.5, 45, 2850, 110),
        (str(uuid.uuid4()), 'EXC002', datetime.now().isoformat(), 'Unfastened', 2.1, 95, 3100, 95),
        (str(uuid.uuid4()), 'EXC004', datetime.now().isoformat(), 'Fastened', 3.5, 98, 3050, 98),
    ]
    cursor.executemany("INSERT INTO machine_logs (id, machine_id_str, timestamp, seatbelt_status, tilt_angle, visibility_percent, hydraulic_pressure, engine_temp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", machine_logs)
    print(f"Seeded {len(machine_logs)} machine logs.")
    
    # CORRECTED ORDER: 4. Seed Training and Predefined Tasks BEFORE using them
    training_materials = [
        (str(uuid.uuid4()), 'Excavator Walkaround Inspection', 'Video', 'uaRFepWny-g', 'Caterpillar 336 Excavator'),
        (str(uuid.uuid4()), 'Working Safely Around Heavy Equipment', 'Video', '7tdfizoornI', 'All'),
        (str(uuid.uuid4()), 'Volvo ECR235EL Operator Manual', 'PDF', 'https://www.volvoce.com/-/media/volvoce/global/global-site/products/excavators/crawler-excavators/ecr235e/downloads/product-brochure-ecr235e-en.pdf', 'Volvo ECR235EL'),
    ]
    cursor.executemany("INSERT INTO training_modules (id, title, module_type, url, associated_machine_model) VALUES (?, ?, ?, ?, ?)", training_materials)
    print(f"Seeded {len(training_materials)} training modules.")
    
    predefined_tasks_data = [
        (str(uuid.uuid4()), 'Excavation', 'Trenching', 'cubic_meters'),
        (str(uuid.uuid4()), 'Material Loading', 'Loading', 'cubic_meters'),
        (str(uuid.uuid4()), 'Grading', 'Grading', 'sq_m'),
    ]
    cursor.executemany("INSERT INTO predefined_tasks (id, name, category, task_unit) VALUES (?, ?, ?, ?)", predefined_tasks_data)
    print(f"Seeded {len(predefined_tasks_data)} predefined tasks.")

    # 5. Seed historical data for ML training
    print("Seeding historical data for ML training...")
    historical_records = []
    num_records = 500
    start_date = datetime(2024, 1, 1)
    end_date = datetime.now() - timedelta(days=1)
    
    # This will now succeed because the tables are populated
    all_users = cursor.execute("SELECT id, experience_level FROM users").fetchall()
    all_machines = cursor.execute("SELECT id FROM machines").fetchall()
    all_predefined_tasks = cursor.execute("SELECT id, name FROM predefined_tasks").fetchall()

    for _ in range(num_records):
        task_info = random.choice(all_predefined_tasks)
        predefined_task_id, task_name = task_info[0], task_info[1]
        
        user_id, op_exp_level = random.choice(all_users)
        machine_id = random.choice(all_machines)[0]

        task_volume = 0
        if task_name in ['Excavation', 'Trenching']: task_volume = np.random.uniform(30, 150)
        elif task_name in ['Material Loading', 'Hauling', 'Site Cleanup']: task_volume = np.random.uniform(50, 200)
        elif task_name == 'Grading': task_volume = np.random.uniform(1000, 5000)

        material_density_factor = np.random.uniform(0.8, 1.5)
        weather_factor = random.choice([1.0, 1.0, 1.0, 1.1, 1.1, 1.2, 1.3])
        
        op_exp_multiplier = 1.0
        if op_exp_level == 'Junior': op_exp_multiplier = np.random.uniform(1.1, 1.3)
        if op_exp_level == 'Mid': op_exp_multiplier = np.random.uniform(0.95, 1.05)
        if op_exp_level == 'Senior': op_exp_multiplier = np.random.uniform(0.8, 0.95)

        base_idling = np.random.uniform(0, 5)
        safety_alerts = 0
        if random.random() < 0.1:
            safety_alerts = random.randint(1,3)
            base_idling += np.random.uniform(5, 15)

        idling_time_min = round(base_idling, 1)

        base_duration_factor = np.random.uniform(1.5, 3.0)
        
        actual_duration = (task_volume * base_duration_factor * material_density_factor * weather_factor * op_exp_multiplier) + (idling_time_min * 0.5)
        if safety_alerts > 0: actual_duration += np.random.uniform(10, 30)
        actual_duration = round(max(15, actual_duration + np.random.uniform(-10, 10)))

        task_start_time = start_date + timedelta(seconds=random.randint(0, int((end_date - start_date).total_seconds())))
        task_end_time = task_start_time + timedelta(minutes=actual_duration)
        
        historical_records.append((
            str(uuid.uuid4()), predefined_task_id, 'Completed', task_start_time.strftime('%Y-%m-%d'),
            round(task_volume, 1), round(task_volume, 1), user_id, machine_id, task_start_time.isoformat(),
            task_start_time.isoformat(), task_end_time.isoformat(), actual_duration,
            weather_factor, material_density_factor, safety_alerts, idling_time_min
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
    
    # 6. Seed today's tasks for dashboard demo
    user_id_john = users_data[0][0]
    machine_id_cat = machines_data[0][0]
    today_str = datetime.today().strftime('%Y-%m-%d')
    tasks_today = [
        (str(uuid.uuid4()), predefined_tasks_data[0][0], 'In Progress', today_str, 150, 60, user_id_john, machine_id_cat, datetime.now().isoformat(), datetime.now().isoformat()),
        (str(uuid.uuid4()), predefined_tasks_data[1][0], 'Pending', today_str, 200, 0, user_id_john, machine_id_cat, datetime.now().isoformat(), None),
    ]
    cursor.executemany("""
        INSERT INTO tasks (id, predefined_task_id, status, day, task_volume, current_cycles, assigned_to_user_id, assigned_to_machine_id, created_at, started_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tasks_today)
    print(f"Seeded {len(tasks_today)} tasks for today's dashboard.")

    conn.commit()
    print("Database seeded successfully.")

if __name__ == '__main__':
    conn = create_connection()
    if conn:
        create_tables(conn)
        seed_data(conn)
        conn.close()
        print("Database setup complete.")