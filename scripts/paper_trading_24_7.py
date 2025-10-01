#!/usr/bin/env python3
"""
24/7 Paper Trading System

A robust paper trading system designed to run continuously for weeks/months.
Includes monitoring, logging, error recovery, and automatic restarts.
"""

import asyncio
import argparse
import sys
import time
import json
import signal
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.tracker.core import CryptoTracker
from src.order_manager.models import OrderRequest, OrderType, TimeInForce


class PaperTradingSimulator:
    """Robust paper trading simulator for 24/7 operation."""
    
    def __init__(self, initial_cash: float = 100000.0):
        self.cash = initial_cash
        self.positions: Dict[str, float] = {}  # symbol -> quantity
        self.trades = []
        self.fee_rate = 0.001  # 0.1% fee
        self.current_prices: Dict[str, float] = {}
        self.initial_cash = initial_cash
        self.trade_count = 0
        self.start_time = datetime.now(timezone.utc)
        
    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        """Simulate order placement with robust error handling."""
        try:
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
            self.trade_count += 1
            
            # Log trade
            logging.info(f"TRADE: {order.side.upper()} {order.symbol} {abs(order.quantity):.6f} @ ${order.price:.2f} (Fee: ${fee:.2f})")
            
            return {
                "status": "filled",
                "order_id": trade["order_id"],
                "filled_quantity": abs(order.quantity),
                "filled_price": order.price,
                "fee": fee
            }
            
        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "order_id": f"paper_error_{int(time.time())}"
            }
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value."""
        total = self.cash
        for symbol, quantity in self.positions.items():
            if symbol in self.current_prices:
                total += quantity * self.current_prices[symbol]
        return total
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        current_value = self.get_portfolio_value()
        runtime_hours = (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
        
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
            "positions": self.positions.copy(),
            "runtime_hours": runtime_hours,
            "trades_per_hour": total_trades / runtime_hours if runtime_hours > 0 else 0,
            "start_time": self.start_time.isoformat(),
            "current_time": datetime.now(timezone.utc).isoformat()
        }


class PaperTrading24_7:
    """24/7 Paper Trading System with monitoring and error recovery."""
    
    def __init__(self, config_path: str, initial_cash: float = 100000.0, enable_social: bool = False):
        self.config_path = config_path
        self.initial_cash = initial_cash
        self.simulator = PaperTradingSimulator(initial_cash)
        self.tracker: Optional[CryptoTracker] = None
        self.is_running = False
        self.restart_count = 0
        self.max_restarts = 10
        self.last_heartbeat = datetime.now(timezone.utc)
        self.heartbeat_interval = 300  # 5 minutes
        
        # Social media integration
        self.enable_social = enable_social
        self.enhanced_decision_engine = None
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup comprehensive logging for 24/7 operation."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"paper_trading_24_7_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logging.info(f"Starting 24/7 Paper Trading System")
        logging.info(f"Config: {self.config_path}")
        logging.info(f"Initial Cash: ${self.initial_cash:,.2f}")
        logging.info(f"Log file: {log_file}")
    
    async def initialize(self):
        """Initialize the trading system with error recovery."""
        try:
            logging.info("Initializing CryptoTracker...")
            self.tracker = CryptoTracker(self.config_path)
            
            # Patch execution manager
            self._patch_execution_manager()
            
            # Disable API calls for paper trading
            self._disable_api_calls()
            
            # Initialize social media integration if enabled
            if self.enable_social:
                await self._initialize_social_media()
            
            logging.info("✅ Initialization complete")
            return True
            
        except Exception as e:
            logging.error(f"❌ Initialization failed: {e}")
            logging.error(traceback.format_exc())
            return False
    
    async def _initialize_social_media(self):
        """Initialize social media integration for enhanced decisions."""
        try:
            logging.info("Initializing Enhanced Decision Engine with Social Media...")
            
            from src.social_media.example_integration import EnhancedDecisionEngine
            self.enhanced_decision_engine = EnhancedDecisionEngine(self.config_path)
            
            logging.info("✅ Social media integration enabled")
            
        except Exception as e:
            logging.error(f"❌ Social media initialization failed: {e}")
            logging.error(traceback.format_exc())
            # Disable social media if initialization fails
            self.enable_social = False
            self.enhanced_decision_engine = None
    
    def _patch_execution_manager(self):
        """Patch the execution manager with correct function signatures."""
        
        def paper_execute_buy(symbol: str, price: float, size_usd: float, **kwargs) -> Dict[str, Any]:
            """Paper trading version of execute_buy_order."""
            try:
                quantity = size_usd / price
                order = OrderRequest(
                    symbol=symbol,
                    side="buy",
                    quantity=quantity,
                    price=price,
                    order_type=OrderType.MARKET,
                    time_in_force=TimeInForce.GTC
                )
                return self.simulator.place_order(order)
            except Exception as e:
                logging.error(f"Error in paper_execute_buy: {e}")
                return {"status": "error", "reason": str(e)}
        
        def paper_execute_sell(symbol: str, price: float, quantity: float, **kwargs) -> Dict[str, Any]:
            """Paper trading version of execute_sell_order."""
            try:
                order = OrderRequest(
                    symbol=symbol,
                    side="sell",
                    quantity=quantity,
                    price=price,
                    order_type=OrderType.MARKET,
                    time_in_force=TimeInForce.GTC
                )
                return self.simulator.place_order(order)
            except Exception as e:
                logging.error(f"Error in paper_execute_sell: {e}")
                return {"status": "error", "reason": str(e)}
        
        # Replace the methods
        self.tracker.execution_manager.execute_buy_order = paper_execute_buy
        self.tracker.execution_manager.execute_sell_order = paper_execute_sell
        
        logging.info("🔧 Patched execution manager for paper trading")
    
    def _disable_api_calls(self):
        """Disable all API calls to prevent rate limits."""
        try:
            # Disable price providers
            if hasattr(self.tracker, 'price_providers'):
                for provider in self.tracker.price_providers.values():
                    if hasattr(provider, 'enabled'):
                        provider.enabled = False
            
            # Disable market data API calls
            if hasattr(self.tracker, 'market_data_adapter'):
                if hasattr(self.tracker.market_data_adapter, 'enabled'):
                    self.tracker.market_data_adapter.enabled = False
            
            logging.info("🚫 Disabled all API calls for paper trading")
        except Exception as e:
            logging.warning(f"Could not disable API calls: {e}")
    
    async def _make_enhanced_decisions(self):
        """Make trading decisions using enhanced decision engine with social media."""
        try:
            decisions = {}  # Collect all decisions for batch display
            
            for coin_id, coin_config in self.tracker.config.tracked_coins.items():
                if coin_config.disabled:
                    continue
                
                try:
                    # Get enhanced decision with social media
                    decision = await self.enhanced_decision_engine.make_enhanced_decision(self.tracker, coin_id)
                    
                    # Log decision with social context
                    social_info = ""
                    if hasattr(decision, 'social_context'):
                        social_info = f" | Social: {decision.social_context}"
                    
                    logging.info(f"ENHANCED DECISION: {coin_id} -> {decision.action_recommended} (Confidence: {decision.confidence:.3f}){social_info}")
                    
                    # Collect decision for batch display (same format as standard decisions)
                    decisions[coin_id] = {
                        "signal": getattr(decision, 'signal', 'unknown'),
                        "confidence": getattr(decision, 'confidence', 0.0),
                        "action": getattr(decision, 'action_recommended', 'Hold'),
                        "reason": getattr(decision, 'reason', 'Enhanced decision with social media'),
                    }
                    
                except Exception as e:
                    logging.error(f"Error making enhanced decision for {coin_id}: {e}")
                    # Fallback to base decision if enhanced fails
                    try:
                        from src.decision import make_decision
                        base_decision = make_decision(self.tracker, coin_id)
                        decisions[coin_id] = {
                            "signal": getattr(base_decision, 'signal', 'unknown'),
                            "confidence": getattr(base_decision, 'confidence', 0.0),
                            "action": getattr(base_decision, 'action_recommended', 'Hold'),
                            "reason": getattr(base_decision, 'reason', 'Fallback base decision'),
                        }
                        logging.info(f"FALLBACK DECISION: {coin_id} -> {base_decision.action_recommended} (Confidence: {base_decision.confidence:.3f})")
                    except Exception as fallback_error:
                        logging.error(f"Fallback decision also failed for {coin_id}: {fallback_error}")
                        # Last resort - create a basic decision
                        decisions[coin_id] = {
                            "signal": "error",
                            "confidence": 0.0,
                            "action": "Hold",
                            "reason": f"Decision failed: {e}",
                        }
            
            # Display all decisions together (same as standard check_all_prices)
            if decisions and self.tracker.display_manager:
                self.tracker.display_manager.display_decisions(decisions)
            else:
                logging.warning("No decisions to display or display manager not available")
                    
        except Exception as e:
            logging.error(f"Error in enhanced decision making: {e}")
            # Fallback to standard decision making
            logging.info("Falling back to standard decision making...")
            self.tracker.check_all_prices()
    
    async def run_24_7(self, check_interval: int = 300):
        """Run the paper trading system 24/7 with monitoring."""
        logging.info(f"🚀 Starting 24/7 paper trading (check interval: {check_interval}s)")
        
        self.is_running = True
        self.tracker.execution_manager.auto_trade_enable = True
        
        try:
            while self.is_running:
                try:
                    # Update current prices (mock for paper trading)
                    self._update_mock_prices()
                    
                    # Let the tracker make decisions
                    if self.enable_social and self.enhanced_decision_engine:
                        await self._make_enhanced_decisions()
                    else:
                        self.tracker.check_all_prices()
                    
                    # Heartbeat logging
                    if (datetime.now(timezone.utc) - self.last_heartbeat).total_seconds() > self.heartbeat_interval:
                        self._log_heartbeat()
                        self.last_heartbeat = datetime.now(timezone.utc)
                    
                    # Wait for next check
                    await asyncio.sleep(check_interval)
                    
                except Exception as e:
                    logging.error(f"Error in main trading loop: {e}")
                    logging.error(traceback.format_exc())
                    
                    # Try to recover
                    if self.restart_count < self.max_restarts:
                        self.restart_count += 1
                        logging.warning(f"Attempting restart #{self.restart_count}")
                        await asyncio.sleep(60)  # Wait 1 minute before restart
                    else:
                        logging.error("Max restarts reached, stopping")
                        break
                    
        except KeyboardInterrupt:
            logging.info("🛑 Received interrupt signal")
        except Exception as e:
            logging.error(f"Fatal error in 24/7 loop: {e}")
            logging.error(traceback.format_exc())
        finally:
            self.is_running = False
            self.tracker.execution_manager.auto_trade_enable = False
            self._log_final_summary()
    
    def _update_mock_prices(self):
        """Update mock prices for paper trading."""
        # Simple mock price updates (in real implementation, you'd use historical data)
        base_prices = {
            "BTC/USDT": 50000,
            "ETH/USDT": 3000,
            "SOL/USDT": 100
        }
        
        for symbol, base_price in base_prices.items():
            # Add some random variation
            import random
            variation = random.uniform(0.95, 1.05)
            self.simulator.current_prices[symbol] = base_price * variation
    
    def _log_heartbeat(self):
        """Log system heartbeat with current status."""
        summary = self.simulator.get_performance_summary()
        
        logging.info("💓 HEARTBEAT")
        logging.info(f"   Runtime: {summary['runtime_hours']:.1f} hours")
        logging.info(f"   Portfolio: ${summary['current_value']:,.2f}")
        logging.info(f"   Return: {summary['total_return_pct']:.2f}%")
        logging.info(f"   Trades: {summary['total_trades']}")
        logging.info(f"   Trades/hour: {summary['trades_per_hour']:.2f}")
        logging.info(f"   Positions: {len(summary['positions'])}")
        logging.info(f"   Restarts: {self.restart_count}")
    
    def _log_final_summary(self):
        """Log final performance summary."""
        logging.info("\n" + "="*60)
        logging.info("📊 24/7 PAPER TRADING FINAL SUMMARY")
        logging.info("="*60)
        
        summary = self.simulator.get_performance_summary()
        
        logging.info(f"💰 Initial Cash: ${summary['initial_cash']:,.2f}")
        logging.info(f"💰 Final Value: ${summary['current_value']:,.2f}")
        logging.info(f"📈 Total Return: {summary['total_return_pct']:.2f}%")
        logging.info(f"🔄 Total Trades: {summary['total_trades']}")
        logging.info(f"🎯 Win Rate: {summary['win_rate_pct']:.1f}%")
        logging.info(f"💵 Net P&L: ${summary['total_pnl']:,.2f}")
        logging.info(f"💵 Cash: ${summary['cash']:,.2f}")
        logging.info(f"📦 Positions: {summary['positions']}")
        logging.info(f"⏱️  Runtime: {summary['runtime_hours']:.1f} hours")
        logging.info(f"📊 Trades/Hour: {summary['trades_per_hour']:.2f}")
        logging.info(f"🔄 Restarts: {self.restart_count}")
        logging.info(f"📅 Start Time: {summary['start_time']}")
        logging.info(f"📅 End Time: {summary['current_time']}")
        logging.info("="*60)
    
    def stop(self):
        """Stop the 24/7 trading system."""
        logging.info("🛑 Stopping 24/7 paper trading system")
        self.is_running = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    if 'paper_system' in globals():
        paper_system.stop()
    sys.exit(0)


def main():
    """Main CLI entry point for 24/7 paper trading."""
    parser = argparse.ArgumentParser(description="24/7 Paper Trading System")
    
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Initial cash amount")
    parser.add_argument("--check-interval", type=int, default=300, help="Check interval in seconds (default: 5 minutes)")
    parser.add_argument("--max-restarts", type=int, default=10, help="Maximum restart attempts")
    parser.add_argument("--enable-social", action="store_true", help="Enable social media integration for enhanced decisions")
    parser.add_argument("--disable-social", action="store_true", help="Disable social media integration (use standard decisions only)")
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    async def run():
        global paper_system
        
        # Determine social media setting
        enable_social = args.enable_social and not args.disable_social
        
        paper_system = PaperTrading24_7(args.config, args.initial_cash, enable_social)
        paper_system.max_restarts = args.max_restarts
        
        # Initialize
        if not await paper_system.initialize():
            logging.error("Failed to initialize, exiting")
            return
        
        # Run 24/7
        await paper_system.run_24_7(args.check_interval)
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        logging.error(traceback.format_exc())


if __name__ == "__main__":
    main()
