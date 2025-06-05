from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.sql import func
from database import Base
import enum

class TradeType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    side = Column(Enum(TradeType), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Trade(ticker={self.ticker}, price={self.price}, quantity={self.quantity}, side={self.side})>"

class StockPrice(Base):
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<StockPrice(ticker={self.ticker}, price={self.price}, timestamp={self.timestamp})>"

class AveragePrice(Base):
    __tablename__ = "average_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    average_price = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AveragePrice(ticker={self.ticker}, average_price={self.average_price}, timestamp={self.timestamp})>"
