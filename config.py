"""
Configuration file for CpyTro
"""

# Network Settings
NETWORK_ID = "cpytro_mainnet"
DEFAULT_PORT = 8333
RPC_PORT = 8334
DNS_SEEDS = [
    "seed1.cpytro.net",
    "seed2.cpytro.net",
    "seed3.cpytro.net"
]

# Blockchain Parameters
MAX_SUPPLY = 210_000_000
INITIAL_BLOCK_REWARD = 500
HALVING_INTERVAL = 1_050_000  # blocks
TARGET_BLOCK_TIME = 120  # seconds
DIFFICULTY_ADJUSTMENT_INTERVAL = 2027  # blocks
MAX_BLOCK_SIZE = 1_000_000  # 1 MB

# Mining Settings
MOBILE_MINING_ENABLED = True
MINIMUM_MINING_BALANCE = 0  # สามารถขุดได้ฟรี
ENERGY_SAVING_MODE = True

# Wallet Settings
WALLET_VERSION = "1.0"
ENCRYPTION_ENABLED = True
BACKUP_INTERVAL = 24  # hours

# Mobile Optimization
MOBILE_CONFIG = {
    "battery_saver": True,
    "data_saver": True,
    "background_mining": True,
    "thermal_throttling": True,
    "auto_sync": True,
    "push_notifications": True
}

# Fees
MIN_TRANSACTION_FEE = 0.0001  # CPT
PRIORITY_FEE_MULTIPLIER = 2.0

# Development
TESTNET = False
DEBUG = False
LOG_LEVEL = "INFO"

# Paths
DATA_DIR = "./cpytro_data"
WALLET_DIR = "./wallets"
LOG_FILE = "./cpytro.log"
DATABASE_FILE = "./cpytro_blockchain.db"
