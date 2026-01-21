import time
import schedule
from datetime import datetime
from config import Config
from trading.binance_client import BinanceClient
from trading.order_manager import OrderManager
from indicators.multi_timeframe import MultiTimeframeAnalyzer
from indicators.signal_generator import SignalGenerator
from utils.logger import ColoredLogger

class CryptroBot:
    def __init__(self):
        # Validate config
        Config.validate()
        
        # Initialize components
        self.config = Config()
        self.logger = ColoredLogger("CryptroBot")
        self.client = BinanceClient(
            self.config.BINANCE_API_KEY,
            self.config.BINANCE_API_SECRET
        )
        self.order_manager = OrderManager(self.client, self.config)
        self.analyzer = MultiTimeframeAnalyzer(self.config)
        self.signal_gen = SignalGenerator(self.config)
        
        # State
        self.blacklist = set(self.config.BLACKLIST)
        self.processed_symbols = set()
        
    def scan_market(self):
        """สแกนตลาดหาสัญญาณเทรด"""
        self.logger.info("Starting market scan...")
        
        try:
            # ดึงรายการเหรียญทั้งหมด
            symbols = self.client.get_all_trading_pairs('USDT')
            self.logger.info(f"Found {len(symbols)} trading pairs")
            
            # ตรวจสอบ positions ที่เปิดอยู่
            self.order_manager.check_open_positions()
            
            # จำกัดจำนวนเหรียญที่สแกนเพื่อป้องกัน rate limit
            symbols_to_scan = [s for s in symbols if s not in self.blacklist][:50]
            
            for symbol in symbols_to_scan:
                try:
                    # ตรวจสอบว่าไม่เกินจำนวน positions สูงสุด
                    if len(self.order_manager.open_positions) >= self.config.MAX_OPEN_POSITIONS:
                        self.logger.warning("Maximum open positions reached")
                        break
                    
                    # ข้ามเหรียญที่อยู่ใน blacklist
                    if symbol in self.blacklist:
                        continue
                    
                    # วิเคราะห์ทุก timeframe
                    timeframe_signals = self.analyzer.analyze_all_timeframes(symbol, self.client)
                    
                    if not timeframe_signals:
                        continue
                    
                    # สร้างสัญญาณเทรด
                    signal = self.signal_gen.generate_signal(symbol, timeframe_signals)
                    
                    if signal:
                        self.logger.signal(f"BUY SIGNAL: {symbol}")
                        self.logger.info(f"Price: {signal['price']:.8f}")
                        self.logger.info(f"TP: {signal['take_profit']:.8f} (+{self.config.TARGET_PROFIT_PERCENT}%)")
                        self.logger.info(f"Score: {signal['score']}/100")
                        self.logger.info(f"Conditions: {', '.join(signal['conditions'])}")
                        
                        # ดำเนินการซื้อ
                        success = self.order_manager.execute_buy(signal)
                        
                        if success:
                            self.blacklist.add(symbol)  # หลีกเลี่ยงการซื้อซ้ำในรอบถัดไป
                            time.sleep(1)  # รอเพื่อป้องกัน rate limit
                            
                except Exception as e:
                    self.logger.error(f"Error processing {symbol}: {e}")
                    continue
                    
                time.sleep(0.5)  # รอระหว่างการสแกนแต่ละเหรียญ
                
        except Exception as e:
            self.logger.error(f"Error in market scan: {e}")
            
        self.logger.info(f"Scan completed. Open positions: {len(self.order_manager.open_positions)}")
    
    def show_status(self):
        """แสดงสถานะปัจจุบัน"""
        self.logger.info("=" * 50)
        self.logger.info(f"CRYPTRO BOT STATUS - {datetime.now()}")
        self.logger.info("=" * 50)
        
        # แสดงยอดเงิน
        balances = self.client.get_account_balance()
        usdt_balance = balances.get('USDT', {}).get('free', 0)
        self.logger.info(f"USDT Balance: {usdt_balance:.2f}")
        
        # แสดง positions ที่เปิดอยู่
        positions = self.order_manager.open_positions
        if positions:
            self.logger.info(f"Open Positions: {len(positions)}")
            for symbol, pos in positions.items():
                profit_pct = ((pos['take_profit_price'] - pos['buy_price']) / pos['buy_price']) * 100
                self.logger.info(f"  {symbol}: {pos['quantity']:.4f} @ {pos['buy_price']:.8f} | TP: {pos['take_profit_price']:.8f} (+{profit_pct:.1f}%)")
        else:
            self.logger.info("No open positions")
        
        self.logger.info("=" * 50)
    
    def run(self):
        """เริ่มการทำงานของบอท"""
        self.logger.signal("CRYPTRO BOT STARTED")
        self.show_status()
        
        # ตั้งเวลาให้สแกนตลาดทุก 5 นาที
        schedule.every(self.config.CHECK_INTERVAL_MINUTES).minutes.do(self.scan_market)
        
        # แสดงสถานะทุกชั่วโมง
        schedule.every(1).hours.do(self.show_status)
        
        # รันครั้งแรกทันที
        self.scan_market()
        
        # Main loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.signal("BOT STOPPED BY USER")
        except Exception as e:
            self.logger.error(f"Bot crashed: {e}")

if __name__ == "__main__":
    bot = CryptroBot()
    bot.run()
