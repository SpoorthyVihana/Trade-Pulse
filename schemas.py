from pydantic import BaseModel, validator, Field
from datetime import datetime
from typing import Optional, List
from models import TradeType

class TradeCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    price: float = Field(..., gt=0, description="Trade price must be positive")
    quantity: int = Field(..., gt=0, description="Quantity must be positive")
    side: TradeType = Field(..., description="Trade side: buy or sell")
    timestamp: Optional[datetime] = Field(None, description="Trade timestamp")
    
    @validator('ticker')
    def ticker_must_be_uppercase(cls, v):
        return v.upper().strip()
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return round(v, 2)
    
    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class TradeResponse(BaseModel):
    id: int
    ticker: str
    price: float
    quantity: int
    side: TradeType
    timestamp: datetime
    
    class Config:
        from_attributes = True

class TradeFilter(BaseModel):
    ticker: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class StockPriceResponse(BaseModel):
    ticker: str
    price: float
    timestamp: datetime
    
    class Config:
        from_attributes = True

class TradingSignal(BaseModel):
    ticker: str
    signal: str  # "BUY" or "SELL"
    price: float
    short_ma: float
    long_ma: float
    timestamp: datetime

class ProfitLossReport(BaseModel):
    ticker: str
    total_trades: int
    total_profit_loss: float
    winning_trades: int
    losing_trades: int
    win_rate: float
    signals: List[TradingSignal]
