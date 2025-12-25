
## 7. ไฟล์สำหรับมือถือเพิ่มเติม (mobile_utils.py)

```python
"""
Mobile utilities for CpyTro
"""

import os
import sys
import json
import time
from typing import Dict, List, Optional
import hashlib

class MobileOptimizer:
    """Optimize mining for mobile devices"""
    
    @staticmethod
    def check_device_capabilities() -> Dict:
        """Check mobile device capabilities"""
        capabilities = {
            "mining_supported": True,
            "recommended_threads": 1,
            "battery_warning": False,
            "thermal_warning": False,
            "memory_warning": False
        }
        
        # Check battery level (simulated)
        try:
            # This would use platform-specific APIs
            # For now, we'll simulate
            battery_level = 80  # Simulated battery level
            if battery_level < 20:
                capabilities["battery_warning"] = True
        except:
            pass
        
        # Check memory
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 90:
                capabilities["memory_warning"] = True
        except:
            pass
        
        # Determine recommended threads
        try:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            capabilities["recommended_threads"] = max(1, cpu_count // 2)
        except:
            capabilities["recommended_threads"] = 1
        
        return capabilities
    
    @staticmethod
    def optimize_for_battery() -> Dict:
        """Optimize settings for battery saving"""
        return {
            "mining_intensity": 0.5,
            "sleep_interval": 0.01,
            "background_priority": False,
            "thermal_limit": 40,  # Celsius
            "auto_pause_below": 15  # Pause mining below 15% battery
        }
    
    @staticmethod
    def generate_mobile_wallet() -> Dict:
        """Generate wallet optimized for mobile"""
        # Generate key pair
        private_key = hashlib.sha256(os.urandom(32)).hexdigest()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        
        # Generate mobile-friendly address (shorter)
        address = "CPT" + public_key[:37]
        
        return {
            "private_key": private_key,
            "public_key": public_key,
            "address": address,
            "type": "mobile",
            "created": int(time.time())
        }
    
    @staticmethod
    def compress_transaction(tx_data: Dict) -> str:
        """Compress transaction for mobile transmission"""
        # Simple compression for mobile data saving
        import zlib
        import base64
        
        tx_json = json.dumps(tx_data).encode()
        compressed = zlib.compress(tx_json)
        return base64.b64encode(compressed).decode()

class MobileNotification:
    """Handle mobile notifications"""
    
    @staticmethod
    def send_mining_notification(title: str, message: str):
        """Send notification to mobile device"""
        # This would integrate with mobile notification APIs
        # For now, just print
        print(f"[Notification] {title}: {message}")
    
    @staticmethod
    def block_mined_notification(block_height: int, reward: float):
        """Notify when block is mined"""
        title = "Block Mined!"
        message = f"Block #{block_height} mined. Reward: {reward} CPT"
        MobileNotification.send_mining_notification(title, message)
    
    @staticmethod
    def transaction_received_notification(amount: float, from_address: str):
        """Notify when transaction is received"""
        title = "CPT Received"
        message = f"Received {amount} CPT from {from_address[:10]}..."
        MobileNotification.send_mining_notification(title, message)

def main():
    """Test mobile utilities"""
    print("Testing Mobile Utilities...")
    
    optimizer = MobileOptimizer()
    
    # Check device capabilities
    caps = optimizer.check_device_capabilities()
    print(f"Device Capabilities: {caps}")
    
    # Generate mobile wallet
    wallet = optimizer.generate_mobile_wallet()
    print(f"Mobile Wallet Address: {wallet['address']}")
    
    # Battery optimization
    battery_settings = optimizer.optimize_for_battery()
    print(f"Battery Settings: {battery_settings}")

if __name__ == "__main__":
    main()
