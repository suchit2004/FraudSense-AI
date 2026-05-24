import time
import threading
import numpy as np
from collections import deque
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.cache import VelocityCache
from backend.features import extract_features
from backend.model import FraudModel
from backend.graph_engine import GraphEngine
from backend.drift_monitor import DriftMonitor
from backend.simulator import TransactionSimulator

app = FastAPI(title="FraudSense AI Backend", version="1.0.0")

# Enable CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Engines State
cache = VelocityCache()
model = FraudModel()
graph_engine = GraphEngine()
drift_monitor = DriftMonitor(baseline_data=model.get_baseline_distributions())
simulator = TransactionSimulator()

# Thread-safe storage for processed transactions (max 300)
processed_txns = deque(maxlen=300)
txns_lock = threading.Lock()

# Metrics counter
stats = {
    'total_processed': 0,
    'flagged_low': 0,
    'flagged_medium': 0,
    'flagged_high': 0,
    'start_time': time.time(),
    'latency_history': deque(maxlen=100) # track p95 latency
}
stats_lock = threading.Lock()

# Background Thread Control
sim_thread = None
sim_lock = threading.Lock()

class TransactionRequest(BaseModel):
    txn_id: str
    sender_vpa: str
    receiver_vpa: str
    device_id: str
    amount: float
    timestamp: Optional[float] = None
    attack_injected: Optional[str] = None

class AttackRequest(BaseModel):
    attack_name: Optional[str] = None  # "velocity_surge", "mule_ring", "device_spoofing", None

class RetrainRequest(BaseModel):
    use_live_data: bool = True

def process_transaction_internal(tx: Dict[str, Any]) -> Dict[str, Any]:
    """Processes a transaction dictionary through the features, model, graph, and MLOps monitor."""
    start_time = time.perf_counter()
    
    timestamp = tx.get('timestamp') or time.time()
    tx['timestamp'] = timestamp
    
    # 1. Feature Engineering (reads from cache and updates it)
    features = extract_features(tx, cache, current_time=timestamp)
    
    # 2. Graph Engine update & checks
    graph_engine.add_transaction(
        sender=tx['sender_vpa'],
        receiver=tx['receiver_vpa'],
        amount=tx['amount'],
        timestamp=timestamp
    )
    
    # Check if sender or receiver is part of a circular laundering loop
    in_cycle = graph_engine.is_in_cycle(tx['sender_vpa']) or graph_engine.is_in_cycle(tx['receiver_vpa'])
    
    # 3. Model Prediction
    risk_score, risk_label = model.predict_risk(features)
    
    # Graph-Model Synergy: Escalation
    # If the graph engine detects that this transaction is part of an active laundering cycle,
    # we override/escalate the risk label to High and set the score to a critical level (95+).
    if in_cycle:
        risk_score = max(risk_score, 98.0)
        risk_label = "High"
        
    # 4. Explainability Layer
    explanation = {}
    if risk_label in ["Medium", "High"]:
        explanation = model.explain_transaction(features)
        if in_cycle:
            # Append graph finding to explainability summary
            explanation['explanation_summary'] = (
                "CRITICAL: " + explanation.get('explanation_summary', '') + 
                " [GRAPH ENGINE ALERT]: Sender/Receiver VPA is active in a circular money laundering loop."
            )
            
    # 5. MLOps Drift Monitor Update
    drift_monitor.add_transaction_features(features)
    
    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000
    
    result = {
        'txn_id': tx['txn_id'],
        'sender_vpa': tx['sender_vpa'],
        'receiver_vpa': tx['receiver_vpa'],
        'device_id': tx['device_id'],
        'amount': tx['amount'],
        'timestamp': timestamp,
        'attack_injected': tx.get('attack_injected'),
        'risk_score': risk_score,
        'risk_label': risk_label,
        'in_cycle': in_cycle,
        'features': features,
        'explanation': explanation,
        'latency_ms': latency_ms
    }
    
    # Update global lists and stats
    with txns_lock:
        processed_txns.append(result)
        
    with stats_lock:
        stats['total_processed'] += 1
        if risk_label == "Low":
            stats['flagged_low'] += 1
        elif risk_label == "Medium":
            stats['flagged_medium'] += 1
        else:
            stats['flagged_high'] += 1
        stats['latency_history'].append(latency_ms)
        
    return result

def simulator_worker():
    """Background task generating transactions continuously."""
    while simulator.is_running:
        try:
            tx = simulator.generate_transaction()
            process_transaction_internal(tx)
        except Exception as e:
            print(f"Simulation error: {e}")
        time.sleep(simulator.delay)

# --- FastAPI Router Endpoints ---

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "FraudSense AI Analytics Engine",
        "timestamp": time.time()
    }

@app.post("/api/transaction")
def process_transaction(txn: TransactionRequest):
    """Processes an ad-hoc transaction."""
    try:
        tx_dict = txn.model_dump()
        result = process_transaction_internal(tx_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulator/start")
def start_simulator(delay: float = Query(1.0, description="Delay between transactions in seconds")):
    """Starts the background transaction simulator."""
    global sim_thread
    with sim_lock:
        if simulator.is_running:
            # Just update delay if already running
            simulator.delay = delay
            return {"status": "running", "message": f"Simulator delay updated to {delay}s"}
            
        simulator.is_running = True
        simulator.delay = delay
        sim_thread = threading.Thread(target=simulator_worker, daemon=True)
        sim_thread.start()
        
    return {"status": "started", "message": f"Simulator started with delay {delay}s"}

@app.post("/api/simulator/stop")
def stop_simulator():
    """Stops the transaction simulator."""
    with sim_lock:
        simulator.is_running = False
    return {"status": "stopped", "message": "Simulator stopped"}

@app.get("/api/simulator/status")
def get_simulator_status():
    return {
        "is_running": simulator.is_running,
        "delay": simulator.delay,
        "active_attack": simulator.active_attack
    }

@app.post("/api/simulator/inject")
def inject_attack(req: AttackRequest):
    """Injects an attack vector into the simulation stream."""
    success = simulator.inject_attack(req.attack_name)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid attack name. Choose 'velocity_surge', 'mule_ring', 'device_spoofing', or None.")
    return {"status": "injected", "attack_name": req.attack_name}

@app.get("/api/transactions/recent")
def get_recent_transactions(limit: int = 50):
    """Retrieves recent transactions processed by the simulator."""
    with txns_lock:
        tx_list = list(processed_txns)
    # Return latest first
    tx_list.reverse()
    return tx_list[:limit]

@app.get("/api/metrics")
def get_metrics():
    """Fetches real-time system MLOps health and fraud statistics."""
    with stats_lock:
        tot = stats['total_processed']
        med = stats['flagged_medium']
        high = stats['flagged_high']
        latency_list = list(stats['latency_history'])
        
    # Calculate fraud rate
    fraud_rate = (med + high) / tot * 100 if tot > 0 else 0.0
    
    # Calculate p95 latency
    p95_latency = np.percentile(latency_list, 95) if latency_list else 0.0
    
    # Check concept drift
    drift_status = drift_monitor.check_drift()
    
    # Get active cycles (mule rings)
    active_cycles = graph_engine.detect_cycles()
    
    # Get top mule accounts
    top_mules = graph_engine.detect_mule_nodes(top_n=5)
    
    # Calculate running TPS (Transactions per second) over the lifetime
    uptime = time.time() - stats['start_time']
    tps = tot / uptime if uptime > 0 else 0.0
    
    return {
        'total_processed': tot,
        'fraud_rate_pct': float(round(fraud_rate, 2)),
        'p95_latency_ms': float(round(p95_latency, 2)),
        'running_tps': float(round(tps, 2)),
        'distribution': {
            'low': stats['flagged_low'],
            'medium': med,
            'high': high
        },
        'drift_monitor': drift_status,
        'active_cycles_count': len(active_cycles),
        'active_cycles': active_cycles,
        'suspected_mules': top_mules
    }

@app.get("/api/graph")
def get_full_graph():
    """Returns the complete network nodes and edges."""
    return graph_engine.get_full_graph_data()

@app.get("/api/graph/neighborhood/{vpa}")
def get_node_neighborhood(vpa: str, depth: int = 1):
    """Returns local transactions around a target VPA."""
    return graph_engine.get_neighborhood(vpa, depth=depth)

@app.post("/api/model/retrain")
def retrain_model(req: RetrainRequest):
    """
    MLOps trigger: Retrains the Isolation Forest model.
    By default, it compiles the last 200 normal-labeled transactions from the cache
    and mixes it with baseline to adapt to new user patterns.
    """
    try:
        # Collect recent normal transactions to update model
        recent_txns = []
        with txns_lock:
            for tx in processed_txns:
                # We only retrain on transactions that are labeled Low Risk (healthy)
                if tx['risk_label'] == "Low":
                    recent_txns.append(tx['features'])
                    
        if len(recent_txns) < 50:
            # Generate a new clean baseline to simulate model tuning
            # (Ensures retraining works even if not enough transactions have occurred)
            new_baseline = model._generate_healthy_baseline(1000)
        else:
            # Mix recent normal data with 80% baseline
            recent_df = pd.DataFrame(recent_txns)
            old_baseline = model._generate_healthy_baseline(800)
            new_baseline = pd.concat([old_baseline, recent_df], ignore_index=True)
            
        # Fit new model
        model.train(new_baseline)
        
        # Reset MLOps baseline in drift monitor
        drift_monitor.set_baseline(model.get_baseline_distributions())
        
        return {
            "status": "success", 
            "message": f"Isolation Forest retrained successfully. New baseline set with {len(new_baseline)} samples."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
def reset_all():
    """Resets all metrics, caches, graphs, and simulation logs."""
    global cache, graph_engine, drift_monitor, processed_txns, stats
    
    with txns_lock:
        processed_txns.clear()
        
    with stats_lock:
        stats = {
            'total_processed': 0,
            'flagged_low': 0,
            'flagged_medium': 0,
            'flagged_high': 0,
            'start_time': time.time(),
            'latency_history': deque(maxlen=100)
        }
        
    cache.clear()
    graph_engine.clear()
    
    # Reload model baseline
    drift_monitor.set_baseline(model.get_baseline_distributions())
    
    return {"status": "reset", "message": "All database and monitoring systems cleared."}
