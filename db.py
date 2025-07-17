import psycopg2
from psycopg2 import Error
from datetime import datetime

# 1. Database connection parameters
# IMPORTANT: Replace these with your actual PostgreSQL credentials
DB_PARAMS = {
    "host": "localhost",
    "database": "hackathon", # e.g., 'postgres' or your specific DB name
    "user": "postgres",         # e.g., 'postgres'
    "password": "shreya123",
    "port": "5432"
}

def execute_sql(cursor, sql_statement, message="Executing SQL"):
    """Helper function to execute SQL and print status."""
    print(f"{message}...")
    try:
        cursor.execute(sql_statement)
        print("Success.")
    except Error as e:
        print(f"Error: {e}")
        raise # Re-raise the exception to trigger rollback

def create_tables(conn, cursor):
    """Creates all necessary tables in the correct order."""

    # 1. Create Users table
    create_users_sql = """
    CREATE TABLE IF NOT EXISTS Users (
        operator_id VARCHAR(50) PRIMARY KEY,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE,
        phone_number VARCHAR(20),
        employment_date DATE,
        certification_level VARCHAR(50),
        assigned_shift VARCHAR(50),
        status VARCHAR(50) DEFAULT 'Active'
    );
    """
    execute_sql(cursor, create_users_sql, "Creating 'Users' table")

    # 2. Create Machines table
    create_machines_sql = """
    CREATE TABLE IF NOT EXISTS Machines (
        machine_id VARCHAR(50) PRIMARY KEY,
        machine_type VARCHAR(100) NOT NULL,
        model_number VARCHAR(100),
        serial_number VARCHAR(100) UNIQUE,
        purchase_date DATE,
        current_location VARCHAR(255),
        last_service_date DATE,
        next_service_due_hours INT,
        status VARCHAR(50) DEFAULT 'Operational'
    );
    """
    execute_sql(cursor, create_machines_sql, "Creating 'Machines' table")

    # 3. Create Machine_Operations_Log table (depends on Users and Machines)
    create_ops_log_sql = """
    CREATE TABLE IF NOT EXISTS Machine_Operations_Log (
        log_id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL,
        machine_id VARCHAR(50) NOT NULL,
        operator_id VARCHAR(50) NOT NULL,
        engine_hours REAL,
        fuel_used_liters REAL,
        load_cycles INT,
        idling_time_min INT,
        seatbelt_status VARCHAR(50),
        safety_alert_triggered VARCHAR(50),
        slope_angle_alert VARCHAR(50),
        visibility_condition VARCHAR(50),
        load_distribution_status VARCHAR(50),
        FOREIGN KEY (machine_id) REFERENCES Machines(machine_id),
        FOREIGN KEY (operator_id) REFERENCES Users(operator_id)
    );
    """
    execute_sql(cursor, create_ops_log_sql, "Creating 'Machine_Operations_Log' table")

    # 4. Create Tasks table (depends on Users and Machines)
    create_tasks_sql = """
    CREATE TABLE IF NOT EXISTS Tasks (
        task_id VARCHAR(50) PRIMARY KEY,
        task_name VARCHAR(255) NOT NULL,
        machine_id VARCHAR(50) NOT NULL,
        operator_id VARCHAR(50) NOT NULL,
        scheduled_start_time TIMESTAMP NOT NULL,
        scheduled_end_time TIMESTAMP NOT NULL,
        actual_start_time TIMESTAMP,
        actual_end_time TIMESTAMP,
        status VARCHAR(50) DEFAULT 'Scheduled',
        task_description TEXT,
        verification_status VARCHAR(50) DEFAULT 'Pending',
        FOREIGN KEY (machine_id) REFERENCES Machines(machine_id),
        FOREIGN KEY (operator_id) REFERENCES Users(operator_id)
    );
    """
    execute_sql(cursor, create_tasks_sql, "Creating 'Tasks' table")
    conn.commit() # Commit after all table creations

def insert_sample_data(conn, cursor):
    """Inserts sample data into all tables in the correct order."""

    # 1. Insert into Users table
    users_data = [
        ('OP1001', 'Alice', 'Smith', 'alice.smith@example.com', '555-1001', '2022-01-15', 'Certified Excavator', 'Day Shift', 'Active'),
        ('OP1002', 'Bob', 'Johnson', 'bob.j@example.com', '555-1002', '2021-06-01', 'Certified Wheel Loader', 'Day Shift', 'Active'),
        ('OP1003', 'Charlie', 'Brown', 'charlie.b@example.com', '555-1003', '2023-03-10', 'Certified Grader', 'Night Shift', 'Active'),
        ('OP1004', 'Diana', 'Prince', 'diana.p@example.com', '555-1004', '2020-09-20', 'Certified Dozer', 'Day Shift', 'Active'),
        ('OP1005', 'Eve', 'Davis', 'eve.d@example.com', '555-1005', '2024-02-01', 'Certified Excavator', 'Night Shift', 'Active'),
        ('OP1006', 'Frank', 'White', 'frank.w@example.com', '555-1006', '2025-01-05', 'Trainee', 'Day Shift', 'Active')
    ]
    insert_users_sql = """
    INSERT INTO Users (operator_id, first_name, last_name, email, phone_number, employment_date, certification_level, assigned_shift, status) VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (operator_id) DO NOTHING; -- Prevents errors if data already exists
    """
    print("Inserting sample data into 'Users' table...")
    cursor.executemany(insert_users_sql, users_data)
    print(f"Inserted {cursor.rowcount} new rows into Users.")

    # 2. Insert into Machines table
    machines_data = [
        ('EXC001', 'Excavator', 'Cat 320D', 'SN-EXC-001-A', '2020-03-10', 'Mine Site A - Sector 3', '2025-06-15', 200, 'Operational'),
        ('WHL002', 'Wheel Loader', 'Cat 980M', 'SN-WHL-002-B', '2019-07-22', 'Quarry B - Stockpile', '2025-05-20', 150, 'Operational'),
        ('GRD003', 'Grader', 'Cat 140K', 'SN-GRD-003-C', '2021-01-05', 'Road Construction C', '2025-06-01', 100, 'Operational'),
        ('BULL004', 'Dozer', 'Cat D6N', 'SN-BUL-004-D', '2022-09-18', 'Mine Site A - Pit 1', '2025-04-25', 250, 'Operational'),
        ('ART005', 'Articulated Truck', 'Cat 745', 'SN-ART-005-E', '2023-02-14', 'Quarry B - Haul Road', '2025-07-01', 300, 'Operational')
    ]
    insert_machines_sql = """
    INSERT INTO Machines (machine_id, machine_type, model_number, serial_number, purchase_date, current_location, last_service_date, next_service_due_hours, status) VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (machine_id) DO NOTHING; -- Prevents errors if data already exists
    """
    print("Inserting sample data into 'Machines' table...")
    cursor.executemany(insert_machines_sql, machines_data)
    print(f"Inserted {cursor.rowcount} new rows into Machines.")

    # 3. Insert into Machine_Operations_Log table
    # Note: Timestamps need to be converted to datetime objects
    ops_log_data = [
        ('2025-07-17 08:00:00', 'EXC001', 'OP1001', 1550.5, 6.2, 15, 25, 'Fastened', 'No', 'Normal', 'Clear', 'Balanced'),
        ('2025-07-17 09:15:00', 'WHL002', 'OP1002', 2320.1, 4.8, 10, 55, 'Fastened', 'No', 'Normal', 'Dusty', 'Balanced'),
        ('2025-07-17 21:30:00', 'GRD003', 'OP1003', 890.3, 3.1, 7, 18, 'Unfastened', 'Yes', 'Normal', 'Night Operations', 'Balanced'),
        ('2025-07-18 10:00:00', 'BULL004', 'OP1004', 1205.7, 7.5, 12, 30, 'Fastened', 'Yes', 'Warning (12deg)', 'Clear', 'Unbalanced (Right)'),
        ('2025-07-18 14:45:00', 'EXC001', 'OP1005', 1560.1, 8.9, 18, 40, 'Fastened', 'Yes', 'Critical (28deg)', 'Dusty', 'Overloaded'),
        ('2025-07-18 16:00:00', 'WHL002', 'OP1001', 2325.5, 5.5, 11, 30, 'Fastened', 'No', 'Normal', 'Clear', 'Balanced'),
        ('2025-07-18 17:30:00', 'GRD003', 'OP1002', 895.0, 3.5, 8, 20, 'Fastened', 'No', 'Normal', 'Clear', 'Balanced'),
        ('2025-07-18 19:00:00', 'BULL004', 'OP1003', 1210.0, 6.0, 10, 65, 'Unfastened', 'Yes', 'Normal', 'Night Operations', 'Balanced')
    ]
    # Convert timestamp strings to datetime objects
    formatted_ops_log_data = [
        (datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S'),) + row[1:]
        for row in ops_log_data
    ]

    insert_ops_log_sql = """
    INSERT INTO Machine_Operations_Log (timestamp, machine_id, operator_id, engine_hours, fuel_used_liters, load_cycles, idling_time_min, seatbelt_status, safety_alert_triggered, slope_angle_alert, visibility_condition, load_distribution_status) VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    print("Inserting sample data into 'Machine_Operations_Log' table...")
    cursor.executemany(insert_ops_log_sql, formatted_ops_log_data)
    print(f"Inserted {cursor.rowcount} new rows into Machine_Operations_Log.")

    # 4. Insert into Tasks table
    tasks_data = [
        ('TASK001', 'Daily Pre-Op Check', 'EXC001', 'OP1001', '2025-07-17 07:30:00', '2025-07-17 08:00:00', '2025-07-17 07:35:00', '2025-07-17 07:55:00', 'Completed', 'Perform full pre-operation checklist for excavator.', 'Verified'),
        ('TASK002', 'Haul Material to Stockpile A', 'WHL002', 'OP1002', '2025-07-17 09:00:00', '2025-07-17 12:00:00', '2025-07-17 09:05:00', '2025-07-17 12:05:00', 'Completed', 'Transport excavated material to designated stockpile area.', 'Pending'),
        ('TASK003', 'Grade Access Road Section 1', 'GRD003', 'OP1003', '2025-07-17 21:00:00', '2025-07-18 01:00:00', None, None, 'Scheduled', 'Smooth and level access road in Section 1 for night shift.', 'Pending'),
        ('TASK004', 'Clear Overburden Pit 1', 'BULL004', 'OP1004', '2025-07-18 09:30:00', '2025-07-18 13:00:00', None, None, 'Scheduled', 'Remove topsoil and rock from Pit 1 area.', 'Pending'),
        ('TASK005', 'Load Haul Trucks Section 3', 'EXC001', 'OP1005', '2025-07-18 14:00:00', '2025-07-18 17:00:00', None, None, 'Scheduled', 'Load articulated trucks from excavation point in Section 3.', 'Pending')
    ]
    # Convert timestamp strings to datetime objects, handle None for actual_start/end_time
    formatted_tasks_data = []
    for row in tasks_data:
        formatted_row = list(row)
        for i in [4, 5, 6, 7]: # Indices for scheduled_start/end, actual_start/end
            if formatted_row[i] is not None:
                formatted_row[i] = datetime.strptime(formatted_row[i], '%Y-%m-%d %H:%M:%S')
        formatted_tasks_data.append(tuple(formatted_row))

    insert_tasks_sql = """
    INSERT INTO Tasks (task_id, task_name, machine_id, operator_id, scheduled_start_time, scheduled_end_time, actual_start_time, actual_end_time, status, task_description, verification_status) VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (task_id) DO NOTHING; -- Prevents errors if data already exists
    """
    print("Inserting sample data into 'Tasks' table...")
    cursor.executemany(insert_tasks_sql, formatted_tasks_data)
    print(f"Inserted {cursor.rowcount} new rows into Tasks.")

    conn.commit() # Commit all insertions

def setup_database():
    """
    Connects to a PostgreSQL database, creates all tables, and inserts sample data.
    """
    conn = None
    cursor = None
    try:
        print("Connecting to the PostgreSQL database...")
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        print("Database connection successful.")

        # Create tables
        create_tables(conn, cursor)

        # Insert sample data
        insert_sample_data(conn, cursor)

        print("\nDatabase setup complete: Tables created and populated with sample data.")

    except (Exception, Error) as error:
        print(f"\nAn error occurred during database setup: {error}")
        if conn:
            conn.rollback() # Rollback all changes in case of error

    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("PostgreSQL connection closed.")

if __name__ == "__main__":
    setup_database()
