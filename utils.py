import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_moving_average(prices: List[float], period: int) -> List[float]:
    """Calculate moving average for given prices and period"""
    if len(prices) < period:
        return [np.nan] * len(prices)
    
    ma_values = []
    for i in range(len(prices)):
        if i < period - 1:
            ma_values.append(np.nan)
        else:
            ma_values.append(np.mean(prices[i - period + 1:i + 1]))
    
    return ma_values

def detect_crossover(short_ma: List[float], long_ma: List[float]) -> List[str]:
    """Detect moving average crossovers and generate signals"""
    signals = []
    
    for i in range(1, len(short_ma)):
        if np.isnan(short_ma[i]) or np.isnan(long_ma[i]) or np.isnan(short_ma[i-1]) or np.isnan(long_ma[i-1]):
            signals.append("HOLD")
            continue
            
        # Buy signal: short MA crosses above long MA
        if short_ma[i-1] <= long_ma[i-1] and short_ma[i] > long_ma[i]:
            signals.append("BUY")
        # Sell signal: short MA crosses below long MA
        elif short_ma[i-1] >= long_ma[i-1] and short_ma[i] < long_ma[i]:
            signals.append("SELL")
        else:
            signals.append("HOLD")
    
    return ["HOLD"] + signals  # First value is always HOLD

def calculate_profit_loss(trades: List[Dict]) -> Tuple[float, int, int]:
    """Calculate total profit/loss and trade statistics"""
    if not trades:
        return 0.0, 0, 0
    
    total_pnl = 0.0
    winning_trades = 0
    losing_trades = 0
    position = 0
    avg_cost = 0
    
    for trade in trades:
        if trade['signal'] == 'BUY':
            if position == 0:
                position = 1
                avg_cost = trade['price']
            elif position < 0:  # Covering short position
                pnl = (avg_cost - trade['price']) * abs(position)
                total_pnl += pnl
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                position = 1
                avg_cost = trade['price']
        elif trade['signal'] == 'SELL':
            if position == 0:
                position = -1
                avg_cost = trade['price']
            elif position > 0:  # Selling long position
                pnl = (trade['price'] - avg_cost) * position
                total_pnl += pnl
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                position = -1
                avg_cost = trade['price']
    
    return total_pnl, winning_trades, losing_trades

def format_currency(amount: float) -> str:
    """Format currency amount"""
    return f"${amount:,.2f}"

def calculate_percentage_change(old_price: float, new_price: float) -> float:
    """Calculate percentage change between two prices"""
    if old_price == 0:
        return 0.0
    return ((new_price - old_price) / old_price) * 100

class PriceTracker:
    """Track price changes and detect significant movements"""
    
    def __init__(self, threshold_percent: float = 2.0):
        self.threshold_percent = threshold_percent
        self.price_history: Dict[str, List[Tuple[float, datetime]]] = {}
    
    def add_price(self, ticker: str, price: float, timestamp: datetime = None):
        """Add a new price point for tracking"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if ticker not in self.price_history:
            self.price_history[ticker] = []
        
        self.price_history[ticker].append((price, timestamp))
        
        # Keep only last hour of data for efficiency
        cutoff_time = timestamp - timedelta(hours=1)
        self.price_history[ticker] = [
            (p, t) for p, t in self.price_history[ticker] if t >= cutoff_time
        ]
    
    def check_significant_change(self, ticker: str) -> bool:
        """Check if price has changed significantly in the last minute"""
        if ticker not in self.price_history or len(self.price_history[ticker]) < 2:
            return False
        
        current_time = datetime.now()
        one_minute_ago = current_time - timedelta(minutes=1)
        
        # Get prices from the last minute
        recent_prices = [
            price for price, timestamp in self.price_history[ticker]
            if timestamp >= one_minute_ago
        ]
        
        if len(recent_prices) < 2:
            return False
        
        old_price = recent_prices[0]
        new_price = recent_prices[-1]
        
        change_percent = abs(calculate_percentage_change(old_price, new_price))
        return change_percent >= self.threshold_percent
