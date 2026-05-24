import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import shap
import threading
from backend.features import FEATURE_COLUMNS

class FraudModel:
    def __init__(self, contamination: float = 0.05):
        self.lock = threading.Lock()
        self.contamination = contamination
        self.model = None
        self.explainer = None
        self.baseline_df = None
        
        # Initialize and bootstrap with normal synthetic data
        self._bootstrap_model()

    def _generate_healthy_baseline(self, num_samples: int = 1500) -> pd.DataFrame:
        """Generates a dataset representing normal UPI user transactions for training."""
        np.random.seed(42)
        
        # 1. Transaction amounts (mostly small, 10 to 2000 rupees)
        amounts = np.random.exponential(scale=350, size=num_samples) + 10
        
        # 2. VPA domains (85% standard PhonePe, 15% other UPI handles)
        vpa_is_phone_pe = np.random.choice([1, 0], size=num_samples, p=[0.85, 0.15])
        
        # 3. VPA lengths (normally between 10 to 18 chars)
        vpa_lengths = np.random.normal(loc=13, scale=2.5, size=num_samples).astype(int)
        vpa_lengths = np.clip(vpa_lengths, 8, 25)
        
        # 4. VPA digits ratio (low for normal, e.g. 0 to 20%)
        vpa_digits_ratios = np.random.beta(a=1, b=5, size=num_samples) * 0.3
        
        # 5. Hour of day (mostly day hours 8am to 10pm)
        hours = np.random.choice(
            list(range(24)), 
            size=num_samples, 
            p=[0.01]*6 + [0.05]*16 + [0.07]*2  # Very low probability at night
        )
        is_night = np.where((hours >= 23) | (hours <= 5), 1, 0)
        
        # 6. Velocities: VPA transactions in last 1 min (mostly 0 or 1, rarely 2)
        vpa_vel_1m = np.random.choice([0, 1, 2], size=num_samples, p=[0.7, 0.28, 0.02])
        vpa_vel_10m = vpa_vel_1m + np.random.choice([0, 1, 2, 3], size=num_samples, p=[0.6, 0.3, 0.08, 0.02])
        
        # Amount velocities
        vpa_amt_1m = vpa_vel_1m * amounts * np.random.uniform(0.8, 1.0, size=num_samples)
        vpa_amt_10m = vpa_vel_10m * amounts * np.random.uniform(0.8, 1.2, size=num_samples)
        
        # 7. Velocities: Device transactions in last 1 min (mostly 0 or 1)
        dev_vel_1m = vpa_vel_1m.copy()
        dev_vel_10m = vpa_vel_10m.copy()
        dev_amt_1m = vpa_amt_1m.copy()
        dev_amt_10m = vpa_amt_10m.copy()
        
        # 8. Device VPA count in 10 mins (usually 1, rarely 2)
        device_vpas = np.random.choice([1, 2], size=num_samples, p=[0.97, 0.03])
        
        data = {
            'amount': amounts,
            'vpa_is_phone_pe': vpa_is_phone_pe,
            'vpa_length': vpa_lengths,
            'vpa_digits_ratio': vpa_digits_ratios,
            'hour_of_day': hours,
            'is_night': is_night,
            'vpa_velocity_1m': vpa_vel_1m.astype(float),
            'vpa_velocity_10m': vpa_vel_10m.astype(float),
            'vpa_amount_velocity_1m': vpa_amt_1m,
            'vpa_amount_velocity_10m': vpa_amt_10m,
            'device_velocity_1m': dev_vel_1m.astype(float),
            'device_velocity_10m': dev_vel_10m.astype(float),
            'device_amount_velocity_1m': dev_amt_1m,
            'device_amount_velocity_10m': dev_amt_10m,
            'device_vpa_count_10m': device_vpas.astype(float)
        }
        
        return pd.DataFrame(data)[FEATURE_COLUMNS]

    def _bootstrap_model(self):
        """Generates normal baseline data and fits the Isolation Forest model."""
        self.baseline_df = self._generate_healthy_baseline()
        self.train(self.baseline_df)

    def train(self, X_train: pd.DataFrame):
        """Fits the IsolationForest and initializes SHAP TreeExplainer."""
        with self.lock:
            # Fit Isolation Forest
            self.model = IsolationForest(
                n_estimators=100,
                contamination=self.contamination,
                random_state=42,
                n_jobs=-1
            )
            self.model.fit(X_train[FEATURE_COLUMNS])
            
            # Initialize TreeExplainer (supported for IsolationForest in SHAP)
            # TreeExplainer is efficient for tree models
            self.explainer = shap.TreeExplainer(self.model, data=X_train[FEATURE_COLUMNS].sample(100, random_state=42))

    def predict_risk(self, features: dict) -> tuple[float, str]:
        """
        Calculates risk score (0-100) and risk label (Low, Medium, High).
        Normal transactions score low, outliers score high.
        """
        # Convert single feature dict to DataFrame row matching column order
        df_row = pd.DataFrame([features])[FEATURE_COLUMNS]
        
        with self.lock:
            # decision_function outputs: lower values mean more anomalous (ranges ~ -0.5 to 0.5)
            # typically 0.0 is the boundary
            score = self.model.decision_function(df_row)[0]
            
        # Map decision score to 0 - 100 risk score
        # If score is > 0.1 -> Low (0 to 30)
        # If score is 0.0 to 0.1 -> Medium (30 to 70)
        # If score is < 0.0 -> High (70 to 100)
        if score >= 0.1:
            # Map [0.1, 0.4] -> [0, 30]
            risk = 30 * (1.0 - (score - 0.1) / 0.3)
        elif score >= 0.0:
            # Map [0.0, 0.1] -> [30, 70]
            risk = 30 + 40 * (1.0 - score / 0.1)
        else:
            # Map [-0.4, 0.0] -> [70, 100]
            risk = 70 + 30 * (min(0.4, abs(score)) / 0.4)
            
        risk_score = float(max(0.0, min(100.0, risk)))
        
        if risk_score < 35.0:
            label = "Low"
        elif risk_score < 70.0:
            label = "Medium"
        else:
            label = "High"
            
        return risk_score, label

    def explain_transaction(self, features: dict) -> dict:
        """
        Generates SHAP explainability values and a natural language summary.
        """
        df_row = pd.DataFrame([features])[FEATURE_COLUMNS]
        
        with self.lock:
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(df_row)[0]
            
        # For IsolationForest, a negative SHAP value pulls the decision_function down
        # (making it more anomalous, i.e., HIGHER risk).
        # To make it intuitive in the UI:
        # A positive feature contribution to fraud is represented by NEGATIVE SHAP values.
        # We will flip the sign of SHAP values so that positive values indicate INCREASING FRAUD RISK.
        flipped_shap = -shap_values
        
        feature_contributions = []
        for col, val, sh_val in zip(FEATURE_COLUMNS, df_row.iloc[0], flipped_shap):
            feature_contributions.append({
                'feature': col,
                'value': float(val),
                'shap_value': float(sh_val)
            })
            
        # Sort features by contribution to fraud (highest flipped SHAP first)
        sorted_contributions = sorted(feature_contributions, key=lambda x: x['shap_value'], reverse=True)
        
        # Generate Natural Language Explanation
        explanations = []
        for item in sorted_contributions[:3]:
            # Only explain if the feature actually pushed risk upwards
            if item['shap_value'] <= 0.02:
                continue
                
            feat = item['feature']
            val = item['value']
            
            if feat == 'vpa_velocity_1m' and val > 2:
                explanations.append(f"VPA transacted {int(val)} times in the last 60 seconds (high velocity).")
            elif feat == 'vpa_velocity_10m' and val > 5:
                explanations.append(f"VPA transacted {int(val)} times in the last 10 minutes.")
            elif feat == 'device_velocity_1m' and val > 2:
                explanations.append(f"Device transacted {int(val)} times in the last 60 seconds (device velocity spike).")
            elif feat == 'device_vpa_count_10m' and val > 2:
                explanations.append(f"Device has been linked to {int(val)} different UPI handles in the last 10 minutes.")
            elif feat == 'amount' and val > 5000:
                explanations.append(f"Transaction amount of ₹{val:,.2f} is significantly higher than normal profile.")
            elif feat == 'is_night' and val == 1:
                explanations.append("Transaction occurred during high-risk late night hours (11 PM - 5 AM).")
            elif feat == 'vpa_digits_ratio' and val > 0.3:
                explanations.append(f"Sender VPA prefix has a high density of numeric digits ({val:.1%}), matching fake handle profiles.")
            elif feat == 'vpa_is_phone_pe' and val == 0:
                explanations.append("Transaction originated from a non-standard third-party UPI handle.")
                
        if not explanations:
            explanation_summary = "Transaction characteristics match typical, low-risk user behavior profiles."
        else:
            explanation_summary = "Flagged due to: " + " ".join(explanations)
            
        return {
            'features': feature_contributions,
            'explanation_summary': explanation_summary,
            'top_contributors': sorted_contributions[:3]
        }
        
    def get_baseline_distributions(self) -> dict:
        """Returns baseline distributions for numerical features to feed the drift monitor."""
        return {
            'amount': self.baseline_df['amount'].tolist(),
            'vpa_velocity_1m': self.baseline_df['vpa_velocity_1m'].tolist(),
            'device_vpa_count_10m': self.baseline_df['device_vpa_count_10m'].tolist(),
            'device_velocity_1m': self.baseline_df['device_velocity_1m'].tolist()
        }
