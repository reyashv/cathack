# ml_predictor.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib
import sqlite3
import os

DB_NAME = "operator_assistant.db"
MODEL_PATH = "task_time_predictor.joblib"

def get_training_data():
    """Fetches and processes historical data from the database for model training."""
    if not os.path.exists(DB_NAME):
        print(f"Database '{DB_NAME}' not found. Please run 'db.py' first to create and seed it.")
        return None
        
    conn = sqlite3.connect(DB_NAME)
    # This query joins all necessary tables to get features for the model
    query = """
        SELECT
            t.task_volume,
            t.weather_factor,
            t.material_density_factor,
            t.safety_alerts_triggered,
            t.idling_time_min,
            pt.name as task_type,
            u.experience_level as operator_experience_level,
            m.machine_id_str,
            u.operator_id_str,
            STRFTIME('%w', t.started_at) as day_of_week,
            STRFTIME('%H', t.started_at) as hour_of_day,
            t.actual_duration_minutes
        FROM tasks t
        JOIN predefined_tasks pt ON t.predefined_task_id = pt.id
        JOIN users u ON t.assigned_to_user_id = u.id
        JOIN machines m ON t.assigned_to_machine_id = m.id
        WHERE t.status = 'Completed' AND t.actual_duration_minutes IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return df

    # Convert types for modeling
    df['day_of_week'] = df['day_of_week'].astype(int)
    df['hour_of_day'] = df['hour_of_day'].astype(int)

    print(f"Loaded {len(df)} completed tasks for training.")
    print("Data types for training:\n", df.dtypes)
    return df

def train_model():
    """Trains the Random Forest Regressor model and saves it to a file."""
    df = get_training_data()

    if df is None or len(df) < 50:
        print("Not enough historical data to train model. Skipping.")
        return

    X = df.drop('actual_duration_minutes', axis=1)
    y = df['actual_duration_minutes']

    # Define which columns are numerical and which are categorical
    numerical_features = [
        'task_volume', 'weather_factor', 'material_density_factor',
        'safety_alerts_triggered', 'idling_time_min', 'hour_of_day'
    ]
    categorical_features = [
        'task_type', 'operator_experience_level', 'machine_id_str',
        'operator_id_str', 'day_of_week'
    ]

    # Create a preprocessor to handle different data types
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ],
        remainder='drop'
    )

    # Create the full model pipeline
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1))
    ])

    # Split data for training and testing
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("--- Training the prediction model... ---")
    model_pipeline.fit(X_train, y_train)
    print("Model training complete.")

    # Evaluate the model
    y_pred = model_pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"Model Evaluation (Mean Absolute Error): {mae:.2f} minutes")

    # Save the trained model
    joblib.dump(model_pipeline, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    return model_pipeline

if __name__ == '__main__':
    train_model()
