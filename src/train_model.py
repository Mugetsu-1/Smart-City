import os
import joblib
import pandas as pd
import numpy as np
import psycopg2
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error

DB_CONN = "postgresql://postgres:postgrespassword@localhost:5432/transit_db"

def load_data_from_db():
    print("Attempting to load data from PostgreSQL database...")
    query = """
        SELECT 
            mv.demand_hour AS timestamp,
            mv.stop_id,
            mv.tap_in_count AS demand,
            hc.precipitation_mm,
            hc.temperature_c AS temp_c
        FROM mv_hourly_stop_demand mv
        LEFT JOIN hourly_context hc ON mv.demand_hour = hc.context_timestamp
        ORDER BY mv.stop_id, mv.demand_hour
    """
    conn = psycopg2.connect(DB_CONN)
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # Re-calculate is_weekend
    df['is_weekend'] = (df['timestamp'].dt.dayofweek >= 5).astype(int)
    
    print(f"Loaded {len(df)} records from database.")
    return df

def load_data_from_csv():
    print("Loading data from fallback CSV file...")
    csv_path = "data/synthetic_transit_demand.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Fallback CSV file not found at {csv_path}. Please run generate_data.py first.")
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    print(f"Loaded {len(df)} records from CSV.")
    return df

def prepare_features(df):
    print("Preparing features (Temporal encodings, Lags, and Rolling averages)...")
    df = df.sort_values(['stop_id', 'timestamp']).copy()
    
    # Temporal Encodings
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    df['month'] = df['timestamp'].dt.month
    df['is_peak'] = df['hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)
    
    # Lag Features per Stop
    df['demand_lag_1h'] = df.groupby('stop_id')['demand'].shift(1)
    df['demand_lag_24h'] = df.groupby('stop_id')['demand'].shift(24)
    df['demand_lag_168h'] = df.groupby('stop_id')['demand'].shift(168) # 1 week lag
    
    # Rolling Averages
    df['rolling_3h_mean'] = df.groupby('stop_id')['demand_lag_1h'].transform(lambda x: x.rolling(3).mean())
    df['rolling_24h_mean'] = df.groupby('stop_id')['demand_lag_1h'].transform(lambda x: x.rolling(24).mean())
    
    return df.dropna()

def train_and_evaluate():
    # Load raw data
    try:
        df_raw = load_data_from_db()
    except Exception as e:
        print(f"Database connection failed ({e}). Falling back to CSV.")
        df_raw = load_data_from_csv()
        
    df_features = prepare_features(df_raw)
    
    feature_cols = [
        'hour', 'dayofweek', 'month', 'is_peak', 'is_weekend',
        'precipitation_mm', 'temp_c',
        'demand_lag_1h', 'demand_lag_24h', 'demand_lag_168h',
        'rolling_3h_mean', 'rolling_24h_mean'
    ]
    target_col = 'demand'
    
    X = df_features[feature_cols]
    y = df_features[target_col]
    
    # Time-based Train/Test Split (80% Train, 20% Test)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"Training set size: {len(X_train)} | Test set size: {len(X_test)}")
    
    # Model Training
    print("Training XGBoost Regressor...")
    model = XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Evaluation
    print("Evaluating model...")
    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    mae = mean_absolute_error(y_test, preds)
    
    print("\n--- Model Evaluation ---")
    print(f"RMSE: {rmse:.2f} passengers/hour")
    print(f"MAE:  {mae:.2f} passengers/hour\n")
    
    # Save the trained model and features
    os.makedirs("models", exist_ok=True)
    model_path = "models/xgboost_transit_model.joblib"
    joblib.dump(model, model_path)
    print(f"Trained model saved successfully to {model_path}")
    
    # Also save the columns list for prediction reference
    joblib.dump(feature_cols, "models/feature_cols.joblib")
    
    return model, rmse, mae

if __name__ == "__main__":
    train_and_evaluate()
