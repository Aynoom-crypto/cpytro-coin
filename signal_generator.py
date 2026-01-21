class SignalGenerator:
    def __init__(self, config):
        self.config = config
        
    def generate_signal(self, symbol, timeframe_signals):
        """สร้างสัญญาณเทรดจากข้อมูลทุก timeframe"""
        if not timeframe_signals:
            return None
            
        # ตรวจสอบว่ามีข้อมูลครบทุก timeframe ที่ต้องการหรือไม่
        required_tfs = ['5m', '15m', '1h', '4h']
        if not all(tf in timeframe_signals for tf in required_tfs):
            return None
            
        signal_score = 0
        conditions_met = []
        
        # 1. ตรวจสอบ alignment ของ trend จากหลาย timeframe
        bullish_tfs = 0
        bearish_tfs = 0
        
        for tf, data in timeframe_signals.items():
            # Conditions for bullish
            tf_bullish = 0
            tf_bearish = 0
            
            # RSI condition
            if data['rsi'] < 35:
                tf_bullish += 1
            elif data['rsi'] > 65:
                tf_bearish += 1
                
            # MACD condition
            if data['macd_diff'] > 0:
                tf_bullish += 1
            elif data['macd_diff'] < 0:
                tf_bearish += 1
                
            # Bollinger Band position
            if data['bb_position'] < 0.2:  # Near lower band
                tf_bullish += 1
            elif data['bb_position'] > 0.8:  # Near upper band
                tf_bearish += 1
                
            # Volume confirmation
            if data['volume_ratio'] > 1.2:
                if tf_bullish > tf_bearish:
                    tf_bullish += 1
                elif tf_bearish > tf_bullish:
                    tf_bearish += 1
            
            if tf_bullish > tf_bearish:
                bullish_tfs += 1
            elif tf_bearish > tf_bullish:
                bearish_tfs += 1
        
        # 2. Multi-timeframe confirmation
        if bullish_tfs >= 3:  # อย่างน้อย 3 timeframe แสดงแนวโน้มขาขึ้น
            signal_score += 30
            conditions_met.append("multi_tf_bullish_alignment")
            
        # 3. Short-term momentum (5m, 15m)
        short_term_bullish = True
        for tf in ['5m', '15m']:
            if tf in timeframe_signals:
                data = timeframe_signals[tf]
                if data['macd_diff'] <= 0 or data['rsi'] < 45:
                    short_term_bullish = False
                    break
                    
        if short_term_bullish:
            signal_score += 20
            conditions_met.append("short_term_momentum_bullish")
            
        # 4. Medium-term trend (1h, 4h)
        medium_term_bullish = True
        for tf in ['1h', '4h']:
            if tf in timeframe_signals:
                data = timeframe_signals[tf]
                if data['macd'] < data['macd_signal']:
                    medium_term_bullish = False
                    break
                    
        if medium_term_bullish:
            signal_score += 25
            conditions_met.append("medium_term_trend_bullish")
            
        # 5. Long-term confirmation (1D)
        if '1d' in timeframe_signals:
            data = timeframe_signals['1d']
            if data['macd_diff'] > 0:
                signal_score += 15
                conditions_met.append("daily_trend_confirmation")
                
        # 6. Volatility check
        low_volatility = True
        for tf, data in timeframe_signals.items():
            if data['bb_width'] > 0.1:  # BB width > 10%
                low_volatility = False
                break
                
        if low_volatility:
            signal_score -= 10  # ลดคะแนนหาก volatility ต่ำเกินไป
            
        # Generate final signal
        if signal_score >= 60 and len(conditions_met) >= 3:
            current_price = timeframe_signals['5m']['close']
            
            return {
                'symbol': symbol,
                'signal': 'BUY',
                'score': signal_score,
                'price': current_price,
                'take_profit': current_price * (1 + self.config.TARGET_PROFIT_PERCENT / 100),
                'conditions': conditions_met,
                'timestamp': pd.Timestamp.now()
            }
            
        return None
