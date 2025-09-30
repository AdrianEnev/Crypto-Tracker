#!/usr/bin/env python3
"""
Paper Trading Wrapper

A simple wrapper around the real trading script that:
1. Uses the real script (src/tracker/core.py) with all its strategies, ML, risk management
2. Intercepts execution calls and replaces them with paper trading simulation
3. Provides enhanced testing capabilities (faster execution, better reporting)
4. Keeps everything else exactly the same
"""

import asyncio
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.tracker.core import CryptoTracker
from src.order_manager.models import OrderRequest, OrderType, TimeInForce


class PaperExecutionSimulator:
    """Simulates execution without real API calls."""
    
    def __init__(self, initial_cash: float = 100000.0):
        self.cash = initial_cash
        self.positions: Dict[str, float] = {}  # symbol -> quantity
        self.trades = []
        self.fee_rate = 0.001  # 0.1% fee
        
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
                    "order_id": f"paper_{int(time.time())}"
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
                    "order_id": f"paper_{int(time.time())}"
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
            "order_id": f"paper_{int(time.time())}"
        }
        self.trades.append(trade)
        
        return {
            "status": "filled",
            "order_id": trade["order_id"],
            "filled_quantity": abs(order.quantity),
            "filled_price": order.price,
            "fee": fee
        }
    
    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value."""
        total = self.cash
        for symbol, quantity in self.positions.items():
            if symbol in prices:
                total += quantity * prices[symbol]
        return total
    
    def get_performance_summary(self, prices: Dict[str, float]) -> Dict[str, Any]:
        """Get performance summary."""
        current_value = self.get_portfolio_value(prices)
        initial_cash = 100000.0  # TODO: make this configurable
        
        total_trades = len(self.trades)
        winning_trades = 0
        total_pnl = 0.0
        
        # Simple P&L calculation (could be more sophisticated)
        for trade in self.trades:
            if trade["side"] == "sell":
                # Find corresponding buy trade (simplified)
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


class PaperTradingWrapper:
    """Wrapper around the real trading script for paper trading."""
    
    def __init__(self, config_path: str, initial_cash: float = 100000.0):
        self.config_path = config_path
        self.initial_cash = initial_cash
        self.execution_simulator = PaperExecutionSimulator(initial_cash)
        self.tracker: Optional[CryptoTracker] = None
        self.is_running = False
        
    async def initialize(self):
        """Initialize the real tracker with paper execution."""
        print(f"🚀 Initializing Paper Trading Wrapper")
        print(f"📁 Config: {self.config_path}")
        print(f"💰 Initial Cash: ${self.initial_cash:,.2f}")
        
        # Initialize the real tracker
        self.tracker = CryptoTracker(self.config_path)
        
        # Replace the execution manager with our paper simulator
        self._patch_execution_manager()
        
        print("✅ Initialization complete")
    
    def _patch_execution_manager(self):
        """Patch the execution manager to use paper trading."""
        
        # Store original methods
        original_execute_buy = self.tracker.execution_manager.execute_buy_order
        original_execute_sell = self.tracker.execution_manager.execute_sell_order
        
        def paper_execute_buy(symbol: str, price: float, size_usd: float, **kwargs) -> Dict[str, Any]:
            """Paper trading version of execute_buy_order."""
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
        
        def paper_execute_sell(symbol: str, price: float, quantity: float, **kwargs) -> Dict[str, Any]:
            """Paper trading version of execute_sell_order."""
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
        self.tracker.execution_manager.execute_buy_order = paper_execute_buy
        self.tracker.execution_manager.execute_sell_order = paper_execute_sell
        
        print("🔧 Patched execution manager for paper trading")
    
    async def run_simulation(self, duration_minutes: int = 60, speed_multiplier: float = 1.0):
        """Run the simulation."""
        print(f"🎯 Starting simulation for {duration_minutes} minutes at {speed_multiplier}x speed")
        
        self.is_running = True
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60 / speed_multiplier)
        
        # Enable auto trading for the simulation
        self.tracker.execution_manager.auto_trade_enable = True
        
        try:
            while self.is_running and time.time() < end_time:
                # Let the real tracker do its thing
                self.tracker.check_all_prices()
                
                # Print periodic updates
                if int(time.time()) % 30 == 0:  # Every 30 seconds
                    self._print_status_update()
                
                # Sleep based on speed multiplier
                await asyncio.sleep(1.0 / speed_multiplier)
                
        except KeyboardInterrupt:
            print("\n🛑 Simulation interrupted by user")
        finally:
            self.is_running = False
            self.tracker.execution_manager.auto_trade_enable = False
            self._print_final_summary()
    
    def _print_status_update(self):
        """Print periodic status update."""
        # Get current prices (simplified - in real implementation, get from tracker)
        prices = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0}  # Placeholder
        
        portfolio_value = self.execution_simulator.get_portfolio_value(prices)
        print(f"📊 Portfolio Value: ${portfolio_value:,.2f} | Cash: ${self.execution_simulator.cash:,.2f} | Positions: {len(self.execution_simulator.positions)}")
    
    def _print_final_summary(self):
        """Print final performance summary."""
        print("\n" + "="*60)
        print("📊 FINAL PERFORMANCE SUMMARY")
        print("="*60)
        
        # Get current prices (simplified)
        prices = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0}  # Placeholder
        summary = self.execution_simulator.get_performance_summary(prices)
        
        print(f"💰 Initial Cash: ${summary['initial_cash']:,.2f}")
        print(f"💰 Current Value: ${summary['current_value']:,.2f}")
        print(f"📈 Total Return: {summary['total_return_pct']:.2f}%")
        print(f"🔄 Total Trades: {summary['total_trades']}")
        print(f"🎯 Win Rate: {summary['win_rate_pct']:.1f}%")
        print(f"💵 Net P&L: ${summary['total_pnl']:,.2f}")
        print(f"💵 Cash: ${summary['cash']:,.2f}")
        print(f"📦 Positions: {summary['positions']}")
        print("="*60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Paper Trading Wrapper - Real Script with Fake Money")
    
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Initial cash amount")
    parser.add_argument("--duration", type=int, default=60, help="Simulation duration in minutes")
    parser.add_argument("--speed", type=float, default=1.0, help="Speed multiplier (1.0 = real-time)")
    parser.add_argument("--mode", choices=["live", "replay"], default="live", help="Trading mode")
    
    args = parser.parse_args()
    
    async def run():
        wrapper = PaperTradingWrapper(args.config, args.initial_cash)
        await wrapper.initialize()
        
        if args.mode == "live":
            await wrapper.run_simulation(args.duration, args.speed)
        else:
            print("Replay mode not implemented yet - use live mode")
            await wrapper.run_simulation(args.duration, args.speed)
    
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
