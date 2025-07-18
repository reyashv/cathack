# app.py
import sqlite3
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_cors import CORS
import os
import joblib
import pandas as pd
from functools import wraps
from datetime import datetime
import uuid
import random

# --- CONFIGURATION ---
DB_NAME = "operator_assistant.db"
MODEL_PATH = "task_time_predictor.joblib"

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_for_production'
CORS(app)

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def load_model():
    """Loads the prediction model from disk."""
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            print(f"Error loading model: {e}")
    return None

model = load_model()
if model:
    print("Prediction model loaded successfully.")
else:
    print(f"Model file not found at {MODEL_PATH}. Prediction endpoint will not work. Run 'python ml_predictor.py' to train it.")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({"success": False, "message": "Authentication required"}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
    
# --- AUTHENTICATION & PAGE SERVING ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        operator_id_str = data.get('operator_id_str')
        password = data.get('password')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE operator_id_str = ?', (operator_id_str,)).fetchone()
        conn.close()
        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['operator_id_str'] = user['operator_id_str']
            return jsonify({"success": True, "user": {"name": user['name'], "operator_id_str": user['operator_id_str']}})
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('login') if 'user_id' not in session else url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/scheduler')
@login_required
def scheduler():
    return render_template('scheduler.html')


# --- PROTECTED API ENDPOINTS ---

@app.route('/api/dashboard_data')
@login_required
def get_dashboard_data():
    conn = get_db_connection()
    today_str = datetime.today().strftime('%Y-%m-%d')
    # This query correctly fetches tasks only for the logged-in user.
    tasks_today = conn.execute("""
        SELECT t.id, t.status, t.task_volume as target_cycles, t.current_cycles, pt.name as title, t.assigned_to_machine_id
        FROM tasks t
        JOIN predefined_tasks pt ON t.predefined_task_id = pt.id
        WHERE t.assigned_to_user_id = ? AND t.day = ?
        ORDER BY CASE t.status WHEN 'In Progress' THEN 1 WHEN 'Pending' THEN 2 ELSE 3 END, t.created_at
    """, (session['user_id'], today_str)).fetchall()

    machine = None
    # Find the machine assigned to the user, either from today's tasks or their most recent task.
    if tasks_today and tasks_today[0]['assigned_to_machine_id']:
        machine_id = tasks_today[0]['assigned_to_machine_id']
        machine = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    else:
        task_with_machine = conn.execute("SELECT assigned_to_machine_id FROM tasks WHERE assigned_to_user_id = ? ORDER BY day DESC LIMIT 1", (session['user_id'],)).fetchone()
        if task_with_machine:
            machine = conn.execute("SELECT * FROM machines WHERE id = ?", (task_with_machine['assigned_to_machine_id'],)).fetchone()

    conn.close()
    return jsonify({
        "machine": dict(machine) if machine else None,
        "tasks_today": [dict(task) for task in tasks_today]
    })

@app.route('/api/task/update_cycles', methods=['POST'])
@login_required
def update_task_cycles():
    data = request.json
    conn = get_db_connection()
    conn.execute("UPDATE tasks SET current_cycles = ? WHERE id = ? AND assigned_to_user_id = ?", 
                 (data.get('current_cycles'), data.get('task_id'), session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/task/update_status', methods=['POST'])
@login_required
def update_task_status():
    data = request.json
    conn = get_db_connection()
    conn.execute("UPDATE tasks SET status = ? WHERE id = ? AND assigned_to_user_id = ?", 
                 (data.get('status'), data.get('task_id'), session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/issue/report', methods=['POST'])
@login_required
def report_issue():
    data = request.json
    conn = get_db_connection()
    # Find the machine associated with the user to log the issue correctly.
    machine = conn.execute("SELECT assigned_to_machine_id as id FROM tasks WHERE assigned_to_user_id = ? ORDER BY created_at DESC LIMIT 1", (session['user_id'],)).fetchone()
    machine_id = machine['id'] if machine else None
    
    conn.execute("INSERT INTO issue_reports (machine_id, user_id, category, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                 (machine_id, session['user_id'], data['category'], data.get('details', ''), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Issue reported successfully."})

@app.route('/api/status/<machine_id_str>')
@login_required
def get_machine_status(machine_id_str):
    conn = get_db_connection()
    log = conn.execute(
        "SELECT * FROM machine_logs WHERE machine_id_str = ? ORDER BY timestamp DESC LIMIT 1",
        (machine_id_str,)
    ).fetchone()
    conn.close()
    if log:
        return jsonify(dict(log))
    return jsonify({"error": "No status found for this machine"}), 404

@app.route('/api/training/<path:machine_model>')
@login_required
def get_training_materials(machine_model):
    conn = get_db_connection()
    materials = conn.execute(
        "SELECT * FROM training_modules WHERE associated_machine_model = ? OR associated_machine_model = 'All'",
        (machine_model,)
    ).fetchall()
    conn.close()
    return jsonify([dict(m) for m in materials])

# --- FIXED AND IMPROVED ENDPOINTS ---

@app.route('/api/tasks_for_month')
@login_required
def get_tasks_for_month():
    """
    FIXED: Fetches tasks for the logged-in user only.
    IMPROVED: Returns more task details for the calendar pop-up.
    """
    month_str = request.args.get('month') # e.g., '2025-07'
    conn = get_db_connection()
    tasks = conn.execute("""
        SELECT t.id, t.day, t.status, t.task_volume, pt.name as title, pt.task_unit
        FROM tasks t
        JOIN predefined_tasks pt ON t.predefined_task_id = pt.id
        WHERE strftime('%Y-%m', t.day) = ? AND t.assigned_to_user_id = ?
    """, (month_str, session['user_id'])).fetchall()
    conn.close()
    return jsonify([dict(task) for task in tasks])
    
@app.route('/api/predefined_tasks')
@login_required
def get_predefined_tasks():
    conn = get_db_connection()
    tasks = conn.execute("SELECT * FROM predefined_tasks ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(task) for task in tasks])

@app.route('/api/predict/time', methods=['POST'])
@login_required
def predict_time():
    if not model:
        return jsonify({"success": False, "message": "Model not loaded"}), 503
    
    data = request.json
    try:
        df = pd.DataFrame([data])
        # Add default/contextual values for features not in the simplified UI
        df['safety_alerts_triggered'] = 0
        df['idling_time_min'] = 0
        df['day_of_week'] = datetime.strptime(data['day'], '%Y-%m-%d').strftime('%w')
        df['hour_of_day'] = 8 # Assume tasks start in the morning
        
        # Get operator and machine info from session/DB for accurate prediction
        conn = get_db_connection()
        user = conn.execute("SELECT experience_level, operator_id_str FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        
        # Use the user's last known machine for prediction context
        last_task = conn.execute("SELECT m.machine_id_str FROM tasks t JOIN machines m ON t.assigned_to_machine_id = m.id WHERE t.assigned_to_user_id = ? ORDER BY t.day DESC LIMIT 1", (session['user_id'],)).fetchone()
        conn.close()
        
        df['operator_experience_level'] = user['experience_level'] if user else 'Mid'
        df['operator_id_str'] = user['operator_id_str'] if user else 'OP-UNKNOWN'
        df['machine_id_str'] = last_task['machine_id_str'] if last_task else 'EXC-UNKNOWN'
        
        prediction = model.predict(df)
        return jsonify({"success": True, "predicted_duration_minutes": round(prediction[0])})
    except Exception as e:
        print(f"Prediction Error: {e}")
        return jsonify({"success": False, "message": f"Prediction error: {e}"}), 400

@app.route('/api/tasks/create', methods=['POST'])
@login_required
def create_task():
    """
    FIXED: Assigns the new task to the currently logged-in user instead of a random one.
    IMPROVED: Assigns the user's most recently used machine, with a fallback to a random one.
    """
    data = request.json
    conn = get_db_connection()
    try:
        # The new task is assigned to the user in the current session.
        assigned_user_id = session['user_id']

        # Find the user's most recently used machine to maintain consistency.
        last_task = conn.execute(
            "SELECT assigned_to_machine_id FROM tasks WHERE assigned_to_user_id = ? ORDER BY day DESC, created_at DESC LIMIT 1",
            (assigned_user_id,)
        ).fetchone()
        
        if last_task and last_task['assigned_to_machine_id']:
            assigned_machine_id = last_task['assigned_to_machine_id']
        else:
            # Fallback to a random machine if the user has no task history.
            machines = conn.execute("SELECT id FROM machines").fetchall()
            if not machines:
                return jsonify({"success": False, "message": "No machines available in the system."}), 500
            assigned_machine_id = random.choice(machines)['id']

        conn.execute("""
            INSERT INTO tasks (id, predefined_task_id, assigned_to_user_id, assigned_to_machine_id, day, task_volume, weather_factor, material_density_factor, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
        """, (
            str(uuid.uuid4()), data['predefined_task_id'], assigned_user_id, assigned_machine_id,
            data['day'], data['task_volume'], data['weather_factor'], data['material_density_factor'],
            datetime.now().isoformat()
        ))
        conn.commit()
    finally:
        conn.close()
        
    return jsonify({"success": True, "message": "Task scheduled successfully."}), 201


if __name__ == '__main__':
    if not os.path.exists(DB_NAME):
        print(f"Database not found. Please run 'python db.py' to create and seed it.")
    app.run(debug=True, port=5000)
