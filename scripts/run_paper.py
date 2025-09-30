#!/usr/bin/env python3
"""
Paper Trading CLI

Command-line interface for running paper trading simulations.
Supports both historical replay and live paper trading modes.
"""

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from paper_trader import (
    PaperBroker, 
    MarketDataAdapter, 
    PaperTradingPersistence,
    PerformanceMetrics,
    ReportGenerator,
    PaperTradingConfig
)
from paper_trader.broker import AbstractBroker
from paper_trader.market_data import MarketTick
from paper_trader.execution import SlippageConfig, FeeConfig, LatencyConfig
from paper_trader.config import load_config_from_env

# Import existing trading system components
from src.tracker.core import CryptoTracker
from src.tracker.execution_manager import ExecutionManager
from src.order_manager.models import OrderRequest, OrderType, TimeInForce


class PaperTradingRunner:
    """Main runner for paper trading simulations."""
    
    def __init__(self, config: PaperTradingConfig):
        self.config = config
        self.broker: Optional[PaperBroker] = None
        self.market_data_adapter: Optional[MarketDataAdapter] = None
        self.persistence: Optional[PaperTradingPersistence] = None
        self.tracker: Optional[CryptoTracker] = None
        self.is_running = False
        
    async def initialize(self):
        """Initialize all components."""
        
        print(f"Initializing paper trading run: {self.config.run_id}")
        
        # Initialize broker
        self.broker = PaperBroker(
            initial_cash=self.config.initial_cash,
            base_currency=self.config.base_currency,
            slippage_config=self.config.slippage_config,
            fee_config=self.config.fee_config,
            latency_config=self.config.latency_config,
            supported_symbols=self.config.market_data_config.symbols
        )
        
        # Initialize market data adapter
        self.market_data_adapter = MarketDataAdapter(self.config.market_data_config)
        
        # Initialize persistence
        self.persistence = PaperTradingPersistence()
        
        # Create run in database
        self.persistence.create_run(
            self.config.run_id,
            self.config.to_dict(),
            self.config.initial_cash
        )
        
        # Initialize existing tracker with paper broker
        await self._setup_tracker()
        
        print("✅ Initialization complete")
    
    async def _setup_tracker(self):
        """Setup the existing tracker to use paper broker."""
        
        # Create a modified config for the tracker
        tracker_config_path = "config/config.yaml"
        
        # Initialize tracker
        self.tracker = CryptoTracker(tracker_config_path)
        
        # Replace the execution manager's broker with our paper broker
        if hasattr(self.tracker.execution_manager, 'paper'):
            self.tracker.execution_manager.paper = self.broker
        else:
            # Create a paper executor that uses our broker
            from src.executor import PaperExecutor
            paper_executor = PaperExecutor()
            paper_executor._broker = self.broker
            self.tracker.execution_manager.paper = paper_executor
        
        # Ensure paper mode is enabled
        self.tracker.execution_manager.auto_trade_mode = "paper"
        self.tracker.execution_manager.auto_trade_enable = True
        self.tracker.execution_manager.paper_place_orders = True
    
    async def run_replay_mode(self):
        """Run in historical replay mode."""
        
        print(f"Starting historical replay mode...")
        print(f"Symbols: {self.config.market_data_config.symbols}")
        print(f"Replay speed: {self.config.market_data_config.replay_speed}x")
        
        # Setup market data callbacks
        self.market_data_adapter.add_data_callback(self._on_market_data)
        
        # Start replay
        await self.market_data_adapter.replay_historical_data(
            symbols=self.config.market_data_config.symbols,
            start_time=self.config.market_data_config.start_time,
            end_time=self.config.market_data_config.end_time
        )
        
        print("✅ Historical replay complete")
    
    async def run_live_mode(self):
        """Run in live paper trading mode."""
        
        print(f"Starting live paper trading mode...")
        print(f"Symbols: {self.config.market_data_config.symbols}")
        
        # Setup market data callbacks
        self.market_data_adapter.add_data_callback(self._on_market_data)
        
        # Start streaming
        await self.market_data_adapter.start_streaming(
            symbols=self.config.market_data_config.symbols
        )
        
        # Keep running until interrupted
        try:
            while self.is_running:
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            print("\n🛑 Stopping live trading...")
            await self.market_data_adapter.stop_streaming()
        
        print("✅ Live trading complete")
    
    def _on_market_data(self, tick: MarketTick):
        """Handle incoming market data."""
        
        # Update broker with market data
        ticker = tick.to_ticker()
        self.broker.update_market_data(tick.symbol, ticker)
        
        # Trigger trading decisions
        self._process_trading_decisions(tick)
        
        # Save account snapshot periodically
        if len(self.broker.portfolio.account_history) % 10 == 0:
            snapshot = self.broker.portfolio.create_account_snapshot({tick.symbol: tick.price})
            self.persistence.save_account_snapshot(snapshot, self.config.run_id)
    
    def _process_trading_decisions(self, tick: MarketTick):
        """Process trading decisions for the current market data."""
        
        # This is where we would integrate with the existing strategy system
        # For now, we'll implement a simple example
        
        # Get current position
        position = self.broker.get_position(tick.symbol)
        
        # Simple strategy: buy on price drops, sell on price increases
        if position is None:
            # No position - consider buying
            if tick.price < tick.high * 0.95:  # 5% below high
                self._place_buy_order(tick.symbol, tick.price)
        else:
            # Have position - consider selling
            if tick.price > position.entry_price * 1.02:  # 2% profit
                self._place_sell_order(tick.symbol, tick.price, position.size)
    
    def _place_buy_order(self, symbol: str, price: float):
        """Place a buy order."""
        
        # Calculate position size (simplified)
        position_size_usd = self.config.initial_cash * self.config.position_size_limit_pct
        quantity = position_size_usd / price
        
        order_request = OrderRequest(
            symbol=symbol,
            side="buy",
            order_type=OrderType.MARKET,
            quantity=quantity,
            strategy_id="paper_trader"
        )
        
        result = self.broker.place_order(order_request)
        
        if result.success:
            print(f"📈 Placed buy order for {symbol}: {quantity:.4f} @ {price:.2f}")
            
            # Save order
            if self.persistence:
                order = self.broker.orders[result.order_id]
                self.persistence.save_order(order, self.config.run_id)
        else:
            print(f"❌ Failed to place buy order for {symbol}: {result.error_message}")
    
    def _place_sell_order(self, symbol: str, price: float, quantity: float):
        """Place a sell order."""
        
        order_request = OrderRequest(
            symbol=symbol,
            side="sell",
            order_type=OrderType.MARKET,
            quantity=quantity,
            strategy_id="paper_trader"
        )
        
        result = self.broker.place_order(order_request)
        
        if result.success:
            print(f"📉 Placed sell order for {symbol}: {quantity:.4f} @ {price:.2f}")
            
            # Save order
            if self.persistence:
                order = self.broker.orders[result.order_id]
                self.persistence.save_order(order, self.config.run_id)
        else:
            print(f"❌ Failed to place sell order for {symbol}: {result.error_message}")
    
    async def run(self):
        """Main run method."""
        
        await self.initialize()
        
        self.is_running = True
        
        try:
            if self.config.mode == "replay":
                await self.run_replay_mode()
            elif self.config.mode == "live":
                await self.run_live_mode()
            else:
                raise ValueError(f"Unsupported mode: {self.config.mode}")
        
        finally:
            await self.finalize()
    
    async def finalize(self):
        """Finalize the run and generate reports."""
        
        print("Finalizing paper trading run...")
        
        # Update run status
        final_equity = self.broker.get_total_equity()
        self.persistence.update_run(
            self.config.run_id,
            end_time=datetime.now(timezone.utc).isoformat(),
            final_equity=final_equity,
            total_trades=len(self.broker.portfolio.trades),
            total_pnl=self.broker.portfolio.net_pnl,
            status="completed"
        )
        
        # Generate reports
        if self.config.generate_reports:
            await self._generate_reports()
        
        print("✅ Finalization complete")
    
    async def _generate_reports(self):
        """Generate performance reports."""
        
        print("Generating reports...")
        
        # Get data
        trades = self.persistence.get_trades(self.config.run_id)
        account_history = self.persistence.get_account_history(self.config.run_id)
        
        # Calculate metrics
        metrics = PerformanceMetrics(trades, account_history, self.config.initial_cash)
        
        # Generate reports
        report_generator = ReportGenerator(metrics, self.config.run_id, self.config.to_dict())
        
        output_dir = Path("data/paper_runs") / self.config.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON report
        if "json" in self.config.report_formats:
            json_file = report_generator.generate_json_report(str(output_dir / "metrics.json"))
            print(f"📊 JSON report: {json_file}")
        
        # HTML report
        if "html" in self.config.report_formats:
            html_file = report_generator.generate_html_report(str(output_dir / "report.html"))
            print(f"📊 HTML report: {html_file}")
        
        # Export data
        if self.config.save_trades:
            csv_files = self.persistence.export_to_csv(self.config.run_id, str(output_dir))
            print(f"📁 Exported data: {list(csv_files.values())}")
        
        # Print summary
        summary = metrics.get_summary()
        print("\n" + "="*50)
        print("PERFORMANCE SUMMARY")
        print("="*50)
        print(f"Total Return: {summary['total_return']:.2f}%")
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Win Rate: {summary['win_rate']:.1f}%")
        print(f"Max Drawdown: {summary['max_drawdown']:.2f}%")
        print(f"Sharpe Ratio: {summary['sharpe_ratio']:.3f}")
        print(f"Net P&L: ${summary['net_pnl']:.2f}")
        print("="*50)


def create_default_config_file(config_path: str):
    """Create a default configuration file."""
    
    config = PaperTradingConfig.create_default_config()
    config.save_to_file(config_path)
    print(f"Created default configuration: {config_path}")


def main():
    """Main CLI entry point."""
    
    parser = argparse.ArgumentParser(description="Paper Trading System")
    
    # Mode selection
    parser.add_argument("--mode", choices=["replay", "live"], default="replay",
                       help="Trading mode (default: replay)")
    
    # Configuration
    parser.add_argument("--config", "-c", default="config/paper.yaml",
                       help="Configuration file path")
    
    parser.add_argument("--run-id", default=None,
                       help="Run ID (default: auto-generated)")
    
    # Data settings
    parser.add_argument("--data", help="Historical data file or directory")
    parser.add_argument("--symbols", nargs="+", help="Trading symbols")
    parser.add_argument("--start-time", help="Start time for replay (YYYY-MM-DD)")
    parser.add_argument("--end-time", help="End time for replay (YYYY-MM-DD)")
    
    # Execution settings
    parser.add_argument("--initial-cash", type=float, default=100000.0,
                       help="Initial cash amount")
    parser.add_argument("--slippage-bps", type=float, default=5.0,
                       help="Slippage in basis points")
    parser.add_argument("--fee-bps", type=float, default=10.0,
                       help="Trading fee in basis points")
    
    # Replay settings
    parser.add_argument("--replay-speed", type=float, default=1.0,
                       help="Replay speed multiplier")
    
    # Output settings
    parser.add_argument("--output-dir", default="data/paper_runs",
                       help="Output directory for results")
    parser.add_argument("--no-reports", action="store_true",
                       help="Skip report generation")
    
    # Utility commands
    parser.add_argument("--create-config", action="store_true",
                       help="Create default configuration file and exit")
    parser.add_argument("--list-runs", action="store_true",
                       help="List previous runs and exit")
    
    args = parser.parse_args()
    
    # Handle utility commands
    if args.create_config:
        create_default_config_file(args.config)
        return
    
    if args.list_runs:
        persistence = PaperTradingPersistence()
        runs = persistence.list_runs()
        if runs:
            print("Previous Paper Trading Runs:")
            print("-" * 80)
            for run in runs:
                print(f"ID: {run['id']}")
                print(f"  Mode: {run['mode']}")
                print(f"  Start: {run['start_time']}")
                print(f"  Status: {run['status']}")
                print(f"  Return: {run['total_pnl']:.2f}")
                print()
        else:
            print("No previous runs found.")
        return
    
    # Load configuration
    try:
        if Path(args.config).exists():
            config = PaperTradingConfig.from_file(args.config)
        else:
            print(f"Configuration file not found: {args.config}")
            print("Creating default configuration...")
            create_default_config_file(args.config)
            config = PaperTradingConfig.from_file(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return 1
    
    # Override with command line arguments
    if args.run_id:
        config.run_id = args.run_id
    else:
        config.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    config.mode = args.mode
    config.initial_cash = args.initial_cash
    
    if args.symbols:
        config.market_data_config.symbols = args.symbols
    
    if args.data:
        config.market_data_config.data_directory = args.data
    
    if args.start_time:
        config.market_data_config.start_time = datetime.fromisoformat(args.start_time)
    
    if args.end_time:
        config.market_data_config.end_time = datetime.fromisoformat(args.end_time)
    
    config.market_data_config.replay_speed = args.replay_speed
    config.slippage_config.base_slippage_bps = args.slippage_bps
    config.fee_config.taker_fee_bps = args.fee_bps
    
    if args.no_reports:
        config.generate_reports = False
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    # Run paper trading
    try:
        runner = PaperTradingRunner(config)
        asyncio.run(runner.run())
        return 0
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
