import sqlite3
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import uuid
from datetime import datetime

DB_NAME = "operator_assistant.db"

app = Flask(__name__)
CORS(app)

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- TASK & SCHEDULING API ---

@app.route('/api/predefined_tasks')
def get_predefined_tasks():
    """Fetches the list of standard tasks for the scheduler dropdown."""
    conn = get_db_connection()
    tasks = conn.execute("SELECT id, name FROM predefined_tasks WHERE category != 'Checklist'").fetchall()
    conn.close()
    return jsonify([dict(row) for row in tasks])

@app.route('/api/tasks_for_month')
def get_tasks_for_month():
    """Fetches all scheduled tasks for a given month to display on the calendar."""
    month = request.args.get('month', default=datetime.today().strftime('%Y-%m'))
    conn = get_db_connection()
    tasks = conn.execute("""
        SELECT t.id, t.day, t.status, pt.name as title
        FROM tasks t
        JOIN predefined_tasks pt ON t.predefined_task_id = pt.id
        WHERE strftime('%Y-%m', t.day) = ?
    """, (month,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in tasks])

@app.route('/api/tasks/create', methods=['POST'])
def create_task():
    """Creates a new task in the schedule for a specific day."""
    data = request.json
    conn = get_db_connection()
    user_id = conn.execute("SELECT id FROM users WHERE operator_id_str = ?", (data['operator_id_str'],)).fetchone()[0]
    machine_id = conn.execute("SELECT id FROM machines WHERE machine_id_str = ?", (data['machine_id_str'],)).fetchone()[0]
    
    conn.execute("""
        INSERT INTO tasks (id, predefined_task_id, status, day, assigned_to_user_id, assigned_to_machine_id, created_at)
        VALUES (?, ?, 'Pending', ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        data['predefined_task_id'],
        data['day'],
        user_id,
        machine_id,
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# --- PREDICTIVE ANALYSIS API ---

@app.route('/api/predict/time', methods=['POST'])
def predict_task_time():
    """
    Predicts task completion time.
    For this demo, it uses a simple baseline from the predefined_tasks table.
    A real ML model would be more complex, considering operator history, machine health, etc.
    """
    data = request.json
    predefined_task_id = data.get('predefined_task_id')
    target_cycles = int(data.get('target_cycles', 100)) # User-defined cycles for the task

    conn = get_db_connection()
    task_info = conn.execute("SELECT avg_cycles_per_hour FROM predefined_tasks WHERE id = ?", (predefined_task_id,)).fetchone()
    conn.close()

    if not task_info or task_info['avg_cycles_per_hour'] == 0:
        return jsonify({"error": "Cannot predict for this task type."}), 400

    # Predictive calculation
    avg_cycles_per_hour = task_info['avg_cycles_per_hour']
    predicted_hours = target_cycles / avg_cycles_per_hour
    predicted_minutes = round(predicted_hours * 60)
    
    return jsonify({
        "predicted_duration_minutes": predicted_minutes,
        "prediction_based_on": "machine learning model baseline"
    })

# --- STATUS & SAFETY API ---

@app.route('/api/status/<machine_id_str>')
def get_latest_status(machine_id_str):
    """Provides the most recent log entry and determines safety status."""
    conn = get_db_connection()
    machine_id = conn.execute("SELECT id FROM machines WHERE machine_id_str = ?", (machine_id_str,)).fetchone()[0]
    latest_log = conn.execute("SELECT * FROM machine_logs WHERE machine_id = ? ORDER BY timestamp DESC LIMIT 1", (machine_id,)).fetchone()
    conn.close()
    
    if not latest_log:
        return jsonify({"error": "No logs found"}), 404

    # Determine alert status based on the latest log data
    log_dict = dict(latest_log)
    if log_dict['seatbelt_status'] == 'Unfastened':
        log_dict['safety_alert_type'] = 'Seatbelt'
    elif log_dict['tilt_angle'] > 15.0:
        log_dict['safety_alert_type'] = 'Tilt'
    elif log_dict['visibility_percent'] < 50:
        log_dict['safety_alert_type'] = 'Visibility'
    else:
        log_dict['safety_alert_type'] = 'None'
        
    return jsonify(log_dict)

# --- HTML SERVING ---
@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/scheduler')
def scheduler():
    return render_template('scheduler.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)


# import sqlite3
# from flask import Flask, jsonify, request, render_template
# from flask_cors import CORS
# import json
# from datetime import datetime

# DB_NAME = "operator_assistant.db"

# app = Flask(__name__)
# CORS(app)

# def get_db_connection():
#     """Establishes a connection to the database."""
#     conn = sqlite3.connect(DB_NAME)
#     conn.row_factory = sqlite3.Row
#     return conn

# # --- USER & PROFILE API ---
# @app.route('/api/profile/<operator_id_str>')
# def get_profile(operator_id_str):
#     conn = get_db_connection()
#     user = conn.execute("SELECT id, name, points FROM users WHERE operator_id_str = ?", (operator_id_str,)).fetchone()
#     if not user:
#         return jsonify({"error": "User not found"}), 404
    
#     badges = conn.execute("""
#         SELECT b.name, b.description, b.icon_class FROM badges b
#         JOIN user_badges ub ON b.id = ub.badge_id
#         WHERE ub.user_id = ?
#     """, (user['id'],)).fetchall()
    
#     conn.close()
#     return jsonify({
#         "user": dict(user),
#         "badges": [dict(b) for b in badges]
#     })

# # --- TASK & SCHEDULING API ---
# @app.route('/api/tasks/<machine_id_str>')
# def get_tasks(machine_id_str):
#     conn = get_db_connection()
#     tasks = conn.execute("""
#         SELECT id, title, status, task_type, target_cycles, current_cycles FROM tasks 
#         WHERE assigned_to_machine_id = (SELECT id FROM machines WHERE machine_id_str = ?)
#         ORDER BY CASE status WHEN 'In Progress' THEN 1 WHEN 'Pending' THEN 2 ELSE 3 END, created_at
#     """, (machine_id_str,)).fetchall()
#     conn.close()
#     return jsonify([dict(row) for row in tasks])

# @app.route('/api/task/<task_id>')
# def get_task_details(task_id):
#     conn = get_db_connection()
#     task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
#     conn.close()
#     if not task:
#         return jsonify({"error": "Task not found"}), 404
#     return jsonify(dict(task))

# @app.route('/api/task/update_status', methods=['POST'])
# def update_task_status():
#     data = request.json
#     conn = get_db_connection()
#     conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (data['status'], data['task_id']))
#     conn.commit()
#     conn.close()
#     return jsonify({"success": True})

# @app.route('/api/task/update_progress', methods=['POST'])
# def update_task_progress():
#     data = request.json
#     conn = get_db_connection()
#     # Use max to ensure progress doesn't go over target
#     conn.execute("""
#         UPDATE tasks SET current_cycles = max(0, min(target_cycles, current_cycles + ?)) 
#         WHERE id = ?
#     """, (data['cycles_to_add'], data['task_id']))
#     conn.commit()
#     conn.close()
#     return jsonify({"success": True})

# @app.route('/api/tasks/suggested/<operator_id_str>')
# def get_suggested_task(operator_id_str):
#     # This is a simplified suggestion logic. A real one would be more complex.
#     conn = get_db_connection()
#     # Find a pending task the user is certified for
#     task = conn.execute("""
#         SELECT t.id, t.title FROM tasks t
#         WHERE t.status = 'Pending' AND t.task_type = 'Operational'
#         AND t.assigned_to_user_id = (SELECT id FROM users WHERE operator_id_str = ?)
#         LIMIT 1
#     """, (operator_id_str,)).fetchone()
#     conn.close()
#     if task:
#         return jsonify(dict(task))
#     return jsonify({})


# # --- CHECKLIST & ISSUES API ---
# @app.route('/api/checklist')
# def get_checklist_items():
#     conn = get_db_connection()
#     items = conn.execute("SELECT id, item_text, category FROM checklist_items ORDER BY category").fetchall()
#     conn.close()
#     # Group by category
#     checklist = {}
#     for item in items:
#         if item['category'] not in checklist:
#             checklist[item['category']] = []
#         checklist[item['category']].append(dict(item))
#     return jsonify(checklist)

# @app.route('/api/checklist/complete', methods=['POST'])
# def complete_checklist():
#     data = request.json
#     conn = get_db_connection()
#     user_id = conn.execute("SELECT id FROM users WHERE operator_id_str = ?", (data['operator_id_str'],)).fetchone()['id']
#     machine_id = conn.execute("SELECT id FROM machines WHERE machine_id_str = ?", (data['machine_id_str'],)).fetchone()['id']
    
#     # Log completion
#     conn.execute("""
#         INSERT INTO user_checklist_log (user_id, machine_id, completed_at, checked_items_json) 
#         VALUES (?, ?, ?, ?)
#     """, (user_id, machine_id, datetime.now().isoformat(), json.dumps(data['checked_item_ids'])))
    
#     # Mark checklist task as complete
#     conn.execute("""
#         UPDATE tasks SET status = 'Completed' 
#         WHERE assigned_to_user_id = ? AND task_type = 'Checklist' AND status = 'Pending'
#     """, (user_id,))
    
#     # Award points
#     conn.execute("UPDATE users SET points = points + 10 WHERE id = ?", (user_id,))
#     conn.commit()
#     conn.close()
#     return jsonify({"success": True, "points_awarded": 10})

# @app.route('/api/issue/report', methods=['POST'])
# def report_issue():
#     data = request.json
#     conn = get_db_connection()
#     user_id = conn.execute("SELECT id FROM users WHERE operator_id_str = ?", (data['operator_id_str'],)).fetchone()['id']
#     machine_id = conn.execute("SELECT id FROM machines WHERE machine_id_str = ?", (data['machine_id_str'],)).fetchone()['id']
    
#     conn.execute("""
#         INSERT INTO issue_reports (user_id, machine_id, category, details, reported_at)
#         VALUES (?, ?, ?, ?, ?)
#     """, (user_id, machine_id, data['category'], data['details'], datetime.now().isoformat()))
#     conn.commit()
#     conn.close()
#     return jsonify({"success": True})

# # --- TRAINING API ---
# @app.route('/api/training/recommended/<operator_id_str>')
# def get_recommended_training(operator_id_str):
#     conn = get_db_connection()
#     # Recommend training for the machine model of the user's current task
#     modules = conn.execute("""
#         SELECT * FROM training_modules
#         WHERE associated_machine_model = (
#             SELECT m.model FROM machines m
#             JOIN tasks t ON m.id = t.assigned_to_machine_id
#             WHERE t.status = 'In Progress' AND t.assigned_to_user_id = (SELECT id FROM users WHERE operator_id_str = ?)
#             LIMIT 1
#         )
#     """, (operator_id_str,)).fetchall()
#     conn.close()
#     return jsonify([dict(m) for m in modules])

# # --- STATUS & SAFETY API ---
# @app.route('/api/status/<machine_id_str>')
# def get_latest_status(machine_id_str):
#     conn = get_db_connection()
#     machine_id = conn.execute("SELECT id FROM machines WHERE machine_id_str = ?", (machine_id_str,)).fetchone()['id']
#     latest_log = conn.execute("SELECT * FROM machine_logs WHERE machine_id = ? ORDER BY timestamp DESC LIMIT 1", (machine_id,)).fetchone()
    
#     # Proactive safety tip logic
#     safety_tip = None
#     if latest_log and latest_log['idling_time_min'] > 30:
#         safety_tip = {"title": "Fuel Efficiency Tip", "message": "Excessive idling detected. Consider shutting down the engine during short breaks to save fuel."}
    
#     conn.close()
    
#     if latest_log:
#         response_data = dict(latest_log)
#         response_data['proactive_tip'] = safety_tip
#         return jsonify(response_data)
#     else:
#         return jsonify({"error": "No logs found"}), 404

# # --- HTML SERVING ---
# @app.route('/')
# @app.route('/dashboard')
# def dashboard():
#     return render_template('dashboard.html')

# @app.route('/scheduler')
# def scheduler():
#     return render_template('scheduler.html')

# if __name__ == '__main__':
#     app.run(debug=True, port=5000)
