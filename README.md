# 📈 TradePulse - Real-Time Stock Trading System

**TradePulse** is a full-stack Python-based trading simulation platform that supports:
- RESTful APIs for trade management,
- real-time stock data simulation using WebSockets,
- algorithmic trading strategies,
- frontend visualization (HTML, JS, CSS),
- and AWS-based cloud analytics (via S3 + Lambda).

---

## 📁 Project Structure Overview
```
STOCK PROJECT/
│
├── static/ # Frontend UI files
│   ├── index.html # UI interface
│   ├── style.css # UI styling
│   └── app.js # JavaScript to fetch/display trades
│
├── main.py # FastAPI entry point
├── config.py # Configs for DB, constants
├── database.py # DB connection setup
├── models.py # SQLAlchemy models
├── schemas.py # Pydantic schemas for API
├── utils.py # Helper functions
├── trading_strategy.py # Moving Average Crossover logic
├── websocket_client.py # Real-time client for price simulation
├── websocket_server.py # WebSocket server (full version)
├── websocket_server_simple.py # WebSocket server (basic version)
├── sample_historical_data.csv # Data file for strategy testing
├── trading_system.db # SQLite database file
├── pyproject.toml # Project metadata & dependencies
```
---

## ⚙️ Setup & Run Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/tradepulse.git
cd tradepulse
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Or, if using Poetry:

```bash
poetry install
```

### 3. Run the Backend (FastAPI)

```bash
uvicorn main:app --reload
```

API available at: http://localhost:8000/docs

### 4. Launch Frontend

Simply open `static/index.html` in your browser.  
(If desired, serve it using FastAPI's `StaticFiles`.)

### 5. Run WebSocket Server & Client

In separate terminals:

```bash
# Start WebSocket server
python websocket_server.py

# Start client to simulate and monitor stock prices
python websocket_client.py
```

This simulates stock price changes and prints alerts when price spikes >2% in 1 minute.

---

## ☁️ AWS Integration (Lambda + S3)

Upload CSV (like `trades.csv`) to S3 path:

```
bucket-name/YYYY/MM/DD/trades.csv
```

Deploy `lambda_function.py` on AWS Lambda to:

- Fetch the file
- Analyze total volume & average price
- Save `analysis_DATE.csv` in the same folder

Optionally add API Gateway to trigger Lambda via a date parameter.

💡 For local testing of S3 operations, install `boto3` and set AWS credentials in `.env`.

---

## ✅ Assumptions Made

- Valid stock tickers (e.g., AAPL, TSLA)
- CSV format: `ticker,price,quantity,side,timestamp`
- SQLite used for simplicity (can switch to PostgreSQL)
- Static frontend (upgradeable to React/Vue)
- AWS credentials securely stored using environment variables

---

## 📈 Features Completed

- ✅ REST API for trade records
- ✅ Real-time stock simulation with alerts
- ✅ Moving Average Strategy simulator
- ✅ SQLite DB integration
- ✅ Basic frontend for trade viewing
- ✅ Lambda script for CSV analytics

---
## 🫵 Dashboard
- Full Dashboard Overview
  
![Dashboard](https://github.com/SpoorthyVihana/Trade-Pulse/blob/main/Dashboard.png)
---

- Live Stock Prices
  
![Live Stock Prices](https://github.com/SpoorthyVihana/Trade-Pulse/blob/main/LIVE-STOCK-PRICES.png)
---
- Add Trade
  
![Add Trade](https://github.com/SpoorthyVihana/Trade-Pulse/blob/main/ADD-TRADE.png)
---
- Recent Tradings
  
![Recent Trades](https://github.com/SpoorthyVihana/Trade-Pulse/blob/main/RECENT-TRADES.png)
---
- Price Alerts
  
![Price Alerts](https://github.com/SpoorthyVihana/Trade-Pulse/blob/main/PRICE-ALERTS.png)
---

## 📌 Future Enhancements

- PostgreSQL + SQLAlchemy ORM (for production-grade setup)
- Web dashboard (charts via Chart.js or D3.js)
- Containerization using Docker
- Cloud deployment via AWS EC2 or Elastic Beanstalk
- Enhanced strategy with real Alpha Vantage data

---

## 👤 Author

**Spoorthy Vihana**  
Intern at [Moneyy.ai]  
📧 rebbaspoorthyvihana05@gmail.com  
🔗 [LinkedIn Profile](https://www.linkedin.com/in/rebbaspoorthyvihana/)
