import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple
import logging

from schemas import TradingSignal, ProfitLossReport
from utils import calculate_moving_average, detect_crossover, calculate_profit_loss, format_currency
from config import settings

logger = logging.getLogger(__name__)

class MovingAverageCrossoverStrategy:
    def __init__(self, short_period: int = None, long_period: int = None):
        self.short_period = short_period or settings.SHORT_MA_PERIOD
        self.long_period = long_period or settings.LONG_MA_PERIOD
        
        if self.short_period >= self.long_period:
            raise ValueError("Short period must be less than long period")
    
    def load_historical_data(self, csv_file: str) -> pd.DataFrame:
        """Load historical stock data from CSV file"""
        try:
            df = pd.read_csv(csv_file)
            
            # Validate required columns
            required_columns = ['ticker', 'date', 'price']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Convert date column to datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # Sort by ticker and date
            df = df.sort_values(['ticker', 'date']).reset_index(drop=True)
            
            # Validate data
            if df['price'].isna().any():
                logger.warning("Found missing price data, filling with forward fill")
                df['price'] = df['price'].fillna(method='ffill')
            
            if (df['price'] <= 0).any():
                raise ValueError("Found non-positive prices in data")
            
            logger.info(f"Loaded {len(df)} records for {df['ticker'].nunique()} tickers")
            return df
            
        except Exception as e:
            logger.error(f"Error loading historical data: {str(e)}")
            raise
    
    def calculate_signals(self, df: pd.DataFrame) -> Dict[str, List[TradingSignal]]:
        """Calculate trading signals for all tickers"""
        results = {}
        
        try:
            for ticker in df['ticker'].unique():
                ticker_data = df[df['ticker'] == ticker].copy()
                
                if len(ticker_data) < self.long_period:
                    logger.warning(f"Insufficient data for {ticker}: {len(ticker_data)} records")
                    continue
                
                # Calculate moving averages
                prices = ticker_data['price'].tolist()
                short_ma = calculate_moving_average(prices, self.short_period)
                long_ma = calculate_moving_average(prices, self.long_period)
                
                # Detect crossover signals
                signals = detect_crossover(short_ma, long_ma)
                
                # Create trading signals
                trading_signals = []
                for i, signal in enumerate(signals):
                    if signal in ['BUY', 'SELL']:
                        trading_signal = TradingSignal(
                            ticker=ticker,
                            signal=signal,
                            price=prices[i],
                            short_ma=short_ma[i] if not np.isnan(short_ma[i]) else 0,
                            long_ma=long_ma[i] if not np.isnan(long_ma[i]) else 0,
                            timestamp=ticker_data.iloc[i]['date']
                        )
                        trading_signals.append(trading_signal)
                
                results[ticker] = trading_signals
                logger.info(f"Generated {len(trading_signals)} signals for {ticker}")
        
        except Exception as e:
            logger.error(f"Error calculating signals: {str(e)}")
            raise
        
        return results
    
    def generate_report(self, signals_dict: Dict[str, List[TradingSignal]]) -> List[ProfitLossReport]:
        """Generate profit/loss report for all tickers"""
        reports = []
        
        try:
            for ticker, signals in signals_dict.items():
                if not signals:
                    continue
                
                # Convert signals to trade format for P&L calculation
                trades = [
                    {
                        'signal': signal.signal,
                        'price': signal.price,
                        'timestamp': signal.timestamp
                    }
                    for signal in signals
                ]
                
                # Calculate profit/loss
                total_pnl, winning_trades, losing_trades = calculate_profit_loss(trades)
                total_trades = winning_trades + losing_trades
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                # Create report
                report = ProfitLossReport(
                    ticker=ticker,
                    total_trades=len(signals),
                    total_profit_loss=total_pnl,
                    winning_trades=winning_trades,
                    losing_trades=losing_trades,
                    win_rate=win_rate,
                    signals=signals
                )
                
                reports.append(report)
                
                # Log summary
                logger.info(
                    f"{ticker} Summary: {len(signals)} signals, "
                    f"P&L: {format_currency(total_pnl)}, "
                    f"Win Rate: {win_rate:.1f}%"
                )
        
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise
        
        return reports
    
    def print_detailed_report(self, reports: List[ProfitLossReport]):
        """Print detailed trading report to console"""
        print("\n" + "="*80)
        print("MOVING AVERAGE CROSSOVER STRATEGY REPORT")
        print("="*80)
        print(f"Strategy Parameters:")
        print(f"  Short MA Period: {self.short_period} days")
        print(f"  Long MA Period: {self.long_period} days")
        print()
        
        total_pnl_all = 0
        total_signals_all = 0
        
        for report in reports:
            print(f"📊 {report.ticker}")
            print(f"  Total Signals: {report.total_trades}")
            print(f"  Profit/Loss: {format_currency(report.total_profit_loss)}")
            print(f"  Winning Trades: {report.winning_trades}")
            print(f"  Losing Trades: {report.losing_trades}")
            print(f"  Win Rate: {report.win_rate:.1f}%")
            print()
            
            # Show recent signals
            if report.signals:
                print(f"  Recent Signals:")
                for signal in report.signals[-5:]:  # Show last 5 signals
                    ma_info = f"MA({self.short_period})={signal.short_ma:.2f}, MA({self.long_period})={signal.long_ma:.2f}"
                    print(f"    {signal.timestamp.strftime('%Y-%m-%d')}: {signal.signal} at ${signal.price:.2f} ({ma_info})")
                print()
            
            total_pnl_all += report.total_profit_loss
            total_signals_all += report.total_trades
        
        print("="*80)
        print("OVERALL SUMMARY")
        print("="*80)
        print(f"Total Tickers: {len(reports)}")
        print(f"Total Signals: {total_signals_all}")
        print(f"Total P&L: {format_currency(total_pnl_all)}")
        print("="*80)
    
    def run_strategy(self, csv_file: str = "sample_historical_data.csv") -> List[ProfitLossReport]:
        """Run the complete trading strategy"""
        try:
            logger.info("Starting Moving Average Crossover Strategy...")
            
            # Load historical data
            df = self.load_historical_data(csv_file)
            
            # Calculate signals
            signals_dict = self.calculate_signals(df)
            
            # Generate reports
            reports = self.generate_report(signals_dict)
            
            # Print detailed report
            self.print_detailed_report(reports)
            
            return reports
            
        except Exception as e:
            logger.error(f"Error running strategy: {str(e)}")
            raise

def main():
    """Main function to run the trading strategy"""
    try:
        strategy = MovingAverageCrossoverStrategy()
        reports = strategy.run_strategy()
        
        print(f"\n✅ Strategy completed successfully!")
        print(f"📈 Analyzed {len(reports)} tickers")
        
    except FileNotFoundError:
        print("❌ Error: sample_historical_data.csv not found!")
        print("Please ensure the CSV file exists with columns: ticker, date, price")
    except Exception as e:
        print(f"❌ Error running strategy: {str(e)}")

if __name__ == "__main__":
    main()
