import os
import joblib
import pandas as pd
import numpy as np
import psycopg2
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error

DB_CONN = "postgresql://postgres:postgrespassword@localhost:5433/transit_db"

def load_data_from_db():
    print("Attempting to load demand data from PostgreSQL database...")
    query = """
        SELECT 
            mv.demand_hour AS timestamp,
            mv.stop_id,
            mv.tap_in_count AS demand,
            ec.precipitation_mm,
            ec.temperature_c AS temp_c,
            ec.is_saturday,
            ec.is_holiday,
            ec.is_festival
        FROM mv_hourly_stop_demand mv
        LEFT JOIN environmental_context ec ON mv.demand_hour = ec.context_timestamp
        ORDER BY mv.stop_id, mv.demand_hour
    """
    conn = psycopg2.connect(DB_CONN)
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['precipitation_mm'] = pd.to_numeric(df['precipitation_mm'], errors='coerce').fillna(0.0)
    df['temp_c'] = pd.to_numeric(df['temp_c'], errors='coerce').fillna(20.0)
    df['is_saturday'] = pd.to_numeric(df['is_saturday'], errors='coerce').fillna(0).astype(int)
    df['is_holiday'] = pd.to_numeric(df['is_holiday'], errors='coerce').fillna(0).astype(int)
    df['is_festival'] = pd.to_numeric(df['is_festival'], errors='coerce').fillna(0).astype(int)
    
    print(f"Loaded {len(df)} records from database.")
    return df

def load_data_from_csv():
    print("Loading demand data from fallback CSV dataset...")
    csv_path = "data/synthetic_transit_demand.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Fallback CSV dataset not found at {csv_path}. Run generate_data.py first.")
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    print(f"Loaded {len(df)} records from CSV.")
    return df

def prepare_features(df):
    print("Executing Nepal-specific feature engineering (Temporal, Lags, Monsoon, Festival)...")
    df = df.sort_values(['stop_id', 'timestamp']).copy()
    
    # 1. Temporal & Calendar Encodings
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    df['month'] = df['timestamp'].dt.month
    df['is_peak'] = df['hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)
    if 'is_saturday' not in df.columns:
        df['is_saturday'] = (df['dayofweek'] == 5).astype(int)
    if 'is_holiday' not in df.columns:
        df['is_holiday'] = df['is_saturday']
    if 'is_festival' not in df.columns:
        df['is_festival'] = 0
        
    # 2. Environmental & Monsoon Indicators
    if 'temp_c' not in df.columns and 'temperature_c' in df.columns:
        df['temp_c'] = df['temperature_c']
    if 'precipitation_mm' not in df.columns:
        df['precipitation_mm'] = 0.0
    df['is_heavy_monsoon'] = (df['precipitation_mm'] > 2.0).astype(int)
    
    # 3. Time-Series Lag Features per Stop
    df['demand_lag_1h'] = df.groupby('stop_id')['demand'].shift(1)
    df['demand_lag_24h'] = df.groupby('stop_id')['demand'].shift(24)
    df['demand_lag_168h'] = df.groupby('stop_id')['demand'].shift(168) # 1-week lag
    
    # 4. Rolling Averages
    df['rolling_3h_mean'] = df.groupby('stop_id')['demand_lag_1h'].transform(lambda x: x.rolling(3).mean())
    df['rolling_24h_mean'] = df.groupby('stop_id')['demand_lag_1h'].transform(lambda x: x.rolling(24).mean())
    
    return df.dropna()

def train_and_evaluate():
    try:
        df_raw = load_data_from_db()
    except Exception as e:
        print(f"PostgreSQL connection bypass ({e}). Using CSV dataset.")
        df_raw = load_data_from_csv()
        
    df_features = prepare_features(df_raw)
    
    feature_cols = [
        'hour', 'dayofweek', 'month', 'is_peak', 'is_saturday', 'is_holiday', 'is_festival',
        'precipitation_mm', 'temp_c', 'is_heavy_monsoon',
        'demand_lag_1h', 'demand_lag_24h', 'demand_lag_168h',
        'rolling_3h_mean', 'rolling_24h_mean'
    ]
    target_col = 'demand'
    
    X = df_features[feature_cols]
    y = df_features[target_col]
    
    # Chronological Train/Test Split (80% Train, 20% Test)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"Training set size: {len(X_train)} | Test set size: {len(X_test)}")
    
    print("Training XGBoost Regressor model...")
    model = XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    print("Evaluating model performance on test set...")
    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    mae = mean_absolute_error(y_test, preds)
    
    print("\n--- XGBoost Forecast Evaluation Results ---")
    print(f"RMSE: {rmse:.2f} passengers/hour")
    print(f"MAE:  {mae:.2f} passengers/hour\n")
    
    os.makedirs("models", exist_ok=True)
    model_path = "models/xgboost_transit_model.joblib"
    joblib.dump(model, model_path)
    print(f"Trained XGBoost model saved successfully to {model_path}")
    
    joblib.dump(feature_cols, "models/feature_cols.joblib")
    print("Feature column layout saved successfully to models/feature_cols.joblib")
    
    return model, rmse, mae

if __name__ == "__main__":
    train_and_evaluate()
