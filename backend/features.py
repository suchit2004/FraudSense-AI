import re
from datetime import datetime
from backend.cache import VelocityCache

# PhonePe's standard UPI handles
PHONEPE_HANDLES = ['@ybl', '@axl', '@ibl']

def is_phonepe_vpa(vpa: str) -> int:
    """Returns 1 if the VPA is a standard PhonePe VPA, 0 otherwise."""
    vpa_lower = vpa.lower()
    for handle in PHONEPE_HANDLES:
        if vpa_lower.endswith(handle):
            return 1
    return 0

def get_vpa_digits_ratio(vpa: str) -> float:
    """
    Returns the ratio of digits to total characters in the VPA prefix (before @).
    Fraudulent synthetic VPAs often have long numerical suffixes.
    """
    prefix = vpa.split('@')[0] if '@' in vpa else vpa
    if not prefix:
        return 0.0
    digits = sum(1 for c in prefix if c.isdigit())
    return digits / len(prefix)

def get_vpa_length(vpa: str) -> int:
    """Returns the total length of the VPA."""
    return len(vpa)

def extract_features(tx: dict, cache: VelocityCache, current_time: float = None) -> dict:
    """
    Extracts features for a transaction.
    Adds the transaction to the velocity cache after feature extraction to avoid self-counting,
    or extracts features, gets velocity metrics, and updates cache.
    Note: To get accurate velocities prior to this transaction, we fetch velocities first,
    then we add the transaction to the cache.
    """
    sender_vpa = tx.get('sender_vpa', '')
    device_id = tx.get('device_id', '')
    amount = float(tx.get('amount', 0.0))
    timestamp = tx.get('timestamp', None)
    
    # Calculate hour features
    if timestamp is not None:
        dt = datetime.fromtimestamp(timestamp)
    else:
        dt = datetime.now()
        timestamp = dt.timestamp()
        
    hour = dt.hour
    is_night = 1 if (hour >= 23 or hour <= 5) else 0
    
    # Extract velocities prior to adding this transaction to the cache
    vpa_cnt_1m, vpa_sum_1m = cache.get_vpa_velocity(sender_vpa, 60, current_time=timestamp)
    vpa_cnt_10m, vpa_sum_10m = cache.get_vpa_velocity(sender_vpa, 600, current_time=timestamp)
    
    dev_cnt_1m, dev_sum_1m = cache.get_device_velocity(device_id, 60, current_time=timestamp)
    dev_cnt_10m, dev_sum_10m = cache.get_device_velocity(device_id, 600, current_time=timestamp)
    
    device_vpa_count = cache.get_unique_vpas_for_device(device_id, 600, current_time=timestamp)
    
    # Build feature dict
    features = {
        'amount': amount,
        'vpa_is_phone_pe': is_phonepe_vpa(sender_vpa),
        'vpa_length': get_vpa_length(sender_vpa),
        'vpa_digits_ratio': get_vpa_digits_ratio(sender_vpa),
        'hour_of_day': hour,
        'is_night': is_night,
        
        # VPA velocity features
        'vpa_velocity_1m': vpa_cnt_1m,
        'vpa_velocity_10m': vpa_cnt_10m,
        'vpa_amount_velocity_1m': vpa_sum_1m,
        'vpa_amount_velocity_10m': vpa_sum_10m,
        
        # Device velocity features
        'device_velocity_1m': dev_cnt_1m,
        'device_velocity_10m': dev_cnt_10m,
        'device_amount_velocity_1m': dev_sum_1m,
        'device_amount_velocity_10m': dev_sum_10m,
        
        # Multiplexing VPA check
        'device_vpa_count_10m': device_vpa_count
    }
    
    # Add to cache for subsequent transactions
    cache.add_transaction(sender_vpa, device_id, amount, timestamp)
    
    return features

# Column names in order for model consumption
FEATURE_COLUMNS = [
    'amount',
    'vpa_is_phone_pe',
    'vpa_length',
    'vpa_digits_ratio',
    'hour_of_day',
    'is_night',
    'vpa_velocity_1m',
    'vpa_velocity_10m',
    'vpa_amount_velocity_1m',
    'vpa_amount_velocity_10m',
    'device_velocity_1m',
    'device_velocity_10m',
    'device_amount_velocity_1m',
    'device_amount_velocity_10m',
    'device_vpa_count_10m'
]
