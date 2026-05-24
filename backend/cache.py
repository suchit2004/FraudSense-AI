import time
from collections import deque
import threading

class VelocityCache:
    def __init__(self):
        self.lock = threading.Lock()
        # Each transaction entry will be: (timestamp, sender_vpa, device_id, amount)
        self.transactions = deque()

    def add_transaction(self, sender_vpa: str, device_id: str, amount: float, timestamp: float = None):
        """Adds a transaction to the sliding window cache and prunes expired records (>15 mins old)."""
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            self.transactions.append({
                'timestamp': timestamp,
                'sender_vpa': sender_vpa,
                'device_id': device_id,
                'amount': amount
            })
            self._prune_old_transactions(timestamp)

    def _prune_old_transactions(self, current_time: float):
        """Removes transactions older than 15 minutes (900 seconds) to maintain memory size."""
        cutoff = current_time - 900
        while self.transactions and self.transactions[0]['timestamp'] < cutoff:
            self.transactions.popleft()

    def get_vpa_velocity(self, sender_vpa: str, window_seconds: float, current_time: float = None) -> tuple[int, float]:
        """
        Returns (count, sum_amount) of transactions from a VPA within the window_seconds.
        """
        if current_time is None:
            current_time = time.time()
        
        cutoff = current_time - window_seconds
        count = 0
        total_amount = 0.0
        
        with self.lock:
            for tx in reversed(self.transactions):
                if tx['timestamp'] < cutoff:
                    break
                if tx['sender_vpa'] == sender_vpa:
                    count += 1
                    total_amount += tx['amount']
                    
        return count, total_amount

    def get_device_velocity(self, device_id: str, window_seconds: float, current_time: float = None) -> tuple[int, float]:
        """
        Returns (count, sum_amount) of transactions from a device_id within the window_seconds.
        """
        if current_time is None:
            current_time = time.time()
        
        cutoff = current_time - window_seconds
        count = 0
        total_amount = 0.0
        
        with self.lock:
            for tx in reversed(self.transactions):
                if tx['timestamp'] < cutoff:
                    break
                if tx['device_id'] == device_id:
                    count += 1
                    total_amount += tx['amount']
                    
        return count, total_amount

    def get_unique_vpas_for_device(self, device_id: str, window_seconds: float, current_time: float = None) -> int:
        """
        Returns count of unique VPAs associated with a device_id within the window_seconds.
        Useful for detecting multi-account device hijacking.
        """
        if current_time is None:
            current_time = time.time()
            
        cutoff = current_time - window_seconds
        vpas = set()
        
        with self.lock:
            for tx in reversed(self.transactions):
                if tx['timestamp'] < cutoff:
                    break
                if tx['device_id'] == device_id:
                    vpas.add(tx['sender_vpa'])
                    
        return len(vpas)

    def clear(self):
        """Clears all transactions in the cache."""
        with self.lock:
            self.transactions.clear()
