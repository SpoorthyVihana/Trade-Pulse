import os
from typing import Optional

class Settings:
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./trading_system.db")
    
    # WebSocket configuration
    WEBSOCKET_HOST: str = "0.0.0.0"
    WEBSOCKET_PORT: int = 8001
    
    # Trading configuration
    PRICE_CHANGE_THRESHOLD: float = 0.02  # 2% threshold for notifications
    AVERAGE_CALCULATION_INTERVAL: int = 300  # 5 minutes in seconds
    
    # Moving average configuration
    SHORT_MA_PERIOD: int = 50
    LONG_MA_PERIOD: int = 200
    
    # Stock tickers for simulation
    STOCK_TICKERS: list = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "META", "NVDA"]

settings = Settings()
