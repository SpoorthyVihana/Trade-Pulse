import asyncio
import json
import logging
from datetime import datetime
import websockets
from websockets.client import WebSocketClientProtocol

from config import settings
from utils import PriceTracker, calculate_percentage_change, logger

class StockPriceClient:
    def __init__(self):
        self.price_tracker = PriceTracker(threshold_percent=settings.PRICE_CHANGE_THRESHOLD)
        self.websocket_url = f"ws://{settings.WEBSOCKET_HOST}:{settings.WEBSOCKET_PORT}"
        self.running = False
    
    async def connect_and_monitor(self):
        """Connect to WebSocket server and monitor price changes"""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Attempting to connect to WebSocket server: {self.websocket_url}")
                
                async with websockets.connect(self.websocket_url) as websocket:
                    logger.info("Connected to WebSocket server")
                    self.running = True
                    retry_count = 0  # Reset retry count on successful connection
                    
                    # Subscribe to all tickers
                    for ticker in settings.STOCK_TICKERS:
                        subscribe_message = {
                            "type": "subscribe",
                            "ticker": ticker
                        }
                        await websocket.send(json.dumps(subscribe_message))
                        logger.info(f"Subscribed to {ticker}")
                    
                    # Listen for messages
                    async for message in websocket:
                        await self.handle_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self.running = False
                break
            except websockets.exceptions.InvalidURI:
                logger.error(f"Invalid WebSocket URI: {self.websocket_url}")
                break
            except ConnectionRefusedError:
                retry_count += 1
                logger.warning(f"Connection refused. Retry {retry_count}/{max_retries}")
                if retry_count < max_retries:
                    await asyncio.sleep(5)  # Wait 5 seconds before retrying
                else:
                    logger.error("Max retries reached. Could not connect to WebSocket server.")
                    break
            except Exception as e:
                retry_count += 1
                logger.error(f"Error connecting to WebSocket: {str(e)}. Retry {retry_count}/{max_retries}")
                if retry_count < max_retries:
                    await asyncio.sleep(5)
                else:
                    break
    
    async def handle_message(self, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            if data.get("type") == "price_update":
                ticker = data.get("ticker")
                price = data.get("price")
                timestamp_str = data.get("timestamp")
                
                if ticker and price is not None:
                    # Parse timestamp
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    
                    # Add price to tracker
                    self.price_tracker.add_price(ticker, price, timestamp)
                    
                    # Check for significant price changes
                    if self.price_tracker.check_significant_change(ticker):
                        await self.notify_significant_change(ticker, price)
                    
                    # Log price update
                    logger.info(f"Price update: {ticker} = ${price:.2f} at {timestamp}")
            
            elif data.get("type") == "subscription_confirmed":
                ticker = data.get("ticker")
                price = data.get("price")
                logger.info(f"Subscription confirmed for {ticker}: ${price:.2f}")
            
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
    
    async def notify_significant_change(self, ticker: str, current_price: float):
        """Send notification for significant price changes"""
        try:
            # Get price history for the last minute
            if ticker in self.price_tracker.price_history:
                recent_prices = [
                    price for price, timestamp in self.price_tracker.price_history[ticker]
                    if (datetime.now() - timestamp).total_seconds() <= 60
                ]
                
                if len(recent_prices) >= 2:
                    old_price = recent_prices[0]
                    change_percent = calculate_percentage_change(old_price, current_price)
                    
                    if abs(change_percent) >= settings.PRICE_CHANGE_THRESHOLD:
                        direction = "↑" if change_percent > 0 else "↓"
                        
                        notification = (
                            f"🚨 PRICE ALERT: {ticker} {direction} "
                            f"{abs(change_percent):.2f}% in 1 minute! "
                            f"${old_price:.2f} → ${current_price:.2f}"
                        )
                        
                        logger.warning(notification)
                        print(f"\n{notification}\n")
                        
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
    
    async def run_monitoring(self):
        """Run the price monitoring client"""
        logger.info("Starting stock price monitoring client...")
        print("🔄 Starting stock price monitoring...")
        print(f"📈 Monitoring {len(settings.STOCK_TICKERS)} tickers: {', '.join(settings.STOCK_TICKERS)}")
        print(f"⚠️  Will alert on price changes > {settings.PRICE_CHANGE_THRESHOLD}% in 1 minute")
        print("Press Ctrl+C to stop monitoring\n")
        
        try:
            await self.connect_and_monitor()
        except KeyboardInterrupt:
            logger.info("Price monitoring stopped by user")
            print("\n👋 Price monitoring stopped")
        except Exception as e:
            logger.error(f"Unexpected error in price monitoring: {str(e)}")
            print(f"\n❌ Error: {str(e)}")

async def main():
    client = StockPriceClient()
    await client.run_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
