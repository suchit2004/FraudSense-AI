import numpy as np
from scipy.stats import ks_2samp
from collections import deque
import threading

class DriftMonitor:
    def __init__(self, baseline_data: dict = None, window_size: int = 200, p_value_threshold: float = 0.05):
        """
        baseline_data: dict of feature_name -> list of baseline float values
        window_size: size of the rolling window of live transactions to compare against baseline
        p_value_threshold: standard alpha (typically 0.05) below which drift is flagged
        """
        self.lock = threading.Lock()
        self.window_size = window_size
        self.p_value_threshold = p_value_threshold
        
        # Dictionary of feature name -> list of values
        self.baseline = baseline_data if baseline_data is not None else {}
        
        # Dictionary of feature name -> rolling deque of values
        self.live_window = {}
        for feature in self.baseline.keys():
            self.live_window[feature] = deque(maxlen=window_size)
            
        self.drifted_features = {}

    def set_baseline(self, baseline_data: dict):
        """Sets or resets the baseline dataset distributions."""
        with self.lock:
            self.baseline = {k: list(v) for k, v in baseline_data.items()}
            self.live_window = {k: deque(maxlen=self.window_size) for k in self.baseline.keys()}
            self.drifted_features.clear()

    def add_transaction_features(self, features: dict):
        """Appends the features of a new transaction to the rolling live window."""
        with self.lock:
            for feat, val in features.items():
                if feat in self.live_window:
                    self.live_window[feat].append(val)

    def check_drift(self) -> dict:
        """
        Runs Kolmogorov-Smirnov test on all monitored features.
        Returns a dictionary summarizing drift status, p-values, and if a drift is detected.
        """
        with self.lock:
            drift_summary = {
                'drift_detected': False,
                'details': {}
            }
            
            # We need at least 30 samples in the live window to run a reliable KS test
            first_feat = next(iter(self.live_window.keys())) if self.live_window else None
            if not first_feat or len(self.live_window[first_feat]) < 30:
                return {
                    'drift_detected': False,
                    'message': f"Insufficient live data. Need at least 30 samples (current: {len(self.live_window[first_feat]) if first_feat else 0}).",
                    'details': {}
                }
            
            any_drift = False
            for feature in self.baseline.keys():
                baseline_vals = self.baseline[feature]
                live_vals = list(self.live_window[feature])
                
                # Perform KS test
                stat, p_val = ks_2samp(baseline_vals, live_vals)
                
                # If p_val is NaN or 0, check. Convert float values safely.
                if np.isnan(p_val):
                    p_val = 1.0
                
                is_drifted = p_val < self.p_value_threshold
                if is_drifted:
                    any_drift = True
                    self.drifted_features[feature] = p_val
                else:
                    self.drifted_features.pop(feature, None)
                    
                drift_summary['details'][feature] = {
                    'p_value': float(p_val),
                    'statistic': float(stat),
                    'drifted': bool(is_drifted),
                    'baseline_mean': float(np.mean(baseline_vals)),
                    'live_mean': float(np.mean(live_vals))
                }
                
            drift_summary['drift_detected'] = any_drift
            return drift_summary
            
    def get_live_window_size(self) -> int:
        """Returns the number of current samples in the live window."""
        with self.lock:
            if not self.live_window:
                return 0
            first_feat = next(iter(self.live_window.keys()))
            return len(self.live_window[first_feat])
