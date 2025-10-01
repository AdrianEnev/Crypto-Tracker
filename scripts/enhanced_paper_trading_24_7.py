#!/usr/bin/env python3
"""
Enhanced 24/7 Paper Trading System with Social Media Integration

This version integrates social media signals into the paper trading system.
All social media features are configurable and can be disabled independently.
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
from src.social_media.example_integration import EnhancedDecisionEngine


class EnhancedPaperTradingSimulator:
    """Enhanced paper trading simulator with social media integration."""
    
    def __init__(self, initial_cash: float = 100000.0):
        self.cash = initial_cash
        self.positions: Dict[str, float] = {}  # symbol -> quantity
        self.trades = []
        self.fee_rate = 0.001  # 0.1% fee
        self.current_prices: Dict[str, float] = {}
        self.initial_cash = initial_cash
        self.trade_count = 0
        self.start_time = datetime.now(timezone.utc)
        
        # Social media tracking
        self.social_signals: Dict[str, Dict[str, Any]] = {}
        self.social_trades: List[Dict[str, Any]] = []
        
    def place_order(self, order: OrderRequest, social_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Simulate order placement with social media context."""
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
            
            # Record trade with social context
            trade = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": order.symbol,
                "side": order.side,
                "quantity": abs(order.quantity),
                "price": order.price,
                "fee": fee,
                "order_id": f"paper_{int(time.time())}",
                "social_context": social_context or {}
            }
            self.trades.append(trade)
            self.trade_count += 1
            
            # Log trade with social context
            social_info = ""
            if social_context:
                sms = social_context.get("sms", 0)
                sentiment = social_context.get("sentiment", 0)
                social_info = f" | SMS: {sms:.3f}, Sentiment: {sentiment:.3f}"
            
            logging.info(f"TRADE: {order.side.upper()} {order.symbol} {abs(order.quantity):.6f} @ ${order.price:.2f} (Fee: ${fee:.2f}){social_info}")
            
            return {
                "status": "filled",
                "order_id": trade["order_id"],
                "filled_quantity": abs(order.quantity),
                "filled_price": order.price,
                "fee": fee,
                "social_context": social_context
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
        """Get comprehensive performance summary including social media metrics."""
        current_value = self.get_portfolio_value()
        runtime_hours = (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
        
        total_trades = len(self.trades)
        social_trades = len([t for t in self.trades if t.get("social_context")])
        winning_trades = 0
        total_pnl = current_value - self.initial_cash
        
        # Calculate win rate from trades
        for trade in self.trades:
            if trade["side"] == "sell":
                winning_trades += 1
        
        # Calculate social media metrics
        social_metrics = self._calculate_social_metrics()
        
        return {
            "initial_cash": self.initial_cash,
            "current_value": current_value,
            "total_return_pct": ((current_value - self.initial_cash) / self.initial_cash) * 100,
            "total_trades": total_trades,
            "social_trades": social_trades,
            "social_trade_pct": (social_trades / total_trades * 100) if total_trades > 0 else 0,
            "winning_trades": winning_trades,
            "win_rate_pct": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": total_pnl,
            "cash": self.cash,
            "positions": self.positions.copy(),
            "runtime_hours": runtime_hours,
            "trades_per_hour": total_trades / runtime_hours if runtime_hours > 0 else 0,
            "start_time": self.start_time.isoformat(),
            "current_time": datetime.now(timezone.utc).isoformat(),
            "social_metrics": social_metrics
        }
    
    def _calculate_social_metrics(self) -> Dict[str, Any]:
        """Calculate social media performance metrics."""
        social_trades = [t for t in self.trades if t.get("social_context")]
        
        if not social_trades:
            return {"enabled": False, "trades": 0}
        
        # Calculate average SMS and sentiment for trades
        avg_sms = sum(t["social_context"].get("sms", 0) for t in social_trades) / len(social_trades)
        avg_sentiment = sum(t["social_context"].get("sentiment", 0) for t in social_trades) / len(social_trades)
        
        # Calculate social trade performance
        social_buy_trades = [t for t in social_trades if t["side"] == "buy"]
        social_sell_trades = [t for t in social_trades if t["side"] == "sell"]
        
        return {
            "enabled": True,
            "total_social_trades": len(social_trades),
            "social_buy_trades": len(social_buy_trades),
            "social_sell_trades": len(social_sell_trades),
            "avg_sms": avg_sms,
            "avg_sentiment": avg_sentiment,
            "social_trade_pct": (len(social_trades) / len(self.trades) * 100) if self.trades else 0
        }


class EnhancedPaperTrading24_7:
    """Enhanced 24/7 Paper Trading System with social media integration."""
    
    def __init__(self, config_path: str, initial_cash: float = 100000.0, enable_social: bool = True, 
                 verbose: bool = False, quiet: bool = False):
        self.config_path = config_path
        self.initial_cash = initial_cash
        self.enable_social = enable_social
        self.verbose = verbose
        self.quiet = quiet
        self.simulator = EnhancedPaperTradingSimulator(initial_cash)
        self.tracker: Optional[CryptoTracker] = None
        self.enhanced_decision_engine: Optional[EnhancedDecisionEngine] = None
        self.is_running = False
        self.restart_count = 0
        self.max_restarts = 10
        self.last_heartbeat = datetime.now(timezone.utc)
        self.heartbeat_interval = 300  # 5 minutes
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup comprehensive logging for 24/7 operation."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"enhanced_paper_trading_24_7_{timestamp}.log"
        
        # Configure logging based on verbosity settings
        if hasattr(self, 'verbose') and self.verbose:
            log_level = logging.DEBUG
        elif hasattr(self, 'quiet') and self.quiet:
            log_level = logging.ERROR
        else:
            log_level = logging.INFO if self.enable_social else logging.WARNING
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Reduce social media logging verbosity unless verbose mode
        if not (hasattr(self, 'verbose') and self.verbose):
            social_logger = logging.getLogger('src.social_media')
            social_logger.setLevel(logging.WARNING)
        
        logging.info(f"Starting Enhanced 24/7 Paper Trading System")
        logging.info(f"Config: {self.config_path}")
        logging.info(f"Initial Cash: ${self.initial_cash:,.2f}")
        logging.info(f"Social Media: {'Enabled' if self.enable_social else 'Disabled'}")
        logging.info(f"Log file: {log_file}")
    
    async def initialize(self):
        """Initialize the trading system with social media integration."""
        try:
            logging.info("Initializing CryptoTracker...")
            self.tracker = CryptoTracker(self.config_path)
            
            # Initialize enhanced decision engine if social media is enabled
            if self.enable_social:
                logging.info("Initializing Enhanced Decision Engine with Social Media...")
                self.enhanced_decision_engine = EnhancedDecisionEngine()
                
                # Check social media status
                social_status = self.enhanced_decision_engine.get_social_status()
                logging.info(f"Social Media Status: {social_status}")
                
                if not social_status['enabled']:
                    logging.warning("Social media integration is disabled in config")
                    logging.warning("Set 'enabled: true' in config/social_media.yaml to enable")
                    self.enable_social = False
                else:
                    logging.info("✅ Social media integration enabled")
            
            # Patch execution manager
            self._patch_execution_manager()
            
            # Disable API calls for paper trading
            self._disable_api_calls()
            
            logging.info("✅ Initialization complete")
            return True
            
        except Exception as e:
            logging.error(f"❌ Initialization failed: {e}")
            logging.error(traceback.format_exc())
            return False
    
    def _patch_execution_manager(self):
        """Patch the execution manager with social media context."""
        
        def enhanced_paper_execute_buy(symbol: str, price: float, size_usd: float, **kwargs) -> Dict[str, Any]:
            """Enhanced paper trading version with social context."""
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
                
                # Get social context if available
                social_context = None
                if self.enable_social and self.enhanced_decision_engine:
                    try:
                        # Map symbol to coin_id
                        coin_id = self._symbol_to_coin_id(symbol)
                        if coin_id:
                            social_signal = asyncio.run(self.enhanced_decision_engine.social_integration.get_social_signal(coin_id))
                            if social_signal.get('enabled', False):
                                social_context = {
                                    "sms": social_signal.get('social_features', {}).get('sms', 0),
                                    "sentiment": social_signal.get('social_features', {}).get('weighted_sentiment', 0),
                                    "volume_velocity": social_signal.get('social_features', {}).get('volume_velocity', 0),
                                    "bot_likeness": social_signal.get('social_features', {}).get('bot_likeness', 0),
                                    "validation_score": social_signal.get('validation', {}).get('validation_score', 0),
                                    "risk_level": social_signal.get('validation', {}).get('risk_level', 'unknown')
                                }
                    except Exception as e:
                        logging.warning(f"Could not get social context for {symbol}: {e}")
                
                return self.simulator.place_order(order, social_context)
            except Exception as e:
                logging.error(f"Error in enhanced_paper_execute_buy: {e}")
                return {"status": "error", "reason": str(e)}
        
        def enhanced_paper_execute_sell(symbol: str, price: float, quantity: float, **kwargs) -> Dict[str, Any]:
            """Enhanced paper trading version with social context."""
            try:
                order = OrderRequest(
                    symbol=symbol,
                    side="sell",
                    quantity=quantity,
                    price=price,
                    order_type=OrderType.MARKET,
                    time_in_force=TimeInForce.GTC
                )
                
                # Get social context if available
                social_context = None
                if self.enable_social and self.enhanced_decision_engine:
                    try:
                        coin_id = self._symbol_to_coin_id(symbol)
                        if coin_id:
                            social_signal = asyncio.run(self.enhanced_decision_engine.social_integration.get_social_signal(coin_id))
                            if social_signal.get('enabled', False):
                                social_context = {
                                    "sms": social_signal.get('social_features', {}).get('sms', 0),
                                    "sentiment": social_signal.get('social_features', {}).get('weighted_sentiment', 0),
                                    "volume_velocity": social_signal.get('social_features', {}).get('volume_velocity', 0),
                                    "bot_likeness": social_signal.get('social_features', {}).get('bot_likeness', 0),
                                    "validation_score": social_signal.get('validation', {}).get('validation_score', 0),
                                    "risk_level": social_signal.get('validation', {}).get('risk_level', 'unknown')
                                }
                    except Exception as e:
                        logging.warning(f"Could not get social context for {symbol}: {e}")
                
                return self.simulator.place_order(order, social_context)
            except Exception as e:
                logging.error(f"Error in enhanced_paper_execute_sell: {e}")
                return {"status": "error", "reason": str(e)}
        
        # Replace the methods
        self.tracker.execution_manager.execute_buy_order = enhanced_paper_execute_buy
        self.tracker.execution_manager.execute_sell_order = enhanced_paper_execute_sell
        
        logging.info("🔧 Patched execution manager for enhanced paper trading")
    
    def _symbol_to_coin_id(self, symbol: str) -> Optional[str]:
        """Convert trading symbol to coin_id."""
        symbol_map = {
            "BTC/USDT": "bitcoin",
            "ETH/USDT": "ethereum", 
            "SOL/USDT": "solana",
            "ADA/USDT": "cardano",
            "DOT/USDT": "polkadot",
            "LINK/USDT": "chainlink",
            "LTC/USDT": "litecoin",
            "BCH/USDT": "bitcoin-cash",
            "DOGE/USDT": "dogecoin"
        }
        return symbol_map.get(symbol)
    
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
    
    async def run_24_7(self, check_interval: int = 300):
        """Run the enhanced paper trading system 24/7."""
        logging.info(f"🚀 Starting Enhanced 24/7 paper trading (check interval: {check_interval}s)")
        
        self.is_running = True
        self.tracker.execution_manager.auto_trade_enable = True
        
        try:
            while self.is_running:
                try:
                    # Update current prices (mock for paper trading)
                    self._update_mock_prices()
                    
                    # Let the tracker make decisions (now with social media integration)
                    if self.enable_social and self.enhanced_decision_engine:
                        # Use enhanced decision engine
                        await self._make_enhanced_decisions()
                    else:
                        # Use standard decision engine
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
    
    async def _make_enhanced_decisions(self):
        """Make trading decisions using enhanced decision engine with social media."""
        try:
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
                    
                except Exception as e:
                    logging.error(f"Error making enhanced decision for {coin_id}: {e}")
                    
        except Exception as e:
            logging.error(f"Error in enhanced decision making: {e}")
    
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
        """Log system heartbeat with social media metrics."""
        summary = self.simulator.get_performance_summary()
        
        logging.info("💓 ENHANCED HEARTBEAT")
        logging.info(f"   Runtime: {summary['runtime_hours']:.1f} hours")
        logging.info(f"   Portfolio: ${summary['current_value']:,.2f}")
        logging.info(f"   Return: {summary['total_return_pct']:.2f}%")
        logging.info(f"   Trades: {summary['total_trades']}")
        logging.info(f"   Social Trades: {summary['social_trades']} ({summary['social_trade_pct']:.1f}%)")
        logging.info(f"   Trades/hour: {summary['trades_per_hour']:.2f}")
        logging.info(f"   Positions: {len(summary['positions'])}")
        logging.info(f"   Restarts: {self.restart_count}")
        
        # Log social media metrics
        social_metrics = summary.get('social_metrics', {})
        if social_metrics.get('enabled', False):
            logging.info(f"   Social Metrics:")
            logging.info(f"     Avg SMS: {social_metrics['avg_sms']:.3f}")
            logging.info(f"     Avg Sentiment: {social_metrics['avg_sentiment']:.3f}")
            logging.info(f"     Social Trade %: {social_metrics['social_trade_pct']:.1f}%")
    
    def _log_final_summary(self):
        """Log final performance summary with social media metrics."""
        logging.info("\n" + "="*70)
        logging.info("📊 ENHANCED 24/7 PAPER TRADING FINAL SUMMARY")
        logging.info("="*70)
        
        summary = self.simulator.get_performance_summary()
        
        logging.info(f"💰 Initial Cash: ${summary['initial_cash']:,.2f}")
        logging.info(f"💰 Final Value: ${summary['current_value']:,.2f}")
        logging.info(f"📈 Total Return: {summary['total_return_pct']:.2f}%")
        logging.info(f"🔄 Total Trades: {summary['total_trades']}")
        logging.info(f"📱 Social Trades: {summary['social_trades']} ({summary['social_trade_pct']:.1f}%)")
        logging.info(f"🎯 Win Rate: {summary['win_rate_pct']:.1f}%")
        logging.info(f"💵 Net P&L: ${summary['total_pnl']:,.2f}")
        logging.info(f"💵 Cash: ${summary['cash']:,.2f}")
        logging.info(f"📦 Positions: {summary['positions']}")
        logging.info(f"⏱️  Runtime: {summary['runtime_hours']:.1f} hours")
        logging.info(f"📊 Trades/Hour: {summary['trades_per_hour']:.2f}")
        logging.info(f"🔄 Restarts: {self.restart_count}")
        
        # Social media summary
        social_metrics = summary.get('social_metrics', {})
        if social_metrics.get('enabled', False):
            logging.info(f"\n📱 SOCIAL MEDIA METRICS:")
            logging.info(f"   Total Social Trades: {social_metrics['total_social_trades']}")
            logging.info(f"   Social Buy Trades: {social_metrics['social_buy_trades']}")
            logging.info(f"   Social Sell Trades: {social_metrics['social_sell_trades']}")
            logging.info(f"   Average SMS: {social_metrics['avg_sms']:.3f}")
            logging.info(f"   Average Sentiment: {social_metrics['avg_sentiment']:.3f}")
            logging.info(f"   Social Trade Percentage: {social_metrics['social_trade_pct']:.1f}%")
        else:
            logging.info(f"\n📱 SOCIAL MEDIA: Disabled")
        
        logging.info(f"📅 Start Time: {summary['start_time']}")
        logging.info(f"📅 End Time: {summary['current_time']}")
        logging.info("="*70)
    
    def stop(self):
        """Stop the enhanced 24/7 trading system."""
        logging.info("🛑 Stopping Enhanced 24/7 paper trading system")
        self.is_running = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    if 'paper_system' in globals():
        paper_system.stop()
    sys.exit(0)


def main():
    """Main CLI entry point for enhanced 24/7 paper trading."""
    parser = argparse.ArgumentParser(description="Enhanced 24/7 Paper Trading System with Social Media")
    
    parser.add_argument("--config", default="config/paper_24_7.yaml", help="Path to config file")
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Initial cash amount")
    parser.add_argument("--check-interval", type=int, default=300, help="Check interval in seconds (default: 5 minutes)")
    parser.add_argument("--max-restarts", type=int, default=10, help="Maximum restart attempts")
    parser.add_argument("--disable-social", action="store_true", help="Disable social media integration")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Enable quiet mode (minimal logging)")
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    async def run():
        global paper_system
            paper_system = EnhancedPaperTrading24_7(
                args.config, 
                args.initial_cash, 
                enable_social=not args.disable_social,
                verbose=args.verbose,
                quiet=args.quiet
            )
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
