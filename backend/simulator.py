import time
import random
from faker import Faker

fake = Faker()

class TransactionSimulator:
    def __init__(self):
        self.active_attack = None  # None, "velocity_surge", "mule_ring", "device_spoofing"
        self.delay = 1.0           # Seconds between normal transactions
        self.is_running = False
        
        # Predefined nodes for stable simulation
        self.normal_vpas = [f"{fake.user_name()}{random.randint(10,99)}@ybl" for _ in range(30)]
        self.normal_vpas += [f"{fake.user_name()}{random.randint(10,99)}@axl" for _ in range(15)]
        self.normal_vpas += [f"{fake.user_name()}@ibl" for _ in range(10)]
        # Other bank handles
        self.normal_vpas += [f"{fake.user_name()}@okaxis" for _ in range(10)]
        self.normal_vpas += [f"{fake.user_name()}@paytm" for _ in range(5)]
        
        self.merchants = [
            "amzn_pay@upi", "flipkart@pos", "swiggy@upi", "zomato@pay", 
            "reliance_retail@okaxis", "netflix@auto", "uber_ride@ybl"
        ]
        
        # Predefined device IDs
        self.device_pool = [f"dev_{random.randint(100000, 999999)}" for _ in range(40)]
        
        # Mapping of VPA to stable Device ID (normal users usually use 1 device)
        self.vpa_to_device = {vpa: random.choice(self.device_pool) for vpa in self.normal_vpas}
        
        # State counters for attacks
        self.attack_step = 0
        self.surge_vpa = "mishra_sharmila89@ybl"
        self.surge_device = "dev_991204"
        
        self.spoof_vpa = "kapoor_arun99@ybl"
        
        # Mule ring accounts (circular chain: mule_A -> mule_B -> mule_C -> mule_D -> mule_A)
        self.mule_ring_vpas = [
            "mule_alok@ybl",
            "mule_bhupesh@okaxis",
            "mule_chitra@paytm",
            "mule_deepak@axl"
        ]
        self.mule_ring_devices = {vpa: f"dev_mule_{i}" for i, vpa in enumerate(self.mule_ring_vpas)}

    def inject_attack(self, attack_name: str):
        """Sets the active attack mode."""
        if attack_name in [None, "velocity_surge", "mule_ring", "device_spoofing"]:
            self.active_attack = attack_name
            self.attack_step = 0
            return True
        return False

    def generate_transaction(self) -> dict:
        """
        Generates a transaction dictionary.
        Integrates normal user distributions or attack simulation based on active_attack.
        """
        timestamp = time.time()
        tx_id = f"TXN{random.randint(10000000, 99999999)}"
        
        # --- ATTACK MODE 1: VELOCITY SURGE ---
        if self.active_attack == "velocity_surge":
            # Injects rapid high-frequency, high-value transactions from one VPA
            sender = self.surge_vpa
            device = self.surge_device
            receiver = random.choice(self.merchants)
            
            # Escalate amount over steps
            amount = float(500 + self.attack_step * 2500)
            self.attack_step += 1
            
            # Switch off attack after 8 transactions
            if self.attack_step >= 8:
                self.active_attack = None
                
            return {
                'txn_id': tx_id,
                'sender_vpa': sender,
                'receiver_vpa': receiver,
                'device_id': device,
                'amount': amount,
                'timestamp': timestamp,
                'attack_injected': "Velocity Surge"
            }
            
        # --- ATTACK MODE 2: MULE RING (LAUNDERING LOOP) ---
        elif self.active_attack == "mule_ring":
            # Circular transfer: mule_0 -> mule_1 -> mule_2 -> mule_3 -> mule_0
            idx = self.attack_step % len(self.mule_ring_vpas)
            next_idx = (self.attack_step + 1) % len(self.mule_ring_vpas)
            
            sender = self.mule_ring_vpas[idx]
            receiver = self.mule_ring_vpas[next_idx]
            device = self.mule_ring_devices[sender]
            
            # Large circular amounts
            amount = 15000.0 + random.uniform(-100, 100)
            self.attack_step += 1
            
            # Run for 2 full cycles (8 transactions)
            if self.attack_step >= 8:
                self.active_attack = None
                
            return {
                'txn_id': tx_id,
                'sender_vpa': sender,
                'receiver_vpa': receiver,
                'device_id': device,
                'amount': amount,
                'timestamp': timestamp,
                'attack_injected': "Mule Ring"
            }
            
        # --- ATTACK MODE 3: DEVICE SPOOFING ---
        elif self.active_attack == "device_spoofing":
            # Single VPA transacting from different device IDs in rapid succession
            sender = self.spoof_vpa
            receiver = random.choice(self.merchants)
            
            # Every transaction has a brand-new device ID
            device = f"dev_spoofed_{random.randint(100000, 999999)}"
            amount = float(random.randint(1000, 6000))
            self.attack_step += 1
            
            # End after 6 spoofed transactions
            if self.attack_step >= 6:
                self.active_attack = None
                
            return {
                'txn_id': tx_id,
                'sender_vpa': sender,
                'receiver_vpa': receiver,
                'device_id': device,
                'amount': amount,
                'timestamp': timestamp,
                'attack_injected': "Device Spoofing"
            }
            
        # --- NORMAL OPERATION MODE ---
        else:
            # Generate normal transactions (97% healthy, 3% random anomalies)
            is_anomaly = random.random() < 0.03
            
            if is_anomaly:
                # Random anomaly generation (e.g. extremely high amount, weird late-night VPA)
                sender = f"suspicious_user_{random.randint(1000, 9999)}@quickpay"
                receiver = random.choice(self.merchants)
                device = f"dev_susp_{random.randint(10,99)}"
                amount = float(random.choice([15000, 25000, 48000]))
                
                # Make timestamp late-night
                # We subtract or add time offset to force night hours in extraction
                # Or we can just let current time dictate, but we can simulate late night hour by forcing dt
                # Let's keep it simple: high amount and weird handle are anomalies
                return {
                    'txn_id': tx_id,
                    'sender_vpa': sender,
                    'receiver_vpa': receiver,
                    'device_id': device,
                    'amount': amount,
                    'timestamp': timestamp,
                    'attack_injected': None
                }
            else:
                # Standard healthy transaction
                sender = random.choice(self.normal_vpas)
                receiver = random.choice(self.merchants + self.normal_vpas)
                # Ensure sender != receiver
                while sender == receiver:
                    receiver = random.choice(self.merchants + self.normal_vpas)
                    
                device = self.vpa_to_device[sender]
                # Normal amount: log-normal or exponential to keep values realistic (average ~300 rupees)
                amount = float(round(random.expovariate(1/250) + 10, 2))
                
                return {
                    'txn_id': tx_id,
                    'sender_vpa': sender,
                    'receiver_vpa': receiver,
                    'device_id': device,
                    'amount': amount,
                    'timestamp': timestamp,
                    'attack_injected': None
                }
