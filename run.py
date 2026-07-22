import subprocess
import sys
import os

def run_cmd(cmd, cwd=None):
    print(f"Running command: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed with exit code: {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    # Find Python executable inside virtual env
    python_exe = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python" # Fallback to system python if venv not found
        
    print("\n--- STEP 1: Initializing Database Schema & Ingesting Data ---")
    run_cmd(f"{python_exe} src/generate_data.py")
    
    print("\n--- STEP 2: Training XGBoost Demand Forecasting Model ---")
    run_cmd(f"{python_exe} src/train_model.py")
    
    print("\n--- PIPELINE EXECUTION COMPLETED ---")
    print("\nTo launch the interactive dashboard, run the following command:")
    print("  .venv\\Scripts\\streamlit.exe run app/app.py")
    print("\nPress Ctrl+C inside the terminal to stop the Streamlit server when finished.\n")
