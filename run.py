import subprocess
import sys
import time
import os
import signal

def run_services():
    backend_cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"]
    frontend_cmd = [sys.executable, "-m", "streamlit", "run", "frontend/app.py"]

    print("[INFO] Starting FraudSense AI Dual Services...")
    print("----------------------------------------")
    
    # Start Backend FastAPI
    print("[BACKEND] Starting FastAPI Analytics Backend on port 8000...")
    backend_proc = subprocess.Popen(
        backend_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Wait for FastAPI to start up
    time.sleep(3)
    
    # Start Frontend Streamlit
    print("[FRONTEND] Starting Streamlit UI Dashboard...")
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Define cleaner for shutting down both services on interrupt
    def kill_processes():
        print("\n[STOP] Shutting down backend and frontend services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        try:
            backend_proc.wait(timeout=3)
            frontend_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            backend_proc.kill()
            frontend_proc.kill()
        print("[OK] Services terminated. Goodbye!")
        sys.exit(0)

    # Listen to signal termination
    def signal_handler(sig, frame):
        kill_processes()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("----------------------------------------")
    print("Backend API is live at http://127.0.0.1:8000")
    print("Streamlit Dashboard is opening in your browser...")
    print("Press Ctrl+C in this terminal to stop both services.")
    print("----------------------------------------\n")

    # Monitor outputs without blocking
    os.set_blocking(backend_proc.stdout.fileno(), False)
    os.set_blocking(frontend_proc.stdout.fileno(), False)

    while True:
        try:
            # Check backend output
            try:
                line = backend_proc.stdout.readline()
                if line:
                    print(f"[Backend] {line.strip()}")
            except IOError:
                pass

            # Check frontend output
            try:
                line = frontend_proc.stdout.readline()
                if line:
                    print(f"[Frontend] {line.strip()}")
            except IOError:
                pass

            # Check if any process exited unexpectedly
            if backend_proc.poll() is not None:
                print("[ERROR] Backend service stopped unexpectedly.")
                kill_processes()
            if frontend_proc.poll() is not None:
                print("[ERROR] Frontend service stopped unexpectedly.")
                kill_processes()
                
            time.sleep(0.1)
        except KeyboardInterrupt:
            kill_processes()

if __name__ == "__main__":
    run_services()
