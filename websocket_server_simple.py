import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Set
import websockets

from config import settings
from database import SessionLocal
from models import StockPrice
from utils import logger

class StockPriceServer:
    def __init__(self):
        self.clients = set()
        self.stock_prices = {ticker: random.uniform(100, 500) for ticker in settings.STOCK_TICKERS}
        self.running = False
    
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send current prices to new client
        for ticker, price in self.stock_prices.items():
            message = {
                "ticker": ticker,
                "price": round(price, 2),
                "timestamp": datetime.now().isoformat(),
                "type": "price_update"
            }
            try:
                await websocket.send(json.dumps(message))
            except:
                break
    
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def broadcast_price_update(self, ticker: str, price: float):
        """Broadcast price update to all connected clients"""
        if not self.clients:
            return
        
        message = {
            "ticker": ticker,
            "price": round(price, 2),
            "timestamp": datetime.now().isoformat(),
            "type": "price_update"
        }
        
        # Store price in database
        await self.store_price(ticker, price)
        
        # Broadcast to all clients
        disconnected_clients = set()
        for client in self.clients.copy():
            try:
                await client.send(json.dumps(message))
            except:
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.discard(client)
    
    async def store_price(self, ticker: str, price: float):
        """Store price in database"""
        try:
            db = SessionLocal()
            db_price = StockPrice(
                ticker=ticker,
                price=round(price, 2),
                timestamp=datetime.now()
            )
            db.add(db_price)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Error storing price for {ticker}: {str(e)}")
            if 'db' in locals():
                db.rollback()
                db.close()
    
    async def generate_price_updates(self):
        """Generate random price updates for all tickers"""
        while self.running:
            try:
                # Update prices for all tickers
                for ticker in settings.STOCK_TICKERS:
                    # Generate realistic price movement (±5% max change)
                    current_price = self.stock_prices[ticker]
                    change_percent = random.uniform(-0.05, 0.05)  # ±5%
                    new_price = current_price * (1 + change_percent)
                    
                    # Ensure price doesn't go below $1
                    new_price = max(new_price, 1.0)
                    
                    self.stock_prices[ticker] = new_price
                    
                    # Broadcast update
                    await self.broadcast_price_update(ticker, new_price)
                
                # Wait 1-3 seconds before next update
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"Error generating price updates: {str(e)}")
                await asyncio.sleep(1)
    
    async def handle_client(self, websocket):
        """Handle WebSocket client connection"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.info(f"Received message from client: {data}")
                    
                    # Handle different message types
                    if data.get("type") == "subscribe":
                        ticker = data.get("ticker")
                        if ticker and ticker in settings.STOCK_TICKERS:
                            # Send current price for requested ticker
                            current_price = self.stock_prices[ticker]
                            response = {
                                "ticker": ticker,
                                "price": round(current_price, 2),
                                "timestamp": datetime.now().isoformat(),
                                "type": "subscription_confirmed"
                            }
                            await websocket.send(json.dumps(response))
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from client: {message}")
                except Exception as e:
                    logger.error(f"Error handling client message: {str(e)}")
                    
        except Exception as e:
            logger.info(f"Client connection closed: {str(e)}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        """Start the WebSocket server"""
        self.running = True
        
        # Start price generation task
        asyncio.create_task(self.generate_price_updates())
        
        # Start WebSocket server
        logger.info(f"Starting WebSocket server on {settings.WEBSOCKET_HOST}:{settings.WEBSOCKET_PORT}")
        
        async with websockets.serve(
            self.handle_client,
            settings.WEBSOCKET_HOST,
            settings.WEBSOCKET_PORT
        ):
            logger.info(f"WebSocket server started on {settings.WEBSOCKET_HOST}:{settings.WEBSOCKET_PORT}")
            # Keep server running
            try:
                await asyncio.Future()  # Run forever
            except KeyboardInterrupt:
                logger.info("WebSocket server stopping...")
                self.running = False

async def main():
    server = StockPriceServer()
    await server.start_server()

if __name__ == "__main__":
    asyncio.run(main())