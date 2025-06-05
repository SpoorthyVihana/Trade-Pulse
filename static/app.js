class TradingDashboard {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        this.stockPrices = new Map();
        this.priceHistory = new Map();
        this.alerts = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadRecentTrades();
        
        // Try to connect automatically
        setTimeout(() => this.connectWebSocket(), 1000);
    }
    
    setupEventListeners() {
        // Connect button
        document.getElementById('connectBtn').addEventListener('click', () => {
            if (this.isConnected) {
                this.disconnectWebSocket();
            } else {
                this.connectWebSocket();
            }
        });
        
        // Trade form
        document.getElementById('tradeForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitTrade();
        });
        
        // Refresh trades button
        document.getElementById('refreshTrades').addEventListener('click', () => {
            this.loadRecentTrades();
        });
    }
    
    async connectWebSocket() {
        try {
            this.updateConnectionStatus('connecting');
            
            // Use Server-Sent Events instead of WebSocket for better compatibility
            const sseUrl = '/stock-prices/stream';
            console.log('Connecting to price stream via SSE:', sseUrl);
            
            this.eventSource = new EventSource(sseUrl);
            
            this.eventSource.onopen = () => {
                console.log('SSE connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
                this.showToast('Connected to live data feed', 'success');
            };
            
            this.eventSource.onmessage = (event) => {
                this.handleSSEMessage(event);
            };
            
            this.eventSource.onerror = (error) => {
                console.error('SSE error:', error);
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                
                // Attempt to reconnect
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    setTimeout(() => this.connectWebSocket(), 5000);
                } else {
                    this.showToast('Connection lost. Click Connect to retry.', 'warning');
                }
            };
            
        } catch (error) {
            console.error('Failed to connect:', error);
            this.updateConnectionStatus('disconnected');
            this.showToast('Failed to connect to price stream', 'danger');
        }
    }
    
    disconnectWebSocket() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        this.isConnected = false;
        this.updateConnectionStatus('disconnected');
        this.showToast('Disconnected from live data feed', 'info');
    }
    
    handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'price_update') {
                this.updateStockPrice(data.ticker, data.price, data.timestamp);
            } else if (data.type === 'subscription_confirmed') {
                console.log(`Subscribed to ${data.ticker}: $${data.price}`);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }
    
    handleSSEMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'price_update') {
                this.updateStockPrice(data.ticker, data.price, data.timestamp);
            }
        } catch (error) {
            console.error('Error parsing SSE message:', error);
        }
    }
    
    updateStockPrice(ticker, price, timestamp) {
        const previousPrice = this.stockPrices.get(ticker);
        this.stockPrices.set(ticker, { price, timestamp, previousPrice });
        
        // Store price history for change detection
        if (!this.priceHistory.has(ticker)) {
            this.priceHistory.set(ticker, []);
        }
        
        const history = this.priceHistory.get(ticker);
        history.push({ price, timestamp: new Date(timestamp) });
        
        // Keep only last 10 minutes of history
        const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000);
        this.priceHistory.set(ticker, history.filter(h => h.timestamp > tenMinutesAgo));
        
        // Check for significant price changes
        this.checkPriceAlert(ticker, price);
        
        // Update UI
        this.renderStockPrices();
    }
    
    checkPriceAlert(ticker, currentPrice) {
        const history = this.priceHistory.get(ticker);
        if (!history || history.length < 2) return;
        
        // Check for 2% change in the last minute
        const oneMinuteAgo = new Date(Date.now() - 60 * 1000);
        const recentPrices = history.filter(h => h.timestamp > oneMinuteAgo);
        
        if (recentPrices.length >= 2) {
            const oldPrice = recentPrices[0].price;
            const changePercent = ((currentPrice - oldPrice) / oldPrice) * 100;
            
            if (Math.abs(changePercent) >= 2) {
                const direction = changePercent > 0 ? '↑' : '↓';
                const alertType = changePercent > 0 ? 'success' : 'danger';
                
                const alertMessage = `${ticker} ${direction} ${Math.abs(changePercent).toFixed(2)}% in 1 minute! $${oldPrice.toFixed(2)} → $${currentPrice.toFixed(2)}`;
                
                this.addAlert(alertMessage, alertType);
                this.showToast(alertMessage, alertType);
            }
        }
    }
    
    addAlert(message, type) {
        const alert = {
            message,
            type,
            timestamp: new Date()
        };
        
        this.alerts.unshift(alert);
        
        // Keep only last 50 alerts
        if (this.alerts.length > 50) {
            this.alerts = this.alerts.slice(0, 50);
        }
        
        this.renderAlerts();
    }
    
    renderStockPrices() {
        const container = document.getElementById('stockPrices');
        
        if (this.stockPrices.size === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-wifi-slash fa-2x mb-2"></i>
                    <p>No price data available</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        for (const [ticker, data] of this.stockPrices) {
            const { price, previousPrice } = data;
            let changeClass = 'price-neutral';
            let changeIcon = '';
            
            if (previousPrice !== undefined) {
                if (price > previousPrice) {
                    changeClass = 'price-up';
                    changeIcon = '<i class="fas fa-arrow-up me-1"></i>';
                } else if (price < previousPrice) {
                    changeClass = 'price-down';
                    changeIcon = '<i class="fas fa-arrow-down me-1"></i>';
                }
            }
            
            html += `
                <div class="stock-item">
                    <div>
                        <div class="stock-symbol">${ticker}</div>
                        <div class="text-muted small">Real-time</div>
                    </div>
                    <div class="text-end">
                        <div class="stock-price">$${price.toFixed(2)}</div>
                        <div class="price-change ${changeClass}">
                            ${changeIcon}Live
                        </div>
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
    }
    
    renderAlerts() {
        const container = document.getElementById('alerts');
        
        if (this.alerts.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-bell-slash fa-2x mb-2"></i>
                    <p>No alerts yet</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        this.alerts.slice(0, 10).forEach(alert => {
            const timeStr = alert.timestamp.toLocaleTimeString();
            html += `
                <div class="alert-item alert-${alert.type}">
                    <div class="alert-time">${timeStr}</div>
                    <div>${alert.message}</div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connectionStatus');
        const connectBtn = document.getElementById('connectBtn');
        
        switch (status) {
            case 'connected':
                statusElement.innerHTML = '<i class="fas fa-circle text-success me-1"></i>Connected';
                connectBtn.innerHTML = '<i class="fas fa-times me-1"></i>Disconnect';
                connectBtn.className = 'btn btn-sm btn-danger';
                break;
            case 'connecting':
                statusElement.innerHTML = '<i class="fas fa-circle text-warning me-1"></i>Connecting...';
                connectBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Connecting';
                connectBtn.className = 'btn btn-sm btn-warning';
                connectBtn.disabled = true;
                break;
            case 'disconnected':
            default:
                statusElement.innerHTML = '<i class="fas fa-circle text-danger me-1"></i>Disconnected';
                connectBtn.innerHTML = '<i class="fas fa-plug me-1"></i>Connect';
                connectBtn.className = 'btn btn-sm btn-primary';
                connectBtn.disabled = false;
                break;
        }
    }
    
    async submitTrade() {
        const formData = {
            ticker: document.getElementById('ticker').value,
            side: document.getElementById('side').value,
            price: parseFloat(document.getElementById('price').value),
            quantity: parseInt(document.getElementById('quantity').value)
        };
        
        try {
            const response = await fetch('/trade', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showToast(`Trade added successfully: ${result.side.toUpperCase()} ${result.quantity} ${result.ticker} @ $${result.price}`, 'success');
                document.getElementById('tradeForm').reset();
                this.loadRecentTrades();
            } else {
                const error = await response.json();
                this.showToast(`Error: ${error.detail}`, 'danger');
            }
        } catch (error) {
            console.error('Error submitting trade:', error);
            this.showToast('Error submitting trade', 'danger');
        }
    }
    
    async loadRecentTrades() {
        try {
            const response = await fetch('/trades?limit=10');
            if (response.ok) {
                const trades = await response.json();
                this.renderTrades(trades);
            } else {
                console.error('Error loading trades:', response.statusText);
            }
        } catch (error) {
            console.error('Error loading trades:', error);
        }
    }
    
    renderTrades(trades) {
        const container = document.getElementById('recentTrades');
        
        if (trades.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p>No trades yet</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        trades.forEach(trade => {
            const sideClass = trade.side === 'buy' ? 'trade-side-buy' : 'trade-side-sell';
            const sideIcon = trade.side === 'buy' ? 'fa-arrow-up text-success' : 'fa-arrow-down text-danger';
            const timestamp = new Date(trade.timestamp).toLocaleString();
            const total = (trade.price * trade.quantity).toFixed(2);
            
            html += `
                <div class="trade-item ${sideClass}">
                    <div>
                        <div class="trade-symbol">
                            <i class="fas ${sideIcon} me-1"></i>
                            ${trade.ticker}
                        </div>
                        <div class="trade-details">
                            ${trade.quantity} shares @ $${trade.price.toFixed(2)}
                        </div>
                        <div class="trade-details text-muted small">
                            ${timestamp}
                        </div>
                    </div>
                    <div class="trade-amount">
                        <div class="fw-bold">$${total}</div>
                        <div class="small text-muted">${trade.side.toUpperCase()}</div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container');
        const toastId = 'toast-' + Date.now();
        
        const bgClass = {
            'success': 'bg-success',
            'danger': 'bg-danger',
            'warning': 'bg-warning',
            'info': 'bg-info'
        }[type] || 'bg-info';
        
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 5000
        });
        
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Initialize the dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TradingDashboard();
});
