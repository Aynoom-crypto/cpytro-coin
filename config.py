import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Binance API Keys
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
    
    # Trading Settings
    TARGET_PROFIT_PERCENT = 6.0  # 6% take profit
    USE_ALL_BALANCE = True      # ใช้เงินทั้งหมดเมื่อเข้าเงื่อนไข
    MIN_BALANCE_USDT = 11       # ยอดขั้นต่ำในการเทรด
    
    # Timeframes to analyze
    TIMEFRAMES = ['5m', '15m', '30m', '1h', '4h', '1d']
    
    # Indicator Settings
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    BB_PERIOD = 20
    BB_STD = 2
    
    # Risk Management
    MAX_OPEN_POSITIONS = 10
    BLACKLIST = []  # รายการเหรียญที่ไม่ต้องการเทรด
    
    # Bot Settings
    CHECK_INTERVAL_MINUTES = 5
    LOG_LEVEL = 'INFO'
    
    @classmethod
    def validate(cls):
        if not cls.BINANCE_API_KEY or not cls.BINANCE_API_SECRET:
            raise ValueError("Binance API keys must be set in .env file")
