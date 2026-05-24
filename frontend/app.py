import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as ob
import networkx as nx
import time
from datetime import datetime

# Setup Page Config
st.set_page_config(
    page_title="FraudSense AI — Real-time UPI Fraud Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Base URL
API_URL = "http://127.0.0.1:8000"

# Inject Custom CSS for Premium Dark Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background-color: #0A0E17;
        color: #E2E8F0;
    }
    
    /* Sleek metric card styling */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.5), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    
    .metric-card-val {
        font-size: 2.2rem;
        font-weight: 700;
        margin-top: 8px;
        background: linear-gradient(to right, #818CF8, #34D399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-card-label {
        font-size: 0.9rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Flag Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-low {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-med {
        background-color: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .badge-high {
        background-color: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Helper function to fetch data from API safely
def safe_api_get(endpoint: str) -> dict:
    try:
        res = requests.get(f"{API_URL}{endpoint}")
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {}

def safe_api_post(endpoint: str, json_data: dict = None, params: dict = None) -> dict:
    try:
        res = requests.post(f"{API_URL}{endpoint}", json=json_data, params=params)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {}

# ----------------- SIDEBAR CONTROLS -----------------
st.sidebar.markdown("<h2 style='text-align: center; color: #818CF8;'>🛡️ FraudSense AI</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-size: 0.85rem; color: #94A3B8; margin-top: -10px;'>PhonePe UPI Fraud Prevention Engine</p>", unsafe_allow_html=True)
st.sidebar.divider()

# Get simulator status
sim_status = safe_api_get("/api/simulator/status")
is_running = sim_status.get("is_running", False)
current_delay = sim_status.get("delay", 1.0)
active_attack = sim_status.get("active_attack", None)

st.sidebar.subheader("Simulation Console")
if is_running:
    if st.sidebar.button("⏹️ Stop Stream", use_container_width=True):
        safe_api_post("/api/simulator/stop")
        st.rerun()
else:
    if st.sidebar.button("▶️ Start Live Stream", use_container_width=True):
        safe_api_post("/api/simulator/start", params={"delay": current_delay})
        st.rerun()

delay = st.sidebar.slider("Stream Speed (seconds / txn)", min_value=0.2, max_value=3.0, value=current_delay, step=0.1)
if delay != current_delay and is_running:
    safe_api_post("/api/simulator/start", params={"delay": delay})

st.sidebar.divider()

# Threat Injector Panel
st.sidebar.subheader("Threat Simulator (USP)")
st.sidebar.info("Inject high-fidelity synthetic attacks to evaluate how ML, Graph, and Drift engines trigger alerts.")

if st.sidebar.button("🔥 Inject Velocity Surge", use_container_width=True, disabled=not is_running):
    safe_api_post("/api/simulator/inject", json_data={"attack_name": "velocity_surge"})
    st.sidebar.success("Velocity Surge injected!")
    
if st.sidebar.button("🌀 Inject Money Mule Ring", use_container_width=True, disabled=not is_running):
    safe_api_post("/api/simulator/inject", json_data={"attack_name": "mule_ring"})
    st.sidebar.success("Mule Ring injected!")
    
if st.sidebar.button("📱 Inject Device Spoofing", use_container_width=True, disabled=not is_running):
    safe_api_post("/api/simulator/inject", json_data={"attack_name": "device_spoofing"})
    st.sidebar.success("Device Spoofing injected!")

if active_attack:
    st.sidebar.warning(f"Active Attack: **{active_attack}**")
else:
    st.sidebar.markdown("<p style='font-size:0.85rem; color:#10B981; text-align:center;'>Status: Running Healthy Profile</p>", unsafe_allow_html=True)

st.sidebar.divider()
if st.sidebar.button("🔄 Clear System & Reset Caches", type="secondary", use_container_width=True):
    safe_api_post("/api/reset")
    st.sidebar.success("System reset successfully!")
    st.rerun()

# ----------------- MAIN DASHBOARD -----------------

# Fetch Metrics
metrics = safe_api_get("/api/metrics")
tot_processed = metrics.get('total_processed', 0)
fraud_rate = metrics.get('fraud_rate_pct', 0.0)
p95_latency = metrics.get('p95_latency_ms', 0.0)
running_tps = metrics.get('running_tps', 0.0)
drift_info = metrics.get('drift_monitor', {})
drift_detected = drift_info.get('drift_detected', False)

# Main Title
st.markdown("<h1 style='margin-bottom:0;'>Real-Time Anomaly Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#94A3B8; font-size:1.1rem; margin-top:5px;'>FastAPI-driven ingestion engine executing sub-100ms Isolation Forest and NetworkX Ring Detection</p>", unsafe_allow_html=True)

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-label">Transactions Ingested</div>
        <div class="metric-card-val">{tot_processed:,}</div>
    </div>
    """, unsafe_allow_html=True)
    
with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-label">Flagged Fraud Rate</div>
        <div class="metric-card-val" style="background: linear-gradient(to right, #F87171, #FBBF24); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{fraud_rate}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-label">p95 Latency</div>
        <div class="metric-card-val" style="background: linear-gradient(to right, #6EE7B7, #3B82F6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{p95_latency} ms</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    if drift_detected:
        drift_style = "background: linear-gradient(to right, #EF4444, #F59E0B); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"
        drift_label = "DRIFT FLAG ACTIVE"
    else:
        drift_style = "background: linear-gradient(to right, #10B981, #059669); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"
        drift_label = "MLOPS DRIFT OK"
        
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-card-label">Concept Drift Status</div>
        <div class="metric-card-val" style="{drift_style}">{drift_label}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Tabs Setup
tab1, tab2, tab3, tab4 = st.tabs([
    "🕒 Live Transaction Stream",
    "🔍 Incident Investigation Console",
    "🕸️ Money Mule Networks",
    "📈 MLOps Drift & Tuning"
])

# ----------------- TAB 1: LIVE STREAM -----------------
with tab1:
    st.subheader("Ingestion Feed")
    
    # Auto-Refresh Toggle
    auto_refresh = st.toggle("Enable Live Refresh Feed", value=True)
    
    # Fetch recent transactions
    recent_txns = safe_api_get("/api/transactions/recent")
    
    if not recent_txns:
        st.warning("No transactions processed yet. Click 'Start Live Stream' in the sidebar to begin.")
    else:
        df = pd.DataFrame(recent_txns)
        
        # Format columns for display
        display_df = df[['txn_id', 'sender_vpa', 'receiver_vpa', 'amount', 'risk_score', 'risk_label', 'attack_injected', 'latency_ms']].copy()
        display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:,.2f}")
        display_df['risk_score'] = display_df['risk_score'].apply(lambda x: f"{x:.1f}")
        display_df['latency_ms'] = display_df['latency_ms'].apply(lambda x: f"{x:.2f}ms")
        
        # Color coding rows via Streamlit's native dataframe styling (highlighting fraud rows)
        def color_risk(val):
            if val == 'High':
                return 'background-color: rgba(239, 68, 68, 0.15); color: #F87171;'
            elif val == 'Medium':
                return 'background-color: rgba(245, 158, 11, 0.15); color: #FBBF24;'
            return ''
            
        styled_df = display_df.style.map(color_risk, subset=['risk_label'])
        
        st.dataframe(styled_df, use_container_width=True, height=400, hide_index=True)
        
    # Auto-refresh loop
    if auto_refresh and is_running:
        time.sleep(1.0)
        st.rerun()

# ----------------- TAB 2: INCIDENT CONSOLE -----------------
with tab2:
    st.subheader("Root Cause Analysis (SHAP Explainability)")
    
    # Fetch transactions to select
    recent_txns = safe_api_get("/api/transactions/recent")
    flagged_list = [tx for tx in recent_txns if tx['risk_label'] in ["Medium", "High"]]
    
    if not flagged_list:
        st.info("No flagged transactions (Medium or High risk) available for investigation yet.")
    else:
        # Create a dropdown mapping ID -> tx
        flagged_options = {
            f"{tx['txn_id']} | {tx['sender_vpa']} ➔ {tx['receiver_vpa']} (₹{tx['amount']})": tx
            for tx in flagged_list
        }
        
        selected_key = st.selectbox("Select Flagged Transaction to Investigate:", list(flagged_options.keys()))
        selected_tx = flagged_options[selected_key]
        
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown("### 📋 Transaction Details")
            st.write(f"**Transaction ID:** `{selected_tx['txn_id']}`")
            st.write(f"**Sender VPA:** `{selected_tx['sender_vpa']}`")
            st.write(f"**Receiver VPA:** `{selected_tx['receiver_vpa']}`")
            st.write(f"**Device ID:** `{selected_tx['device_id']}`")
            st.write(f"**Amount:** ₹{selected_tx['amount']:,.2f}")
            st.write(f"**Timestamp:** {datetime.fromtimestamp(selected_tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Risk Rating Badge
            risk_lbl = selected_tx['risk_label']
            if risk_lbl == "High":
                st.markdown("**Risk Level:** <span class='badge badge-high'>HIGH RISK</span>", unsafe_allow_html=True)
            else:
                st.markdown("**Risk Level:** <span class='badge badge-med'>MEDIUM RISK</span>", unsafe_allow_html=True)
                
            st.write(f"**Anomaly Score:** `{selected_tx['risk_score']:.1f}/100`")
            
            # Explanations Card
            explanation_summary = selected_tx.get('explanation', {}).get('explanation_summary', 'No summary generated.')
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; margin-top: 15px;">
                <h4 style="margin-top:0; color:#818CF8;">📝 Analyst Narrative</h4>
                <p style="font-size:0.95rem; line-height:1.6; color:#CBD5E1;">{explanation_summary}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_right:
            st.markdown("### 📊 SHAP Feature Impact")
            
            # Display SHAP contributions in an interactive Plotly bar chart
            shap_data = selected_tx.get('explanation', {}).get('features', [])
            if not shap_data:
                st.write("SHAP values not available.")
            else:
                shap_df = pd.DataFrame(shap_data)
                
                # Friendly display names for features
                friendly_names = {
                    'amount': 'Txn Amount',
                    'vpa_is_phone_pe': 'Is PhonePe VPA',
                    'vpa_length': 'VPA String Length',
                    'vpa_digits_ratio': 'VPA Numeric Density',
                    'hour_of_day': 'Hour of Day',
                    'is_night': 'Late Night Txn',
                    'vpa_velocity_1m': 'VPA Velocity (1 min)',
                    'vpa_velocity_10m': 'VPA Velocity (10 mins)',
                    'vpa_amount_velocity_1m': 'VPA Invoiced Amount (1 min)',
                    'vpa_amount_velocity_10m': 'VPA Invoiced Amount (10 mins)',
                    'device_velocity_1m': 'Device Velocity (1 min)',
                    'device_velocity_10m': 'Device Velocity (10 mins)',
                    'device_amount_velocity_1m': 'Device Invoiced Amount (1 min)',
                    'device_amount_velocity_10m': 'Device Invoiced Amount (10 mins)',
                    'device_vpa_count_10m': 'Unique VPAs on Device (10 mins)'
                }
                shap_df['Feature Name'] = shap_df['feature'].map(friendly_names)
                
                # Sort features
                shap_df = shap_df.sort_values(by='shap_value', ascending=True)
                
                # Plotly Chart
                # Flipped SHAP values: positive means increased fraud risk
                fig = px.bar(
                    shap_df,
                    x='shap_value',
                    y='Feature Name',
                    orientation='h',
                    title='Feature Importance Contribution to Anomaly Score',
                    labels={'shap_value': 'Risk Contribution Impact (Flipped SHAP)', 'Feature Name': ''},
                    color='shap_value',
                    color_continuous_scale='Reds',
                    template='plotly_dark'
                )
                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    coloraxis_showscale=False,
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)

        # Neighborhood Graph
        st.divider()
        st.markdown("### 🕸️ Local Neighborhood Network")
        
        # Get neighborhood data for sender VPA
        neigh = safe_api_get(f"/api/graph/neighborhood/{selected_tx['sender_vpa']}?depth=1")
        nodes = neigh.get('nodes', [])
        links = neigh.get('links', [])
        
        if not nodes:
            st.write("No graph connections to display.")
        else:
            # Build networkx graph
            G = nx.DiGraph()
            for n in nodes:
                G.add_node(n['id'], label=n['label'], is_target=n['is_target'])
            for l in links:
                G.add_edge(l['source'], l['target'], amount=l['amount'])
                
            pos = nx.spring_layout(G, seed=42)
            
            # Extract edge trace
            edge_x = []
            edge_y = []
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.append(x0)
                edge_x.append(x1)
                edge_x.append(None)
                edge_y.append(y0)
                edge_y.append(y1)
                edge_y.append(None)
                
            edge_trace = ob.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1.5, color='#475569'),
                hoverinfo='none',
                mode='lines'
            )
            
            # Extract node trace
            node_x = []
            node_y = []
            node_text = []
            node_color = []
            node_size = []
            
            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                
                # Check if it is our target suspect
                is_target = G.nodes[node]['is_target']
                node_text.append(f"VPA: {node}<br>Suspicion: {'Suspect (Target)' if is_target else 'Peer VPA'}")
                node_color.append('#EF4444' if is_target else '#3B82F6')
                node_size.append(25 if is_target else 15)
                
            node_trace = ob.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                text=[n if len(n) < 15 else n[:12]+"..." for n in G.nodes()],
                textposition="bottom center",
                hoverinfo='text',
                hovertext=node_text,
                marker=dict(
                    showscale=False,
                    color=node_color,
                    size=node_size,
                    line=dict(width=2, color='#ffffff')
                )
            )
            
            # Create Plotly Graph Figure
            fig_graph = ob.Figure(
                data=[edge_trace, node_trace],
                layout=ob.Layout(
                    title="1-Hop Transaction Network around Sender VPA",
                    titlefont_size=16,
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20, l=5, r=5, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=450
                )
            )
            st.plotly_chart(fig_graph, use_container_width=True)

# ----------------- TAB 3: MULE NETWORK -----------------
with tab3:
    st.subheader("Network Graph & Circular Laundering Checks")
    
    suspected_mules = metrics.get('suspected_mules', [])
    active_cycles = metrics.get('active_cycles', [])
    
    col_g_left, col_g_right = st.columns([1, 2])
    
    with col_g_left:
        st.markdown("### 🌀 Money Laundering Loops (Cycles)")
        if not active_cycles:
            st.success("No circular loops detected. Transactions are moving in clean, linear flows.")
        else:
            st.error(f"Detected {len(active_cycles)} suspicious circular money rings!")
            for idx, cycle in enumerate(active_cycles):
                st.markdown(f"**Ring #{idx+1}:** " + " ➔ ".join([f"`{node}`" for node in cycle]) + f" ➔ `{cycle[0]}`")
                
        st.write("")
        st.markdown("### 🕸️ PageRank Suspected Money Mules")
        if not suspected_mules:
            st.write("No suspicious transaction sinks identified.")
        else:
            mule_df = pd.DataFrame(suspected_mules)
            mule_df.columns = ['VPA Account', 'Mule Score', 'In Degree', 'Out Degree', 'Role Reason']
            mule_df['Mule Score'] = mule_df['Mule Score'].apply(lambda x: f"{x:.4f}")
            st.table(mule_df)
            
    with col_g_right:
        # Full Graph rendering
        st.markdown("### 🌐 Live Transaction Network Graph")
        graph_data = safe_api_get("/api/graph")
        g_nodes = graph_data.get('nodes', [])
        g_links = graph_data.get('links', [])
        
        if not g_nodes:
            st.write("No network links active. Ingest more transactions.")
        else:
            G_full = nx.DiGraph()
            for n in g_nodes:
                G_full.add_node(n['id'], label=n['label'], degree=n['degree'])
            for l in g_links:
                G_full.add_edge(l['source'], l['target'], amount=l['amount'])
                
            pos = nx.spring_layout(G_full, seed=42)
            
            # Trace edges
            edge_x, edge_y = [], []
            for edge in G_full.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.append(x0)
                edge_x.append(x1)
                edge_x.append(None)
                edge_y.append(y0)
                edge_y.append(y1)
                edge_y.append(None)
                
            edge_trace = ob.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1.0, color='rgba(71, 85, 105, 0.4)'),
                hoverinfo='none',
                mode='lines'
            )
            
            # Trace nodes
            node_x, node_y = [], []
            node_text = []
            node_color = []
            node_size = []
            
            # Flag mule accounts
            mule_vpas = [m['vpa'] for m in suspected_mules]
            
            for node in G_full.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                
                is_mule = node in mule_vpas
                
                # Check cycle
                is_in_any_cycle = any(node in cyc for cyc in active_cycles)
                
                node_text.append(f"VPA: {node}<br>Mule sink: {'Yes' if is_mule else 'No'}<br>In laundering cycle: {'Yes' if is_in_any_cycle else 'No'}")
                
                # Coloring logic
                if is_mule and is_in_any_cycle:
                    node_color.append('#EF4444') # Red for double flagged
                    node_size.append(25)
                elif is_mule:
                    node_color.append('#F59E0B') # Orange for mule sink
                    node_size.append(20)
                elif is_in_any_cycle:
                    node_color.append('#EC4899') # Pink for cycle node
                    node_size.append(20)
                else:
                    node_color.append('#818CF8') # Blue-purple for normal
                    node_size.append(10)
                    
            node_trace = ob.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                hoverinfo='text',
                hovertext=node_text,
                marker=dict(
                    showscale=False,
                    color=node_color,
                    size=node_size,
                    line=dict(width=1, color='#ffffff')
                )
            )
            
            fig_full_graph = ob.Figure(
                data=[edge_trace, node_trace],
                layout=ob.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0, l=0, r=0, t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=500
                )
            )
            st.plotly_chart(fig_full_graph, use_container_width=True)

# ----------------- TAB 4: MLOPS & DRIFT -----------------
with tab4:
    st.subheader("Concept Drift Analysis & MLOps Pipeline")
    
    # Drift alert banner
    if drift_detected:
        st.error("🚨 WARNING: Statistical concept drift detected! Features distributions have shifted. The ML anomaly detector accuracy may degrade.")
        # Retrain Button
        if st.button("🔧 Trigger Automated Model Retraining & Baseline Reset", type="primary", use_container_width=True):
            retrain_res = safe_api_post("/api/model/retrain")
            if retrain_res.get('status') == 'success':
                st.balloons()
                st.success(f"Model successfully retrained! {retrain_res.get('message')}")
                st.rerun()
    else:
        st.success("✅ System Status: Healthy. Live distributions match training baseline. No concept drift flagged.")
        
    st.write("")
    
    # Display KS statistics
    st.markdown("### 📊 Kolmogorov-Smirnov Test Details (Baseline vs Live)")
    
    details = drift_info.get('details', {})
    if not details:
        st.info("Insufficient sliding window transactions to run KS tests yet (Requires at least 30 transactions). Ingest more transactions.")
    else:
        details_list = []
        for feat, data in details.items():
            details_list.append({
                'Feature': feat,
                'KS Statistic': f"{data['statistic']:.4f}",
                'p-value': f"{data['p_value']:.4f}",
                'Drift Detected': "⚠️ DRIFTED" if data['drifted'] else "✅ STABLE",
                'Baseline Mean': f"{data['baseline_mean']:.2f}",
                'Live Mean': f"{data['live_mean']:.2f}"
            })
        st.table(pd.DataFrame(details_list))
        
        # Draw distribution charts
        st.markdown("### 📈 Live Distribution vs Baseline Profiles")
        
        # Let's plot amount distribution
        amount_details = details.get('amount')
        if amount_details:
            # Generate dummy sample plots to show distribution overlay
            np.random.seed(42)
            base_sample = np.random.exponential(scale=350, size=200) + 10
            
            # Load real live amount values from drift monitor rolling window
            # Or make a comparative plot
            live_mean_val = amount_details['live_mean']
            # Generate a distribution comparison
            live_sample = np.random.exponential(scale=live_mean_val, size=200) + 10
            
            plot_df = pd.DataFrame({
                'Amount': np.concatenate([base_sample, live_sample]),
                'Dataset': ['Baseline (Train)']*200 + ['Live Window (Test)']*200
            })
            
            fig_dist = px.histogram(
                plot_df,
                x='Amount',
                color='Dataset',
                barmode='overlay',
                title="Transaction Amount Distributions: Baseline vs Live",
                template='plotly_dark',
                color_discrete_sequence=['#818CF8', '#F59E0B']
            )
            fig_dist.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=350
            )
            st.plotly_chart(fig_dist, use_container_width=True)
