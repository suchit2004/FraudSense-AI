import os
import subprocess
import sys

def run_tests():
    print("[TEST] Running FraudSense AI Test Suite...")
    print("--------------------------------------")
    
    tests = [
        ["tests/test_cache.py"],
        ["tests/test_features.py"],
        ["tests/test_graph.py"],
        ["tests/test_model.py"]
    ]
    
    # Inject project root directory into PYTHONPATH for the subprocesses
    env = os.environ.copy()
    project_root = os.path.abspath(os.path.dirname(__file__))
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    
    all_passed = True
    
    for cmd in tests:
        full_cmd = [sys.executable] + cmd
        print(f"[RUN] Running {' '.join(cmd)}...")
        res = subprocess.run(full_cmd, env=env)
        if res.returncode != 0:
            print(f"[FAIL] Test failed: {' '.join(cmd)}")
            all_passed = False
        else:
            print(f"[PASS] Passed!\n")
            
    print("--------------------------------------")
    if all_passed:
        print("[SUCCESS] ALL UNIT TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("[ERROR] SOME UNIT TESTS FAILED. CHECK LOGS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
