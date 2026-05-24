import subprocess
import sys

def run_tests():
    print("🧪 Running FraudSense AI Test Suite...")
    print("--------------------------------------")
    
    tests = [
        ["tests/test_cache.py"],
        ["tests/test_features.py"],
        ["tests/test_graph.py"],
        ["tests/test_model.py"]
    ]
    
    all_passed = True
    
    for cmd in tests:
        # Run test script with current python interpreter
        full_cmd = [sys.executable] + cmd
        print(f"▶️ Running {' '.join(cmd)}...")
        res = subprocess.run(full_cmd)
        if res.returncode != 0:
            print(f"❌ Test failed: {' '.join(cmd)}")
            all_passed = False
        else:
            print(f"✅ Passed!\n")
            
    print("--------------------------------------")
    if all_passed:
        print("🎉 ALL UNIT TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("❌ SOME UNIT TESTS FAILED. CHECK LOGS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
