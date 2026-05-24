import pandas as pd
from backend.model import FraudModel
from backend.features import FEATURE_COLUMNS

def test_model_training_and_inference():
    # Model auto-bootstraps on instantiation
    fm = FraudModel()
    assert fm.model is not None
    assert fm.explainer is not None
    
    # Generate an anomalous feature vector (high velocity, high amount, night-time)
    anomaly_tx = {
        'amount': 25000.0,
        'vpa_is_phone_pe': 0,
        'vpa_length': 20,
        'vpa_digits_ratio': 0.6,
        'hour_of_day': 3,
        'is_night': 1,
        'vpa_velocity_1m': 12.0,
        'vpa_velocity_10m': 25.0,
        'vpa_amount_velocity_1m': 150000.0,
        'vpa_amount_velocity_10m': 300000.0,
        'device_velocity_1m': 12.0,
        'device_velocity_10m': 25.0,
        'device_amount_velocity_1m': 150000.0,
        'device_amount_velocity_10m': 300000.0,
        'device_vpa_count_10m': 6.0
    }
    
    # Predict risk
    risk_score, risk_label = fm.predict_risk(anomaly_tx)
    assert 0.0 <= risk_score <= 100.0
    assert risk_label in ["Medium", "High"]  # Should be flagged as anomalous
    
    # Explain transaction
    explanation = fm.explain_transaction(anomaly_tx)
    assert 'explanation_summary' in explanation
    assert len(explanation['features']) == len(FEATURE_COLUMNS)
    assert len(explanation['top_contributors']) > 0
    
    # Confirm it generates a narrative
    assert explanation['explanation_summary'].startswith("Flagged due to:")

if __name__ == "__main__":
    test_model_training_and_inference()
    print("✅ All Model tests passed!")
