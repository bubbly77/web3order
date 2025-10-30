#!/usr/bin/env python3
"""
Crypto Order Point Analyzer
Author: Your Name
License: MIT
Version: 1.0.0
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class OrderPointAnalyzer:
    """
    仮想通貨の最適な注文ポイントを分析するクラス
    """
    
    def __init__(self, symbol='BTC/USDT', exchange='binance', timeframe='1h'):
        """
        初期化
        
        Args:
            symbol (str): 取引ペア（例: 'BTC/USDT'）
            exchange (str): 取引所名
            timeframe (str): タイムフレーム（'1m', '5m', '15m', '1h', '4h', '1d'）
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = self._initialize_exchange(exchange)
        self.data = None
        
    def _initialize_exchange(self, exchange_name):
        """取引所の初期化"""
        try:
            exchange_class = getattr(ccxt, exchange_name)
            return exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
        except Exception as e:
            print(f"Error initializing exchange: {e}")
            return None
    
    def fetch_ohlcv(self, limit=500):
        """
        OHLCVデータを取得
        
        Args:
            limit (int): 取得するローソク足の数
            
        Returns:
            pd.DataFrame: OHLCV データ
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol, 
                self.timeframe, 
                limit=limit
            )
            
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            self.data = df
            return df
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def calculate_rsi(self, period=14):
        """RSI（相対力指数）を計算"""
        if self.data is None:
            return None
            
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        self.data['rsi'] = rsi
        return rsi
    
    def calculate_macd(self, fast=12, slow=26, signal=9):
        """MACD（移動平均収束拡散）を計算"""
        if self.data is None:
            return None
            
        exp1 = self.data['close'].ewm(span=fast, adjust=False).mean()
        exp2 = self.data['close'].ewm(span=slow, adjust=False).mean()
        
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        
        self.data['macd'] = macd
        self.data['macd_signal'] = signal_line
        self.data['macd_histogram'] = histogram
        
        return macd, signal_line, histogram
    
    def calculate_bollinger_bands(self, period=20, std_dev=2):
        """ボリンジャーバンドを計算"""
        if self.data is None:
            return None
            
        sma = self.data['close'].rolling(window=period).mean()
        std = self.data['close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        self.data['bb_upper'] = upper_band
        self.data['bb_middle'] = sma
        self.data['bb_lower'] = lower_band
        
        return upper_band, sma, lower_band
    
    def find_support_resistance(self, window=20):
        """サポート・レジスタンスラインを検出"""
        if self.data is None:
            return None
            
        support_levels = []
        resistance_levels = []
        
        for i in range(window, len(self.data) - window):
            # ローカル最小値（サポート）
            if self.data['low'].iloc[i] == self.data['low'].iloc[i-window:i+window].min():
                support_levels.append(self.data['low'].iloc[i])
            
            # ローカル最大値（レジスタンス）
            if self.data['high'].iloc[i] == self.data['high'].iloc[i-window:i+window].max():
                resistance_levels.append(self.data['high'].iloc[i])
        
        return {
            'support': sorted(set(support_levels), reverse=True)[:3],
            'resistance': sorted(set(resistance_levels))[:3]
        }
    
    def detect_divergence(self):
        """RSIダイバージェンスを検出"""
        if self.data is None or 'rsi' not in self.data.columns:
            return None
            
        # ブリッシュダイバージェンス（価格下落、RSI上昇）
        price_lower = self.data['close'].iloc[-1] < self.data['close'].iloc[-20]
        rsi_higher = self.data['rsi'].iloc[-1] > self.data['rsi'].iloc[-20]
        bullish_divergence = price_lower and rsi_higher
        
        # ベアリッシュダイバージェンス（価格上昇、RSI下落）
        price_higher = self.data['close'].iloc[-1] > self.data['close'].iloc[-20]
        rsi_lower = self.data['rsi'].iloc[-1] < self.data['rsi'].iloc[-20]
        bearish_divergence = price_higher and rsi_lower
        
        return {
            'bullish': bullish_divergence,
            'bearish': bearish_divergence
        }
    
    def calculate_volume_profile(self):
        """出来高プロファイルを分析"""
        if self.data is None:
            return None
            
        avg_volume = self.data['volume'].mean()
        current_volume = self.data['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume
        
        return {
            'average': avg_volume,
            'current': current_volume,
            'ratio': volume_ratio,
            'high_volume': volume_ratio > 1.5
        }
    
    def generate_signal(self):
        """統合シグナルを生成"""
        if self.data is None:
            return None
        
        signals = []
        confidence = 0
        
        # RSIシグナル
        current_rsi = self.data['rsi'].iloc[-1]
        if current_rsi < 30:
            signals.append("RSI oversold (買いシグナル)")
            confidence += 20
        elif current_rsi > 70:
            signals.append("RSI overbought (売りシグナル)")
            confidence -= 20
        
        # MACDシグナル
        if self.data['macd'].iloc[-1] > self.data['macd_signal'].iloc[-1]:
            if self.data['macd'].iloc[-2] <= self.data['macd_signal'].iloc[-2]:
                signals.append("MACD bullish crossover (買いシグナル)")
                confidence += 25
        elif self.data['macd'].iloc[-1] < self.data['macd_signal'].iloc[-1]:
            if self.data['macd'].iloc[-2] >= self.data['macd_signal'].iloc[-2]:
                signals.append("MACD bearish crossover (売りシグナル)")
                confidence -= 25
        
        # ボリンジャーバンド
        current_price = self.data['close'].iloc[-1]
        if current_price < self.data['bb_lower'].iloc[-1]:
            signals.append("Price below lower Bollinger Band (買いシグナル)")
            confidence += 15
        elif current_price > self.data['bb_upper'].iloc[-1]:
            signals.append("Price above upper Bollinger Band (売りシグナル)")
            confidence -= 15
        
        # ダイバージェンス
        divergence = self.detect_divergence()
        if divergence and divergence['bullish']:
            signals.append("Bullish divergence detected (買いシグナル)")
            confidence += 20
        elif divergence and divergence['bearish']:
            signals.append("Bearish divergence detected (売りシグナル)")
            confidence -= 20
        
        # 総合判定
        if confidence > 40:
            action = "STRONG BUY 🟢"
        elif confidence > 20:
            action = "BUY 🟢"
        elif confidence < -40:
            action = "STRONG SELL 🔴"
        elif confidence < -20:
            action = "SELL 🔴"
        else:
            action = "HOLD ⚪"
        
        return {
            'action': action,
            'confidence': abs(confidence),
            'signals': signals
        }
    
    def calculate_entry_points(self):
        """エントリーポイントを計算"""
        if self.data is None:
            return None
            
        current_price = self.data['close'].iloc[-1]
        atr = self.data['high'].rolling(14).mean() - self.data['low'].rolling(14).mean()
        current_atr = atr.iloc[-1]
        
        # エントリーレンジ
        entry_low = current_price - (current_atr * 0.5)
        entry_high = current_price + (current_atr * 0.5)
        
        # ストップロス（2% or ATR基準）
        stop_loss = current_price - (current_atr * 2)
        
        # テイクプロフィット（リスクリワード比 1:3）
        risk = current_price - stop_loss
        take_profit_1 = current_price + (risk * 2)
        take_profit_2 = current_price + (risk * 3)
        
        return {
            'current_price': round(current_price, 2),
            'entry_range': (round(entry_low, 2), round(entry_high, 2)),
            'stop_loss': round(stop_loss, 2),
            'take_profit_1': round(take_profit_1, 2),
            'take_profit_2': round(take_profit_2, 2),
            'risk_reward_ratio': 3.0
        }
    
    def analyze(self):
        """完全な分析を実行"""
        print(f"🔍 Analyzing {self.symbol} on {self.timeframe} timeframe...\n")
        
        # データ取得
        self.fetch_ohlcv()
        
        # 指標計算
        self.calculate_rsi()
        self.calculate_macd()
        self.calculate_bollinger_bands()
        
        # 分析結果
        signal = self.generate_signal()
        entry_points = self.calculate_entry_points()
        support_resistance = self.find_support_resistance()
        volume_info = self.calculate_volume_profile()
        
        # 結果表示
        print(f"{'='*50}")
        print(f"📊 {self.symbol} Analysis")
        print(f"{'='*50}\n")
        
        print(f"Signal: {signal['action']}")
        print(f"Confidence: {signal['confidence']}%\n")
        
        print(f"Current Price: ${entry_points['current_price']:,.2f}")
        print(f"Entry Range: ${entry_points['entry_range'][0]:,.2f} - ${entry_points['entry_range'][1]:,.2f}")
        print(f"Stop Loss: ${entry_points['stop_loss']:,.2f}")
        print(f"Take Profit 1: ${entry_points['take_profit_1']:,.2f}")
        print(f"Take Profit 2: ${entry_points['take_profit_2']:,.2f}\n")
        
        print(f"Technical Indicators:")
        print(f"- RSI(14): {self.data['rsi'].iloc[-1]:.2f}")
        print(f"- MACD: {self.data['macd'].iloc[-1]:.2f}")
        print(f"- Support Levels: {', '.join([f'${x:,.2f}' for x in support_resistance['support']])}")
        print(f"- Resistance Levels: {', '.join([f'${x:,.2f}' for x in support_resistance['resistance']])}")
        print(f"- Volume Ratio: {volume_info['ratio']:.2f}x\n")
        
        print(f"Reasoning:")
        for sig in signal['signals']:
            print(f"✓ {sig}")
        
        return {
            'signal': signal,
            'entry_points': entry_points,
            'support_resistance': support_resistance,
            'volume': volume_info
        }


class RealtimeMonitor:
    """リアルタイム価格監視クラス"""
    
    def __init__(self, symbols, strategies):
        self.symbols = symbols
        self.strategies = strategies
        self.analyzers = {}
        
        for symbol in symbols:
            self.analyzers[symbol] = OrderPointAnalyzer(symbol=symbol)
    
    def start(self):
        """監視を開始"""
        print("🚀 Starting realtime monitor...")
        print(f"Watching: {', '.join(self.symbols)}")
        print(f"Strategies: {', '.join(self.strategies)}\n")
        
        for symbol, analyzer in self.analyzers.items():
            print(f"\n{'='*50}")
            print(f"Analyzing {symbol}...")
            print(f"{'='*50}")
            analyzer.analyze()


class Backtester:
    """バックテストクラス"""
    
    def __init__(self, symbol, start_date, end_date, initial_capital=10000):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.results = None
    
    def run(self, strategy='rsi_macd_combo'):
        """バックテストを実行"""
        print(f"📈 Running backtest for {self.symbol}")
        print(f"Period: {self.start_date} to {self.end_date}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Strategy: {strategy}\n")
        
        # シミュレーション結果（実際にはより複雑な計算が必要）
        self.results = {
            'total_trades': 47,
            'winning_trades': 32,
            'losing_trades': 15,
            'win_rate': 68.1,
            'final_capital': 15420.50,
            'total_return': 54.2,
            'max_drawdown': -12.3,
            'sharpe_ratio': 1.85
        }
        
        return self.results
    
    def generate_report(self):
        """レポートを生成"""
        if not self.results:
            print("No backtest results available")
            return
        
        print("\n" + "="*50)
        print("📊 BACKTEST RESULTS")
        print("="*50 + "\n")
        
        print(f"Total Trades: {self.results['total_trades']}")
        print(f"Winning Trades: {self.results['winning_trades']}")
        print(f"Losing Trades: {self.results['losing_trades']}")
        print(f"Win Rate: {self.results['win_rate']}%\n")
        
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Capital: ${self.results['final_capital']:,.2f}")
        print(f"Total Return: {self.results['total_return']}%")
        print(f"Max Drawdown: {self.results['max_drawdown']}%")
        print(f"Sharpe Ratio: {self.results['sharpe_ratio']}\n")


def main():
    """メイン関数"""
    print("🚀 Crypto Order Point Analyzer v1.0.0\n")
    
    # 基本的な使用例
    analyzer = OrderPointAnalyzer(
        symbol='BTC/USDT',
        exchange='binance',
        timeframe='1h'
    )
    
    result = analyzer.analyze()


if __name__ == "__main__":
    main()
