import subprocess
import sys
import os

def run_cmd(cmd, cwd=None):
    print(f"Executing command: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed with exit code: {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    python_exe = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python"
        
    print("\n=======================================================")
    print(" Smart City: Dynamic Transit Scheduling System (Nepal)")
    print("=======================================================\n")
    
    print("--- STEP 1: Generating Dataset & Initializing Schema ---")
    run_cmd(f"{python_exe} src/generate_data.py")
    
    print("\n--- STEP 2: Training XGBoost Demand Forecasting Model ---")
    run_cmd(f"{python_exe} src/train_model.py")
    
    print("\n--- STEP 3: Testing Schedule Optimization & Hotspots ---")
    run_cmd(f"{python_exe} src/test_optimize.py")
    
    print("\n=======================================================")
    print(" PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
    print("=======================================================")
    print("\nTo launch the interactive control dashboard, run:")
    print("  .venv\\Scripts\\streamlit.exe run app/app.py\n")
