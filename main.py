import asyncio
import logging
import json
import random
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import get_db, create_tables, SessionLocal
from models import Trade, StockPrice, AveragePrice, TradeType
from schemas import TradeCreate, TradeResponse, TradeFilter, StockPriceResponse
from config import settings
from utils import logger

# Configure logging
logging.basicConfig(level=logging.INFO)

# Background task for calculating averages and price simulation
background_tasks = set()
stock_prices = {ticker: random.uniform(100, 500) for ticker in settings.STOCK_TICKERS}
price_subscribers = set()

async def generate_stock_prices():
    """Generate random stock prices and store them in database"""
    global stock_prices
    
    while True:
        try:
            db = SessionLocal()
            
            for ticker in settings.STOCK_TICKERS:
                # Generate realistic price movement (±5% max change)
                current_price = stock_prices[ticker]
                change_percent = random.uniform(-0.05, 0.05)  # ±5%
                new_price = current_price * (1 + change_percent)
                
                # Ensure price doesn't go below $1
                new_price = max(new_price, 1.0)
                stock_prices[ticker] = new_price
                
                # Store price in database
                db_price = StockPrice(
                    ticker=ticker,
                    price=round(new_price, 2),
                    timestamp=datetime.now()
                )
                db.add(db_price)
            
            db.commit()
            db.close()
            
            # Wait 1-3 seconds before next update
            await asyncio.sleep(random.uniform(1, 3))
            
        except Exception as e:
            logger.error(f"Error generating stock prices: {str(e)}")
            if 'db' in locals():
                db.rollback()
                db.close()
            await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_tables()
    logger.info("Database tables created successfully")
    
    # Start background tasks
    avg_task = asyncio.create_task(calculate_and_store_averages())
    price_task = asyncio.create_task(generate_stock_prices())
    background_tasks.add(avg_task)
    background_tasks.add(price_task)
    logger.info("Background tasks started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down background tasks...")
    for task in background_tasks:
        task.cancel()

# Create FastAPI app with lifespan
app = FastAPI(
    title="Trading System API",
    description="A comprehensive trading system with REST API, WebSocket support, and algorithmic trading",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/trade", response_model=TradeResponse)
async def create_trade(trade: TradeCreate, db: Session = Depends(get_db)):
    """Create a new trade"""
    try:
        # Create trade object
        db_trade = Trade(
            ticker=trade.ticker,
            price=trade.price,
            quantity=trade.quantity,
            side=trade.side,
            timestamp=trade.timestamp or datetime.now()
        )
        
        # Add to database
        db.add(db_trade)
        db.commit()
        db.refresh(db_trade)
        
        logger.info(f"Created trade: {db_trade}")
        return db_trade
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating trade: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating trade: {str(e)}")

@app.get("/trades", response_model=List[TradeResponse])
async def get_trades(
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of trades to return"),
    db: Session = Depends(get_db)
):
    """Get trades with optional filtering"""
    try:
        query = db.query(Trade)
        
        # Apply filters
        if ticker:
            query = query.filter(Trade.ticker == ticker.upper())
        
        if start_date:
            query = query.filter(Trade.timestamp >= start_date)
        
        if end_date:
            query = query.filter(Trade.timestamp <= end_date)
        
        # Order by timestamp descending and limit results
        trades = query.order_by(Trade.timestamp.desc()).limit(limit).all()
        
        logger.info(f"Retrieved {len(trades)} trades with filters: ticker={ticker}, start_date={start_date}, end_date={end_date}")
        return trades
        
    except Exception as e:
        logger.error(f"Error retrieving trades: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving trades: {str(e)}")

@app.get("/stock-prices", response_model=List[StockPriceResponse])
async def get_stock_prices(
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of prices to return"),
    db: Session = Depends(get_db)
):
    """Get stock prices with optional filtering"""
    try:
        query = db.query(StockPrice)
        
        if ticker:
            query = query.filter(StockPrice.ticker == ticker.upper())
        
        prices = query.order_by(StockPrice.timestamp.desc()).limit(limit).all()
        
        logger.info(f"Retrieved {len(prices)} stock prices for ticker: {ticker}")
        return prices
        
    except Exception as e:
        logger.error(f"Error retrieving stock prices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving stock prices: {str(e)}")

@app.get("/average-prices")
async def get_average_prices(
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of averages to return"),
    db: Session = Depends(get_db)
):
    """Get average prices with optional filtering"""
    try:
        query = db.query(AveragePrice)
        
        if ticker:
            query = query.filter(AveragePrice.ticker == ticker.upper())
        
        averages = query.order_by(AveragePrice.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "ticker": avg.ticker,
                "average_price": avg.average_price,
                "timestamp": avg.timestamp
            }
            for avg in averages
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving average prices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving average prices: {str(e)}")

async def calculate_and_store_averages():
    """Background task to calculate and store average prices every 5 minutes"""
    from database import SessionLocal
    
    while True:
        try:
            db = SessionLocal()
            current_time = datetime.now()
            five_minutes_ago = current_time - timedelta(minutes=5)
            
            # Calculate averages for each ticker
            for ticker in settings.STOCK_TICKERS:
                # Get prices from the last 5 minutes
                recent_prices = db.query(StockPrice).filter(
                    and_(
                        StockPrice.ticker == ticker,
                        StockPrice.timestamp >= five_minutes_ago
                    )
                ).all()
                
                if recent_prices:
                    avg_price = sum(price.price for price in recent_prices) / len(recent_prices)
                    
                    # Store average price
                    db_avg = AveragePrice(
                        ticker=ticker,
                        average_price=round(avg_price, 2),
                        timestamp=current_time
                    )
                    
                    db.add(db_avg)
                    logger.info(f"Calculated average price for {ticker}: ${avg_price:.2f}")
            
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error calculating averages: {str(e)}")
            if 'db' in locals():
                db.rollback()
                db.close()
        
        # Wait 5 minutes before next calculation
        await asyncio.sleep(settings.AVERAGE_CALCULATION_INTERVAL)



async def generate_stock_prices():
    """Generate random stock prices and store them in database"""
    global stock_prices
    
    while True:
        try:
            db = SessionLocal()
            
            for ticker in settings.STOCK_TICKERS:
                # Generate realistic price movement (±5% max change)
                current_price = stock_prices[ticker]
                change_percent = random.uniform(-0.05, 0.05)  # ±5%
                new_price = current_price * (1 + change_percent)
                
                # Ensure price doesn't go below $1
                new_price = max(new_price, 1.0)
                stock_prices[ticker] = new_price
                
                # Store price in database
                db_price = StockPrice(
                    ticker=ticker,
                    price=round(new_price, 2),
                    timestamp=datetime.now()
                )
                db.add(db_price)
            
            db.commit()
            db.close()
            
            # Wait 1-3 seconds before next update
            await asyncio.sleep(random.uniform(1, 3))
            
        except Exception as e:
            logger.error(f"Error generating stock prices: {str(e)}")
            if 'db' in locals():
                db.rollback()
                db.close()
            await asyncio.sleep(1)

@app.get("/stock-prices/stream")
async def stream_stock_prices():
    """Stream real-time stock prices using Server-Sent Events"""
    
    async def generate():
        while True:
            try:
                # Send current stock prices
                for ticker, price in stock_prices.items():
                    data = {
                        "ticker": ticker,
                        "price": round(price, 2),
                        "timestamp": datetime.now().isoformat(),
                        "type": "price_update"
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                
                # Wait before next update
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in SSE stream: {str(e)}")
                yield f"data: {json.dumps({'error': 'Stream error'})}\n\n"
                break
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="192.168.29.51",
        port=8001,
        reload=True,
        log_level="info"
    )
