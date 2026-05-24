import time
from backend.cache import VelocityCache

def test_cache_velocity_aggregation():
    cache = VelocityCache()
    now = time.time()
    
    # Add transactions
    cache.add_transaction("user1@ybl", "dev_1", 100.0, timestamp=now - 10)
    cache.add_transaction("user1@ybl", "dev_1", 200.0, timestamp=now - 5)
    cache.add_transaction("user1@ybl", "dev_2", 150.0, timestamp=now - 2)
    # Outside window (older than 60s)
    cache.add_transaction("user1@ybl", "dev_1", 500.0, timestamp=now - 80)
    
    # Check 1m velocity
    count, total = cache.get_vpa_velocity("user1@ybl", 60, current_time=now)
    assert count == 3
    assert total == 450.0
    
    # Check 10m velocity (should include the 80s old transaction)
    count_10m, total_10m = cache.get_vpa_velocity("user1@ybl", 600, current_time=now)
    assert count_10m == 4
    assert total_10m == 950.0

def test_cache_unique_vpas_on_device():
    cache = VelocityCache()
    now = time.time()
    
    # Add transactions using same device with different VPAs
    cache.add_transaction("user1@ybl", "dev_1", 50.0, timestamp=now - 5)
    cache.add_transaction("user2@axl", "dev_1", 120.0, timestamp=now - 4)
    cache.add_transaction("user3@ibl", "dev_1", 80.0, timestamp=now - 2)
    # Different device
    cache.add_transaction("user4@ybl", "dev_2", 300.0, timestamp=now - 1)
    
    unique_vpas = cache.get_unique_vpas_for_device("dev_1", 60, current_time=now)
    assert unique_vpas == 3

if __name__ == "__main__":
    test_cache_velocity_aggregation()
    test_cache_unique_vpas_on_device()
    print("✅ All VelocityCache tests passed!")
