import time
from backend.cache import VelocityCache
from backend.features import is_phonepe_vpa, get_vpa_digits_ratio, extract_features, FEATURE_COLUMNS

def test_vpa_validations():
    # PhonePe domains
    assert is_phonepe_vpa("user@ybl") == 1
    assert is_phonepe_vpa("my_account@axl") == 1
    assert is_phonepe_vpa("business@ibl") == 1
    # Other domains
    assert is_phonepe_vpa("user@okaxis") == 0
    assert is_phonepe_vpa("friend@paytm") == 0

def test_vpa_digits_ratio():
    assert get_vpa_digits_ratio("suchit@ybl") == 0.0
    assert get_vpa_digits_ratio("user12345@axl") == 5/9  # 5 digits out of 9 chars
    assert get_vpa_digits_ratio("123@ibl") == 1.0

def test_feature_extraction_shape():
    cache = VelocityCache()
    tx = {
        'txn_id': 'TXN123',
        'sender_vpa': 'suchit123@ybl',
        'receiver_vpa': 'merchant@paytm',
        'device_id': 'dev_test',
        'amount': 250.0,
        'timestamp': time.time()
    }
    
    features = extract_features(tx, cache)
    
    # Check that all required model columns are in the output dictionary
    for col in FEATURE_COLUMNS:
        assert col in features
        assert isinstance(features[col], (int, float))

if __name__ == "__main__":
    test_vpa_validations()
    test_vpa_digits_ratio()
    test_feature_extraction_shape()
    print("✅ All Features extraction tests passed!")
