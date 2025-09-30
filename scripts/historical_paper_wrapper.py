#!/usr/bin/env python3
"""
Historical Paper Trading Wrapper

Replays historical market data to test strategies over realistic timeframes.
This addresses the issue that crypto strategies work on days/weeks, not minutes.
"""

import asyncio
import argparse
import sys
import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.tracker.core import CryptoTracker
from src.order_manager.models import OrderRequest, OrderType, TimeInForce


class HistoricalExecutionSimulator:
    """Simulates execution with historical data replay."""
    
    def __init__(self, initial_cash: float = 100000.0):
        self.cash = initial_cash
        self.positions: Dict[str, float] = {}  # symbol -> quantity
        self.trades = []
        self.fee_rate = 0.001  # 0.1% fee
        self.current_prices: Dict[str, float] = {}
        
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
                    "order_id": f"hist_{int(time.time())}"
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
                    "order_id": f"hist_{int(time.time())}"
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
            "order_id": f"hist_{int(time.time())}"
        }
        self.trades.append(trade)
        
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
        initial_cash = 100000.0  # TODO: make this configurable
        
        total_trades = len(self.trades)
        winning_trades = 0
        total_pnl = 0.0
        
        # Simple P&L calculation
        for trade in self.trades:
            if trade["side"] == "sell":
                total_pnl += trade["quantity"] * trade["price"] - trade["fee"]
                winning_trades += 1
        
        return {
            "initial_cash": initial_cash,
            "current_value": current_value,
            "total_return_pct": ((current_value - initial_cash) / initial_cash) * 100,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "win_rate_pct": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": current_value - initial_cash,
            "cash": self.cash,
            "positions": self.positions.copy()
        }


class HistoricalPaperWrapper:
    """Historical replay wrapper around the real trading script."""
    
    def __init__(self, config_path: str, initial_cash: float = 100000.0):
        self.config_path = config_path
        self.initial_cash = initial_cash
        self.execution_simulator = HistoricalExecutionSimulator(initial_cash)
        self.tracker: Optional[CryptoTracker] = None
        self.historical_data: Dict[str, List[Dict]] = {}
        
    async def initialize(self):
        """Initialize the real tracker with historical data."""
        print(f"🚀 Initializing Historical Paper Trading Wrapper")
        print(f"📁 Config: {self.config_path}")
        print(f"💰 Initial Cash: ${self.initial_cash:,.2f}")
        
        # Initialize the real tracker
        self.tracker = CryptoTracker(self.config_path)
        
        # Replace the execution manager with our historical simulator
        self._patch_execution_manager()
        
        print("✅ Initialization complete")
    
    def _patch_execution_manager(self):
        """Patch the execution manager to use historical simulation."""
        
        # Store original methods
        original_execute_buy = self.tracker.execution_manager.execute_buy_order
        original_execute_sell = self.tracker.execution_manager.execute_sell_order
        
        def hist_execute_buy(symbol: str, price: float, size_usd: float, **kwargs) -> Dict[str, Any]:
            """Historical trading version of execute_buy_order."""
            quantity = size_usd / price
            order = OrderRequest(
                symbol=symbol,
                side="buy",
                quantity=quantity,
                price=price,
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC
            )
            result = self.execution_simulator.place_order(order)
            
            if result["status"] == "filled":
                print(f"📈 BUY {symbol}: {quantity:.6f} @ ${price:.2f} (Fee: ${result['fee']:.2f})")
            else:
                print(f"❌ Buy order rejected: {result['reason']}")
            
            return result
        
        def hist_execute_sell(symbol: str, price: float, quantity: float, **kwargs) -> Dict[str, Any]:
            """Historical trading version of execute_sell_order."""
            order = OrderRequest(
                symbol=symbol,
                side="sell",
                quantity=quantity,
                price=price,
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC
            )
            result = self.execution_simulator.place_order(order)
            
            if result["status"] == "filled":
                print(f"📉 SELL {symbol}: {quantity:.6f} @ ${price:.2f} (Fee: ${result['fee']:.2f})")
            else:
                print(f"❌ Sell order rejected: {result['reason']}")
            
            return result
        
        # Replace the methods
        self.tracker.execution_manager.execute_buy_order = hist_execute_buy
        self.tracker.execution_manager.execute_sell_order = hist_execute_sell
        
        print("🔧 Patched execution manager for historical trading")
    
    def load_historical_data(self, symbols: List[str], days: int = 30):
        """Load historical data for replay."""
        print(f"📊 Loading {days} days of historical data for {symbols}")
        
        # This would load from your data_cache directory
        # For now, we'll create mock data that shows realistic patterns
        for symbol in symbols:
            self.historical_data[symbol] = self._generate_mock_historical_data(symbol, days)
        
        print(f"✅ Loaded historical data for {len(symbols)} symbols")
    
    def _generate_mock_historical_data(self, symbol: str, days: int) -> List[Dict]:
        """Generate mock historical data with realistic patterns."""
        import random
        
        # Base prices
        base_prices = {
            "BTC/USDT": 50000,
            "ETH/USDT": 3000,
            "SOL/USDT": 100
        }
        
        base_price = base_prices.get(symbol, 100)
        data = []
        
        # Generate realistic price movements over time
        current_price = base_price
        trend = random.choice([-0.1, 0, 0.1])  # Slight trend
        
        for day in range(days):
            for hour in range(24):  # Hourly data
                # Add trend and random walk
                change = random.normalvariate(trend, 0.02)  # 2% volatility
                current_price *= (1 + change)
                
                # Add some volatility spikes
                if random.random() < 0.05:  # 5% chance of volatility spike
                    current_price *= random.uniform(0.95, 1.05)
                
                data.append({
                    "timestamp": datetime.now(timezone.utc) - timedelta(days=days-day, hours=23-hour),
                    "price": current_price,
                    "volume": random.uniform(1000, 10000),
                    "high": current_price * random.uniform(1.0, 1.02),
                    "low": current_price * random.uniform(0.98, 1.0)
                })
        
        return data
    
    async def run_historical_simulation(self, symbols: List[str], days: int = 30, speed_multiplier: float = 1000.0):
        """Run historical simulation."""
        print(f"🎯 Starting historical simulation for {days} days at {speed_multiplier}x speed")
        
        # Load historical data
        self.load_historical_data(symbols, days)
        
        # Enable auto trading
        self.tracker.execution_manager.auto_trade_enable = True
        
        try:
            # Replay historical data
            for symbol, data in self.historical_data.items():
                print(f"📈 Replaying {symbol} data...")
                
                for i, tick in enumerate(data):
                    # Update current price
                    self.execution_simulator.current_prices[symbol] = tick["price"]
                    
                    # Let the tracker make decisions
                    self.tracker.check_all_prices()
                    
                    # Print progress every 100 ticks
                    if i % 100 == 0:
                        portfolio_value = self.execution_simulator.get_portfolio_value()
                        print(f"📊 Day {i//24 + 1}: Portfolio Value: ${portfolio_value:,.2f} | Trades: {len(self.execution_simulator.trades)}")
                    
                    # Speed control
                    await asyncio.sleep(1.0 / speed_multiplier)
                    
        except KeyboardInterrupt:
            print("\n🛑 Historical simulation interrupted by user")
        finally:
            self.tracker.execution_manager.auto_trade_enable = False
            self._print_final_summary()
    
    def _print_final_summary(self):
        """Print final performance summary."""
        print("\n" + "="*60)
        print("📊 HISTORICAL SIMULATION SUMMARY")
        print("="*60)
        
        summary = self.execution_simulator.get_performance_summary()
        
        print(f"💰 Initial Cash: ${summary['initial_cash']:,.2f}")
        print(f"💰 Final Value: ${summary['current_value']:,.2f}")
        print(f"📈 Total Return: {summary['total_return_pct']:.2f}%")
        print(f"🔄 Total Trades: {summary['total_trades']}")
        print(f"🎯 Win Rate: {summary['win_rate_pct']:.1f}%")
        print(f"💵 Net P&L: ${summary['total_pnl']:,.2f}")
        print(f"💵 Cash: ${summary['cash']:,.2f}")
        print(f"📦 Positions: {summary['positions']}")
        print("="*60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Historical Paper Trading Wrapper")
    
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Initial cash amount")
    parser.add_argument("--days", type=int, default=30, help="Days of historical data to replay")
    parser.add_argument("--speed", type=float, default=1000.0, help="Speed multiplier")
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT", "ETH/USDT"], help="Symbols to test")
    
    args = parser.parse_args()
    
    async def run():
        wrapper = HistoricalPaperWrapper(args.config, args.initial_cash)
        await wrapper.initialize()
        await wrapper.run_historical_simulation(args.symbols, args.days, args.speed)
    
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
