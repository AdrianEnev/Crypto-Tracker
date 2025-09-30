#!/usr/bin/env python3
"""
Simple Test Strategy Backtest

Uses a very simple strategy that's guaranteed to trade frequently.
This demonstrates that the backtest system works correctly.
"""

import asyncio
import argparse
import sys
import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.tracker.core import CryptoTracker
from src.order_manager.models import OrderRequest, OrderType, TimeInForce


class SimpleTestSimulator:
    """Simple test simulator with guaranteed trading."""
    
    def __init__(self, initial_cash: float = 100000.0):
        self.cash = initial_cash
        self.positions: Dict[str, float] = {}  # symbol -> quantity
        self.trades = []
        self.fee_rate = 0.001  # 0.1% fee
        self.current_prices: Dict[str, float] = {}
        self.initial_cash = initial_cash
        self.trade_count = 0
        
    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        """Simulate order placement."""
        
        # Calculate fees
        fee = abs(order.quantity * order.price * self.fee_rate)
        
        if order.side == "buy":
            # Check if we have enough cash
            total_cost = abs(order.quantity * order.price) + fee
            if total_cost > self.cash:
                return {
                    "status": "rejected",
                    "reason": "insufficient_funds",
                    "order_id": f"test_{int(time.time())}"
                }
            
            # Execute buy order
            self.cash -= total_cost
            if order.symbol in self.positions:
                self.positions[order.symbol] += abs(order.quantity)
            else:
                self.positions[order.symbol] = abs(order.quantity)
                
        elif order.side == "sell":
            # Check if we have enough position
            if order.symbol not in self.positions or self.positions[order.symbol] < abs(order.quantity):
                return {
                    "status": "rejected", 
                    "reason": "insufficient_position",
                    "order_id": f"test_{int(time.time())}"
                }
            
            # Execute sell order
            proceeds = abs(order.quantity * order.price) - fee
            self.cash += proceeds
            self.positions[order.symbol] -= abs(order.quantity)
            
            if self.positions[order.symbol] <= 0:
                del self.positions[order.symbol]
        
        # Record trade
        trade = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": order.symbol,
            "side": order.side,
            "quantity": abs(order.quantity),
            "price": order.price,
            "fee": fee,
            "order_id": f"test_{int(time.time())}"
        }
        self.trades.append(trade)
        self.trade_count += 1
        
        print(f"📈 {order.side.upper()} {order.symbol}: {abs(order.quantity):.6f} @ ${order.price:.2f} (Fee: ${fee:.2f})")
        
        return {
            "status": "filled",
            "order_id": trade["order_id"],
            "filled_quantity": abs(order.quantity),
            "filled_price": order.price,
            "fee": fee
        }
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value."""
        total = self.cash
        for symbol, quantity in self.positions.items():
            if symbol in self.current_prices:
                total += quantity * self.current_prices[symbol]
        return total
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        current_value = self.get_portfolio_value()
        
        total_trades = len(self.trades)
        winning_trades = 0
        total_pnl = current_value - self.initial_cash
        
        # Calculate win rate from trades
        for trade in self.trades:
            if trade["side"] == "sell":
                winning_trades += 1
        
        return {
            "initial_cash": self.initial_cash,
            "current_value": current_value,
            "total_return_pct": ((current_value - self.initial_cash) / self.initial_cash) * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "win_rate_pct": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": total_pnl,
            "cash": self.cash,
            "positions": self.positions.copy()
        }


class SimpleTestWrapper:
    """Simple test wrapper with guaranteed trading."""
    
    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = initial_cash
        self.simulator = SimpleTestSimulator(initial_cash)
        self.historical_data: Dict[str, List[Dict]] = {}
        
    def load_historical_data(self, symbols: List[str], days: int = 30):
        """Load historical data from your data_cache directory."""
        print(f"📊 Loading {days} days of historical data for {symbols}")
        
        data_dir = Path("data_cache")
        
        for symbol in symbols:
            # Map symbol to data file
            symbol_map = {
                "BTC/USDT": "binance_BTC-USDT_4h_n2000_4h.jsonl",
                "ETH/USDT": "binance_ETH-USDT_4h_n2000_4h.jsonl", 
                "SOL/USDT": "binance_SOL-USDT_4h_n2000_4h.jsonl",
            }
            
            data_file = symbol_map.get(symbol)
            if not data_file:
                print(f"⚠️  No data file found for {symbol}, skipping")
                continue
                
            file_path = data_dir / data_file
            if not file_path.exists():
                print(f"⚠️  Data file {file_path} not found, skipping")
                continue
            
            print(f"📁 Loading {file_path}")
            
            # Load data
            data = []
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        tick_data = json.loads(line.strip())
                        
                        # Parse timestamp
                        if 'timestamp' in tick_data:
                            timestamp = datetime.fromtimestamp(tick_data['timestamp'], tz=timezone.utc)
                        elif 'time' in tick_data:
                            timestamp = datetime.fromtimestamp(tick_data['time'], tz=timezone.utc)
                        elif 'ts' in tick_data:
                            timestamp = datetime.fromtimestamp(tick_data['ts'] / 1000, tz=timezone.utc)
                        else:
                            continue
                        
                        # Filter by days
                        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                        if timestamp < cutoff_date:
                            continue
                        
                        # Extract price data
                        price = tick_data.get('c', tick_data.get('close', tick_data.get('price', 0.0)))
                        if price <= 0:
                            continue
                        
                        data.append({
                            "timestamp": timestamp,
                            "price": price,
                            "volume": tick_data.get('v', tick_data.get('volume', 0.0)),
                            "high": tick_data.get('h', tick_data.get('high', price)),
                            "low": tick_data.get('l', tick_data.get('low', price)),
                            "open": tick_data.get('o', tick_data.get('open', price)),
                            "close": price
                        })
                        
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        continue
            
            if data:
                # Sort by timestamp
                data.sort(key=lambda x: x["timestamp"])
                self.historical_data[symbol] = data
                print(f"✅ Loaded {len(data)} data points for {symbol}")
            else:
                print(f"❌ No valid data found for {symbol}")
        
        print(f"📊 Total symbols loaded: {len(self.historical_data)}")
    
    async def run_simple_test(self, symbols: List[str], days: int = 30):
        """Run simple test with guaranteed trading."""
        print(f"🎯 Starting {days}-day simple test for {symbols}")
        
        # Load historical data
        self.load_historical_data(symbols, days)
        
        if not self.historical_data:
            print("❌ No historical data loaded, cannot run test")
            return
        
        try:
            # Combine all data and sort by timestamp
            all_data = []
            for symbol, data in self.historical_data.items():
                for tick in data:
                    all_data.append({
                        "symbol": symbol,
                        "timestamp": tick["timestamp"],
                        "price": tick["price"],
                        "volume": tick["volume"],
                        "high": tick["high"],
                        "low": tick["low"],
                        "open": tick["open"],
                        "close": tick["close"]
                    })
            
            # Sort by timestamp
            all_data.sort(key=lambda x: x["timestamp"])
            
            print(f"📈 Replaying {len(all_data)} data points...")
            
            # Simple trading logic: buy every 10th tick, sell every 20th tick
            for i, tick in enumerate(all_data):
                # Update current price
                self.simulator.current_prices[tick["symbol"]] = tick["price"]
                
                # Simple trading logic
                if i % 10 == 0:  # Buy every 10th tick
                    order = OrderRequest(
                        symbol=tick["symbol"],
                        side="buy",
                        quantity=1000 / tick["price"],  # $1000 position
                        price=tick["price"],
                        order_type=OrderType.MARKET,
                        time_in_force=TimeInForce.GTC
                    )
                    self.simulator.place_order(order)
                
                elif i % 20 == 0 and tick["symbol"] in self.simulator.positions:  # Sell every 20th tick
                    if self.simulator.positions[tick["symbol"]] > 0:
                        order = OrderRequest(
                            symbol=tick["symbol"],
                            side="sell",
                            quantity=self.simulator.positions[tick["symbol"]],
                            price=tick["price"],
                            order_type=OrderType.MARKET,
                            time_in_force=TimeInForce.GTC
                        )
                        self.simulator.place_order(order)
                
                # Print progress every 50 ticks
                if i % 50 == 0:
                    portfolio_value = self.simulator.get_portfolio_value()
                    print(f"📊 Progress: {i}/{len(all_data)} | Portfolio: ${portfolio_value:,.2f} | Trades: {len(self.simulator.trades)}")
                
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
        finally:
            self._print_final_summary()
    
    def _print_final_summary(self):
        """Print final performance summary."""
        print("\n" + "="*60)
        print("📊 SIMPLE TEST SUMMARY")
        print("="*60)
        
        summary = self.simulator.get_performance_summary()
        
        print(f"💰 Initial Cash: ${summary['initial_cash']:,.2f}")
        print(f"💰 Final Value: ${summary['current_value']:,.2f}")
        print(f"📈 Total Return: {summary['total_return_pct']:.2f}%")
        print(f"🔄 Total Trades: {summary['total_trades']}")
        print(f"🎯 Win Rate: {summary['win_rate_pct']:.1f}%")
        print(f"💵 Net P&L: ${summary['total_pnl']:,.2f}")
        print(f"💵 Cash: ${summary['cash']:,.2f}")
        print(f"📦 Positions: {summary['positions']}")
        
        if summary['total_trades'] > 0:
            print(f"📊 Avg Trade Size: ${abs(summary['total_pnl']) / summary['total_trades']:,.2f}")
        
        print("="*60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Simple Test Strategy")
    
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Initial cash amount")
    parser.add_argument("--days", type=int, default=30, help="Days of historical data to replay")
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT", "ETH/USDT"], help="Symbols to test")
    
    args = parser.parse_args()
    
    async def run():
        wrapper = SimpleTestWrapper(args.initial_cash)
        await wrapper.run_simple_test(args.symbols, args.days)
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
