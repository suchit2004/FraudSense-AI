import sys

def verify():
    print("[INFO] Verifying FraudSense AI Environment Dependencies...")
    print("-----------------------------------------------------")
    
    modules = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("streamlit", "Streamlit"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("sklearn", "Scikit-Learn"),
        ("shap", "SHAP"),
        ("networkx", "NetworkX"),
        ("scipy", "SciPy"),
        ("faker", "Faker"),
        ("plotly", "Plotly"),
        ("requests", "Requests")
    ]
    
    success = True
    for mod_name, label in modules:
        try:
            if mod_name == "sklearn":
                import sklearn
                version = sklearn.__version__
            elif mod_name == "shap":
                import shap
                version = shap.__version__
            else:
                mod = __import__(mod_name)
                version = getattr(mod, "__version__", "installed")
            print(f"[OK] {label:<15} : {version}")
        except ImportError as e:
            print(f"[ERROR] {label:<15} : NOT INSTALLED ({e})")
            success = False
            
    print("-----------------------------------------------------")
    if success:
        print("[SUCCESS] Environment is fully configured and ready to run!")
        sys.exit(0)
    else:
        print("[WARNING] Some dependencies are missing. Run: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    verify()
